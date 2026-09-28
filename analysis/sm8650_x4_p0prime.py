# SPDX-License-Identifier: Apache-2.0
"""P0″（SM8650 X4 demand/prefetch 复测）逐样本分析器。

与 `analysis.sm8650_l2`（历史校准/细扫专用）并列的独立模块：本复测的
证据契约是 demand 与 prefetch 计数分离、链洗牌 seed 与 ring passes 逐
样本入档、multiplex 样本拒绝（保留同记录其余样本并登记），任何契约
缺项（缺 seed、缺 backing、索引错位、编码不符、PMU 时间非法）都是硬
错误——本复测不接受"大概齐全"的记录。

分组键：(run_label, buffer_kb, seed, page_policy_actual, ring_passes)。
ring passes 由记录参数直接推出（loads / (buffer_kb×1024/stride)），不
依赖配置名约定——定圈训练是本复测的实验变量，必须可从记录自证。

双峰标记规则（预注册，见计划 2026-09-28-sm8650-x4-p0prime-demand-
prefetch.md §验收规则 6）：组内 `l2d_miss_per_1k` 排序后，若存在相邻
比值 ≥ 4 且两侧各 ≥ 2 个样本，则 `bimodal=True` 并记录分割点；单样本
离群不经标记，只经每字段 min/max 呈现。该标记只服务于"中位数不得掩
盖双态"的报告纪律，不构成任何容量推断。
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from runner.statistics import summarize

from .load import load_run


class P0PrimeError(ValueError):
    """输入不满足 P0″ demand/prefetch 复测证据契约。"""


_LATENCY = "latency_ns"
# metric 名 → (期望 type, 期望 config, 派生字段名, 归一化系数)
_PMU_EVENTS = {
    "pmu.cycles.count": (8, 0x11, "cyc_per_load", 1.0),
    "pmu.mem_access_rd.count": (8, 0x66, "mem_rd_per_1k", 1000.0),
    "pmu.l1d_cache_miss.count": (8, 0x8144, "l1d_miss_per_1k", 1000.0),
    "pmu.l1d_cache_hwprf.count": (8, 0x8154, "l1d_hwprf_per_1k", 1000.0),
    "pmu.l2d_cache_miss.count": (8, 0x814C, "l2d_miss_per_1k", 1000.0),
    "pmu.l2d_cache_hwprf.count": (8, 0x8155, "l2d_hwprf_per_1k", 1000.0),
}
_REQUIRED_METRICS = {_LATENCY, *_PMU_EVENTS}
_BACKING_ORDER = {"base": 0, "mixed": 1, "thp": 2, "hugetlb-2m": 3,
                  "platform-default": 4}
_BIMODAL_RATIO = 4.0
_BIMODAL_MIN_SIDE = 2

_DERIVED_FIELDS = tuple(derived for _, _, derived, _ in _PMU_EVENTS.values())


@dataclass
class AnalysisResult:
    """一次 analyze_records 的产物：分组 + 被拒绝样本的审计行。"""

    run_label: str
    groups: list[dict] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


def _observations_by_index(metric: dict, context: str) -> dict[int, dict]:
    observations = metric.get("observations")
    if not isinstance(observations, list) or not observations:
        raise P0PrimeError(f"{context}: metric {metric.get('name')} has no observations")
    indexed: dict[int, dict] = {}
    for observation in observations:
        index = observation.get("sample_index")
        if not isinstance(index, int) or index < 0:
            raise P0PrimeError(f"{context}: invalid sample_index {index!r}")
        if index in indexed:
            raise P0PrimeError(f"{context}: duplicate sample_index {index}")
        indexed[index] = observation
    return indexed


def _samples_from_record(record: dict, run_label: str,
                         rejected: list[str]) -> list[dict]:
    context = f"{run_label}/buffer={record.get('params', {}).get('buffer_kb')}KiB"
    if record.get("schema_version") != "2.0":
        raise P0PrimeError(f"{context}: schema v2 record required")
    if record.get("target", {}).get("target_id") != "redmi-k70pro-01":
        raise P0PrimeError(f"{context}: unexpected target")
    probe = record.get("probe", {})
    if probe.get("name") != "ptr_chase" or probe.get("protocol_version") != "1.2":
        raise P0PrimeError(f"{context}: ptr_chase protocol 1.2 required")

    params = record.get("params", {})
    buffer_kb = params.get("buffer_kb")
    loads = params.get("loads")
    stride = params.get("stride", 64)
    if not isinstance(buffer_kb, int) or buffer_kb <= 0:
        raise P0PrimeError(f"{context}: positive integer buffer_kb required")
    if not isinstance(loads, int) or loads <= 0:
        raise P0PrimeError(f"{context}: positive integer loads required")
    slots = (buffer_kb * 1024) // stride
    if slots < 2:
        raise P0PrimeError(f"{context}: buffer too small for stride")
    ring_passes = loads / slots

    metrics = record.get("metrics", [])
    by_name = {metric.get("name"): metric for metric in metrics}
    if len(by_name) != len(metrics) or set(by_name) != _REQUIRED_METRICS:
        raise P0PrimeError(
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
            raise P0PrimeError(f"{context}: {name} sample_index set does not align")

    samples = []
    for sample_index in sorted(latency_indexes):
        sample_context = f"{context}/sample={sample_index}"
        latency = indexed[_LATENCY][sample_index]
        actual = latency.get("page_policy_actual")
        if actual not in _BACKING_ORDER:
            raise P0PrimeError(f"{sample_context}: unknown page backing {actual!r}")
        seed = latency.get("seed")
        if not isinstance(seed, int) or seed < 0:
            raise P0PrimeError(f"{sample_context}: seed missing or invalid ({seed!r})")

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
        multiplexed = False
        for name, (expected_type, expected_config, derived_name, scale) in _PMU_EVENTS.items():
            observation = indexed[name][sample_index]
            if (observation.get("pmu_type"), observation.get("pmu_config")) != (
                expected_type,
                expected_config,
            ):
                raise P0PrimeError(f"{sample_context}: {name} has unexpected PMU encoding")
            if observation.get("seed") != seed:
                raise P0PrimeError(f"{sample_context}: {name} seed disagrees with latency metric")
            enabled = observation.get("time_enabled_ns")
            running = observation.get("time_running_ns")
            if not isinstance(enabled, int) or not isinstance(running, int):
                raise P0PrimeError(f"{sample_context}: {name} has invalid PMU time")
            if running > enabled:
                raise P0PrimeError(
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


def _is_bimodal(values: list[float]) -> bool:
    """预注册双峰规则：排序后相邻比值 ≥ _BIMODAL_RATIO 且两侧各
    ≥ _BIMODAL_MIN_SIDE 个样本。零值按比值未定义处理（不参与标记）。"""
    ordered = sorted(values)
    for left in range(_BIMODAL_MIN_SIDE, len(ordered) - _BIMODAL_MIN_SIDE + 1):
        low, high = ordered[left - 1], ordered[left]
        if low <= 0:
            continue
        if high / low >= _BIMODAL_RATIO:
            return True
    return False


def analyze_records(records: Iterable[dict], run_label: str) -> AnalysisResult:
    """校验记录并按 (buffer, seed, backing, ring_passes) 分组。

    status != ok 的记录由调用方（load_run）预先分流；这里只消费 ok 记录，
    multiplex/zero-running 样本被拒绝并登记（同记录其余样本保留）。
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
        raise P0PrimeError(f"{run_label}: no records")

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
            "bimodal": _is_bimodal([s["l2d_miss_per_1k"] for s in samples]),
        }
        for field_name in ("latency_ns", *_DERIVED_FIELDS):
            group[field_name] = summarize([s[field_name] for s in samples])
        result.groups.append(group)
    return result


