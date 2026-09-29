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
≥1.0/1k + 下一页数点持续三条件判 onset；≥2 个 seed 区间一致才报
INTERVAL_IDENTIFIED（单 seed 真空不晋升，保守降级 ORDER_SENSITIVE），
8192 页仍未满足 → RIGHT_CENSORED。

双峰标记（任务书 §9.2 复用契约）：移植 sm8650_x4_p0prime 的预注册规
则（排序后相邻比值 ≥4 且两侧各 ≥2 样本，零值按比值未定义跳过），目
标字段钉为 l1d_tlb_refill_per_1k——knee 判据的消费字段、逐进程布局
/着色方差的主要暴露面。该标记只服务于"中位数不得掩盖双态"的报告纪
律，不构成任何容量推断。

块归组与锚点判定（§6.4/§6.2.5）：group_block 把 anchor-before + 主
体 + anchor-after 三个已加载 run（RunData）归组为块——角色只由
manifest 的 experiment_id 决定（锚点 = ptr-chase-sm8650-x4-tlb-
anchor），不以 buffer 大小、case 顺序或时间邻近推断；关联证据校验
probe SHA-256 与 target 一致、逐记录 timestamp 时序与角色一致（非
交叠），任一不过即 TlbError 拒绝归组；缺 anchor-after →
BLOCK_INCOMPLETE。validate_anchors 执行 §6.2.5 质量门槛：环境门禁
（锚点 run summary failed>0 或记录带 environment-precondition-
failed → 锚点失真）、latency/cyc 对照 short-base 参照 median 偏差
≤3%、512 KiB R 值落入正控 [p25,p75]、3072 KiB 首块自校准
（prior_3072_baseline 缺省时只记录建基线，后续块按同一规则比较）、
前后锚点同指标互判。任一不过 → BLOCK_FAILED 且块 fail-closed：
main_result 不产出，主体 case 不进入判定。ANCHORS_OK /
BLOCK_FAILED / BLOCK_INCOMPLETE 是块级终态，与 §10.2 的 Q 级终态
不同层。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from runner.statistics import summarize

from .load import RunData, load_run


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

# §6.4/§6.2.5 块归组与锚点判定的冻结常量（改阈值/参照 = 改冻结规则，
# 走任务书变更）
_ANCHOR_EXPERIMENT_ID = "ptr-chase-sm8650-x4-tlb-anchor"
_ANCHOR_BUFFERS = (512, 3072)  # 锚点配置固定的两个 base case（KiB）
_ANCHOR_MAX_DEVIATION = 0.03   # latency/cyc median 偏差上限（§6.2.5）
_ANCHOR_MEDIAN_FIELDS = ("latency_ns", "cyc_per_load")
_ANCHOR_RATE_FIELDS = ("l1d_tlb_refill_per_1k", "dtlb_walk_per_1k")

# §6.2.5 latency/cyc 参照：short-base run 20260928T024022Z
# （ptr-chase-sm8650-x4-p0prime-short-base）同 buffer 组的逐样本
# median——每组 4 seed（42/7/1337/20260928）× 10 进程 = 40 个值，经
# runner.statistics.summarize 计算。生成方式：2026-09-29 从
# data/public/runs/20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base/
# records.jsonl 现读现算（latency_ns 与 cycles/loads 逐样本值），不是
# 从任务书转抄——任务书只钉来源 run 与"median 偏差 ≤3%"的规则。
_ANCHOR_REF_MEDIANS = {
    512: {"latency_ns": 2.6548, "cyc_per_load": 7.524879455566406},
    3072: {"latency_ns": 7.73815, "cyc_per_load": 21.27081807454427},
}

# §6.2.5 R 值参照（仅 512 KiB）：TLB 正控 run 20260927T182613Z
# （ptr-chase-sm8650-x4-pmu-ctrl-tlb）512 KiB 组逐样本 R_0x05/R_0x34
# 分布的 [p25, p75]（10 进程，summarize 口径；2026-09-29 现读现算自
# data/public/runs/20260927T182613Z-ptr-chase-sm8650-x4-pmu-ctrl-tlb/
# records.jsonl）。任务书原文括号值 288.08 [287.7, 289.6] /
# 0.0129 [0.0098, 0.0141] 是它们的低位舍入，此处保留全精度。
# 3072 KiB 无 G0 历史数据 → 首块自校准（validate_anchors 的
# prior_3072_baseline 参数），故无 3072 参照常量。
_ANCHOR_REF_R512_P25_P75 = {
    "l1d_tlb_refill_per_1k": (287.7812832593918, 289.3509864807129),
    "dtlb_walk_per_1k": (0.010460615158081055, 0.013381242752075195),
}

