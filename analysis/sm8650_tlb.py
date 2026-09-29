# SPDX-License-Identifier: Apache-2.0
"""SM8650 X4 TLB 层级探测逐样本分析器（任务书 v4.1）。

与 `analysis.sm8650_x4_p0prime` 并列的独立模块（两任务的冻结规则各自
演化，刻意复制契约链而非共享实现）。证据契约与 P0″ 同构：schema
v2、target/probe 校验、metric 集合相等、逐样本 sample_index 对齐、
PMU 编码与 seed 逐样本一致、time_running==time_enabled（multiplex
样本拒绝并登记，同记录其余样本保留）、全失败 run 进 rejected 不抛
错——契约缺项一律硬错误，本探测不接受"大概齐全"的记录。

只消费 G0 事件组记录：G0 确立前的三事件历史 run（如
20260927T182613Z，无 `pmu.mem_access_rd.count`）不满足 metric 集合
契约，会被硬错误拒绝——by-design fail-closed，不为旧数据放宽契约。

分组键：(run_label, buffer_kb, seed, page_policy_actual, ring_passes)。
ring passes 由记录参数直接推出（loads / (buffer_kb×1024/stride)），
不依赖配置名约定。派生密度按任务书 §3.2 统一分母：R_e = 1000×C_e /
N_timed_loads；`0x05` 在 4096 页可超过 1000/1k（事件总数大于 timed
loads 数），分析器保留原值——不截断、不改写为 miss 概率。

事件资格门控（§3.1/S4）：每组的 unqualified_events 列出资格不足
（candidate 或未注册）的 PMU 事件；存在资格不足事件时
detect_knee_candidates 门控返回空。SEMANTICS_UNVERIFIED 只阻断结论
晋升，不阻断采集与审计——样本照常入表（否则 Gate 1 正控无法完成）。

knee 终态机（§6.2.2/6.2.8-1/6.2.6 冻结规则）：detect_knee_candidates
做相邻页数点对的三条件提名（R_0x05 比值 ≥2.0、绝对增量 ≥50/1k、
cyc/load 比值 ≥1.15）；adjudicate_knee 在其上判定终态——左删失优先
（R_0x05(32 页) ≥100/1k → LEFT_CENSORED，先于提名执行）、无候选 →
RIGHT_CENSORED、稳定条件不足（<3/4 order_seed 区间相互重叠 / 未覆盖
8/512 双训练量）→ ORDER_SENSITIVE / TRAINING_SENSITIVE、齐备 →
INTERVAL_IDENTIFIED。walk-onset（§6.2.3/6.2.8-5）：detect_walk_onset
按每个 order_seed 各自的逐样本地板（≥8/10 样本 >0.5/1k）+ 点中位数
≥1.0/1k + 下一页数点持续三条件判 onset；跨 seed 区间一致才报
INTERVAL_IDENTIFIED，8192 页仍未满足 → RIGHT_CENSORED。

双峰标记（任务书 §9.2 复用契约）：移植 sm8650_x4_p0prime 的预注册规
则（排序后相邻比值 ≥4 且两侧各 ≥2 样本，零值按比值未定义跳过），目
标字段钉为 l1d_tlb_refill_per_1k——knee 判据的消费字段、逐进程布局
/着色方差的主要暴露面。该标记只服务于"中位数不得掩盖双态"的报告纪
律，不构成任何容量推断。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from runner.statistics import summarize

from .load import load_run


class TlbError(ValueError):
    """输入不满足 SM8650 TLB 探测证据契约（含注册表结构非法）。"""


_LATENCY = "latency_ns"
# metric 名 → (期望 type, 期望 config, 派生字段名, 归一化系数)
_PMU_EVENTS = {
    "pmu.cycles.count": (8, 0x11, "cyc_per_load", 1.0),
    "pmu.mem_access_rd.count": (8, 0x66, "mem_rd_per_1k", 1000.0),
    "pmu.l1d_tlb_refill.count": (8, 0x05, "l1d_tlb_refill_per_1k", 1000.0),
    "pmu.dtlb_walk.count": (8, 0x34, "dtlb_walk_per_1k", 1000.0),
}
_REQUIRED_METRICS = {_LATENCY, *_PMU_EVENTS}
_BACKING_ORDER = {"base": 0, "mixed": 1, "thp": 2, "hugetlb-2m": 3,
                  "platform-default": 4}
# 与 runner/adapters/ptr_chase.py 同款：vma_base 只认小写 hex 地址形态。
_VMA_BASE_RE = re.compile(r"^0x[0-9a-f]+$")

# §6.2.2 knee 候选三条件的冻结阈值（改阈值 = 改冻结规则，走任务书变更）
_KNEE_REFILL_RATIO = 2.0
_KNEE_REFILL_DELTA_PER_1K = 50.0
_KNEE_CYC_RATIO = 1.15

# §6.2.8-1 左删失阈值（先于 knee 检测执行；改阈值 = 改冻结规则）
_LEFT_CENSOR_PAGES = 32
_LEFT_CENSOR_REFILL_PER_1K = 100.0

# §6.2.3 walk-onset 三条件的冻结阈值（改阈值 = 改冻结规则）
_WALK_ONSET_MIN_PER_1K = 1.0
_WALK_FLOOR_PER_1K = 0.5
_WALK_FLOOR_MIN_SAMPLES = 8

# §6.2.6 稳定条件的覆盖要求（改阈值 = 改冻结规则）
_STABLE_MIN_SEED_OVERLAP = 3  # ≥3/4 个 order_seed 致密区间相互重叠
_STABLE_MIN_TRAININGS = 2     # 8/512 ring passes 两种训练量同制度

# 双峰标记规则（任务书 §9.2 复用契约：移植 sm8650_x4_p0prime 的预注册
# 规则；改阈值 = 改冻结规则）
_BIMODAL_RATIO = 4.0
_BIMODAL_MIN_SIDE = 2

_QUALIFICATIONS = ("candidate", "qualified")

_DERIVED_FIELDS = tuple(derived for _, _, derived, _ in _PMU_EVENTS.values())


@dataclass
class AnalysisResult:
    """一次 analyze_records 的产物：分组 + 被拒绝样本的审计行。"""

    run_label: str
    groups: list[dict] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


class PmuEventRegistry:
    """事件资格注册表（§3.1/S4）：(type, config) → qualification。

    资格两级：qualified 允许事件参与正式结构结论；candidate/未注册
    一律 SEMANTICS_UNVERIFIED——只阻断结论晋升，不阻断采集与审计。
    """

    def __init__(self, events: dict[tuple[int, int], dict]) -> None:
        self._events = events

    def qualification(self, pmu_type: int, pmu_config: int) -> str | None:
        """查 (type, config) 的资格级别；未注册返回 None。"""
        entry = self._events.get((pmu_type, pmu_config))
        return entry["qualification"] if entry is not None else None


def load_registry(path: str | Path) -> PmuEventRegistry:
    """加载注册表；结构非法（缺 events 数组、type/config 形态错、资格值
    越界、(type, config) 重复）都是硬错误——门控输入不接受"大概齐全"。"""
    context = f"registry {path}"
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise TlbError(f"{context}: unreadable ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise TlbError(f"{context}: invalid JSON ({exc})") from exc
    if not isinstance(document, dict) or not isinstance(document.get("events"), list):
        raise TlbError(f"{context}: object with events array required")
    indexed: dict[tuple[int, int], dict] = {}
    for entry in document["events"]:
        if not isinstance(entry, dict):
            raise TlbError(f"{context}: event entry must be an object")
        entry_context = f"{context}/event={entry.get('name')}"
        pmu_type = entry.get("type")
        config = entry.get("config")
        if not isinstance(pmu_type, int) or not isinstance(config, str):
            raise TlbError(
                f"{entry_context}: integer type and hex config string required"
            )
        try:
            pmu_config = int(config, 16)
        except ValueError:
            raise TlbError(
                f"{entry_context}: config {config!r} is not a hex string"
            ) from None
        qualification = entry.get("qualification")
        if qualification not in _QUALIFICATIONS:
            raise TlbError(
                f"{entry_context}: qualification {qualification!r} "
                f"not in {sorted(_QUALIFICATIONS)}"
            )
        if (pmu_type, pmu_config) in indexed:
            raise TlbError(
                f"{entry_context}: duplicate (type={pmu_type}, config={config})"
            )
        indexed[(pmu_type, pmu_config)] = entry
    return PmuEventRegistry(indexed)


def _unqualified_events(registry: PmuEventRegistry | None) -> list[str]:
    """资格不足（非 qualified）的 PMU 事件名列表（按名排序，确定性）。"""
    return [
        name
        for name, (pmu_type, pmu_config, _, _) in sorted(_PMU_EVENTS.items())
        if registry is None
        or registry.qualification(pmu_type, pmu_config) != "qualified"
    ]


def _observations_by_index(metric: dict, context: str) -> dict[int, dict]:
    observations = metric.get("observations")
    if not isinstance(observations, list) or not observations:
        raise TlbError(f"{context}: metric {metric.get('name')} has no observations")
    indexed: dict[int, dict] = {}
    for observation in observations:
        index = observation.get("sample_index")
        if not isinstance(index, int) or index < 0:
            raise TlbError(f"{context}: invalid sample_index {index!r}")
        if index in indexed:
            raise TlbError(f"{context}: duplicate sample_index {index}")
        indexed[index] = observation
    return indexed


def _samples_from_record(record: dict, run_label: str,
                         rejected: list[str]) -> list[dict]:
    context = f"{run_label}/buffer={record.get('params', {}).get('buffer_kb')}KiB"
    if record.get("schema_version") != "2.0":
        raise TlbError(f"{context}: schema v2 record required")
    if record.get("target", {}).get("target_id") != "redmi-k70pro-01":
        raise TlbError(f"{context}: unexpected target")
    probe = record.get("probe", {})
    if probe.get("name") != "ptr_chase" or probe.get("protocol_version") != "1.2":
        raise TlbError(f"{context}: ptr_chase protocol 1.2 required")

    params = record.get("params", {})
    buffer_kb = params.get("buffer_kb")
    loads = params.get("loads")
    stride = params.get("stride", 64)
    if not isinstance(buffer_kb, int) or buffer_kb <= 0:
        raise TlbError(f"{context}: positive integer buffer_kb required")
    if not isinstance(loads, int) or loads <= 0:
        raise TlbError(f"{context}: positive integer loads required")
    if not isinstance(stride, int) or stride <= 0:
        raise TlbError(f"{context}: positive integer stride required")
    slots = (buffer_kb * 1024) // stride
    if slots < 2:
        raise TlbError(f"{context}: buffer too small for stride")
    ring_passes = loads / slots

    metrics = record.get("metrics", [])
    by_name = {metric.get("name"): metric for metric in metrics}
    if len(by_name) != len(metrics) or set(by_name) != _REQUIRED_METRICS:
        raise TlbError(
            f"{context}: metric set {sorted(str(name) for name in by_name)} "
            f"!= {sorted(_REQUIRED_METRICS)}"
        )
    indexed = {
        name: _observations_by_index(metric, context)
        for name, metric in by_name.items()
    }
    latency_indexes = set(indexed[_LATENCY])
    for name, observations in indexed.items():
        if set(observations) != latency_indexes:
            raise TlbError(f"{context}: {name} sample_index set does not align")

    samples = []
    for sample_index in sorted(latency_indexes):
        sample_context = f"{context}/sample={sample_index}"
        latency = indexed[_LATENCY][sample_index]
        actual = latency.get("page_policy_actual")
        if actual not in _BACKING_ORDER:
            raise TlbError(f"{sample_context}: unknown page backing {actual!r}")
        seed = latency.get("seed")
        if not isinstance(seed, int) or seed < 0:
            raise TlbError(f"{sample_context}: seed missing or invalid ({seed!r})")
        vma_base = latency.get("vma_base")
        if vma_base is not None and not (
            isinstance(vma_base, str) and _VMA_BASE_RE.fullmatch(vma_base)
        ):
            raise TlbError(
                f"{sample_context}: vma_base must be a lowercase hex address "
                f"({vma_base!r})"
            )

        sample = {
            "run_label": run_label,
            "buffer_kb": buffer_kb,
            "page_policy_actual": actual,
            "ring_passes": ring_passes,
            "seed": seed,
            "sample_index": sample_index,
            "latency_ns": float(latency["value"]),
            "loads": loads,
        }
        if vma_base is not None:
            # 建链缓冲区起始 VA（任务书路线 A 布局观测）；旧记录无此字
            # 段，保持可选，不升级为硬错误。
            sample["vma_base"] = vma_base
        multiplexed = False
        for name, (expected_type, expected_config, derived_name, scale) in _PMU_EVENTS.items():
            observation = indexed[name][sample_index]
            if (observation.get("pmu_type"), observation.get("pmu_config")) != (
                expected_type,
                expected_config,
            ):
                raise TlbError(f"{sample_context}: {name} has unexpected PMU encoding")
            if observation.get("seed") != seed:
                raise TlbError(f"{sample_context}: {name} seed disagrees with latency metric")
            enabled = observation.get("time_enabled_ns")
            running = observation.get("time_running_ns")
            if not isinstance(enabled, int) or not isinstance(running, int):
                raise TlbError(f"{sample_context}: {name} has invalid PMU time")
            if running > enabled:
                raise TlbError(
                    f"{sample_context}: {name} running time exceeds enabled time"
                )
            if running <= 0 or running != enabled:
                multiplexed = True
                break
            sample[derived_name] = float(observation["value"]) / loads * scale
        if multiplexed:
            rejected.append(f"{sample_context}: multiplexed or zero-running PMU sample")
            continue
        samples.append(sample)
    return samples


def detect_knee_candidates(rows: list[dict],
                           unqualified_events: Iterable[str] = ()
                           ) -> list[tuple[int, int]]:
    """§6.2.2 相邻页数点对的三条件提名。

    rows 为每点 {"pages", "l1d_tlb_refill_per_1k", "cyc_per_load"}（组中
    位数），内部按页数排序；返回候选区间 [(p_i, p_{i+1}), ...]。任一事
    件资格不足（unqualified_events 非空）门控返回空——SEMANTICS_UNVERIFIED
    不出结论。终态判定（左删失优先 / RIGHT_CENSORED / §6.2.6 稳定条件）
    见 adjudicate_knee；walk-onset 见 detect_walk_onset。
    """
    if unqualified_events:
        return []
    ordered = sorted(rows, key=lambda row: row["pages"])
    candidates = []
    for left, right in zip(ordered, ordered[1:]):
        refill_low = left["l1d_tlb_refill_per_1k"]
        refill_high = right["l1d_tlb_refill_per_1k"]
        cyc_low = left["cyc_per_load"]
        cyc_high = right["cyc_per_load"]
        if refill_low <= 0 or cyc_low <= 0:
            continue  # 比值未定义的点对不提名（零值按未定义处理）
        if (refill_high / refill_low >= _KNEE_REFILL_RATIO
                and refill_high - refill_low >= _KNEE_REFILL_DELTA_PER_1K
                and cyc_high / cyc_low >= _KNEE_CYC_RATIO):
            candidates.append((left["pages"], right["pages"]))
    return candidates


def _intervals_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    """闭区间在页数轴上相交（共享 ≥1 个页点，端点相触算重叠）。"""
    return left[0] <= right[1] and right[0] <= left[1]


def adjudicate_knee(rows_by_seed: dict[int, list[dict]], *,
                    seed_coverage: int | None = None,
                    training_coverage: int | None = None,
                    unqualified_events: Iterable[str] = ()) -> dict:
    """§6.2.2 候选 + §6.2.8-1 左删失优先 + §6.2.6 稳定条件的终态判定。

    rows_by_seed：{order_seed: [{"pages", "l1d_tlb_refill_per_1k",
    "cyc_per_load"}]}（每点为该页数组中位数）。返回 {status, intervals,
    evidence}；status 取 §10.2 终态子集：

    - 资格不足事件门控 → SEMANTICS_UNVERIFIED（§9.2，不出结论）；
    - 空输入 → OPEN；
    - 任一 seed 的 32 页点 R_0x05 ≥100/1k → LEFT_CENSORED（§6.2.8-1，
      先于 §6.2.2；任务书未定义跨 seed 聚合，取保守分支：一个 seed 已
      处高位制度即判定，evidence 逐 seed 列值供评审）；
    - 全 seed 无候选 → RIGHT_CENSORED（上界内未识别）；
    - seed 覆盖 <3/4（致密区间相互重叠的 order_seed 数）→
      ORDER_SENSITIVE；训练覆盖 <2（8/512 ring passes 两制度）→
      TRAINING_SENSITIVE（§6.2.6；两者皆不足时按 ORDER_SENSITIVE 结案，
      顺序同任务书列举）；齐备 → INTERVAL_IDENTIFIED。

    seed_coverage / training_coverage 由调用方按致密（Phase B）覆盖情
    况显式传入；缺省时 seed 覆盖按输入曲线候选区间的最大重叠计数、训
    练覆盖按 1 计——Phase A 粗扫（2 seed × 短训练）进来自然落在敏感
    终态，不会被误晋升。
    """
    if unqualified_events:
        return {"status": "SEMANTICS_UNVERIFIED", "intervals": [],
                "evidence": {"unqualified_events": sorted(str(event) for event in unqualified_events)}}
    per_seed: dict[int, dict] = {}
    for seed, rows in sorted(rows_by_seed.items()):
        ordered = sorted(rows, key=lambda row: row["pages"])
        floor = next(
            (row for row in ordered if row["pages"] == _LEFT_CENSOR_PAGES),
            None,
        )
        per_seed[seed] = {
            "floor_refill_per_1k": (
                floor["l1d_tlb_refill_per_1k"] if floor is not None else None
            ),
            "left_censored": (
                floor is not None
                and floor["l1d_tlb_refill_per_1k"] >= _LEFT_CENSOR_REFILL_PER_1K
            ),
            "candidates": detect_knee_candidates(ordered),
        }
    if not per_seed:
        return {"status": "OPEN", "intervals": [],
                "evidence": {"per_seed": per_seed}}
    censored = [seed for seed, entry in per_seed.items() if entry["left_censored"]]
    if censored:
        return {"status": "LEFT_CENSORED", "intervals": [],
                "evidence": {"per_seed": per_seed, "censored_seeds": censored}}
    intervals = sorted({
        candidate for entry in per_seed.values() for candidate in entry["candidates"]
    })
    if not intervals:
        return {"status": "RIGHT_CENSORED", "intervals": [],
                "evidence": {"per_seed": per_seed}}
    if seed_coverage is None:
        seed_coverage = max(
            sum(
                1
                for entry in per_seed.values()
                if any(
                    _intervals_overlap(interval, candidate)
                    for candidate in entry["candidates"]
                )
            )
            for interval in intervals
        )
    if training_coverage is None:
        training_coverage = 1
    evidence = {
        "per_seed": per_seed,
        "seed_coverage": seed_coverage,
        "training_coverage": training_coverage,
    }
    if seed_coverage < _STABLE_MIN_SEED_OVERLAP:
        return {"status": "ORDER_SENSITIVE", "intervals": intervals,
                "evidence": evidence}
    if training_coverage < _STABLE_MIN_TRAININGS:
        return {"status": "TRAINING_SENSITIVE", "intervals": intervals,
                "evidence": evidence}
    return {"status": "INTERVAL_IDENTIFIED", "intervals": intervals,
            "evidence": evidence}


def _walk_point_qualifies(row: dict) -> tuple[bool, int]:
    """§6.2.3 单点前两条件：median R_0x34 ≥1.0/1k 且逐样本地板分离
    （≥8/10 样本 >0.5/1k，§6.2.8-5 按每个 order_seed 各自判定）。
    样本数不足 10 时仍按绝对计数 ≥8 判（§6.2.8-6 的补跑纪律保证
    10 进程，缺样本不放宽门槛）。返回 (合格, 地板样本数)。"""
    floor_samples = sum(
        1 for value in row["walk_samples"] if value > _WALK_FLOOR_PER_1K
    )
    qualified = (
        row["dtlb_walk_per_1k"] >= _WALK_ONSET_MIN_PER_1K
        and floor_samples >= _WALK_FLOOR_MIN_SAMPLES
    )
    return qualified, floor_samples


def detect_walk_onset(rows_by_seed: dict[int, list[dict]], *,
                      unqualified_events: Iterable[str] = ()) -> dict:
    """§6.2.3 walk-onset 检测（Q2a）+ §6.2.8-5 逐 seed 地板判定。

    rows_by_seed：{order_seed: [{"pages", "dtlb_walk_per_1k"（该页数 median）,
    "walk_samples"（逐进程 R_0x34 值）}]}。返回 {status, intervals,
    evidence}：

    - 资格不足事件门控 → SEMANTICS_UNVERIFIED；空输入 → OPEN；
    - 逐 seed 取首个"本点与下一页数点同满足前两项"的相邻点对
      （持续性条件）；末点（如 8192 页）无下一页数点，永不单独构成
      onset——8192 页仍未满足 → RIGHT_CENSORED（onset 下界报告）；
    - 跨 seed：全部一致 → INTERVAL_IDENTIFIED（onset 位于区间内的相
      邻点对）；全部无 → RIGHT_CENSORED；不一致或部分缺失 →
      ORDER_SENSITIVE（任务书未定义跨 seed 聚合，取同 §6.2.6 一致
      精神的保守分支，evidence 逐 seed 列 onset 供评审）。
    """
    if unqualified_events:
        return {"status": "SEMANTICS_UNVERIFIED", "intervals": [],
                "evidence": {"unqualified_events": sorted(str(event) for event in unqualified_events)}}
    per_seed: dict[int, dict] = {}
    for seed, rows in sorted(rows_by_seed.items()):
        points = []
        for row in sorted(rows, key=lambda row: row["pages"]):
            qualified, floor_samples = _walk_point_qualifies(row)
            points.append({
                "pages": row["pages"],
                "median": row["dtlb_walk_per_1k"],
                "floor_samples": floor_samples,
                "qualified": qualified,
            })
        onset = None
        for left, right in zip(points, points[1:]):
            if left["qualified"] and right["qualified"]:
                onset = (left["pages"], right["pages"])
                break
        per_seed[seed] = {
            "onset": onset,
            "scan_max_pages": points[-1]["pages"] if points else None,
            "points": points,
        }
    if not per_seed:
        return {"status": "OPEN", "intervals": [],
                "evidence": {"per_seed": per_seed}}
    onsets = {entry["onset"] for entry in per_seed.values()}
    if onsets == {None}:
        return {"status": "RIGHT_CENSORED", "intervals": [],
                "evidence": {"per_seed": per_seed}}
    if len(onsets) == 1:
        return {"status": "INTERVAL_IDENTIFIED",
                "intervals": [next(iter(onsets))],
                "evidence": {"per_seed": per_seed}}
    intervals = sorted(onset for onset in onsets if onset is not None)
    return {"status": "ORDER_SENSITIVE", "intervals": intervals,
            "evidence": {"per_seed": per_seed}}


def _is_bimodal(values: list[float]) -> bool:
    """双峰规则（任务书 §9.2 复用契约，移植 sm8650_x4_p0prime 预注册规
    则）：排序后相邻比值 ≥ _BIMODAL_RATIO 且两侧各 ≥ _BIMODAL_MIN_SIDE
    个样本。零值按比值未定义处理（不参与标记）。"""
    ordered = sorted(values)
    for left in range(_BIMODAL_MIN_SIDE, len(ordered) - _BIMODAL_MIN_SIDE + 1):
        low, high = ordered[left - 1], ordered[left]
        if low <= 0:
            continue
        if high / low >= _BIMODAL_RATIO:
            return True
    return False


def analyze_records(records: Iterable[dict], run_label: str,
                    registry: PmuEventRegistry | None = None) -> AnalysisResult:
    """校验记录并按 (buffer, seed, backing, ring_passes) 分组。

    status != ok 的记录由调用方（load_run）预先分流；这里只消费 ok 记录，
    multiplex/zero-running 样本被拒绝并登记（同记录其余样本保留）。
    registry 缺省按无注册处理（fail-closed：全部 PMU 事件资格不足）——
    SEMANTICS_UNVERIFIED 只降级结论，不阻断样本入表。
    """
    grouped: dict[tuple[int, int, str, float], list[dict]] = defaultdict(list)
    result = AnalysisResult(run_label=run_label)
    seen = False
    for record in records:
        seen = True
        if record.get("status") != "ok":
            result.rejected.append(
                f"{run_label}/buffer={record.get('params', {}).get('buffer_kb')}KiB"
                f": record status={record.get('status')}"
            )
            continue
        for sample in _samples_from_record(record, run_label, result.rejected):
            key = (
                sample["buffer_kb"],
                sample["seed"],
                sample["page_policy_actual"],
                sample["ring_passes"],
            )
            grouped[key].append(sample)
    if not seen:
        raise TlbError(f"{run_label}: no records")

    for (buffer_kb, seed, backing, passes), samples in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1], _BACKING_ORDER[item[0][2]], item[0][3])
    ):
        group = {
            "run_label": run_label,
            "buffer_kb": buffer_kb,
            "seed": seed,
            "page_policy_actual": backing,
            "ring_passes": int(passes) if passes == int(passes) else passes,
            "samples": samples,
            "unqualified_events": _unqualified_events(registry),
            # §9.2 复用契约：双峰字段钉为 l1d_tlb_refill_per_1k（knee 判
            # 据的消费字段、逐进程布局/着色方差的主要暴露面）。
            "bimodal": _is_bimodal([s["l1d_tlb_refill_per_1k"] for s in samples]),
        }
        for field_name in ("latency_ns", *_DERIVED_FIELDS):
            group[field_name] = summarize([s[field_name] for s in samples])
        result.groups.append(group)
    return result


def _fmt(value: float) -> str:
    return f"{value:.3f}"


def _short_name(metric: str) -> str:
    return metric.removeprefix("pmu.").removesuffix(".count")


def build_markdown(results: list[AnalysisResult], show_samples: bool = False) -> str:
    """分组汇总（median [p25, p75]）+ 拒绝清单；show_samples 展开逐样本行。"""
    lines = [
        "# SM8650 X4 TLB per-sample analysis",
        "",
        "All numeric cells are median [p25, p75]; rates are per 1,000 timed loads.",
        "PMU rows are accepted only when time_running_ns == time_enabled_ns for every event.",
        "Events under `unverified` are SEMANTICS_UNVERIFIED (registry gate): "
        "samples stay in the table, structural conclusions are blocked.",
        "",
        "| run | buffer KiB | seed | backing | passes | n | latency ns | cyc/load | mem rd/1k | l1d tlb refill/1k | dtlb walk/1k | bimodal | unverified |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for result in results:
        for group in result.groups:
            cells = [
                result.run_label,
                str(group["buffer_kb"]),
                f"seed={group['seed']}",
                group["page_policy_actual"],
                str(group["ring_passes"]),
                str(len(group["samples"])),
            ]
            for field_name in ("latency_ns", "cyc_per_load", "mem_rd_per_1k",
                               "l1d_tlb_refill_per_1k", "dtlb_walk_per_1k"):
                stats = group[field_name]
                cells.append(f"{_fmt(stats['median'])} [{_fmt(stats['p25'])}, {_fmt(stats['p75'])}]")
            cells.append("YES" if group["bimodal"] else "no")
            cells.append(
                ", ".join(_short_name(name) for name in group["unqualified_events"])
                or "-"
            )
            lines.append("| " + " | ".join(cells) + " |")
            if show_samples:
                for sample in group["samples"]:
                    lines.append(
                        f"<!-- sample {result.run_label} b{group['buffer_kb']}K "
                        f"seed={sample['seed']} s{sample['sample_index']}: "
                        f"lat={sample['latency_ns']:.4f} cyc={sample['cyc_per_load']:.3f} "
                        f"mem_rd={sample['mem_rd_per_1k']:.2f} "
                        f"refill={sample['l1d_tlb_refill_per_1k']:.2f} "
                        f"walk={sample['dtlb_walk_per_1k']:.3f} "
                        f"vma={sample.get('vma_base', '-')} -->"
                    )
    rejected = [line for result in results for line in result.rejected]
    if rejected:
        lines += ["", "## rejected samples/records", ""]
        lines += [f"- {entry}" for entry in rejected]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", action="append", required=True,
                        help="run 目录（可重复；label 取目录名）")
    parser.add_argument("--registry", default="configs/pmu-event-registry.json",
                        help="PMU 事件资格注册表（默认 configs/pmu-event-registry.json；"
                             "相对 CWD 解析，默认路径要求从仓库根运行）")
    parser.add_argument("--samples", action="store_true",
                        help="在汇总后附逐样本行（HTML 注释形式，便于归档）")
    args = parser.parse_args(argv)

    registry = load_registry(args.registry)
    results: list[AnalysisResult] = []
    for run_dir in args.run:
        data = load_run(Path(run_dir))
        label = Path(run_dir).name
        if data.ok_records:
            result = analyze_records(data.ok_records, label, registry)
        else:
            # 全失败 run（如被环境门禁 fail-closed 的段）：不产生分组，
            # 但失败记录必须全部进入 rejected——统一报告不得缺段。
            result = AnalysisResult(run_label=label)
        for record in data.failed_records:
            failure_reason = (record.get("failure") or {}).get("reason", "")
            result.rejected.append(
                f"{label}/buffer={record.get('params', {}).get('buffer_kb')}KiB"
                f": record status={record.get('status')}"
                + (f" [{failure_reason}]" if failure_reason else "")
            )
        results.append(result)
    sys.stdout.write(build_markdown(results, show_samples=args.samples))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
