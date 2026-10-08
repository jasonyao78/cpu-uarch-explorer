# SPDX-License-Identifier: Apache-2.0
"""A1 标定→不可变冻结工件→正式消费的必经谱系核验。

R5-D：数值决策仍由 freeze_thresholds 实现；本模块锚定实际输入、配置、
代码、二进制与环境 regime，并验证标定/正式数据隔离。哈希提供漂移检测，
不是签名或设备测量真实性证明。不执行探针，不修复输入记录。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .load import load_run
from .sm8650_tlb import TlbError
from .sm8650_tlb_a1_contract import (REPO_ROOT, FORMAL_CONFIGS, PLATFORM_PATH,
    canonical, expected_cases, validate_record)

CALIBRATION_CONFIGS = {role:
    f"configs/experiments/ptr-chase-sm8650-x4-tlb-a1-calibration-{role}.json"
    for role in ('floor', 'scatter')}
CONFIG_PATHS = tuple(sorted((*FORMAL_CONFIGS.values(), *CALIBRATION_CONFIGS.values(), PLATFORM_PATH)))
# 影响条件展开、采集、解析、统计或最终判定的运行时代码。文档提交不使工件失效。
CODE_PATHS = tuple(sorted([
    'analysis/load.py', 'analysis/sm8650_tlb_a1.py',
    'analysis/sm8650_tlb_a1_contract.py', 'analysis/sm8650_tlb_a1_freeze.py',
    'analysis/sm8650_tlb_a1_cli.py', 'runner/engine.py', 'runner/artifacts.py',
    'runner/adapters/base.py', 'runner/adapters/ptr_chase.py', 'runner/plan.py',
    'runner/resolve.py', 'runner/records.py', 'runner/statistics.py',
    'runner/environment/policy.py', 'runner/environment/android_state.py',
    'probes/cache-mem/ptr_chase.cpp', 'probes/common/perf_window.h',
    'probes/common/tlb_set_collect.h', 'probes/common/page_policy.h',
    'probes/platform/linux/perf_counter.cpp', 'probes/platform/linux/perf_counter.h',
]))
RUN_FILES = ('records.jsonl', 'run-manifest.json', 'artifacts.jsonl')
RULES = {'grid': [2.0, 3.0, 4.0, 5.0], 'floor_mad_max': 1.0,
    'scatter_median_max': 1.0, 'floor_mad_multiplier': 5.0,
    'pilot_onset_reference': 6.0, 'pilot_fraction_max': 0.5,
    'classification_floor': 1.0, 'platform_peak_fraction': 0.8}


def file_sha(path: Path) -> str:
    """文件缺失同样是冻结输入漂移；报命名错误。"""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise TlbError(f'a1: frozen input unavailable: {path}: {error}') from error


def artifact_digest(artifact: dict) -> str:
    """工件内容摘要排除自身字段；独立复算决策才是消费资格核验。"""
    return hashlib.sha256(canonical({k: v for k, v in artifact.items()
                                    if k != 'artifact_sha256'}).encode()).hexdigest()


def _json_lines(path: Path) -> list[dict]:
    try:
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError('expected JSON objects')
        return rows
    except (OSError, ValueError) as error:
        raise TlbError(f'a1: invalid input file {path}: {error}') from error


def load_audited_run(directory: Path) -> tuple[list[dict], dict]:
    """真实 loader 回读 + manifest 闭合；禁止静默忽略旧 schema/失败记录。

    raw 字节允许按仓库纪律离线归档；manifest 中每个引用及 SHA 必须闭合。
    工件锚定 manifest 字节，外部 raw 保存/复核仍由采数方负责。
    """
    directory = Path(directory).resolve()
    hashes = {name: file_sha(directory / name) for name in RUN_FILES}
    rows = _json_lines(directory / 'records.jsonl')
    artifacts = _json_lines(directory / 'artifacts.jsonl')
    try:
        run = load_run(directory)
    except (OSError, ValueError, AttributeError) as error:
        raise TlbError(f'a1: cannot load run {directory}: {error}') from error
    manifest = run.manifest
    if not isinstance(manifest, dict):
        raise TlbError('a1: invalid run manifest object')
    records = run.ok_records
    if (not rows or len(records) != len(rows) or run.failed_records
            or manifest.get('summary') != {'total': len(rows), 'ok': len(rows),
                'failed': 0, 'skipped': 0, 'unsupported': 0}
            or any(r.get('experiment_id') != manifest.get('experiment_id') for r in rows)
            or any(r.get('target') != manifest.get('target') for r in rows)):
        raise TlbError('a1: run manifest/eligible record closure failed')
    entries = {a.get('id'): a for a in artifacts if isinstance(a.get('id'), str)}
    if len(entries) != len(artifacts):
        raise TlbError('a1: duplicate or missing artifact id')
    for record in records:
        probe = record.get('probe')
        metrics = record.get('metrics')
        if (not isinstance(probe, dict) or not isinstance(probe.get('artifact'), dict)
                or not isinstance(metrics, list) or any(not isinstance(m, dict)
                or not isinstance(m.get('observations'), list)
                or any(not isinstance(o, dict) for o in m['observations']) for m in metrics)):
            raise TlbError('a1: invalid record artifact references')
        binaries = [a for a in artifacts if a.get('kind') == 'probe-binary'
                    and a.get('sha256') == probe.get('artifact', {}).get('sha256')
                    and a.get('source') == probe.get('git')]
        if len(binaries) != 1:
            raise TlbError('a1: probe binary artifact closure failed')
        for metric in record.get('metrics', []):
            for observation in metric.get('observations', []):
                entry = entries.get(observation.get('raw_sample_ref'))
                if (entry is None or entry.get('kind') != 'raw-samples'
                        or not _valid_sha(entry.get('sha256'))):
                    raise TlbError('a1: raw sample artifact closure failed')
    return records, {'directory': str(directory), 'files': hashes}


def _valid_sha(value, length=64):
    return isinstance(value, str) and len(value) == length and all(c in '0123456789abcdef' for c in value)


def record_provenance(record: dict) -> dict:
    """跨块只比较稳定 regime；温度/瞬时频率不是身份字段。

    每块 before/after 合格且稳定为必要证据；必须保持充电态、屏幕/idle、
    服务、governor 和频率限制。真实 policy7 时钟仍不是此快照能证明的。
    """
    probe, environment = record.get('probe'), record.get('environment')
    if not isinstance(probe, dict) or not isinstance(environment, dict):
        raise TlbError('a1: invalid provenance identity')
    source, artifact = probe.get('git'), probe.get('artifact')
    if (not isinstance(source, dict) or source.get('dirty') is not False
            or not _valid_sha(source.get('commit'), 40) or not isinstance(artifact, dict)
            or not _valid_sha(artifact.get('sha256'))):
        raise TlbError('a1: probe provenance needs clean source and binary digest')
    snapshot = environment.get('state_snapshot')
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('policy_result'), dict):
        raise TlbError('a1: qualified environment snapshot required')
    policy = snapshot['policy_result']
    if policy.get('valid') is not True or policy.get('stage') != 'after' or policy.get('violations') != []:
        raise TlbError('a1: environment policy must pass before and after')
    def regime(state):
        try:
            cpufreq = {p: {k: v[k] for k in ('governor', 'min_khz', 'max_khz')}
                       for p, v in state['cpufreq'].items()}
            if set(cpufreq) != {'policy0', 'policy2', 'policy5', 'policy7'}:
                raise ValueError('missing frequency policy')
            return {'cpufreq': cpufreq,
                'power': {k: state['power'][k] for k in ('powered', 'screen_on', 'wakefulness')},
                'idle': {k: state['device_idle'][k] for k in ('charging', 'force_idle')},
                'airplane_mode': state['airplane_mode'], 'services': state['services']}
        except (KeyError, TypeError, AttributeError, ValueError) as error:
            raise TlbError(f'a1: incomplete environment regime: {error}') from error
    from runner.environment.policy import evaluate_preconditions_full, evaluate_stability_full
    from runner.errors import RunnerError
    try:
        platform = json.loads((REPO_ROOT / PLATFORM_PATH).read_text())
        required = platform['environment_profiles']['charging-thermal']['measurement_environment']
        before_errors, _ = evaluate_preconditions_full(snapshot.get('before'), required)
        after_errors, _ = evaluate_preconditions_full(snapshot.get('after'), required)
        drift_errors, _ = evaluate_stability_full(snapshot.get('before'), snapshot.get('after'), required)
        if before_errors or after_errors or drift_errors:
            raise TlbError('a1: environment policy reevaluation rejected input')
    except (RunnerError, OSError, ValueError, KeyError) as error:
        raise TlbError(f'a1: invalid environment policy evidence: {error}') from error
    before, after = regime(snapshot.get('before')), regime(snapshot.get('after'))
    if canonical(before) != canonical(after):
        raise TlbError('a1: environment regime drift within record')
    return {'target': record.get('target'), 'control': environment.get('control'),
        'probe': {'name': probe.get('name'), 'protocol_version': probe.get('protocol_version'),
                  'source': source, 'sha256': artifact['sha256']},
        'environment_regime': before,
        'accepted_nonbaseline': sorted(policy.get('accepted_nonbaseline', []))}


def _refs(records):
    return sorted({o['raw_sample_ref'] for r in records for m in r['metrics']
                   for o in m['observations']})


def freeze_a1_from_runs(floor_run: Path, scatter_run: Path, *, repo_root: Path | None = None) -> dict:
    """专用两块标定记录冻结规则；STOP 也携带完整谱系，但不能进入正式判定。"""
    from .sm8650_tlb_a1 import freeze_thresholds
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    anchors, values, all_records = {}, {}, []
    for role, directory in (('floor', floor_run), ('scatter', scatter_run)):
        records, anchor = load_audited_run(directory)
        cases = expected_cases(CALIBRATION_CONFIGS[role], 'calibration', root)
        if len(cases) != 1 or len(records) != 1:
            raise TlbError(f'a1: calibration {role} must contain one planned case')
        case, record = cases[0], records[0]
        if (record.get('experiment_id') != case.experiment_id
                or canonical(record.get('params')) != canonical(case.params)):
            raise TlbError(f'a1: calibration {role} identity mismatch')
        if not isinstance(record.get('run_id'), str) or not record['run_id']:
            raise TlbError('a1: calibration record id required')
        metrics = validate_record(record, case)
        values[role] = [o['value'] for o in sorted(metrics['pmu.l2d_tlb_refill.count']['observations'],
                                                key=lambda o: o['sample_index'])]
        anchors[role] = {**anchor, 'experiment_id': case.experiment_id,
                         'record_ids': [record['run_id']], 'raw_refs': _refs(records)}
        all_records.extend(records)
    provenance = record_provenance(all_records[0])
    if any(canonical(record_provenance(r)) != canonical(provenance) for r in all_records):
        raise TlbError('a1: calibration provenance/regime mismatch')
    if (all_records[0]['run_id'] == all_records[1]['run_id']
            or set(anchors['floor']['raw_refs']) & set(anchors['scatter']['raw_refs'])):
        raise TlbError('a1: calibration inputs are not disjoint')
    import statistics
    artifact = {'schema_version': 'a1-freeze-v1',
        **freeze_thresholds(values['floor'], statistics.median(values['scatter'])),
        'rules': json.loads(canonical(RULES)), 'calibration': anchors, 'provenance': provenance,
        'config_sha256': {p: file_sha(root / p) for p in CONFIG_PATHS},
        'code_sha256': {p: file_sha(root / p) for p in CODE_PATHS}}
    artifact['artifact_sha256'] = artifact_digest(artifact)
    return artifact


def verify_frozen_artifact(frozen: dict, records: list[dict], *, repo_root: Path | None = None) -> None:
    """正式消费必经：独立重算冻结决策，并验证当前代码/配置和跨数据隔离。"""
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    if not isinstance(frozen, dict) or frozen.get('frozen') is not True:
        raise TlbError('a1: thresholds not frozen (STOP or missing artifact)')
    if frozen.get('schema_version') != 'a1-freeze-v1':
        raise TlbError('a1: unanchored-thresholds: a1-freeze-v1 artifact required')
    if frozen.get('artifact_sha256') != artifact_digest(frozen):
        raise TlbError('a1: frozen artifact digest mismatch')
    for key, paths in (('code_sha256', CODE_PATHS), ('config_sha256', CONFIG_PATHS)):
        expected = {p: file_sha(root / p) for p in paths}
        if frozen.get(key) != expected:
            raise TlbError(f'a1: frozen {key} drift')
    try:
        calibration = frozen['calibration']
        for role in CALIBRATION_CONFIGS:
            anchor = calibration[role]
            actual = {p: file_sha(Path(anchor['directory']) / p) for p in RUN_FILES}
            if anchor['files'] != actual:
                raise TlbError('a1: calibration input drift')
        rebuilt = freeze_a1_from_runs(calibration['floor']['directory'],
                                     calibration['scatter']['directory'], repo_root=root)
        if canonical(rebuilt) != canonical(frozen):
            raise TlbError('a1: frozen decision differs from calibration inputs')
        if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
            raise TlbError('a1: records must be a list of objects')
        ids = {v for a in calibration.values() for v in a['record_ids']}
        refs = {v for a in calibration.values() for v in a['raw_refs']}
        for record in records:
            if record.get('run_id') in ids or set(_refs([record])) & refs:
                raise TlbError('a1: calibration/formal overlap')
            if canonical(record_provenance(record)) != canonical(frozen['provenance']):
                raise TlbError('a1: formal provenance/regime identity mismatch')
    except (KeyError, TypeError, AttributeError) as error:
        raise TlbError(f'a1: invalid frozen or formal input: {error}') from error