# 块级终态（§6.2.5/§6.4；与 §10.2 的 Q 级终态不同层）
_BLOCK_GROUPED = "BLOCK_GROUPED"        # 三块齐备，待 §6.2.5 判定
_BLOCK_INCOMPLETE = "BLOCK_INCOMPLETE"  # 缺 anchor-after，不成块
_ANCHORS_OK = "ANCHORS_OK"
_BLOCK_FAILED = "BLOCK_FAILED"

_QUALIFICATIONS = ("candidate", "qualified")

_DERIVED_FIELDS = tuple(derived for _, _, derived, _ in _PMU_EVENTS.values())


@dataclass
class AnalysisResult:
    """一次 analyze_records 的产物：分组 + 被拒绝样本的审计行。"""

    run_label: str
    groups: list[dict] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


@dataclass
class BlockResult:
    """§6.4 三块归组产物：角色 + 关联证据。

    status 为 BLOCK_GROUPED（anchor-before + 主体 + anchor-after 三块
    齐备）或 BLOCK_INCOMPLETE（缺 anchor-after）；归组校验不过时
    group_block 直接 TlbError，不产出 BlockResult。
    """

    status: str
    anchor_before: RunData
    main: RunData
    anchor_after: RunData | None = None
    evidence: dict = field(default_factory=dict)