def _fmt(value: float) -> str:
    return f"{value:.3f}"


def build_markdown(results: list[AnalysisResult], show_samples: bool = False) -> str:
    """分组汇总（median [p25, p75]）+ 拒绝清单；show_samples 展开逐样本行。"""
    lines = [
        "# P0″ demand/prefetch per-sample analysis",
        "",
        "All numeric cells are median [p25, p75]; rates are per 1,000 timed loads.",
        "PMU rows are accepted only when time_running_ns == time_enabled_ns for every event.",
        "",
        "| run | buffer KiB | seed | backing | passes | n | latency ns | cyc/load | mem rd/1k | l1 miss/1k | l1 hwprf/1k | l2 miss/1k | l2 hwprf/1k | bimodal |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
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
                               "l1d_miss_per_1k", "l1d_hwprf_per_1k",
                               "l2d_miss_per_1k", "l2d_hwprf_per_1k"):
                stats = group[field_name]
                cells.append(f"{_fmt(stats['median'])} [{_fmt(stats['p25'])}, {_fmt(stats['p75'])}]")
            cells.append("YES" if group["bimodal"] else "no")
            lines.append("| " + " | ".join(cells) + " |")
            if show_samples:
                for sample in group["samples"]:
                    lines.append(
                        f"<!-- sample {result.run_label} b{group['buffer_kb']}K "
                        f"seed={sample['seed']} s{sample['sample_index']}: "
                        f"lat={sample['latency_ns']:.4f} cyc={sample['cyc_per_load']:.3f} "
                        f"mem_rd={sample['mem_rd_per_1k']:.2f} l1miss={sample['l1d_miss_per_1k']:.2f} "
                        f"l1hwprf={sample['l1d_hwprf_per_1k']:.2f} l2miss={sample['l2d_miss_per_1k']:.3f} "
                        f"l2hwprf={sample['l2d_hwprf_per_1k']:.2f} -->"
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
    parser.add_argument("--samples", action="store_true",
                        help="在汇总后附逐样本行（HTML 注释形式，便于归档）")
    args = parser.parse_args(argv)

    results: list[AnalysisResult] = []
    for run_dir in args.run:
        data = load_run(Path(run_dir))
        label = Path(run_dir).name
        result = analyze_records(data.ok_records, label)
        for record in data.failed_records:
            result.rejected.append(
                f"{label}/buffer={record.get('params', {}).get('buffer_kb')}KiB"
                f": record status={record.get('status')}"
            )
        results.append(result)
    sys.stdout.write(build_markdown(results, show_samples=args.samples))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
