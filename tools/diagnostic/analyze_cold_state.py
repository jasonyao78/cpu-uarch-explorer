#!/usr/bin/env python3
"""Independent same-code four-state cold injection; signed model counterexamples.

Contract: docs/design/2026-10-10-cold-state-injection.md. This prospective profile
does not replace cold-pair qualification or authorize an N scan. Raw CLI
acceptance is separate from synthetic pure mathematics and model compatibility.
Internal CNTVCT ticks are time, not core cycles; all signed tails are retained.
"""
import argparse
import copy
import json
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.diagnostic import analyze_cold_pair as shared

MODE = 'rob-cold-state'
PROTOCOL = 'docs/design/2026-10-10-cold-state-injection.md'
BUILD = 'docs/reviews/evidence/2026-10-10-cold-state/build.json'
PLAN = 'docs/reviews/evidence/2026-10-10-cold-state/plan.json'
DRIVER = 'tools/diagnostic/run_sm8650_cold_pair.py'
SOURCES = ('probes/diagnostic/rob_cold_pair.c', 'probes/common/perf_group_read.h',
           'probes/common/rob_backing.h')
MASKS = (0, 4096)
MEMBERS = ('P', 'S', 'E')
STATES = ('hot', 'first-cold', 'second-cold', 'cold')
EVENTS = ('0x11', '0x8', '0x3', '0x17', '0x34', '0x37')
THRESHOLDS = {'model_residual_median_abs_max': 2, 'model_residual_abs_q90_max': 3,
              'delta_ticks_median_min': 3, 'single_refill_delta_mean': [.75, 1.25],
              'both_refill_delta_mean': [1.5, 2.5], 'walk_delta_mean_abs_max': .1,
              'hot_refill_mean_max': .25, 'empty_delta_median_abs_max': 1,
              'empty_delta_abs_q90_max': 2, 'empty_count_delta_abs_mean_max': .5}
_require, _fields, _same = shared._require, shared._fields, shared._same
_sha, _git_blob = shared._sha, shared._git_blob


def trial_order(epoch, trial):
    """Independent fixed 48-cell left rotation/reversal; no runtime matrix knob."""
    _require(type(epoch) is int and epoch in (0, 1) and type(trial) is int and 0 <= trial < 64,
             'invalid four-state epoch/trial')
    base = [(m, s, member, state) for m in MASKS for s in (0, 1)
            for member in MEMBERS for state in STATES]
    offset = trial % 48
    sequence = base[offset:] + base[:offset]
    return sequence[::-1] if (epoch + trial) % 2 else sequence


