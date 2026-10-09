#!/usr/bin/env python3
"""Independent N0 singleton excitation and serial/parallel model diagnosis.

Contract: docs/design/2026-10-10-cold-load-model.md. This prospective profile
does not replace cold-pair qualification or authorize an N scan. Raw CLI
acceptance is separate from synthetic pure mathematics and model compatibility.
Internal CNTVCT ticks are time, not core cycles; all signed tails are retained.
"""
import argparse
import copy
import json
from pathlib import Path
import statistics as st
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.diagnostic import analyze_cold_pair as shared

MODE = 'rob-cold-load-model'
PROTOCOL = 'docs/design/2026-10-10-cold-load-model.md'
BUILD = 'docs/reviews/evidence/2026-10-10-cold-load-model/build.json'
PLAN = 'docs/reviews/evidence/2026-10-10-cold-load-model/plan.json'
DRIVER = 'tools/diagnostic/run_sm8650_cold_pair.py'
SOURCES = ('probes/diagnostic/rob_cold_pair.c', 'probes/common/perf_group_read.h',
           'probes/common/rob_backing.h')
MASKS = (0, 4096)
MEMBERS = ('P', 'S', 'E', 'A', 'B')
EVENTS = ('0x11', '0x8', '0x3', '0x17', '0x34', '0x37')
THRESHOLDS = {'model_residual_median_abs_max': 2, 'model_residual_abs_q90_max': 3,
              'singleton_delta_ticks_median_min': 3, 'singleton_delta_mad_over_median_max': .2,
              'singleton_refill_delta_mean': [.75, 1.25], 'singleton_walk_delta_mean_abs_max': .1}
_require, _fields, _same = shared._require, shared._fields, shared._same
_sha, _git_blob = shared._sha, shared._git_blob


def trial_order(epoch, trial):
    """Independent fixed 40-cell left rotation/reversal; no runtime matrix knob."""
    _require(type(epoch) is int and epoch in (0, 1) and type(trial) is int and 0 <= trial < 64,
             'invalid singleton epoch/trial')
    base = [(m, s, member, state) for m in MASKS for s in (0, 1)
            for member in MEMBERS for state in ('hot', 'cold')]
    offset = trial % 40
    sequence = base[offset:] + base[:offset]
    return sequence[::-1] if (epoch + trial) % 2 else sequence


def audit_cells(run):
    """Typed complete 5120-window identity/order before any model mathematics.

Pure input uses counts, not metrics. This helper cannot establish source,
actual backing, generated code or target provenance; audit_raw must do those.
"""
    _require(type(run) is dict and run.get('mode') == MODE and
             type(run.get('processes')) is int and run['processes'] == 2,
             'singleton mode/process mismatch')
    rows = run.get('rows')
    _require(type(rows) is list and len(rows) == 5120, 'singleton complete window coverage mismatch')
    cells, identities = {}, []
    for row in rows:
        _require(type(row) is dict, 'invalid singleton row')
        epoch, trial, mask, swap, member, state = (row.get(k) for k in
                                                  ('epoch', 'trial', 'mask', 'swap', 'member', 'state'))
        _require(type(epoch) is int and epoch in (0, 1) and type(trial) is int and 0 <= trial < 64 and
                 type(mask) is int and mask in MASKS and type(swap) is int and swap in (0, 1) and
                 type(member) is str and member in MEMBERS and type(state) is str and state in ('hot', 'cold'),
                 'invalid singleton cell identity')
        key = epoch, trial, mask, swap, member, state
        _require(key not in cells, 'duplicate singleton cell identity')
        _require(type(row.get('ticks')) is int and 0 <= row['ticks'] < 2**64, 'invalid internal ticks')
        counts = row.get('counts')
        _require(type(counts) is dict and set(counts) == set(EVENTS) and
                 all(type(v) is int and 0 <= v < 2**64 for v in counts.values()) and counts['0x11'] > 0,
                 'invalid singleton PMU event counts')
        _require(29 <= counts['0x8'] <= 1029, 'singleton retired count outside frozen range')
        cells[key] = row
        identities.append(key)
    expected = [(e, t, *identity) for e in (0, 1) for t in range(64) for identity in trial_order(e, t)]
    _require(identities == expected, 'singleton cell coverage/order mismatch')
    return cells


