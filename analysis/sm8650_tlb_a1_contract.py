# SPDX-License-Identifier: Apache-2.0
"""A1 最终消费合同：正式计划身份/覆盖、逐进程几何和有效统计。

锚点：R3-C/R5-C 与 2026-10-08 软件收口计划。planner 是条件身份的
权威，重复记录拒绝；consumer 不因 adapter 曾校验就跳过最终防线。
本模块不执行探针，不选择硬件模型，不对不合格数据补写或修复。
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import statistics
from typing import Any

from runner.plan import build_plan
from runner.errors import RunnerError
from .sm8650_tlb import TlbError

REPO_ROOT = Path(__file__).resolve().parents[1]
FORMAL_CONFIGS = {
    layer: f"configs/experiments/ptr-chase-sm8650-x4-tlb-a1-{suffix}.json"
    for layer, suffix in (("l1", "l1-main"), ("l2", "l2-repro"), ("l3", "l3-target"))
}
PLATFORM_PATH = "configs/platforms/redmi-k70pro-01.json"
DESCRIPTOR_FIELDS = ("set_hypothesis", "set_target", "set_window", "set_rounds",
    "set_pool_pages", "set_filler_pages", "set_regions", "set_region_scope",
    "set_nsets", "seed")


def canonical(value: Any) -> str:
    """类型保持的 JSON 规范形；dict 键序不分组，bool/int/float 不混同。"""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as error:
        raise TlbError(f"a1: invalid identity value: {error}") from error


def _integer(value: Any) -> bool:
    return type(value) is int


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def realized_processes(record: dict) -> list[dict]:
    """取公共 realized 或逐样本 realized；不将首样本替代全部进程。"""
    probe = record.get("probe")
    realized = probe.get("realized") if isinstance(probe, dict) else None
    if not isinstance(realized, dict) or not realized:
        raise TlbError("a1: missing-realized")
    if "domain_consistent" in realized and realized["domain_consistent"] is not True:
        raise TlbError("a1: mixed-domain")
    if "samples" not in realized:
        return [realized]
    samples = realized["samples"]
    if not isinstance(samples, list) or not samples:
        raise TlbError("a1: missing-realized-samples")
    if any(not isinstance(s, dict) or not isinstance(s.get("realized"), dict)
           for s in samples):
        raise TlbError("a1: invalid-realized-sample")
    return [s["realized"] for s in samples]


def validate_geometry(params: dict, realized: dict) -> None:
    """逐进程 requested/realized 最终核验；任何无效字段均命名 TlbError。

    所有 scope 都要求 purity；高字段按实际 active 槽位取值。空窗只用于
    专用标定，可有零 active；正式矩阵的 W/身份由正式 plan 另行约束。
    """
    if not isinstance(params, dict) or not isinstance(realized, dict):
        raise TlbError("a1: invalid geometry object")
    for key in DESCRIPTOR_FIELDS:
        expected, actual = params.get(key), realized.get(key)
        if not _integer(expected) or not _integer(actual) or actual != expected:
            raise TlbError(f"a1: descriptor mismatch {key}")
    scatter = params.get("set_scatter", 0)
    if not _integer(scatter) or realized.get("scatter") != scatter or type(realized.get("scatter")) is not int:
        raise TlbError("a1: descriptor mismatch scatter")
    if realized.get("mode") != "tlbset" or realized.get("page_kb") != "4":
        raise TlbError("a1: descriptor mismatch mode/page_kb")
    if realized.get("set_domain") != "multi-region":
        raise TlbError("a1: mixed-domain or single-region-fallback")
    regions, scope, window = (params[k] for k in
        ("set_regions", "set_region_scope", "set_window"))
    if not 1 <= regions <= 16 or not -1 <= scope < regions or window < 0:
        raise TlbError("a1: invalid scope/regions/window")
    nodes = realized.get("set_target_region_nodes")
    if not isinstance(nodes, list) or len(nodes) != regions:
        raise TlbError("a1: missing-region-nodes or region-node dimension mismatch")
    if any(not _integer(n) or n < 0 for n in nodes):
        raise TlbError("a1: invalid region-node type/count")
    expected_sum = window * max(params["set_nsets"], 1)
    if sum(nodes) != expected_sum:
        raise TlbError("a1: region-node sum differs from requested window")
    actual_active = sum(n > 0 for n in nodes)
    active = realized.get("set_active_regions")
    expected_active = (regions if scope < 0 else 1) if window > 0 else 0
    if not _integer(active) or active != actual_active or active != expected_active:
        raise TlbError(f"a1: active-regions {active} != expected {expected_active}")
    if scope >= 0 and nodes[scope] != expected_sum:
        raise TlbError("a1: scope-isolation-violated")
    if type(realized.get("set_region_vpn_hi_pure")) is not int or realized["set_region_vpn_hi_pure"] != 1:
        raise TlbError("a1: vpn-hi-impure")
    hi = realized.get("set_region_vpn_hi")
    if (not isinstance(hi, list) or len(hi) != regions
            or any(not _integer(h) or not 0 <= h <= 255 for h in hi)):
        raise TlbError("a1: missing or invalid actual vpn-hi")
    if window > 0 and scope < 0 and len({hi[i] for i, n in enumerate(nodes) if n}) != regions:
        raise TlbError("a1: actual vpn-hi does not separate active regions")


def geometry_gate(record: dict) -> tuple[bool, str]:
    """对所有进程执行几何门，返回命名降级；不抛 TypeError/IndexError。"""
    try:
        if not isinstance(record, dict):
            raise TlbError("a1: invalid record object")
        for realized in realized_processes(record):
            validate_geometry(record.get("params"), realized)
    except TlbError as error:
        return False, str(error).removeprefix("a1: ")
    return True, "ok"


@dataclass(frozen=True)
class ExpectedCase:
    """正式 planner 的一个完整条件单元；role 不由 seed/默认键猜测。"""
    layer: str
    experiment_id: str
    case_id: str
    params: dict
    control: dict
    target: dict
    repetitions: int
    protocol_version: str

    @property
    def key(self) -> tuple[str, str, str]:
        """完整条件身份；规范序列化避免 Python True==1 合并。"""
        return self.experiment_id, canonical(self.params), canonical(self.control)


def expected_cases(relative_path: str, layer: str, repo_root: Path | None = None) -> list[ExpectedCase]:
    """由已登记配置与平台展开 case；文件/配置错误统一为命名输入错误。"""
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    try:
        spec = json.loads((root / relative_path).read_text())
        platform = json.loads((root / PLATFORM_PATH).read_text())
        plan = build_plan(spec, platform)
    except (OSError, ValueError, KeyError, TypeError, RunnerError) as error:
        raise TlbError(f"a1: invalid contract configuration: {error}") from error
    if spec["id"] != Path(relative_path).stem:
        raise TlbError("a1: experiment id differs from registered config path")
    return [ExpectedCase(layer, plan.experiment_id, c.id,
        {k: rv.value for k, rv in c.params},
        {"mechanism": c.control.mechanism, "value": c.control.value},
        plan.target, c.repetitions, plan.protocol_version) for c in plan.cases]


def validate_record(record: dict, expected: ExpectedCase) -> dict:
    """返回完整有效 metric 映射；所有 observations 和 realized 均需合格。

    进程数严格等于 plan 的 repetitions；每进程至少一个有效轮、三类轮数
    守恒、事件有效轮等于窗口有效轮。无效/mux 轮已由探针排除均值，保留
    披露，不另造无依据的比例排除线（软件收口计划，§5.5）。
    """
    if record.get("schema_version") != "2.0" or record.get("status") != "ok":
        raise TlbError("a1: record status/schema is not eligible")
    environment = record.get("environment")
    if (not isinstance(environment, dict) or canonical(record.get("target")) != canonical(expected.target)
            or canonical(environment.get("control")) != canonical(expected.control)):
        raise TlbError("a1: target/control identity mismatch")
    probe = record.get("probe", {})
    if not isinstance(probe, dict) or probe.get("name") != "ptr_chase" or probe.get("protocol_version") != expected.protocol_version:
        raise TlbError("a1: probe/protocol identity mismatch")
    ok, why = geometry_gate(record)
    if not ok:
        raise TlbError(f"a1: record gate rejected ({why})")
    snapshot = environment.get("state_snapshot", {})
    if not isinstance(snapshot, dict):
        raise TlbError("a1: invalid environment identity snapshot")
    policy = snapshot.get("policy_result")
    if policy is not None and (not isinstance(policy, dict) or policy.get("valid") is not True):
        raise TlbError("a1: environment policy is not valid")
    metrics = record.get("metrics")
    if not isinstance(metrics, list) or not metrics or any(not isinstance(m, dict) for m in metrics):
        raise TlbError("a1: missing metrics")
    names = [m.get("name") for m in metrics]
    if any(not isinstance(n, str) for n in names) or len(set(names)) != len(names):
        raise TlbError("a1: duplicate or invalid metric name")
    by_name = {m["name"]: m for m in metrics}
    required = {"window_valid_rounds", "window_invalid_rounds", "window_mux_rounds", "probe_latency_ns"}
    required.update(f"pmu.{e['name']}.{suffix}" for e in expected.params["pmu_events"]
                    for suffix in ("count", "valid_rounds"))
    if missing := sorted(required - by_name.keys()):
        raise TlbError(f"a1: missing required metrics {missing}")
    n = expected.repetitions
    references: dict[int, str] = {}
    observations_by_name = {}
    for name, metric in by_name.items():
        if name in required:
            unit = "rounds" if name.startswith("window_") or name.endswith(".valid_rounds") else "ns" if name == "probe_latency_ns" else "events"
            if metric.get("unit") != unit:
                raise TlbError(f"a1: metric {name} unit differs from estimator contract")
        obs = metric.get("observations")
        if type(metric.get("repetitions")) is not int or metric["repetitions"] != n:
            raise TlbError(f"a1: metric {name} repetitions differ from plan")
        if not isinstance(obs, list) or len(obs) != n or any(not isinstance(o, dict) for o in obs):
            raise TlbError(f"a1: metric {name} observations need exactly {n} samples")
        indices = [o.get("sample_index") for o in obs]
        if any(not _integer(i) for i in indices) or sorted(indices) != list(range(n)):
            raise TlbError(f"a1: metric {name} sample indices incomplete/duplicated")
        ordered = sorted(obs, key=lambda o: o["sample_index"])
        for observation in ordered:
            index, value = observation["sample_index"], observation.get("value")
            ref = observation.get("raw_sample_ref")
            if not _number(value):
                raise TlbError(f"a1: metric {name} needs finite observations")
            if not isinstance(ref, str) or not ref or (index in references and references[index] != ref):
                raise TlbError("a1: metric sample raw references disagree")
            references[index] = ref
        if len(set(references.values())) != n:
            raise TlbError("a1: duplicate process raw sample reference")
        median = statistics.median(o["value"] for o in ordered)
        stats = metric.get("statistics")
        if (not _number(metric.get("value")) or not isinstance(stats, dict)
                or not _number(stats.get("median"))
                or not math.isclose(metric["value"], median, rel_tol=1e-12, abs_tol=1e-12)
                or not math.isclose(stats["median"], median, rel_tol=1e-12, abs_tol=1e-12)):
            raise TlbError(f"a1: metric {name} median differs from observations")
        observations_by_name[name] = ordered
    for i in range(n):
        valid, invalid, mux = (observations_by_name[k][i]["value"] for k in
            ("window_valid_rounds", "window_invalid_rounds", "window_mux_rounds"))
        if (any(v < 0 or int(v) != v for v in (valid, invalid, mux)) or valid < 1
                or valid + invalid + mux != expected.params["set_rounds"] - 1):
            raise TlbError("a1: invalid window round qualification/balance")
        for e in expected.params["pmu_events"]:
            if observations_by_name[f"pmu.{e['name']}.valid_rounds"][i]["value"] != valid:
                raise TlbError("a1: event valid rounds differ from window rounds")
    realized = probe["realized"]
    if "samples" in realized:
        samples = realized["samples"]
        indices = [s.get("sample_index") for s in samples]
        if len(samples) != n or any(not _integer(i) for i in indices) or sorted(indices) != list(range(n)):
            raise TlbError("a1: realized samples incomplete/duplicated")
        if any(s.get("raw_sample_ref") != references[s["sample_index"]] for s in samples):
            raise TlbError("a1: realized sample raw references disagree")
    return by_name


def bind_formal_records(records: list[dict], repo_root: Path | None = None) -> list[tuple[ExpectedCase, dict, dict]]:
    """按正式 128-case 合同绑定，拒绝未知/缺失/重复条件；顺序不影响结果。"""
    cases = [c for layer, path in FORMAL_CONFIGS.items() for c in expected_cases(path, layer, repo_root)]
    expected = {c.key: c for c in cases}
    if len(cases) != 128 or len(expected) != 128:
        raise TlbError("a1: formal configuration must define 128 unique cases")
    ids = {c.experiment_id for c in cases}
    bound, run_ids, raw_refs = {}, set(), set()
    if not isinstance(records, list):
        raise TlbError("a1: records must be a list")
    for record in records:
        if not isinstance(record, dict):
            raise TlbError("a1: invalid record object")
        exp, params = record.get("experiment_id"), record.get("params")
        if exp not in ids:
            raise TlbError(f"a1: unknown layer from experiment_id {exp!r}")
        if not isinstance(params, dict):
            raise TlbError("a1: invalid params identity")
        if exp.endswith("l3-target"):
            if type(params.get("set_target")) is not int or params["set_target"] not in (7, 42, 100, 200):
                raise TlbError("a1: L3 exact coverage violation: unexpected target")
            if type(params.get("set_window")) is not int or params["set_window"] not in (8, 12):
                raise TlbError("a1: L3 window grid violation: unexpected window")
        environment = record.get("environment")
        if not isinstance(environment, dict):
            raise TlbError("a1: invalid environment/control identity")
        control = environment.get("control")
        key = exp, canonical(params), canonical(control)
        if key not in expected:
            raise TlbError(f"a1: plan identity mismatch for {exp!r}")
        if key in bound:
            raise TlbError(f"a1: duplicate case record for {expected[key].case_id}")
        run_id = record.get("run_id")
        if not isinstance(run_id, str) or not run_id or run_id in run_ids:
            raise TlbError("a1: missing or duplicate record run_id")
        metrics = validate_record(record, expected[key])
        refs = {o["raw_sample_ref"] for o in metrics["pmu.l2d_tlb_refill.count"]["observations"]}
        if refs & raw_refs:
            raise TlbError("a1: duplicate raw process across case records")
        run_ids.add(run_id)
        raw_refs.update(refs)
        bound[key] = expected[key], record, metrics
    if missing := sorted(expected.keys() - bound.keys()):
        raise TlbError(f"a1: plan coverage incomplete: missing {len(missing)} cases; first={expected[missing[0]].case_id}")
    return [bound[k] for k in sorted(bound)]
