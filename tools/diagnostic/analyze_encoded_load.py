#!/usr/bin/env python3
"""审核编码双load的完整raw，再按mask独立复算原冻结资格门。

契约：docs/design/2026-10-09-encoded-load-qualification.md。显式mask0
与非零mask均保留两条EOR；不混入旧无EOR数据，不跨编码池化科学门。
纯qualify测试是软件证据；CLI的设备结果必须先通过完整来源/actual审核。
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.diagnostic.analyze_long_load import EVENTS, GATE_SOURCE, audit_environment, qualify as base_qualify

MODE = 'rob-xor-qualify'
MASKS = ('0x0000000000000000', '0xffff000000000000')
PROTOCOL = 'docs/design/2026-10-09-encoded-load-qualification.md'
BUILD = 'docs/reviews/evidence/2026-10-09-encoded-load/build.json'
PLAN = 'docs/reviews/evidence/2026-10-09-encoded-load/plan.json'
DRIVER = 'tools/diagnostic/run_sm8650_minimal.py'
PROFILE = 'configs/platforms/redmi-k70pro-01.json'
PROBE_SOURCES = ('docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c',
                 'probes/common/perf_group_read.h', 'probes/common/rob_backing.h')
PAIR_ORDER = ((0, False, 0), (0, True, 1), (1, True, 0),
              (1, False, 1), (2, False, 0), (2, True, 1))


def _sha(blob):
    return hashlib.sha256(blob).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _matches(actual, expected):
    """JSON标量/列表严格类型比较；bool/float不能代替整数身份。"""
    if type(actual) is not type(expected):
        return False
    if type(expected) is list:
        return len(actual) == len(expected) and all(_matches(a, b) for a, b in zip(actual, expected))
    if type(expected) is dict:
        return set(actual) == set(expected) and all(_matches(actual[k], v) for k, v in expected.items())
    return actual == expected


def _fields(actual, expected, message):
    _require(all(_matches(actual.get(k), v) for k, v in expected.items()), message)


def registered_plan():
    """独立冻结12条件及完整逆序；不从可变producer推导审计期待值。"""
    forward = [(mb, mask) for mb in (1, 64, 128) for mask in MASKS]
    conditions = []
    for epoch in (0, 1):
        for mb, mask in (forward if epoch == 0 else reversed(forward)):
            args = ['-i', str(max(131072, mb * 8192)), '-r', '3', '--pin', '7', '--pmu-type', '8',
                    '-e', '0x03', '-e', '0x17', '-e', '0x34', '-e', '0x37', '--pointer-xor', mask,
                    '--backing', '4k' if mb == 1 else 'thp2m', '-t', 'nop', '-n', '0', '-a', 'miss',
                    '-m', str(mb), '--paired']
            conditions.append({'name': f'e{epoch}-xor{mask[2:]}-miss-m{mb}-n0', 'args': args})
    return {'mode': MODE, 'conditions': conditions, 'processes': 12, 'windows': 72,
            'member_windows': 3, 'masks': list(MASKS)}


def _cells(run):
    """验证全部24member身份与72有限窗口；科学评分之前禁止任何缺格。"""
    _fields(run, {'mode': MODE, 'processes': 12}, 'encoded mode/process mismatch')
    _require(type(run.get('rows')) is list, 'encoded rows must be a list')
    cells = {}
    for row in run['rows']:
        _require(type(row) is dict, 'invalid encoded row')
        epoch, memory, serial, mask = (row.get(k) for k in ('epoch', 'memory_bytes', 'serial', 'pointer_xor'))
        _require(type(epoch) is int and epoch in (0, 1) and type(memory) is int and
                 memory in (1048576, 64 * 1048576, 128 * 1048576) and
                 type(serial) is bool and type(mask) is str and mask in MASKS, 'invalid encoded cell identity')
        mb = memory // 1048576
        _fields(row, {'condition': f'e{epoch}-xor{mask[2:]}-miss-m{mb}-n0', 'class': 'nop', 'anchor': 'miss',
                      'n': 0, 'chain': 8, 'loop_mod64': 0, 'chase_seed': 42,
                      'iterations': max(131072, mb * 8192), 'pointer_xor_requested': True,
                      'decode_instructions_per_iteration': 2, 'loop_instructions': 6, 'code_bytes': 92},
                'encoded excitation/metadata mismatch')
        key = mask, epoch, memory, serial
        _require(key not in cells, 'duplicate encoded cell identity')
        rates = row.get('counts_per_iteration')
        _require(type(rates) is dict and set(rates) == set(EVENTS), 'encoded event coverage mismatch')
        arrays = [row.get('cycles_per_iteration'), *rates.values()]
        _require(all(type(v) is list and len(v) == 3 for v in arrays), 'three rounds per encoded member required')
        _require(all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for v in arrays for x in v),
                 'invalid encoded round value')
        _require(min(row['cycles_per_iteration']) > 0 and row['cycles_per_iteration'] == rates['0x11'],
                 'invalid or inconsistent encoded cycles')
        cells[key] = row
    expected = {(mask, e, mb * 1048576, s) for mask in MASKS for e in (0, 1)
                for mb in (1, 64, 128) for s in (False, True)}
    _require(set(cells) == expected, 'encoded cell coverage mismatch')
    return cells


def qualify(run):
    """新身份完整验收后仅作数学规范化；每mask仍独立沿c93e788原门。"""
    cells = _cells(run)
    encodings, qualified = {}, []
    for mask in MASKS:
        rows = []
        for epoch in (0, 1):
            for mb in (1, 64, 128):
                for serial in (False, True):
                    row = copy.deepcopy(cells[mask, epoch, mb * 1048576, serial])
                    row['condition'] = f'e{epoch}-miss-m{mb}-n0'
                    rows.append(row)
        result = base_qualify({'mode': 'rob-miss-qualify', 'processes': 6, 'rows': rows})
        # 旧mode只是数学适配输入；公开结果始终保留新mode及显式编码。
        result.update(mode=MODE, pointer_xor=mask, base_gate_mode='rob-miss-qualify')
        encodings[mask] = result
        qualified.extend({'pointer_xor': mask, 'footprint_mib': mb} for mb in result['qualified_footprints_mib'])
    contrasts = []
    for epoch in (0, 1):
        for mb in (1, 64, 128):
            for serial in (False, True):
                zero, nonzero = [cells[m, epoch, mb * 1048576, serial] for m in MASKS]
                contrasts.append({'epoch': epoch, 'memory_bytes': mb * 1048576, 'serial': serial,
                                  'encoding_counts_per_iteration': {m: cells[m, epoch, mb * 1048576, serial]['counts_per_iteration']
                                                                   for m in MASKS},
                                  'counts_per_iteration_nonzero_minus_zero':
                                  {k: [b - a for a, b in zip(zero['counts_per_iteration'][k], nonzero['counts_per_iteration'][k])]
                                   for k in EVENTS}})
    return {'mode': MODE, 'processes': 12, 'windows': 72, 'gate_source': dict(GATE_SOURCE),
            'encodings': encodings, 'mask_contrasts': contrasts, 'qualified_conditions': qualified,
            'qualified': bool(qualified), 'all_encodings_qualified': all(q['all_candidates_qualified'] for q in encodings.values()),
            'naming_limit': '仅各编码独立资格；不能认证DRAM、物理ROB或跨编码因果',
            'contrast_limit': '同索引顺序但跨进程VA/PFN未匹配；保留负值/低信号，不能仅凭差值证明预取'}


def _git_blob(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)


def _code(mask, serial):
    """冻结N0的全部23个AArch64 word，包括x12立即数和64B loop对齐。"""
    value = int(mask, 16)
    words = [0xaa0203ee, 0xd2822230, 0xf2a00010, 0xf2c00010, 0xf2e00010,
             0xd2844451, 0xf2a00011, 0xf2c00011, 0xf2e00011,
             0xd280000c | ((value & 65535) << 5)]
    words += [0xf280000c | (((value >> s) & 65535) << 5) | ((s // 16) << 21) for s in (16, 32, 48)]
    words += [0xd503201f] * 3
    words += [0xf9400000, 0xca0c0000, 0xf9400000 if serial else 0xf9400021,
              0xca0c0000 if serial else 0xca0c0021, 0xf1000463, 0x54ffff61, 0xd65f03c0]
    return struct.pack('<23I', *words)


def _backing(info, memory):
    huge = memory > 1048576
    kb = memory // 1024
    _require(type(info) is dict, 'missing actual backing observation')
    _fields(info, {'rss_kb': kb, 'swap_kb': 0, 'anon_huge_kb': kb if huge else 0, 'no_huge': not huge},
            'actual backing coverage mismatch')
    _require(all(type(info.get(k)) is int and info[k] in ((4, 2048) if huge else (4,))
                 for k in ('kernel_page_kb', 'mmu_page_kb')), 'actual backing page geometry mismatch')


def audit_raw(path, summary):
    """全来源、请求/actual、生成码及环境硬门；停块不能进入科学评分。