def describe(values):
    """Signed residuals with unscaled MAD, signed Type7 q10/q90 and absolute q90."""
    _require(type(values) is list and bool(values) and all(type(v) is int for v in values),
             'invalid model residual values')
    median = st.median(values)
    return {'values': values, 'median': median, 'mad': st.median(abs(v - median) for v in values),
            'q10': shared.linear_quantile(values, .1), 'q90': shared.linear_quantile(values, .9),
            'abs_q90': shared.linear_quantile([abs(v) for v in values], .9)}


def analyze(run):
    """Separate singleton excitation from each-state model compatibility.

For every trial/state P predicts max(A,B); S predicts A+B-E. Only then form
cold-hot residual differences. Gates apply to each state, not just differences.
E appears in the serial tick model only and is never subtracted from counts.
Cells are independent; even compatible models grant no old qualification/N scan.
"""
    cells = audit_cells(run)
    candidates = []
    for mask in MASKS:
        for epoch in (0, 1):
            for swap in (0, 1):
                members = {m: shared._member(cells, epoch, mask, swap, m) for m in MEMBERS}
                predictions, residuals = {}, {}
                for member in ('P', 'S'):
                    predictions[member], raw = {}, {}
                    for state in ('hot', 'cold'):
                        a, b, e = (members[m][state + '_ticks'] for m in ('A', 'B', 'E'))
                        prediction = ([max(x, y) for x, y in zip(a, b)] if member == 'P'
                                      else [x + y - z for x, y, z in zip(a, b, e)])
                        predictions[member][state] = prediction
                        raw[state] = [observed - predicted for observed, predicted in
                                      zip(members[member][state + '_ticks'], prediction)]
                    raw['delta'] = [cold - hot for cold, hot in zip(raw['cold'], raw['hot'])]
                    residuals[member] = {state: describe(values) for state, values in raw.items()}
                excitation, model_gates = [], []

                def gate(destination, name, value, lower=None, upper=None):
                    destination.append({'gate': name, 'value': value, 'lower': lower, 'upper': upper,
                                        'passed': value is not None and (lower is None or value >= lower) and
                                                  (upper is None or value <= upper)})

                for member in ('A', 'B'):
                    values = members[member]
                    gate(excitation, f'{member}.delta_ticks_median', values['delta_ticks_median'],
                         lower=THRESHOLDS['singleton_delta_ticks_median_min'])
                    gate(excitation, f'{member}.delta_mad_over_median', values['delta_mad_over_median'],
                         upper=THRESHOLDS['singleton_delta_mad_over_median_max'])
                    for event, label in (('0x17', 'L2'), ('0x37', 'LL')):
                        gate(excitation, f'{member}.{label}_count_delta_mean', values['count_delta_means'][event],
                             *THRESHOLDS['singleton_refill_delta_mean'])
                    gate(excitation, f'{member}.datawalk_count_delta_mean', abs(values['count_delta_means']['0x34']),
                         upper=THRESHOLDS['singleton_walk_delta_mean_abs_max'])
                for member in ('P', 'S'):
                    for state in ('hot', 'cold'):
                        values = residuals[member][state]
                        gate(model_gates, f'{member}.{state}.residual_abs_median', abs(values['median']),
                             upper=THRESHOLDS['model_residual_median_abs_max'])
                        gate(model_gates, f'{member}.{state}.residual_abs_q90', values['abs_q90'],
                             upper=THRESHOLDS['model_residual_abs_q90_max'])
                all_gates = excitation + model_gates
                excitation_passed = all(g['passed'] for g in excitation)
                compatible = all(g['passed'] for g in model_gates)
                candidates.append({'epoch': epoch, 'mask': mask, 'swap': swap, 'members': members,
                                   'predictions': predictions, 'residuals': residuals,
                                   'excitation_gates': excitation, 'model_gates': model_gates,
                                   'failed_gates': [g['gate'] for g in all_gates if not g['passed']],
                                   'excitation_passed': excitation_passed, 'model_compatible': compatible,
                                   'compatible_with_excitation': excitation_passed and compatible})
    return {'mode': MODE, 'protocol_path': PROTOCOL, 'processes': 2, 'windows': 5120,
            'thresholds': copy.deepcopy(THRESHOLDS), 'candidates': candidates,
            'all_excitation_passed': all(c['excitation_passed'] for c in candidates),
            'all_models_compatible': all(c['model_compatible'] for c in candidates),
            'all_compatible_with_excitation': all(c['compatible_with_excitation'] for c in candidates),
            'n_scan_authorized': False, 'empty_subtracted_from_counts': False,
            'tick_unit': 'CNTVCT ticks; no conversion to core cycles',
            'naming_limit': '仅N0单load激励与理想串并模型诊断；不认证DRAM、ROB、原pair资格或N扫描'}


