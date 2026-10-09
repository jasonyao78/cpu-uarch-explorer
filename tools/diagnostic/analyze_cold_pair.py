#!/usr/bin/env python3
"""single-shot双冷line的独立资格数学与完整身份审核。

唯一契约：docs/design/2026-10-09-cold-pair-qualification.md。新机制
不使用旧c93长循环门；ticks来自CNTVCT，不命名核心cycles或DRAM。
pure输入是归一化窗口，合成测试只证明软件；设备CLI另须真实producer
raw/source/actual审核。所有冷热差可负，E是哨兵而非自动扣除项。
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import statistics as st
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

MODE = 'rob-cold-pair-qualify'
PROTOCOL = 'docs/design/2026-10-09-cold-pair-qualification.md'
BUILD = 'docs/reviews/evidence/2026-10-09-cold-pair/build.json'
PLAN = 'docs/reviews/evidence/2026-10-09-cold-pair/plan.json'
DRIVER = 'tools/diagnostic/run_sm8650_cold_pair.py'
PROFILE = 'configs/platforms/redmi-k70pro-01.json'
SOURCES = ('probes/diagnostic/rob_cold_pair.c', 'probes/common/perf_group_read.h', 'probes/common/rob_backing.h')
EVENTS = ('0x11', '0x8', '0x3', '0x17', '0x34', '0x37')
MASKS = (0, 4096)
REFILLS = {'0x3': 'L1', '0x17': 'L2', '0x37': 'LL'}
# 新机制冻结v1；不得用事后改门救扫描。E hot/cold各自验median，不池化。
THRESHOLDS = {'empty_delta_abs_median_ticks_max': 1, 'empty_abs_delta_ticks_q90_max': 2,
              'empty_refill_walk_delta_mean_abs_max': .5, 'empty_raw_tick_hot_reference_margin': 2,
              'load_delta_ticks_median_min': 3, 'load_delta_mad_over_median_max': .2,
              'serial_over_parallel_delta_median': [1.5, 2.5],
              'load_refill_delta_mean': [1.5, 2.5], 'load_walk_delta_mean_abs_max': .1,
              'load_retired_delta_median_abs_max': 4}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def trial_order(epoch, trial):
    """固定24格左轮转trial%24，再当(trial+epoch)奇数时反序。"""
    _require(type(epoch) is int and epoch in (0, 1) and type(trial) is int and 0 <= trial < 64,
             'invalid cold-pair epoch/trial')
    base = [(m, s, member, state) for m in MASKS for s in (0, 1)
            for member in ('P', 'S', 'E') for state in ('hot', 'cold')]
    offset = trial % len(base)
    ordered = base[offset:] + base[:offset]
    return ordered[::-1] if (trial + epoch) % 2 else ordered


def audit_cells(run):
    """先验完整3072格、严格类型及顺序；不借其他epoch/swap/member补格。