@dataclass
class AnchorVerdict:
    """§6.2.5 锚点判定产物（块级终态，与 §10.2 的 Q 级终态不同层）。

    main_result 仅 ANCHORS_OK 时产出——锚点失真（BLOCK_FAILED）或块
    不完整（BLOCK_INCOMPLETE）时主体 case 不进入判定（fail-closed：
    无对象可消费）。main_result 消费主体 run 的全部记录：ok 记录分
    组、failed 记录进 rejected 审计行（measurement-discipline：失败
    的实验也是实验档案的一部分）。baseline_3072 为 3072 KiB 自校准
    基线（首块由 anchor-before 的 3072 组分布建立，后续块回显传入
    值）；非 ANCHORS_OK 时为 None——失败块的分布不晋升为基线。
    """

    status: str  # ANCHORS_OK / BLOCK_FAILED / BLOCK_INCOMPLETE
    evidence: dict = field(default_factory=dict)
    baseline_3072: dict | None = None
    main_result: AnalysisResult | None = None


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

    seed_coverage：致密区间相互重叠的 order_seed 数，由调用方按 Phase B
    覆盖情况显式传入；缺省按输入曲线候选区间的最大重叠计数。training_
    coverage：已确认同制度的训练量数——**只允许在两种训练量（8/512
    ring passes）均已测量且各自候选区间一致时传 2**（自然用法：逐训练
    量分别 adjudicate、比对 intervals 一致后再传入）；否则本函数无法
    察觉未传入维度的区间不一致，会误晋升 INTERVAL_IDENTIFIED。两参数
    缺省（按输入曲线计 seed 覆盖、训练覆盖=1）时 Phase A 粗扫
    （2 seed × 短训练）进来自然落在敏感终态，不会被误晋升。

    {seed: []}（seed 在、数据空）按缺失 seed 处理：不计入覆盖数、不
    进 per_seed（登记 evidence["empty_seeds"]）；全部 seed 数据空 →
    OPEN。per_seed 各 seed 带 scan_max_pages（该曲线最大页数点），
    RIGHT_CENSORED 的扫描上界可审计。
    """
    if unqualified_events:
        return {"status": "SEMANTICS_UNVERIFIED", "intervals": [],
                "evidence": {"unqualified_events": sorted(str(event) for event in unqualified_events)}}
    per_seed: dict[int, dict] = {}
    empty_seeds: list[int] = []
    for seed, rows in sorted(rows_by_seed.items()):
        ordered = sorted(rows, key=lambda row: row["pages"])
        if not ordered:
            empty_seeds.append(seed)  # 数据空的 seed 按缺失处理
            continue
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
            "scan_max_pages": ordered[-1]["pages"],
        }
    if not per_seed:
        return {"status": "OPEN", "intervals": [],
                "evidence": {"per_seed": per_seed, "empty_seeds": empty_seeds}}
    censored = [seed for seed, entry in per_seed.items() if entry["left_censored"]]
    if censored:
        return {"status": "LEFT_CENSORED", "intervals": [],
                "evidence": {"per_seed": per_seed, "empty_seeds": empty_seeds,
                             "censored_seeds": censored}}
    intervals = sorted({
        candidate for entry in per_seed.values() for candidate in entry["candidates"]
    })
    if not intervals:
        return {"status": "RIGHT_CENSORED", "intervals": [],
                "evidence": {"per_seed": per_seed, "empty_seeds": empty_seeds}}
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
        "empty_seeds": empty_seeds,
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
    - 跨 seed：**≥2 个** seed 的曲线均满足且 onset 区间一致 →
      INTERVAL_IDENTIFIED（onset 位于区间内的相邻点对）；全部无 →
      RIGHT_CENSORED；不一致、部分缺失或**单 seed 满足** →
      ORDER_SENSITIVE。单 seed 护栏是有意取舍：顺序敏感是本任务核心
      风险，冻结规则纪律下宁可保守降级，也不让单 seed 真空晋升；
    - {seed: []}（seed 在、数据空）按缺失 seed 处理：不进一致性判定
      与 per_seed（登记 evidence["empty_seeds"]）；全部 seed 数据空
      → OPEN。
    """
    if unqualified_events:
        return {"status": "SEMANTICS_UNVERIFIED", "intervals": [],
                "evidence": {"unqualified_events": sorted(str(event) for event in unqualified_events)}}
    per_seed: dict[int, dict] = {}
    empty_seeds: list[int] = []
    for seed, rows in sorted(rows_by_seed.items()):
        ordered = sorted(rows, key=lambda row: row["pages"])
        if not ordered:
            empty_seeds.append(seed)  # 数据空的 seed 按缺失处理
            continue
        points = []
        for row in ordered:
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
            "scan_max_pages": points[-1]["pages"],
            "points": points,
        }
    if not per_seed:
        return {"status": "OPEN", "intervals": [],
                "evidence": {"per_seed": per_seed, "empty_seeds": empty_seeds}}
    onsets = {entry["onset"] for entry in per_seed.values()}
    if onsets == {None}:
        return {"status": "RIGHT_CENSORED", "intervals": [],
                "evidence": {"per_seed": per_seed, "empty_seeds": empty_seeds}}
    if len(per_seed) >= 2 and len(onsets) == 1:
        return {"status": "INTERVAL_IDENTIFIED",
                "intervals": [next(iter(onsets))],
                "evidence": {"per_seed": per_seed, "empty_seeds": empty_seeds}}
    intervals = sorted(onset for onset in onsets if onset is not None)
    return {"status": "ORDER_SENSITIVE", "intervals": intervals,
            "evidence": {"per_seed": per_seed, "empty_seeds": empty_seeds}}


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


def _record_time_span(run: RunData, context: str) -> tuple[datetime, datetime]:
    """run 全部记录（含失败记录）的 timestamp 跨度（min, max）。

    缺/坏时间戳是硬错误——§6.4 的时序关联不接受"大概齐全"；无记录的
    run 拿不出 SHA/时序证据，同样硬错误。
    """
    stamps = []
    for record in (*run.ok_records, *run.failed_records):
        timestamp = record.get("timestamp")
        if not isinstance(timestamp, str):
            raise TlbError(f"{context}: record missing timestamp")
        try:
            stamps.append(datetime.fromisoformat(
                timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp
            ))
        except ValueError:
            raise TlbError(
                f"{context}: invalid timestamp {timestamp!r}"
            ) from None
    if not stamps:
        raise TlbError(f"{context}: no records (无记录则无 SHA/时序关联证据)")
    return min(stamps), max(stamps)