def registered_plan():
    """Independent immutable singleton profile; legacy paths/matrix cannot relabel it."""
    return {'mode': MODE, 'processes': 2, 'windows': 5120, 'trials': 64, 'cells_per_trial': 40,
            'masks': [0, 4096], 'swaps': [0, 1], 'members': list(MEMBERS), 'states': ['hot', 'cold'],
            'warmup_calls': 128, 'n': 0, 'mapping_bytes': 8192,
            'conditions': [{'name': f'epoch-{e}', 'args': ['--epoch', str(e), '-n', '0', '--trials', '64',
                            '--pin', '7', '--pmu-type', '8', '--singletons']} for e in (0, 1)]}


def generated_code(mask, member):
    """All 29 little-endian words, with independent slot/register/ABI expectations."""
    _require(type(mask) is int and mask in MASKS and type(member) is str and member in MEMBERS,
             'unregistered singleton code identity')
    slots = {'P': [0xf9400000, 0xca0c0000, 0xf9400021, 0xca0c0021],
             'S': [0xf9400000, 0xca0c0000, 0xf9400000, 0xca0c0000],
             'E': [0xd503201f] * 4,
             'A': [0xf9400000, 0xca0c0000, 0xd503201f, 0xd503201f],
             'B': [0xd503201f, 0xd503201f, 0xf9400021, 0xca0c0021]}
    words = [0xd280000c | (mask << 5), 0xf2a0000c, 0xf2c0000c, 0xf2e0000c] + [0xd503201f] * 12
    words += [0xd5033f9f, 0xd5033fdf, 0xd53be04d, 0xd5033fdf] + slots[member]
    words += [0xd5033f9f, 0xd5033fdf, 0xd53be04e, 0xcb0d01c0, 0xd65f03c0]
    return struct.pack('<29I', *words)


def _config(epoch):
    """Exact real producer version2 N0 configuration, not derived from a raw label."""
    return {'type': 'config', 'version': 2, 'probe': 'rob-load-model', 'n': 0, 'trials': 64, 'epoch': epoch,
            'matrix_cells_per_trial': 40, 'windows': 2560, 'memory_bytes': 8192, 'mapping_alignment': 8192,
            'node_offsets': [0, 4096], 'masks': [0, 4096], 'members': list(MEMBERS), 'states': ['hot', 'cold'],
            'warmup_calls': 128, 'internal_clock': 'cntvct_el0', 'code_bytes': 116, 'kernel_instructions': 29,
            'pin': 7, 'pmu_type': 8, 'events': [17, 8, 3, 23, 52, 55], 'exclude_kernel': True,
            'exclude_hv': True, 'backing_requested': '4k', 'singletons_requested': True}