def audit_cells(run):
    """Typed complete 6144-window identity/order before any model mathematics.

Pure input uses counts, not metrics. This helper cannot establish source,
actual backing, generated code or target provenance; audit_raw must do those.
"""
    _require(type(run) is dict and run.get('mode') == MODE and
             type(run.get('processes')) is int and run['processes'] == 2,
             'four-state mode/process mismatch')
    rows = run.get('rows')
    _require(type(rows) is list and len(rows) == 6144, 'four-state complete window coverage mismatch')
    cells, identities = {}, []
    for row in rows:
        _require(type(row) is dict, 'invalid four-state row')
        epoch, trial, mask, swap, member, state = (row.get(k) for k in
                                                  ('epoch', 'trial', 'mask', 'swap', 'member', 'state'))
        _require(type(epoch) is int and epoch in (0, 1) and type(trial) is int and 0 <= trial < 64 and
                 type(mask) is int and mask in MASKS and type(swap) is int and swap in (0, 1) and
                 type(member) is str and member in MEMBERS and type(state) is str and state in STATES,
                 'invalid four-state cell identity')
        key = epoch, trial, mask, swap, member, state
        _require(key not in cells, 'duplicate four-state cell identity')
        _require(type(row.get('ticks')) is int and 0 <= row['ticks'] < 2**64, 'invalid internal ticks')
        counts = row.get('counts')
        _require(type(counts) is dict and set(counts) == set(EVENTS) and
                 all(type(v) is int and 0 <= v < 2**64 for v in counts.values()) and counts['0x11'] > 0,
                 'invalid four-state PMU event counts')
        _require(29 <= counts['0x8'] <= 1029, 'four-state retired count outside frozen range')
        cells[key] = row
        identities.append(key)
    expected = [(e, t, *identity) for e in (0, 1) for t in range(64) for identity in trial_order(e, t)]
    _require(identities == expected, 'four-state cell coverage/order mismatch')
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
    """Per-trial same-code residuals; E is only a sentinel, never compensation.

P: T11-max(T10,T01). S: T11-T10-T01+T00. No clipping, pooling,
MAD acceptance gate, old-gate rescue or N permission. Counts stay raw/signed.
"""
    cells = audit_cells(run)
    candidates = []
    for mask in MASKS:
        for epoch in (0, 1):
            for swap in (0, 1):
                members = {}
                for member in MEMBERS:
                    members[member] = {}
                    hot = [cells[epoch,t,mask,swap,member,'hot'] for t in range(64)]
                    for state in STATES:
                        rows = [cells[epoch,t,mask,swap,member,state] for t in range(64)]
                        ticks = [r['ticks'] for r in rows]
                        delta = [r['ticks']-h['ticks'] for r,h in zip(rows,hot)]
                        counts = {event:[r['counts'][event] for r in rows] for event in EVENTS}
                        cd = {event:[r['counts'][event]-h['counts'][event] for r,h in zip(rows,hot)] for event in EVENTS}
                        members[member][state] = {'ticks':describe(ticks),'delta_ticks':describe(delta),
                            'counts':counts,'count_means':{k:st.mean(v) for k,v in counts.items()},
                            'count_deltas':cd,'count_delta_means':{k:st.mean(v) for k,v in cd.items()}}
                residuals = {}
                for member in ('P','S'):
                    v = members[member]
                    hot,first,second,both = [v[state]['ticks']['values'] for state in STATES]
                    values = ([b-max(f,s) for b,f,s in zip(both,first,second)] if member=='P'
                              else [b-f-s+h for b,f,s,h in zip(both,first,second,hot)])
                    residuals[member] = describe(values)
                stimulus, model_gates = [], []
                def gate(destination,name,value,lower=None,upper=None):
                    destination.append({'gate':name,'value':value,'lower':lower,'upper':upper,
                        'passed':(lower is None or value>=lower) and (upper is None or value<=upper)})
                for member in ('P','S'):
                    for event,label in (('0x17','L2'),('0x37','LL')):
                        gate(stimulus,f'{member}.hot.{label}_count_mean',members[member]['hot']['count_means'][event],upper=THRESHOLDS['hot_refill_mean_max'])
                    for state in STATES[1:]:
                        v=members[member][state]
                        gate(stimulus,f'{member}.{state}.delta_ticks_median',v['delta_ticks']['median'],lower=THRESHOLDS['delta_ticks_median_min'])
                        for event,label in (('0x17','L2'),('0x37','LL')):
                            bounds=THRESHOLDS['both_refill_delta_mean' if state=='cold' else 'single_refill_delta_mean']
                            gate(stimulus,f'{member}.{state}.{label}_count_delta_mean',v['count_delta_means'][event],*bounds)
                        gate(stimulus,f'{member}.{state}.walk_count_delta_abs_mean',abs(v['count_delta_means']['0x34']),upper=THRESHOLDS['walk_delta_mean_abs_max'])
                    v=residuals[member]
                    gate(model_gates,f'{member}.residual_abs_median',abs(v['median']),upper=THRESHOLDS['model_residual_median_abs_max'])
                    gate(model_gates,f'{member}.residual_abs_q90',v['abs_q90'],upper=THRESHOLDS['model_residual_abs_q90_max'])
                for state in STATES[1:]:
                    v=members['E'][state]
                    gate(stimulus,f'E.{state}.delta_ticks_abs_median',abs(v['delta_ticks']['median']),upper=THRESHOLDS['empty_delta_median_abs_max'])
                    gate(stimulus,f'E.{state}.delta_ticks_abs_q90',v['delta_ticks']['abs_q90'],upper=THRESHOLDS['empty_delta_abs_q90_max'])
                    for event,label in (('0x3','L1'),('0x17','L2'),('0x37','LL'),('0x34','walk')):
                        gate(stimulus,f'E.{state}.{label}_count_delta_abs_mean',abs(v['count_delta_means'][event]),upper=THRESHOLDS['empty_count_delta_abs_mean_max'])
                sp,mc=all(g['passed'] for g in stimulus),all(g['passed'] for g in model_gates)
                candidates.append({'epoch':epoch,'mask':mask,'swap':swap,'members':members,'residuals':residuals,
                    'stimulus_gates':stimulus,'model_gates':model_gates,'failed_gates':[g['gate'] for g in stimulus+model_gates if not g['passed']],
                    'stimulus_passed':sp,'model_compatible':mc,'compatible_with_stimulus':sp and mc})
    return {'mode':MODE,'protocol_path':PROTOCOL,'processes':2,'windows':6144,
            'thresholds':copy.deepcopy(THRESHOLDS),'candidates':candidates,
            'all_stimulus_passed':all(c['stimulus_passed'] for c in candidates),
            'all_models_compatible':all(c['model_compatible'] for c in candidates),
            'n_scan_authorized':False,'empty_subtracted_from_counts':False,
            'tick_unit':'CNTVCT ticks; no conversion to core cycles',
            'naming_limit':'仅N0同码形四状态激励/可加性诊断；不认证DRAM、ROB、原pair资格或N扫描'}