def group_block(runs: Sequence[RunData]) -> BlockResult:
    """§6.4：已加载 run 按 experiment_id 归组为块。

    块 = anchor-before + 主体 + anchor-after（调用方按 run 时序给出顺
    序）。角色只由 manifest 的 experiment_id 决定（锚点 =
    `ptr-chase-sm8650-x4-tlb-anchor`）——不以 buffer 大小、case 顺序
    或时间邻近推断角色与关联。校验任一不过 → TlbError（拒绝归组，不
    降级猜测）：

    - 角色模式恰为 [锚, 主体] 或 [锚, 主体, 锚]；
    - 关联证据①（target/probe SHA-256 一致）：全部记录（含失败记录）
      的 probe.artifact.sha256 单一，且各 manifest 的 target.target_id
      一致；
    - 关联证据①（manifest 时序）：逐记录 timestamp 跨度与角色顺序一
      致——前一 run 最晚样本 ≤ 后一 run 最早样本。非交叠是"时序相
      邻"的可机读部分；三块之间是否夹着别的 run 无法本地证伪，任务
      书沉默处取保守分支：只证顺序与角色一致，不证紧邻。关联证据②
      （环境事务 journal）持久在 data/private/ 本地不入库，不在分析
      面，归组不校验。

    缺 anchor-after（[锚, 主体] 二 run）→ status=BLOCK_INCOMPLETE，
    由 validate_anchors 原样结案。
    """
    if len(runs) not in (2, 3):
        raise TlbError(f"group_block: 2 or 3 runs required, got {len(runs)}")
    experiment_ids = []
    for run in runs:
        experiment_id = run.manifest.get("experiment_id")
        if not isinstance(experiment_id, str) or not experiment_id:
            raise TlbError(
                f"group_block/{run.run_dir.name}: manifest missing experiment_id"
            )
        experiment_ids.append(experiment_id)
    roles = [
        "anchor" if experiment_id == _ANCHOR_EXPERIMENT_ID else "main"
        for experiment_id in experiment_ids
    ]
    expected = ["anchor", "main"] + (["anchor"] if len(runs) == 3 else [])
    if roles != expected:
        raise TlbError(
            f"group_block: role pattern {roles} != {expected} "
            f"(角色只由 experiment_id 决定)"
        )
    shas: set[str] = set()
    target_ids: set[str] = set()
    spans = []
    for run in runs:
        context = f"group_block/{run.run_dir.name}"
        target_id = run.manifest.get("target", {}).get("target_id")
        if not target_id:
            raise TlbError(f"{context}: manifest missing target.target_id")
        target_ids.add(target_id)
        for record in (*run.ok_records, *run.failed_records):
            sha = (record.get("probe", {}).get("artifact") or {}).get("sha256")
            if not sha:
                raise TlbError(
                    f"{context}: record missing probe.artifact.sha256"
                )
            shas.add(sha)
        spans.append(_record_time_span(run, context))
    if len(shas) != 1:
        raise TlbError(
            f"group_block: probe SHA-256 mismatch across runs "
            f"({len(shas)} distinct)"
        )
    if len(target_ids) != 1:
        raise TlbError(
            f"group_block: target_id mismatch across runs {sorted(target_ids)}"
        )
    for previous, current in zip(spans, spans[1:]):
        if previous[1] > current[0]:
            raise TlbError(
                "group_block: run time spans overlap or invert vs claimed "
                "anchor-before/main/anchor-after order"
            )
    return BlockResult(
        status=_BLOCK_GROUPED if len(runs) == 3 else _BLOCK_INCOMPLETE,
        anchor_before=runs[0],
        main=runs[1],
        anchor_after=runs[2] if len(runs) == 3 else None,
        evidence={
            "experiment_ids": experiment_ids,
            "probe_sha256": next(iter(shas)),
            "target_id": next(iter(target_ids)),
            "time_spans": [
                [start.isoformat(), end.isoformat()] for start, end in spans
            ],
        },
    )


def _environment_gate_failure(run: RunData) -> dict | None:
    """§6.2.5 环境门禁：锚点 run 的 manifest summary failed>0 或记录带
    environment-precondition-failed → 等同锚点失真。返回证据或 None。"""
    summary_failed = run.manifest.get("summary", {}).get("failed", 0)
    env_buffers = [
        record.get("params", {}).get("buffer_kb")
        for record in run.failed_records
        if (record.get("failure") or {}).get("reason")
        == "environment-precondition-failed"
    ]
    if summary_failed > 0 or env_buffers:
        return {"summary_failed": summary_failed,
                "environment_failed_buffers": env_buffers}
    return None