生产summarizer仍作为独立接缝对账；这里重复的严格检查专门防止身份被
重贴、plan绕过、PMU bool/负计数与重新hash后的错误生成码混入新资格。
"""
    _require(__debug__, 'raw auditor requires Python assertions enabled')
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text())
    _fields(manifest, {'mode': MODE, 'status': 'complete', 'midr': '0x410fd821', 'base_page_bytes': 4096,
                       'protocol_path': PROTOCOL, 'build_evidence_path': BUILD, 'plan_path': PLAN},
            'encoded complete launch identity mismatch')
    plan = registered_plan()
    _require(manifest.get('conditions') == plan['conditions'], 'encoded manifest conditions mismatch')
    results = manifest.get('results')
    _require(type(results) is list and [r.get('name') for r in results] == [c['name'] for c in plan['conditions']],
             'encoded process coverage/order mismatch')
    launch, source = manifest['source_head'], manifest['binary_source_head']
    driver = (path / 'driver.py').read_bytes()
    _require(_sha(driver) == manifest['driver_sha256'] == _sha(_git_blob(launch, DRIVER)), 'driver source binding mismatch')
    protocol_blob = _git_blob(launch, PROTOCOL)
    _require(_sha(protocol_blob) == manifest['protocol_sha256'], 'protocol source binding mismatch')
    build_blob = _git_blob(launch, BUILD)
    _require(_sha(build_blob) == manifest['build_evidence_sha256'], 'build source binding mismatch')
    build = json.loads(build_blob)
    _require(build['source_commit'] == source and build['binaries']['rob_window_probe'] == manifest['binary_sha256'],
             'binary/build binding mismatch')
    _require(set(build['source_sha256']) == set(PROBE_SOURCES), 'probe source coverage mismatch')
    for name, digest in build['source_sha256'].items():
        _require(_sha(_git_blob(source, name)) == digest == _sha(_git_blob(launch, name)), 'probe source binding mismatch')
    plan_blob = _git_blob(launch, PLAN)
    _require(build['plan_path'] == PLAN and _sha(plan_blob) == manifest['plan_sha256'] == build['plan_sha256'],
             'plan source binding mismatch')
    actual_plan = json.loads(plan_blob)
    _require(type(actual_plan) is dict and set(actual_plan) == set(plan), 'registered plan shape mismatch')
    _fields(actual_plan, plan, 'registered encoded plan mismatch')
    _require(_sha(_git_blob(GATE_SOURCE['commit'], GATE_SOURCE['path'])) == GATE_SOURCE['sha256'],
             'original frozen gate source digest mismatch')
    profile_blob = _git_blob(launch, PROFILE)
    registered_policy = json.loads(profile_blob)['environment_profiles']['charging-thermal']['measurement_environment']
    registered_policy['preconditions']['cpufreq_governor'] = 'walt'
    policy = json.loads((path / 'environment-policy.json').read_text())
    envs = {f.name: json.loads(f.read_text()) for f in path.glob('*-environment.json')}
    expected_envs = {'initial-environment.json', 'final-environment.json'} | {
        c['name'] + '-' + suffix + '-environment.json' for c in plan['conditions'] for suffix in ('pre', 'post')}
    _require(set(envs) == expected_envs, 'encoded environment endpoint coverage mismatch')
    audit_environment(envs, policy, registered_policy)
    processes, residuals = [], []
    raw_cells = {}
    for entry, requested in zip(results, plan['conditions']):
        name = entry['name']
        _fields(entry, {'exit_code': 0, 'timed_out': False}, 'encoded process failed')
        _require((path / (name + '.stderr.log')).read_bytes() == b'', 'unexpected encoded stderr')
        stdout = (path / (name + '.stdout.jsonl')).read_bytes()
        _require(_sha(stdout) == entry['stdout_sha256'], 'encoded stdout SHA mismatch')
        records = [json.loads(line) for line in stdout.splitlines()]
        _require(len(records) == 8, 'encoded raw record layout mismatch')
        config, runtime, *rounds = records
        args = requested['args']; mask = args[args.index('--pointer-xor') + 1]
        mb = int(args[args.index('-m') + 1]); memory = mb * 1048576; iterations = max(131072, mb * 8192)
        expected = {'type': 'config', 'version': 2, 'class': 'nop', 'anchor': 'miss', 'n': 0, 'chain': 8,
                    'rounds': 3, 'iterations': iterations, 'memory_bytes': memory, 'chase_seed': 42,
                    'serial': False, 'paired': True, 'asymmetric': False, 'fsqrt_operand_bits': '0x3ff0000000000000',
                    'loop_offset': 64, 'loop_mod64': 0, 'branch_offset': 84, 'code_bytes': 92,
                    'fillers_per_iteration': 0, 'anchors_per_iteration': 2, 'pmu_type': 8,
                    'exclude_kernel': True, 'exclude_hv': True, 'events': [17, 8, 3, 23, 52, 55],
                    'backing_requested': '4k' if mb == 1 else 'thp2m', 'pointer_xor_requested': True,
                    'pointer_xor': mask, 'decode_instructions_per_iteration': 2, 'loop_instructions': 6}
        _fields(config, expected, 'encoded actual config mismatch')
        _require('collapse_requested' not in config, 'unregistered collapse intervention')
        _fields(runtime, {'type': 'runtime', 'cpu': 7, 'fpcr': 0, 'loop_address_mod64': 0,
                         'ring_nodes': memory // 64, 'distinct_lines_per_call': memory // 64,
                         'mapping_4k_verified': mb == 1, 'backing_verified': True,
                         'backing_page_bytes': 4096 if mb == 1 else 2097152}, 'encoded runtime/coverage mismatch')
        ids = runtime.get('event_ids')
        _require(type(ids) is list and len(ids) == 6 and all(type(x) is int and x > 0 for x in ids) and
                 len(set(ids)) == 6, 'encoded PMU event ID mismatch')
        _backing(runtime.get('backing_info'), memory)
        exports = entry.get('generated_code')
        _require(type(exports) is dict and set(exports) == {'parallel', 'serial'}, 'encoded paired code export coverage mismatch')
        code_shas = {}
        for member, generated in exports.items():
            code = (path / (name + '-' + member + '.bin')).read_bytes()
            serial = member == 'serial'
            _require(code == _code(mask, serial) and _sha(code) == generated['sha256'] and
                     _matches(generated['config'], dict(config, paired=False, serial=serial)), 'encoded generated code/config mismatch')
            code_shas[member] = _sha(code)
        for window, (number, serial, step) in zip(rounds, PAIR_ORDER):
            _fields(window, {'type': 'round', 'round': number, 'serial': serial, 'pair_step': step, 'backing_verified': True},
                    'encoded paired round identity mismatch')
            _require(all(type(window.get(k)) is int and window[k] > 0 for k in ('ns', 'enabled', 'running')) and
                     window['enabled'] == window['running'], 'encoded PMU timing/mux failure')
            metrics = window.get('metrics')
            _require(type(metrics) is dict and set(metrics) == set(EVENTS) and
                     all(type(x) is int and x >= 0 for x in metrics.values()) and metrics['0x11'] > 0,
                     'invalid encoded raw PMU counts')
            residual = metrics['0x8'] - (6 * iterations + 17)
            _require(abs(residual) <= max(1000, .01 * (6 * iterations + 17)), 'encoded retired count mismatch')
            residuals.append(residual)
            _backing(window.get('backing_before'), memory); _backing(window.get('backing_after'), memory)
        for serial in (False, True):
            ordered = sorted((r for r in rounds if r['serial'] is serial), key=lambda r: r['round'])
            raw_cells[name, serial] = {event: [r['metrics'][event] / iterations for r in ordered] for event in EVENTS}
        processes.append({'condition': name, 'stdout_sha256': _sha(stdout), 'actual_config': config,
                          'actual_runtime': runtime, 'generated_code_sha256': code_shas, 'windows': rounds})
    from tools.diagnostic.summarize_sm8650_minimal import summarize
    audited = {'runs': [summarize(path)]}
    _require(summary == audited, 'summary differs from audited encoded raw')
    _require(type(summary.get('runs')) is list and len(summary['runs']) == 1, 'one complete encoded run required')
    cells = _cells(summary['runs'][0])
    for cell in cells.values():
        _require(cell['counts_per_iteration'] == raw_cells[cell['condition'], cell['serial']], 'summary/raw count mismatch')
    return {'passed': True, 'raw_directory': path.name, 'manifest_sha256': _sha((path / 'manifest.json').read_bytes()),
            'source_head': launch, 'binary_source_head': source, 'binary_sha256': manifest['binary_sha256'],
            'source_sha256': build['source_sha256'], 'driver_sha256': _sha(driver),
            'build_evidence_path': BUILD, 'build_evidence_sha256': _sha(build_blob),
            'protocol_path': PROTOCOL, 'protocol_sha256': _sha(protocol_blob),
            'plan_path': PLAN, 'plan_sha256': _sha(plan_blob), 'registered_plan': actual_plan,
            'environment_policy_sha256': _sha((path / 'environment-policy.json').read_bytes()),
            'environment_profile_source': {'commit': launch, 'path': PROFILE, 'sha256': _sha(profile_blob),
                                           'overrides': {'preconditions.cpufreq_governor': 'walt'}},
            'environment_endpoints': {name: _sha((path / name).read_bytes()) for name in sorted(envs)},
            'environment_endpoints_count': len(envs), 'environment_preconditions_and_stability_passed': True,
            'max_cpu_c_range': audited['runs'][0]['max_cpu_c_range'],
            'all_raw_sha256': {f.name: _sha(f.read_bytes()) for f in sorted(path.iterdir()) if f.is_file()},
            'retired_minus_generated_kernel_range': [min(residuals), max(residuals)], 'processes': processes}


def main(argv=None):
    """技术失败不写资格；科学失败照常保存全部值及每mask失败门。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary', type=Path)
    parser.add_argument('--raw', required=True, type=Path)
    parser.add_argument('--mode', choices=(MODE,), default=MODE)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    summary = json.loads(args.summary.read_text())
    technical = audit_raw(args.raw, summary)
    result = qualify(summary['runs'][0])
    result.update(summary_input={'path': args.summary.name if args.summary.is_absolute() else args.summary.as_posix(),
                                 'sha256': _sha(args.summary.read_bytes())}, data_origin='device-raw',
                  technical_acceptance=technical, scientific_qualification='qualified' if result['qualified'] else 'not-qualified')
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps({'technical_passed': True, 'qualified_conditions': result['qualified_conditions']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