def registered_plan():
    """Independent immutable four-state profile; legacy paths/matrix cannot relabel it."""
    return {'mode': MODE, 'processes': 2, 'windows': 6144, 'trials': 64, 'cells_per_trial': 48,
            'masks': [0, 4096], 'swaps': [0, 1], 'members': list(MEMBERS), 'states': list(STATES), 'state_cold_slot_masks': [0,1,2,3],
            'warmup_calls': 128, 'n': 0, 'mapping_bytes': 8192,
            'conditions': [{'name': f'epoch-{e}', 'args': ['--epoch', str(e), '-n', '0', '--trials', '64',
                            '--pin', '7', '--pmu-type', '8', '--single-cold']} for e in (0, 1)]}


def generated_code(mask, member):
    """P/S/E keep the independent original 29-word ABI expectation unchanged."""
    _require(type(mask) is int and mask in MASKS and type(member) is str and member in MEMBERS,
             'unregistered four-state code identity')
    return shared.generated_code(mask,member)


def _config(epoch):
    """Exact real producer version3 N0 configuration, not derived from a raw label."""
    return {'type': 'config', 'version': 3, 'probe': 'rob-cold-state', 'n': 0, 'trials': 64, 'epoch': epoch,
            'matrix_cells_per_trial': 48, 'windows': 3072, 'memory_bytes': 8192, 'mapping_alignment': 8192,
            'node_offsets': [0, 4096], 'masks': [0, 4096], 'members': list(MEMBERS), 'states': list(STATES), 'state_cold_slot_masks': [0,1,2,3],
            'warmup_calls': 128, 'internal_clock': 'cntvct_el0', 'code_bytes': 116, 'kernel_instructions': 29,
            'pin': 7, 'pmu_type': 8, 'events': [17, 8, 3, 23, 52, 55], 'exclude_kernel': True,
            'exclude_hv': True, 'backing_requested': '4k', 'single_cold_requested': True}


def _process(records, epoch):
    """Require real config/runtime/3072 round/final layout and typed PMU timing."""
    _require(type(records) is list and len(records) == 3075, 'four-state complete record count mismatch')
    config, runtime, *tail = records
    rounds, final = tail[:-1], tail[-1]
    _require(_same(config, _config(epoch)), 'actual four-state config mismatch')
    _fields(runtime, {'type': 'runtime', 'cpu': 7, 'cache_line_bytes': 64, 'mapping_alignment_verified': True,
                      'raw_self_pointer_verified': True, 'code_address_mod64': 0, 'cache_maintenance_completed': True},
            'actual four-state runtime/capability mismatch')
    frequency, ids = runtime.get('cntfrq_hz'), runtime.get('event_ids')
    _require(type(frequency) is int and 0 < frequency <= 1000000000, 'invalid actual CNTFRQ')
    _require(type(ids) is list and len(ids) == 6 and all(type(v) is int and 0 < v < 2**64 for v in ids) and
             len(set(ids)) == 6, 'actual four-state PMU ID mismatch')
    shared._backing(runtime.get('initial_backing'))
    _fields(final, {'type': 'backing-final'}, 'actual four-state final backing record missing')
    shared._backing(final.get('backing'))
    normalized = []
    for row, identity in zip(rounds, [(t, *cell) for t in range(64) for cell in trial_order(epoch, t)]):
        trial, mask, swap, member, state = identity
        expected = dict(epoch=epoch, trial=trial, mask=mask, swap=swap, member=member, state=state)
        _fields(row, dict(type='round', **expected), 'actual four-state cell/order mismatch')
        _require(all(type(row.get(k)) is int and 0 < row[k] < 2**64 for k in ('enabled', 'running')) and
                 row['enabled'] == row['running'], 'actual four-state PMU timing/mux mismatch')
        normalized.append(dict(**expected, ticks=row.get('ticks'), counts=row.get('metrics')))
    return config, runtime, final, rounds, normalized


