#!/usr/bin/env python3
"""复算冻结 long-load 资格；科学门失败仍保留全部真实窗口。

阈值来源：c93e788 的 docs/design/2026-10-09-long-load-qualification.md。
CLI 先重审 raw 并与 summary 精确比对；qualify 的 synthetic 测试仅证明
软件契约。远层 miss 代理不能直接命名 DRAM，也不能推算物理 ROB 条目。
"""
import argparse
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
# 冻结 v1 §资格门；THP 只改变 backing 控制，不能事后改变这些科学门。
GATE_SOURCE = {
    'commit': 'c93e788a31c077f5575ef6139157b8fe3185bc0f',
    'path': 'docs/design/2026-10-09-long-load-qualification.md',
    'sha256': '7de293eff7033316c2f46a77025a688c7a26e3b6efe37ebe6f5b16b57a53d943',
}
MODES = ('rob-miss-qualify', 'rob-miss-qualify-thp', 'rob-miss-wide-thp', 'rob-miss-fixed-thp', 'rob-collapse-qualify')
EVENTS = ('0x11', '0x8', '0x3', '0x17', '0x34', '0x37')
REFILLS = {'0x3': 'L1_refill', '0x17': 'L2_refill', '0x37': 'LL_miss'}
THRESHOLDS = {
    'refills_per_iteration': [1.8, 2.2], 'datawalk_per_iteration_max': 0.02,
    'cycle_range_over_median_max': 0.10, 'serial_over_parallel': [1.6, 2.4],
    'miss_mean_relative_difference_max': 0.10, 'hot_cycle_multiplier': 4,
    'parallel_cycles_per_iteration_min': 171, 'hot_LL_miss_per_iteration_max': 0.1,
}