def _process(records, epoch):
    """Require real config/runtime/2560 round/final layout and typed PMU timing."""
    _require(type(records) is list and len(records) == 2563, 'singleton complete record count mismatch')
    config, runtime, *tail = records
    rounds, final = tail[:-1], tail[-1]
    _require(_same(config, _config(epoch)), 'actual singleton config mismatch')
    _fields(runtime, {'type': 'runtime', 'cpu': 7, 'cache_line_bytes': 64, 'mapping_alignment_verified': True,
                      'raw_self_pointer_verified': True, 'code_address_mod64': 0, 'cache_maintenance_completed': True},
            'actual singleton runtime/capability mismatch')
    frequency, ids = runtime.get('cntfrq_hz'), runtime.get('event_ids')
    _require(type(frequency) is int and 0 < frequency <= 1000000000, 'invalid actual CNTFRQ')
    _require(type(ids) is list and len(ids) == 6 and all(type(v) is int and 0 < v < 2**64 for v in ids) and
             len(set(ids)) == 6, 'actual singleton PMU ID mismatch')
    shared._backing(runtime.get('initial_backing'))
    _fields(final, {'type': 'backing-final'}, 'actual singleton final backing record missing')
    shared._backing(final.get('backing'))
    normalized = []
    for row, identity in zip(rounds, [(t, *cell) for t in range(64) for cell in trial_order(epoch, t)]):
        trial, mask, swap, member, state = identity
        expected = dict(epoch=epoch, trial=trial, mask=mask, swap=swap, member=member, state=state)
        _fields(row, dict(type='round', **expected), 'actual singleton cell/order mismatch')
        _require(all(type(row.get(k)) is int and 0 < row[k] < 2**64 for k in ('enabled', 'running')) and
                 row['enabled'] == row['running'], 'actual singleton PMU timing/mux mismatch')
        normalized.append(dict(**expected, ticks=row.get('ticks'), counts=row.get('metrics')))
    return config, runtime, final, rounds, normalized