def audit_raw(path):
    """Complete target/source/launch/plan/code/environment chain before diagnosis.

Generic original environment/backing helpers are reused without changing old
consumer or old gates. Four-state identities, code, config and matrix are new
independent expectations. Partial/stopped batches never produce model artifacts.
"""
    path = Path(path)
    manifest_blob = (path / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_blob)
    _fields(manifest, {'mode': MODE, 'status': 'complete', 'target': 'redmi-k70pro-01',
                      'midr': '0x410fd821', 'base_page_bytes': 4096, 'protocol_path': PROTOCOL,
                      'build_evidence_path': BUILD, 'plan_path': PLAN}, 'complete four-state launch identity mismatch')
    plan = registered_plan()
    _require(_same(manifest.get('conditions'), plan['conditions']), 'four-state manifest matrix mismatch')
    entries = manifest.get('results')
    _require(type(entries) is list and [e.get('name') for e in entries] == ['epoch-0', 'epoch-1'],
             'four-state process coverage/order mismatch')
    launch, source = manifest['source_head'], manifest['binary_source_head']
    driver = (path / 'driver.py').read_bytes()
    _require(_sha(driver) == manifest['driver_sha256'] == _sha(_git_blob(launch, DRIVER)), 'four-state driver binding mismatch')
    protocol_blob, build_blob, plan_blob = (_git_blob(launch, rel) for rel in (PROTOCOL, BUILD, PLAN))
    _require(_sha(protocol_blob) == manifest['protocol_sha256'], 'four-state protocol binding mismatch')
    _require(_sha(build_blob) == manifest['build_evidence_sha256'], 'four-state build binding mismatch')
    build = json.loads(build_blob)
    _require(build['source_commit'] == source and build['binaries']['rob_cold_pair'] == manifest['binary_sha256'],
             'four-state binary/source binding mismatch')
    _require(set(build['source_sha256']) == set(SOURCES) and _same(manifest.get('source_sha256'), build['source_sha256']),
             'four-state declared source coverage mismatch')
    for rel, digest in build['source_sha256'].items():
        _require(_sha(_git_blob(source, rel)) == digest == _sha(_git_blob(launch, rel)), 'four-state source blob binding mismatch')
    _require(build['plan_path'] == PLAN and _sha(plan_blob) == build['plan_sha256'] == manifest['plan_sha256'] and
             _same(json.loads(plan_blob), plan), 'four-state frozen plan binding mismatch')
    environment = shared._environment(path, launch, plan['conditions'])
    rows, processes = [], []
    for epoch, entry in enumerate(entries):
        name = entry['name']
        _fields(entry, {'exit_code': 0, 'timed_out': False}, 'four-state process failure')
        _require((path / (name + '.stderr.log')).read_bytes() == b'', 'unexpected four-state stderr')
        stdout = (path / (name + '.stdout.jsonl')).read_bytes()
        _require(_sha(stdout) == entry['stdout_sha256'], 'four-state stdout digest mismatch')
        config, runtime, final, rounds, normalized = _process([json.loads(line) for line in stdout.splitlines()], epoch)
        exports = entry.get('generated_code')
        keys = {f'm{mask}-{member}' for mask in MASKS for member in MEMBERS}
        _require(type(exports) is dict and set(exports) == keys, 'four-state six code export coverage mismatch')
        code_shas = {}
        for mask in MASKS:
            for member in MEMBERS:
                key = f'm{mask}-{member}'; exported = exports[key]
                code = (path / (name + '-' + key + '.bin')).read_bytes()
                expected = dict(config, export={'mask': mask, 'member': member})
                _require(code == generated_code(mask, member) and _sha(code) == exported['sha256'] and
                         _same(exported['config'], expected), 'four-state code/config export binding mismatch')
                code_shas[key] = _sha(code)
        rows.extend(normalized)
        processes.append({'condition': name, 'stdout_sha256': _sha(stdout), 'actual_config': config,
                          'actual_runtime': runtime, 'final_backing': final, 'generated_code_sha256': code_shas,
                          'cntvct_tick_ns': 1000000000 / runtime['cntfrq_hz'], 'windows': rounds})
    run = {'mode': MODE, 'processes': 2, 'windows': 6144, 'rows': rows, 'raw_directory': path.name,
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
    print(json.dumps({'technical_passed': True, 'windows': 6144,
                      'stimulus_passed_cells': sum(c['stimulus_passed'] for c in result['candidates']),
                      'model_compatible_cells': sum(c['model_compatible'] for c in result['candidates']),
                      'n_scan_authorized': False}))


if __name__ == '__main__':
    main()