def qualify(run, *, mode='rob-miss-qualify'):
    """按 epoch/footprint/member/round 独立评门，返回全部值与失败门。

    输入须覆盖所选 mode 的完整双 epoch/双 member 矩阵；缺身份、非有限值
    或激励元数据改变抛 ValueError。此纯函数不证明 raw 来源或 backing，
    CLI 另行核验。THP mode 必须显式选择；wide 为 1/256/512 MiB 的
    6 进程/36 窗，fixed/collapse 为 1/256 MiB 的 4 进程/24 窗。collapse
    每行须显式绑定bool请求标志；均仍使用旧 c93e788 冻结科学门，
    不改写旧模式或既有输出。
    """
    if mode not in MODES or run.get('mode') != mode:
        raise ValueError('qualification mode/process mismatch')
    # fixed 的独立完整矩阵见 docs/design/2026-10-09-fixed-load-qualification.md；
    # 不接受 stopped wide 前缀，也不能通过重标记旧64/128数据改变足迹。
    long_mib = {'rob-miss-wide-thp': (256, 512), 'rob-miss-fixed-thp': (256,),
                'rob-collapse-qualify': (256,)}.get(mode, (64, 128))
    footprints = (1, *long_mib)
    process_count = 2 * len(footprints)
    if run.get('processes') != process_count:
        raise ValueError('qualification mode/process mismatch')
    cells = {}
    for row in run['rows']:
        epoch, memory, serial = row['epoch'], row['memory_bytes'], row['serial']
        if type(epoch) is not int or type(memory) is not int or type(serial) is not bool:
            raise ValueError('invalid cell identity types')
        key = epoch, memory, serial
        if key in cells:
            raise ValueError('duplicate qualification identity')
        mb = memory // 1048576
        if mb not in footprints:
            raise ValueError('qualification mode/footprint mismatch')
        # 新局部干预必须贯穿请求→摘要；缺flag的旧fixed数据不能改名晋升。
        # 契约：docs/design/2026-10-09-local-collapse-qualification.md。
        if mode == 'rob-collapse-qualify' and (
                type(row.get('collapse_requested')) is not bool or
                row['collapse_requested'] != (memory > 1048576)):
            raise ValueError('collapse request metadata mismatch')
        expected = {'condition': f'e{epoch}-miss-m{mb}-n0', 'class': 'nop',
                    'anchor': 'miss', 'n': 0, 'chain': 8, 'loop_mod64': 0,
                    'chase_seed': 42, 'iterations': max(131072, mb * 8192)}
        if any(row.get(k) != v for k, v in expected.items()):
            raise ValueError('qualification excitation metadata mismatch')
        rates = row['counts_per_iteration']
        if set(rates) != set(EVENTS):
            raise ValueError('qualification event set mismatch')
        arrays = [row['cycles_per_iteration'], *rates.values()]
        if any(len(v) != 3 for v in arrays):
            raise ValueError('three rounds per member required')
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or
               not math.isfinite(x) or x < 0 for values in arrays for x in values):
            raise ValueError('invalid qualification round value')
        if min(row['cycles_per_iteration']) <= 0 or row['cycles_per_iteration'] != rates['0x11']:
            raise ValueError('invalid or inconsistent cycle values')
        cells[key] = row
    expected = {(e, mb * 1048576, s) for e in (0, 1) for mb in footprints for s in (False, True)}
    if set(cells) != expected:
        raise ValueError('qualification cell coverage mismatch')

    candidates, hot_controls = [], []
    for epoch in (0, 1):
        hot = {s: cells[epoch, 1048576, s] for s in (False, True)}
        hot_median = st.median(hot[False]['cycles_per_iteration'])
        floor = max(THRESHOLDS['hot_cycle_multiplier'] * hot_median,
                    THRESHOLDS['parallel_cycles_per_iteration_min'])
        hot_controls.append({'epoch': epoch, 'parallel_cycle_median': hot_median,
                             'members': {('S' if s else 'P'): hot[s]['counts_per_iteration'] for s in hot}})
        for mb in long_mib:
            members, gates = {}, []

            def gate(name, value, lower=None, upper=None):
                gates.append({'gate': name, 'value': value, 'lower': lower, 'upper': upper,
                              'passed': (lower is None or value >= lower) and
                                        (upper is None or value <= upper)})

            for serial, label in ((False, 'P'), (True, 'S')):
                row = cells[epoch, mb * 1048576, serial]
                rates = row['counts_per_iteration']
                cycles = row['cycles_per_iteration']
                stability = (max(cycles) - min(cycles)) / st.median(cycles)
                members[label] = {'cycle_median': st.median(cycles),
                                  'cycle_range_over_median': stability,
                                  'rounds': [{'round': r, 'counts_per_iteration': {k: rates[k][r] for k in EVENTS}}
                                             for r in range(3)]}
                for r in range(3):
                    for event, name in REFILLS.items():
                        gate(f'{label}.round{r}.{name}_rate', rates[event][r], *THRESHOLDS['refills_per_iteration'])
                    gate(f'{label}.round{r}.datawalk_rate', rates['0x34'][r],
                         upper=THRESHOLDS['datawalk_per_iteration_max'])
                    gate(f'hot.{label}.round{r}.LL_miss_rate', hot[serial]['counts_per_iteration']['0x37'][r],
                         upper=THRESHOLDS['hot_LL_miss_per_iteration_max'])
                gate(f'{label}.cycle_stability', stability, upper=THRESHOLDS['cycle_range_over_median_max'])
            parallel = cells[epoch, mb * 1048576, False]['counts_per_iteration']
            serial = cells[epoch, mb * 1048576, True]['counts_per_iteration']
            ratios = [s / p for p, s in zip(parallel['0x11'], serial['0x11'])]
            for r, value in enumerate(ratios):
                gate(f'round{r}.paired_ratio', value, *THRESHOLDS['serial_over_parallel'])
            differences = {}
            # 冻结协议的“两种 miss 代理”为 0x17 与 0x37；L1 单独守逐轮率门。
            for event in ('0x17', '0x37'):
                p_mean, s_mean = st.mean(parallel[event]), st.mean(serial[event])
                denominator = (p_mean + s_mean) / 2
                value = abs(p_mean - s_mean) / denominator if denominator else None
                differences[event] = value
                if value is None:
                    gates.append({'gate': f'paired.{REFILLS[event]}_mean_difference',
                                  'value': None, 'lower': None,
                                  'upper': THRESHOLDS['miss_mean_relative_difference_max'], 'passed': False})
                else:
                    gate(f'paired.{REFILLS[event]}_mean_difference', value,
                         upper=THRESHOLDS['miss_mean_relative_difference_max'])
            gate('P.cycle_headroom', members['P']['cycle_median'], lower=floor)
            failed = [g['gate'] for g in gates if not g['passed']]
            candidates.append({'epoch': epoch, 'memory_bytes': mb * 1048576,
                               'members': members, 'serial_over_parallel': ratios,
                               'miss_mean_relative_difference': differences,
                               'parallel_cycle_floor': floor, 'gates': gates,
                               'failed_gates': failed, 'qualified': not failed})
    eligible = [mb for mb in long_mib if all(c['qualified'] for c in candidates if c['memory_bytes'] == mb * 1048576)]
    return {'gate_source': dict(GATE_SOURCE), 'thresholds': dict(THRESHOLDS),
            'mode': mode, 'processes': process_count, 'windows': process_count * 6, 'hot_controls': hot_controls,
            'candidates': candidates, 'qualified': bool(eligible),
            'all_candidates_qualified': all(c['qualified'] for c in candidates),
            'qualified_footprints_mib': eligible,
            'smallest_qualified_footprint_mib': min(eligible) if eligible else None,
            'naming_limit': '低翻译干扰、远层miss主导的双长load候选' if eligible else '双长load锚点资格不通过'}