输入为{'mode', 'processes':2, 'rows'}；每row epoch/trial/mask/swap/
member/state/ticks/counts。counts是单次完整PMU窗，不是每iter比率。
ticks=0合法，IR逐窗29..1029是技术门。此层不能证明raw来源或actual。
"""
    _require(type(run) is dict and run.get('mode') == MODE and
             type(run.get('processes')) is int and run['processes'] == 2,
             'cold-pair mode/process mismatch')
    rows = run.get('rows')
    _require(type(rows) is list and len(rows) == 3072, 'cold-pair window coverage mismatch')
    cells, ordered = {}, []
    for row in rows:
        _require(type(row) is dict, 'invalid cold-pair row')
        epoch, trial, mask, swap, member, state = (row.get(k) for k in
                                                  ('epoch', 'trial', 'mask', 'swap', 'member', 'state'))
        _require(type(epoch) is int and epoch in (0, 1) and type(trial) is int and 0 <= trial < 64 and
                 type(mask) is int and mask in MASKS and type(swap) is int and swap in (0, 1) and
                 type(member) is str and member in ('P', 'S', 'E') and
                 type(state) is str and state in ('hot', 'cold'), 'invalid cold-pair cell identity')
        key = epoch, trial, mask, swap, member, state
        _require(key not in cells, 'duplicate cold-pair cell identity')
        _require(type(row.get('ticks')) is int and 0 <= row['ticks'] < 2**64, 'invalid internal ticks')
        counts = row.get('counts')
        _require(type(counts) is dict and set(counts) == set(EVENTS) and
                 all(type(x) is int and 0 <= x < 2**64 for x in counts.values()) and counts['0x11'] > 0,
                 'invalid cold-pair event counts')
        _require(29 <= counts['0x8'] <= 1029, 'single-shot retired count outside frozen range')
        cells[key] = row
        ordered.append(key)
    expected = [(e, t, *identity) for e in (0, 1) for t in range(64) for identity in trial_order(e, t)]
    _require(set(cells) == set(expected), 'cold-pair cell coverage mismatch')
    _require(ordered == expected, 'cold-pair process/trial order mismatch')
    return cells


def linear_quantile(values, probability):
    """Type7线性分位：位置(n-1)*p；冻结q90应用于64个绝对冷热差。"""
    _require(bool(values) and type(probability) in (int, float) and 0 <= probability <= 1 and
             all(type(x) in (int, float) and math.isfinite(x) for x in values), 'invalid quantile input')
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _member(cells, epoch, mask, swap, member):
    """同trial cold-hot；保留全部原值和有符号差，不扣E、不以PMUcycles计时。"""
    hot = [cells[epoch, t, mask, swap, member, 'hot'] for t in range(64)]
    cold = [cells[epoch, t, mask, swap, member, 'cold'] for t in range(64)]
    delta = [c['ticks'] - h['ticks'] for h, c in zip(hot, cold)]
    median = st.median(delta)
    mad = st.median(abs(x - median) for x in delta)
    deltas = {k: [c['counts'][k] - h['counts'][k] for h, c in zip(hot, cold)] for k in EVENTS}
    return {'hot_ticks': [r['ticks'] for r in hot], 'cold_ticks': [r['ticks'] for r in cold],
            'delta_ticks': delta, 'hot_ticks_median': st.median(r['ticks'] for r in hot),
            'cold_ticks_median': st.median(r['ticks'] for r in cold), 'delta_ticks_median': median,
            'delta_ticks_mad': mad, 'delta_mad_over_median': mad / median if median > 0 else None,
            'delta_ticks_abs_q90': linear_quantile([abs(x) for x in delta], .9),
            'hot_counts': {k: [r['counts'][k] for r in hot] for k in EVENTS},
            'cold_counts': {k: [r['counts'][k] for r in cold] for k in EVENTS}, 'delta_counts': deltas,
            'count_delta_means': {k: st.mean(values) for k, values in deltas.items()},
            'retired_delta_median': st.median(deltas['0x8'])}


def qualify(run):
    """每mask四单元独立评分；需两个swap×两个epoch全过才允许另注册N扫。

