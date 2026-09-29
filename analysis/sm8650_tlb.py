# SPDX-License-Identifier: Apache-2.0
"""SM8650 X4 TLB 层级探测逐样本分析器（任务书 v4.1）。

与 `analysis.sm8650_x4_p0prime` 并列的独立模块（两任务的冻结规则各自
演化，刻意复制契约链而非共享实现）。证据契约与 P0″ 同构：schema
v2、target/probe 校验、metric 集合相等、逐样本 sample_index 对齐、
PMU 编码与 seed 逐样本一致、time_running==time_enabled（multiplex
样本拒绝并登记，同记录其余样本保留）、全失败 run 进 rejected 不抛
错——契约缺项一律硬错误，本探测不接受"大概齐全"的记录。

分组键：(run_label, buffer_kb, seed, page_policy_actual, ring_passes)。
ring passes 由记录参数直接推出（loads / (buffer_kb×1024/stride)），
不依赖配置名约定。派生密度按任务书 §3.2 统一分母：R_e = 1000×C_e /
N_timed_loads；`0x05` 在 4096 页可超过 1000/1k（事件总数大于 timed
loads 数），分析器保留原值——不截断、不改写为 miss 概率。

事件资格门控（§3.1/S4）：每组的 unqualified_events 列出资格不足
（candidate 或未注册）的 PMU 事件；存在资格不足事件时
detect_knee_candidates 门控返回空。SEMANTICS_UNVERIFIED 只阻断结论
晋升，不阻断采集与审计——样本照常入表（否则 Gate 1 正控无法完成）。

knee 候选（§6.2.2 冻结规则；骨架版只实现相邻点对三条件提名，左删失
优先、RIGHT_CENSORED、walk-onset 等完整终态机属后续任务）：相邻页数
点 (p_i, p_{i+1}) 同时满足 R_0x05 比值 ≥2.0、绝对增量 ≥50/1k、
cyc/load 比值 ≥1.15 才提名候选区间 (p_i, p_{i+1})。
"""

from __future__ import annotations

import argparse
import json
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

# §6.2.2 knee 候选三条件的冻结阈值（改阈值 = 改冻结规则，走任务书变更）
_KNEE_REFILL_RATIO = 2.0
_KNEE_REFILL_DELTA_PER_1K = 50.0
_KNEE_CYC_RATIO = 1.15

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
        if vma_base is not None and not isinstance(vma_base, str):
            raise TlbError(
                f"{sample_context}: vma_base must be a hex string ({vma_base!r})"
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
    """§6.2.2 相邻页数点对的三条件提名（骨架版）。

    rows 为每点 {"pages", "l1d_tlb_refill_per_1k", "cyc_per_load"}（组中
    位数），内部按页数排序；返回候选区间 [(p_i, p_{i+1}), ...]。任一事
    件资格不足（unqualified_events 非空）门控返回空——SEMANTICS_UNVERIFIED
    不出结论。左删失优先、RIGHT_CENSORED 终态与 walk-onset 属后续任务。
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
        "| run | buffer KiB | seed | backing | passes | n | latency ns | cyc/load | mem rd/1k | l1d tlb refill/1k | dtlb walk/1k | unverified |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
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
                        help="PMU 事件资格注册表（默认 configs/pmu-event-registry.json）")
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