def _anchor_groups(run: RunData) -> dict[int, dict]:
    """锚点 run 的 {buffer_kb: 组}（analyze_records 分组原样取用）。

    组形契约：恰为 {512: 一组, 3072: 一组}——锚点配置的 case 集合与
    参数本身由 §9.3 plan 展开契约测试钉死，分析器只验组形；不符是契
    约缺项，TlbError 而非判失。
    """
    result = analyze_records(run.ok_records, run.run_dir.name)
    by_buffer: dict[int, list[dict]] = defaultdict(list)
    for group in result.groups:
        by_buffer[group["buffer_kb"]].append(group)
    if set(by_buffer) != set(_ANCHOR_BUFFERS) or any(
        len(groups) != 1 for groups in by_buffer.values()
    ):
        raise TlbError(
            f"{run.run_dir.name}: anchor run must yield exactly one group per "
            f"buffer {sorted(_ANCHOR_BUFFERS)}, got "
            f"{sorted((buffer, len(groups)) for buffer, groups in by_buffer.items())}"
        )
    return {buffer: groups[0] for buffer, groups in by_buffer.items()}


def _relative_deviation(value: float, reference: float) -> float:
    """|value − reference| / reference；reference ≤0 时偏差视为无穷
    （参照分布位置未定，保守判失）。"""
    if reference <= 0:
        return float("inf")
    return abs(value - reference) / reference


def _anchor_stats_evidence(groups: dict[str, dict[int, dict]]) -> dict:
    """前/后锚点各 buffer 组的 median [p25, p75] 快照（审计用）。"""
    return {
        role: {
            buffer_kb: {
                metric: {
                    "median": group[metric]["median"],
                    "p25": group[metric]["p25"],
                    "p75": group[metric]["p75"],
                }
                for metric in (*_ANCHOR_MEDIAN_FIELDS, *_ANCHOR_RATE_FIELDS)
            }
            for buffer_kb, group in by_buffer.items()
        }
        for role, by_buffer in groups.items()
    }