技术缺格/类型/顺序失败抛ValueError；科学阴性照常返回全部窗口差与失败门。
未缩放MAD、线性q90、算术count均值均按新冻结v1；不引用旧c93门。
"""
    cells = audit_cells(run)
    candidates = []
    for mask in MASKS:
        for epoch in (0, 1):
            for swap in (0, 1):
                members = {m: _member(cells, epoch, mask, swap, m) for m in ('P', 'S', 'E')}
                gates = []

                def gate(name, value, lower=None, upper=None):
                    gates.append({'gate': name, 'value': value, 'lower': lower, 'upper': upper,
                                  'passed': value is not None and (lower is None or value >= lower) and
                                            (upper is None or value <= upper)})

                empty = members['E']
                reference = min(members['P']['hot_ticks_median'], members['S']['hot_ticks_median']) + THRESHOLDS['empty_raw_tick_hot_reference_margin']
                gate('E.delta_ticks_abs_median', abs(empty['delta_ticks_median']), upper=THRESHOLDS['empty_delta_abs_median_ticks_max'])
                gate('E.delta_ticks_abs_q90', empty['delta_ticks_abs_q90'], upper=THRESHOLDS['empty_abs_delta_ticks_q90_max'])
                for event, label in (*REFILLS.items(), ('0x34', 'datawalk')):
                    gate(f'E.{label}_count_delta_mean', abs(empty['count_delta_means'][event]), upper=THRESHOLDS['empty_refill_walk_delta_mean_abs_max'])
                for state in ('hot', 'cold'):
                    gate(f'E.{state}_ticks_median', empty[state + '_ticks_median'], upper=reference)
                for member in ('P', 'S'):
                    values = members[member]
                    gate(f'{member}.delta_ticks_median', values['delta_ticks_median'], lower=THRESHOLDS['load_delta_ticks_median_min'])
                    gate(f'{member}.delta_mad_over_median', values['delta_mad_over_median'], upper=THRESHOLDS['load_delta_mad_over_median_max'])
                    for event, label in REFILLS.items():
                        gate(f'{member}.{label}_count_delta_mean', values['count_delta_means'][event], *THRESHOLDS['load_refill_delta_mean'])
                    gate(f'{member}.datawalk_count_delta_mean', abs(values['count_delta_means']['0x34']), upper=THRESHOLDS['load_walk_delta_mean_abs_max'])
                    gate(f'{member}.retired_delta_abs_median', abs(values['retired_delta_median']), upper=THRESHOLDS['load_retired_delta_median_abs_max'])
                p, s = members['P']['delta_ticks_median'], members['S']['delta_ticks_median']
                ratio = s / p if p > 0 else None
                gate('paired.delta_median_ratio', ratio, *THRESHOLDS['serial_over_parallel_delta_median'])
                failed = [g['gate'] for g in gates if not g['passed']]
                candidates.append({'mask': mask, 'epoch': epoch, 'swap': swap, 'members': members,
                                   'empty_tick_upper_bound': reference, 'serial_over_parallel_delta_median': ratio,
                                   'gates': gates, 'failed_gates': failed, 'qualified': not failed})
    eligible = [mask for mask in MASKS if all(c['qualified'] for c in candidates if c['mask'] == mask)]
    return {'mode': MODE, 'protocol_path': PROTOCOL, 'processes': 2, 'windows': 3072,
            'thresholds': copy.deepcopy(THRESHOLDS), 'candidates': candidates, 'qualified_masks': eligible,
            'qualified': bool(eligible), 'all_candidates_qualified': all(c['qualified'] for c in candidates),
            'naming_limit': '仅可辨识的操作性双冷load候选；不认证DRAM、物理ROB或cache维护未被模拟',
            'empty_subtracted': False, 'tick_unit': 'CNTVCT ticks; no conversion to core cycles'}


def registered_plan():
    """独立固定N0两mapping预算；不从可变driver或raw猜矩阵/参数。"""
    return {'mode': MODE, 'processes': 2, 'windows': 3072, 'trials': 64, 'cells_per_trial': 24,
            'masks': [0, 4096], 'swaps': [0, 1], 'members': ['P', 'S', 'E'], 'states': ['hot', 'cold'],
            'warmup_calls': 128, 'n': 0, 'mapping_bytes': 8192,
            'conditions': [{'name': 'epoch-' + str(e), 'args': ['--epoch', str(e), '-n', '0', '--trials', '64',
                                                            '--pin', '7', '--pmu-type', '8']} for e in (0, 1)]}


def generated_code(mask, member):
    """独立冻结全部29word：x12常量/64B起点/DSB/ISB/CNTVCT/依赖/RET。"""
    _require(type(mask) is int and mask in MASKS and member in ('P', 'S', 'E'), 'unregistered code identity')
    words = [0xd280000c | (mask << 5), 0xf2a0000c, 0xf2c0000c, 0xf2e0000c] + [0xd503201f] * 12
    words += [0xd5033f9f, 0xd5033fdf, 0xd53be04d, 0xd5033fdf]
    if member == 'E':
        words += [0xd503201f] * 4
    else:
        words += [0xf9400000, 0xca0c0000,
                  0xf9400021 if member == 'P' else 0xf9400000,
                  0xca0c0021 if member == 'P' else 0xca0c0000]
    words += [0xd5033f9f, 0xd5033fdf, 0xd53be04e, 0xcb0d01c0, 0xd65f03c0]
    return struct.pack('<29I', *words)


def _same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(_same(actual[k], v) for k, v in expected.items())
    if type(expected) is list:
        return len(actual) == len(expected) and all(_same(a, b) for a, b in zip(actual, expected))
    return actual == expected


def _fields(actual, expected, message):
    _require(type(actual) is dict and all(_same(actual.get(k), v) for k, v in expected.items()), message)


def _sha(blob):
    return hashlib.sha256(blob).hexdigest()


def _git_blob(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)


def _config(epoch):
    """真实producer v1的独立N0请求期待值；export只额外含mask/member。"""
    return {'type': 'config', 'version': 1, 'probe': 'rob-cold-pair', 'n': 0, 'trials': 64, 'epoch': epoch,
            'matrix_cells_per_trial': 24, 'windows': 1536, 'memory_bytes': 8192, 'mapping_alignment': 8192,
            'node_offsets': [0, 4096], 'masks': [0, 4096], 'members': ['P', 'S', 'E'], 'states': ['hot', 'cold'],
            'warmup_calls': 128, 'internal_clock': 'cntvct_el0', 'code_bytes': 116, 'kernel_instructions': 29,
            'pin': 7, 'pmu_type': 8, 'events': [17, 8, 3, 23, 52, 55], 'exclude_kernel': True,
            'exclude_hv': True, 'backing_requested': '4k'}


def _backing(info):
    _fields(info, {'kernel_page_kb': 4, 'mmu_page_kb': 4, 'anon_huge_kb': 0,
                   'rss_kb': 8, 'swap_kb': 0, 'no_huge': True}, 'actual two-page 4K backing mismatch')


def _process(records, epoch):
    """严格验真实1539-record布局；normalize仅把metrics改名counts，不删窗口。"""
    _require(type(records) is list and len(records) == 1539, 'cold-pair complete record count mismatch')
    config, runtime, *tail = records
    final, rounds = tail[-1], tail[:-1]
    _require(_same(config, _config(epoch)), 'actual cold-pair config mismatch')
    _fields(runtime, {'type': 'runtime', 'cpu': 7, 'cache_line_bytes': 64, 'mapping_alignment_verified': True,
                      'raw_self_pointer_verified': True, 'code_address_mod64': 0, 'cache_maintenance_completed': True},
            'actual cold-pair runtime/capability mismatch')
    freq = runtime.get('cntfrq_hz')
    _require(type(freq) is int and 0 < freq <= 1000000000, 'invalid actual CNTFRQ')
    ids = runtime.get('event_ids')
    _require(type(ids) is list and len(ids) == 6 and all(type(x) is int and 0 < x < 2**64 for x in ids) and
             len(set(ids)) == 6, 'actual cold-pair PMU ID mismatch')
    _backing(runtime.get('initial_backing'))
    _fields(final, {'type': 'backing-final'}, 'actual final backing record missing')
    _backing(final.get('backing'))
    normalized = []
    for row, identity in zip(rounds, [(t, *cell) for t in range(64) for cell in trial_order(epoch, t)]):
        trial, mask, swap, member, state = identity
        expected = {'epoch': epoch, 'trial': trial, 'mask': mask, 'swap': swap, 'member': member, 'state': state}
        _fields(row, dict(type='round', **expected), 'actual cold-pair cell/order mismatch')
        _require(all(type(row.get(k)) is int and 0 < row[k] < 2**64 for k in ('enabled', 'running')) and
                 row['enabled'] == row['running'], 'actual PMU timing/mux mismatch')
        normalized.append(dict(**expected, ticks=row.get('ticks'), counts=row.get('metrics')))
    return config, runtime, final, rounds, normalized


def _environment(path, launch, conditions):
    """重算launch profile原preconditions/stability；环境flags不能掩盖真实漂移。"""
    from runner.environment.policy import evaluate_preconditions_full, evaluate_stability_full
    profile_blob = _git_blob(launch, PROFILE)
    registered = json.loads(profile_blob)['environment_profiles']['charging-thermal']['measurement_environment']
    registered['preconditions']['cpufreq_governor'] = 'walt'
    policy = json.loads((path / 'environment-policy.json').read_text())
    _require(_same(policy, registered), 'saved environment policy differs from launch profile')
    envs = {f.name: json.loads(f.read_text()) for f in path.glob('*-environment.json')}
    expected = {'initial-environment.json', 'final-environment.json'} | {
        c['name'] + '-' + suffix + '-environment.json' for c in conditions for suffix in ('pre', 'post')}
    _require(set(envs) == expected, 'cold-pair environment endpoint coverage mismatch')
    reference = envs['initial-environment.json']['snapshot']
    temps = []
    for name, env in envs.items():
        snapshot = env['snapshot']
        pre = evaluate_preconditions_full(snapshot, policy)
        stability = evaluate_stability_full(reference, snapshot, policy)
        _require(not any(pre) and not any(stability) and env['violations'] == [] and env['warnings'] == [],
                 'cold-pair environment precondition/stability failure: ' + name)
        temp = snapshot['thermal']['max_cpu_c']
        _require(type(temp) in (int, float) and math.isfinite(temp), 'invalid environment temperature')
        temps.append(temp)
    return {'environment_policy_sha256': _sha((path / 'environment-policy.json').read_bytes()),
            'environment_profile_source': {'commit': launch, 'path': PROFILE, 'sha256': _sha(profile_blob),
                                           'overrides': {'preconditions.cpufreq_governor': 'walt'}},
            'environment_endpoints': {name: _sha((path / name).read_bytes()) for name in sorted(envs)},
            'environment_endpoints_count': len(envs), 'environment_preconditions_and_stability_passed': True,
            'max_cpu_c_range': [min(temps), max(temps)]}


def audit_raw(path):
    """完整raw/source/plan/code/actual硬门之后才返回归一化输入和技术回执。