def audit_environment(envs, policy, registered_policy):
    """重算端点 preconditions/稳定字段；策略偏离启动 profile 抛 ValueError。"""
    from runner.environment.policy import evaluate_preconditions_full, evaluate_stability_full
    if policy != registered_policy:
        raise ValueError('saved environment policy differs from launch profile')
    reference = envs['initial-environment.json']['snapshot']
    for name, env in envs.items():
        pre = evaluate_preconditions_full(env['snapshot'], policy)
        stable = evaluate_stability_full(reference, env['snapshot'], policy)
        if any(pre) or any(stable) or env['violations'] or env['warnings']:
            raise ValueError('environment acceptance/stability failure: ' + name)


def audit_raw(path, summary):
    """只读重验 raw 来源和环境，精确比对摘要；不合格抛 ValueError。

    复用现有生产 auditor 的 source/build/stdout/config/footprint/PMU 门，
    补 paired 顺序、ID 唯一性、导出生成码和环境稳定字段。未来 THP backing
    仍必须先经其生产 auditor，不能仅凭这里相同科学率门宣称 backing 合格。
    """
    if not __debug__:
        raise ValueError('raw auditor requires Python assertions enabled')
    from tools.diagnostic.summarize_sm8650_minimal import summarize
    audited = {'runs': [summarize(path)]}
    if summary != audited:
        raise ValueError('summary differs from audited raw')
    manifest = json.loads((path / 'manifest.json').read_text())
    if manifest['mode'] == 'rob-miss-qualify' and (
            manifest['source_head'] != GATE_SOURCE['commit'] or
            manifest['protocol_path'] != GATE_SOURCE['path'] or
            manifest['protocol_sha256'] != GATE_SOURCE['sha256']):
        raise ValueError('4K run differs from frozen launch/protocol identity')
    frozen = subprocess.check_output(['git', 'show', GATE_SOURCE['commit'] + ':' + GATE_SOURCE['path']], cwd=ROOT)
    if hashlib.sha256(frozen).hexdigest() != GATE_SOURCE['sha256']:
        raise ValueError('frozen gate source digest mismatch')
    policy = json.loads((path / 'environment-policy.json').read_text())
    envs = {f.name: json.loads(f.read_text()) for f in path.glob('*-environment.json')}
    profile_path = 'configs/platforms/redmi-k70pro-01.json'
    profile_blob = subprocess.check_output(['git', 'show', manifest['source_head'] + ':' + profile_path], cwd=ROOT)
    registered_policy = json.loads(profile_blob)['environment_profiles']['charging-thermal']['measurement_environment']
    # c93e788 driver 的唯一 profile override；来源也随启动 commit 绑定。
    registered_policy['preconditions']['cpufreq_governor'] = 'walt'
    audit_environment(envs, policy, registered_policy)
    processes, residuals = [], []
    expected_order = [(0, False, 0), (0, True, 1), (1, True, 0), (1, False, 1), (2, False, 0), (2, True, 1)]
    for result in manifest['results']:
        name = result['name']
        if (path / (name + '.stderr.log')).read_text():
            raise ValueError('unexpected stderr: ' + name)
        records = [json.loads(line) for line in (path / (name + '.stdout.jsonl')).read_text().splitlines()]
        config = records[0]
        collapse = None
        collapse_requested = config.get('collapse_requested', False)
        if manifest['mode'] == 'rob-collapse-qualify' and collapse_requested:
            # 生产summarizer已核唯一性/位置/返回值/actual post；本层保留原记录。
            config, collapse, runtime, *rounds = records
            if collapse.get('type') != 'backing-collapse':
                raise ValueError('raw record layout mismatch')
        else:
            config, runtime, *rounds = records
        if (config['type'], runtime['type']) != ('config', 'runtime') or len(rounds) != 6:
            raise ValueError('raw record layout mismatch')
        if [(r['round'], r['serial'], r['pair_step']) for r in rounds] != expected_order:
            raise ValueError('paired round order mismatch')
        if len(runtime['event_ids']) != len(set(runtime['event_ids'])) or len(runtime['event_ids']) != 6:
            raise ValueError('PMU event IDs mismatch')
        codes = {}
        for member, generated in result['generated_code'].items():
            code = (path / (name + '-' + member + '.bin')).read_bytes()
            digest = hashlib.sha256(code).hexdigest()
            expected_config = dict(config, paired=False, serial=(member == 'serial'))
            if digest != generated['sha256'] or generated['config'] != expected_config or len(code) != 84:
                raise ValueError('generated code/config binding mismatch')
            words = struct.unpack('<21I', code)
            expected_tail = (0xf9400000, 0xf9400000 if member == 'serial' else 0xf9400021,
                             0xf1000463, 0x54ffffa1, 0xd65f03c0)
            if words[16:] != expected_tail:
                raise ValueError('N0 load/branch encoding mismatch')
            codes[member] = digest
        if set(codes) != {'parallel', 'serial'}:
            raise ValueError('missing paired code export')
        for row in rounds:
            if row['type'] != 'round' or not all(type(v) is int and v >= 0 for v in row['metrics'].values()):
                raise ValueError('invalid raw PMU counts')
            residuals.append(row['metrics']['0x8'] - (config['iterations'] * 4 + 17))
        process = {'condition': name, 'stdout_sha256': result['stdout_sha256'],
                          'iterations': config['iterations'], 'memory_bytes': config['memory_bytes'],
                          'ring_nodes': runtime['ring_nodes'], 'distinct_lines_per_call': runtime['distinct_lines_per_call'],
                          'loop_address_mod64': runtime['loop_address_mod64'],
                          'mapping_4k_verified': runtime.get('mapping_4k_verified'),
                          'event_ids': runtime['event_ids'], 'generated_code_sha256': codes,
                          'windows': rounds}
        if manifest['mode'] == 'rob-collapse-qualify':
            process.update(collapse_requested=collapse_requested, collapse_observation=collapse)
        processes.append(process)
    return {'passed': True, 'raw_directory': path.name,
            'manifest_sha256': hashlib.sha256((path / 'manifest.json').read_bytes()).hexdigest(),
            'source_head': manifest['source_head'], 'binary_source_head': manifest['binary_source_head'],
            'binary_sha256': manifest['binary_sha256'], 'driver_sha256': manifest['driver_sha256'],
            'build_evidence_sha256': manifest['build_evidence_sha256'],
            'protocol_path': manifest['protocol_path'], 'protocol_sha256': manifest['protocol_sha256'],
            'environment_policy_sha256': hashlib.sha256((path / 'environment-policy.json').read_bytes()).hexdigest(),
            'environment_profile_source': {'commit': manifest['source_head'], 'path': profile_path,
                                           'sha256': hashlib.sha256(profile_blob).hexdigest(),
                                           'overrides': {'preconditions.cpufreq_governor': 'walt'}},
            'environment_endpoints': {name: hashlib.sha256((path / name).read_bytes()).hexdigest() for name in sorted(envs)},
            'environment_endpoints_count': len(envs), 'environment_preconditions_and_stability_passed': True,
            'max_cpu_c_range': audited['runs'][0]['max_cpu_c_range'],
            'retired_minus_generated_kernel_range': [min(residuals), max(residuals)],
            'processes': processes}


def main(argv=None):
    """CLI 必须以 raw 核验摘要；科学失败返回正常结果，技术失败终止写出。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary', type=Path)
    parser.add_argument('--raw', required=True, type=Path)
    parser.add_argument('--mode', choices=MODES, default='rob-miss-qualify')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    summary = json.loads(args.summary.read_text())
    technical = audit_raw(args.raw, summary)
    if len(summary['runs']) != 1:
        raise ValueError('exactly one qualification run required')
    result = qualify(summary['runs'][0], mode=args.mode)
    result.update({'summary_input': {'path': args.summary.as_posix() if not args.summary.is_absolute() else args.summary.name,
                                     'sha256': hashlib.sha256(args.summary.read_bytes()).hexdigest()},
                   'data_origin': 'device-raw', 'technical_acceptance': technical,
                   'scientific_qualification': 'qualified' if result['qualified_footprints_mib'] else 'not-qualified'})
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps({'technical_passed': True, 'qualified_footprints_mib': result['qualified_footprints_mib'],
                      'failed_gates': [{'epoch': c['epoch'], 'memory_bytes': c['memory_bytes'], 'gates': c['failed_gates']}
                                       for c in result['candidates']]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