def audit_raw(path):
    """Complete target/source/launch/plan/code/environment chain before diagnosis.

Generic original environment/backing helpers are reused without changing old
consumer or old gates. Singleton identities, code, config and matrix are new
independent expectations. Partial/stopped batches never produce model artifacts.
"""
    path = Path(path)
    manifest_blob = (path / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_blob)
    _fields(manifest, {'mode': MODE, 'status': 'complete', 'target': 'redmi-k70pro-01',
                      'midr': '0x410fd821', 'base_page_bytes': 4096, 'protocol_path': PROTOCOL,
                      'build_evidence_path': BUILD, 'plan_path': PLAN}, 'complete singleton launch identity mismatch')
    plan = registered_plan()
    _require(_same(manifest.get('conditions'), plan['conditions']), 'singleton manifest matrix mismatch')
    entries = manifest.get('results')
    _require(type(entries) is list and [e.get('name') for e in entries] == ['epoch-0', 'epoch-1'],
             'singleton process coverage/order mismatch')
    launch, source = manifest['source_head'], manifest['binary_source_head']
    driver = (path / 'driver.py').read_bytes()
    _require(_sha(driver) == manifest['driver_sha256'] == _sha(_git_blob(launch, DRIVER)), 'singleton driver binding mismatch')
    protocol_blob, build_blob, plan_blob = (_git_blob(launch, rel) for rel in (PROTOCOL, BUILD, PLAN))
    _require(_sha(protocol_blob) == manifest['protocol_sha256'], 'singleton protocol binding mismatch')
    _require(_sha(build_blob) == manifest['build_evidence_sha256'], 'singleton build binding mismatch')
    build = json.loads(build_blob)
    _require(build['source_commit'] == source and build['binaries']['rob_cold_pair'] == manifest['binary_sha256'],
             'singleton binary/source binding mismatch')
    _require(set(build['source_sha256']) == set(SOURCES) and _same(manifest.get('source_sha256'), build['source_sha256']),
             'singleton declared source coverage mismatch')
    for rel, digest in build['source_sha256'].items():
        _require(_sha(_git_blob(source, rel)) == digest == _sha(_git_blob(launch, rel)), 'singleton source blob binding mismatch')
    _require(build['plan_path'] == PLAN and _sha(plan_blob) == build['plan_sha256'] == manifest['plan_sha256'] and
             _same(json.loads(plan_blob), plan), 'singleton frozen plan binding mismatch')
    environment = shared._environment(path, launch, plan['conditions'])
    rows, processes = [], []
    for epoch, entry in enumerate(entries):
        name = entry['name']
        _fields(entry, {'exit_code': 0, 'timed_out': False}, 'singleton process failure')
        _require((path / (name + '.stderr.log')).read_bytes() == b'', 'unexpected singleton stderr')
        stdout = (path / (name + '.stdout.jsonl')).read_bytes()
        _require(_sha(stdout) == entry['stdout_sha256'], 'singleton stdout digest mismatch')
        config, runtime, final, rounds, normalized = _process([json.loads(line) for line in stdout.splitlines()], epoch)
        exports = entry.get('generated_code')
        keys = {f'm{mask}-{member}' for mask in MASKS for member in MEMBERS}
        _require(type(exports) is dict and set(exports) == keys, 'singleton ten code export coverage mismatch')
        code_shas = {}
        for mask in MASKS:
            for member in MEMBERS:
                key = f'm{mask}-{member}'; exported = exports[key]
                code = (path / (name + '-' + key + '.bin')).read_bytes()
                expected = dict(config, export={'mask': mask, 'member': member})
                _require(code == generated_code(mask, member) and _sha(code) == exported['sha256'] and
                         _same(exported['config'], expected), 'singleton code/config export binding mismatch')
                code_shas[key] = _sha(code)
        rows.extend(normalized)
        processes.append({'condition': name, 'stdout_sha256': _sha(stdout), 'actual_config': config,
                          'actual_runtime': runtime, 'final_backing': final, 'generated_code_sha256': code_shas,
                          'cntvct_tick_ns': 1000000000 / runtime['cntfrq_hz'], 'windows': rounds})
    run = {'mode': MODE, 'processes': 2, 'windows': 5120, 'rows': rows, 'raw_directory': path.name,
           'source_branch': manifest['source_branch'], 'source_head': launch, 'binary_source_head': source,
           'binary_sha256': manifest['binary_sha256'], 'max_cpu_c_range': environment['max_cpu_c_range'],
           'cntfrq_hz_by_epoch': [p['actual_runtime']['cntfrq_hz'] for p in processes]}
    audit_cells(run)
    technical = {'passed': True, 'raw_directory': path.name, 'manifest_sha256': _sha(manifest_blob),
                 'source_head': launch, 'binary_source_head': source, 'binary_sha256': manifest['binary_sha256'],
                 'source_sha256': build['source_sha256'], 'driver_sha256': _sha(driver),
                 'build_evidence_path': BUILD, 'build_evidence_sha256': _sha(build_blob),
                 'protocol_path': PROTOCOL, 'protocol_sha256': _sha(protocol_blob),
                 'plan_path': PLAN, 'plan_sha256': _sha(plan_blob), 'registered_plan': plan,
                 **environment, 'processes': processes,
                 'all_raw_sha256': {f.name: _sha(f.read_bytes()) for f in sorted(path.iterdir()) if f.is_file()}}
    return {'run': run, 'technical_acceptance': technical}


def main(argv=None):
    """Audit all raw before publishing; incompatible/unexcited models keep all data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('--summary-output', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    audited = audit_raw(args.raw)
    result = analyze(audited['run'])
    result.update(data_origin='device-raw', technical_acceptance=audited['technical_acceptance'])
    rblob = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    sblob = json.dumps({'runs': [audited['run']]}, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    if args.summary_output:
        args.summary_output.write_text(sblob)
    args.output.write_text(rblob)
    print(json.dumps({'technical_passed': True, 'windows': 5120,
                      'excitation_passed_cells': sum(c['excitation_passed'] for c in result['candidates']),
                      'model_compatible_cells': sum(c['model_compatible'] for c in result['candidates']),
                      'n_scan_authorized': False}))


if __name__ == '__main__':
    main()