这里不声称DC未被模拟或所有cache已清，不使用旧c93科学门。record及
code期待值独立于driver；真实host producer测试核全部配置、字节及顺序。
"""
    path = Path(path)
    manifest_blob = (path / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_blob)
    _fields(manifest, {'mode': MODE, 'status': 'complete', 'target': 'redmi-k70pro-01',
                       'midr': '0x410fd821', 'base_page_bytes': 4096, 'protocol_path': PROTOCOL,
                       'build_evidence_path': BUILD, 'plan_path': PLAN}, 'complete cold-pair launch identity mismatch')
    plan = registered_plan()
    _require(_same(manifest.get('conditions'), plan['conditions']), 'cold-pair manifest matrix mismatch')
    entries = manifest.get('results')
    _require(type(entries) is list and [e.get('name') for e in entries] == ['epoch-0', 'epoch-1'],
             'cold-pair process coverage/order mismatch')
    launch, source = manifest['source_head'], manifest['binary_source_head']
    driver = (path / 'driver.py').read_bytes()
    _require(_sha(driver) == manifest['driver_sha256'] == _sha(_git_blob(launch, DRIVER)), 'cold-pair driver binding mismatch')
    protocol_blob = _git_blob(launch, PROTOCOL)
    _require(_sha(protocol_blob) == manifest['protocol_sha256'], 'cold-pair protocol binding mismatch')
    build_blob = _git_blob(launch, BUILD)
    _require(_sha(build_blob) == manifest['build_evidence_sha256'], 'cold-pair build binding mismatch')
    build = json.loads(build_blob)
    _require(build['source_commit'] == source and build['binaries']['rob_cold_pair'] == manifest['binary_sha256'],
             'cold-pair binary/source binding mismatch')
    _require(set(build['source_sha256']) == set(SOURCES) and _same(manifest.get('source_sha256'), build['source_sha256']),
             'cold-pair declared source coverage mismatch')
    for rel, digest in build['source_sha256'].items():
        _require(_sha(_git_blob(source, rel)) == digest == _sha(_git_blob(launch, rel)), 'cold-pair source blob binding mismatch')
    plan_blob = _git_blob(launch, PLAN)
    _require(build['plan_path'] == PLAN and _sha(plan_blob) == build['plan_sha256'] == manifest['plan_sha256'] and
             _same(json.loads(plan_blob), plan), 'cold-pair frozen plan binding mismatch')
    environment = _environment(path, launch, plan['conditions'])
    rows, processes = [], []
    for epoch, entry in enumerate(entries):
        name = entry['name']
        _fields(entry, {'exit_code': 0, 'timed_out': False}, 'cold-pair process failure')
        _require((path / (name + '.stderr.log')).read_bytes() == b'', 'unexpected cold-pair stderr')
        stdout = (path / (name + '.stdout.jsonl')).read_bytes()
        _require(_sha(stdout) == entry['stdout_sha256'], 'cold-pair stdout digest mismatch')
        records = [json.loads(line) for line in stdout.splitlines()]
        config, runtime, final, rounds, normalized = _process(records, epoch)
        exports = entry.get('generated_code')
        keys = {f'm{m}-{member}' for m in MASKS for member in ('P', 'S', 'E')}
        _require(type(exports) is dict and set(exports) == keys, 'cold-pair six code export coverage mismatch')
        code_shas = {}
        for mask in MASKS:
            for member in ('P', 'S', 'E'):
                key = f'm{mask}-{member}'; generated = exports[key]
                code = (path / (name + '-' + key + '.bin')).read_bytes()
                expected = dict(config, export={'mask': mask, 'member': member})
                _require(code == generated_code(mask, member) and _sha(code) == generated['sha256'] and
                         _same(generated['config'], expected), 'cold-pair code/config export binding mismatch')
                code_shas[key] = _sha(code)
        rows.extend(normalized)
        processes.append({'condition': name, 'stdout_sha256': _sha(stdout), 'actual_config': config,
                          'actual_runtime': runtime, 'final_backing': final, 'generated_code_sha256': code_shas,
                          'cntvct_tick_ns': 1000000000 / runtime['cntfrq_hz'], 'windows': rounds})
    run = {'mode': MODE, 'processes': 2, 'windows': 3072, 'rows': rows, 'raw_directory': path.name,
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
    """先完整raw审核，再输出科学资格及可选公开summary；技术失败不写工件。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('--summary-output', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    audited = audit_raw(args.raw)
    run, technical = audited['run'], audited['technical_acceptance']
    result = qualify(run)
    result.update(data_origin='device-raw', technical_acceptance=technical,
                  scientific_qualification='qualified' if result['qualified'] else 'not-qualified')
    qblob = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    sblob = json.dumps({'runs': [run]}, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    if args.summary_output:
        args.summary_output.write_text(sblob)
    args.output.write_text(qblob)
    print(json.dumps({'technical_passed': True, 'windows': 3072, 'qualified_masks': result['qualified_masks']}))


if __name__ == '__main__':
    main()