def validate_anchors(block: BlockResult,
                     registry: PmuEventRegistry | None = None, *,
                     prior_3072_baseline: dict | None = None) -> AnchorVerdict:
    """§6.2.5 锚点判据（块级质量门槛；终态与 §10.2 的 Q 级不同层）。

    全部满足 → ANCHORS_OK 并产出 main_result（主体 case 进入判定）；
    任一不过 → BLOCK_FAILED，块 fail-closed（main_result=None，主体
    case 不入判定）；块缺 anchor-after → BLOCK_INCOMPLETE 原样结案。
    判据：

    1. 环境门禁：任一锚点 run 的 summary failed>0 或记录带
       environment-precondition-failed → 锚点失真；
    2. latency 与 cycles/load：前/后锚点各自同 buffer 组 median 对照
       short-base 参照（_ANCHOR_REF_MEDIANS，来源与生成方式见常量注
       释）偏差 ≤3%；
    3. R_0x05/R_0x34（512 KiB）：前/后锚点组 median 落入正控
       [p25, p75]（_ANCHOR_REF_R512_P25_P75）；
    4. R_0x05/R_0x34（3072 KiB）：无 G0 历史数据——prior_3072_baseline
       缺省（首块）时只记录不判失，以 anchor-before 的 3072 组分布建
       基线随 verdict 输出；有基线时前/后锚点 median 均须落入基线
       [p25, p75]（同一规则，跨块一致性）；
    5. 前后锚点互判（同一规则）：同 buffer latency/cyc median 相对偏
       差 ≤3%（双向）；R 值 median 互落入对方 [p25, p75]（双向）。
       3072 KiB 首块豁免只针对判据 4（无历史可比）——互判仍执行
       （任务书沉默处取保守分支：块内漂移可独立于历史检出）。

    baseline_3072 仅 ANCHORS_OK 时输出（失败块的分布不晋升为基线）。
    """
    if block.status != _BLOCK_GROUPED:
        return AnchorVerdict(
            status=_BLOCK_INCOMPLETE,
            evidence={"reason": "missing anchor-after run",
                      "block": block.evidence},
        )
    checks: list[dict] = []
    for role, run in (("anchor_before", block.anchor_before),
                      ("anchor_after", block.anchor_after)):
        failure = _environment_gate_failure(run)
        checks.append({"check": "environment_gate", "run": role,
                       "ok": failure is None, **(failure or {})})
    failures = [check for check in checks if not check["ok"]]
    if failures:
        # 锚点失真 → 块 fail-closed（§6.2.5）：短路结案，不再消费锚点
        # 分布（失真的锚点分布不参与任何后续比较）。
        return AnchorVerdict(status=_BLOCK_FAILED,
                             evidence={"checks": checks, "failures": failures})
    groups = {
        "anchor_before": _anchor_groups(block.anchor_before),
        "anchor_after": _anchor_groups(block.anchor_after),
    }
    for role in ("anchor_before", "anchor_after"):
        for buffer_kb in _ANCHOR_BUFFERS:
            group = groups[role][buffer_kb]
            for metric in _ANCHOR_MEDIAN_FIELDS:
                reference = _ANCHOR_REF_MEDIANS[buffer_kb][metric]
                median = group[metric]["median"]
                deviation = _relative_deviation(median, reference)
                checks.append({
                    "check": f"{metric}_vs_short_base",
                    "run": role,
                    "buffer_kb": buffer_kb,
                    "median": median,
                    "reference": reference,
                    "deviation": deviation,
                    "ok": deviation <= _ANCHOR_MAX_DEVIATION,
                })
        group_512 = groups[role][512]
        for metric, interval in _ANCHOR_REF_R512_P25_P75.items():
            median = group_512[metric]["median"]
            checks.append({
                "check": f"{metric}_within_positive_control_512",
                "run": role,
                "buffer_kb": 512,
                "median": median,
                "interval": list(interval),
                "ok": interval[0] <= median <= interval[1],
            })
        if prior_3072_baseline is not None:
            group_3072 = groups[role][3072]
            for metric in _ANCHOR_RATE_FIELDS:
                baseline_stats = prior_3072_baseline[metric]
                median = group_3072[metric]["median"]
                checks.append({
                    "check": f"{metric}_within_3072_baseline",
                    "run": role,
                    "buffer_kb": 3072,
                    "median": median,
                    "interval": [baseline_stats["p25"], baseline_stats["p75"]],
                    "ok": baseline_stats["p25"] <= median <= baseline_stats["p75"],
                })
    before, after = groups["anchor_before"], groups["anchor_after"]
    for buffer_kb in _ANCHOR_BUFFERS:
        for metric in _ANCHOR_MEDIAN_FIELDS:
            median_before = before[buffer_kb][metric]["median"]
            median_after = after[buffer_kb][metric]["median"]
            deviation = max(
                _relative_deviation(median_after, median_before),
                _relative_deviation(median_before, median_after),
            )
            checks.append({
                "check": f"{metric}_before_after_mutual",
                "run": "mutual",
                "buffer_kb": buffer_kb,
                "median_before": median_before,
                "median_after": median_after,
                "deviation": deviation,
                "ok": deviation <= _ANCHOR_MAX_DEVIATION,
            })
        for metric in _ANCHOR_RATE_FIELDS:
            stats_before = before[buffer_kb][metric]
            stats_after = after[buffer_kb][metric]
            checks.append({
                "check": f"{metric}_before_after_mutual",
                "run": "mutual",
                "buffer_kb": buffer_kb,
                "median_before": stats_before["median"],
                "median_after": stats_after["median"],
                "interval_before": [stats_before["p25"], stats_before["p75"]],
                "interval_after": [stats_after["p25"], stats_after["p75"]],
                "ok": (
                    stats_before["p25"] <= stats_after["median"] <= stats_before["p75"]
                    and stats_after["p25"] <= stats_before["median"] <= stats_after["p75"]
                ),
            })
    failures = [check for check in checks if not check["ok"]]
    if failures:
        return AnchorVerdict(
            status=_BLOCK_FAILED,
            evidence={"checks": checks, "failures": failures,
                      "anchor_stats": _anchor_stats_evidence(groups)},
        )
    established = {
        metric: dict(before[3072][metric]) for metric in _ANCHOR_RATE_FIELDS
    }
    return AnchorVerdict(
        status=_ANCHORS_OK,
        evidence={
            "checks": checks,
            "anchor_stats": _anchor_stats_evidence(groups),
            "baseline_3072_source": (
                "prior" if prior_3072_baseline is not None else "established"
            ),
        },
        baseline_3072=(
            prior_3072_baseline if prior_3072_baseline is not None else established
        ),
        main_result=analyze_records(
            (*block.main.ok_records, *block.main.failed_records),
            block.main.run_dir.name,
            registry,
        ),
    )


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
