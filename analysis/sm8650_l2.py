# SPDX-License-Identifier: Apache-2.0
"""SM8650 X4 私有 L2 校准的逐样本分析器。

通用报告层按 case 展示 runner 聚合统计；本模块服务一个更严格的裁定：
THP 请求可能在不同进程中得到 base 或 mixed 后备，因此必须按
``sample_index`` 联结 latency/PMU observation，再按实际页后备分组。
任何缺指标、错位或 PMU multiplex 都使本次校准不可裁定。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from runner.statistics import summarize

from .load import load_run


class CalibrationError(ValueError):
    """输入不满足 SM8650 L2 校准证据契约。"""


_LATENCY = "latency_ns"
_PMU_EVENTS = {
    "pmu.cycles.count": (8, 0x11, "cycles_per_load"),
    "pmu.l2d_cache_refill.count": (8, 0x17, "l2_refills_per_1k_loads"),
    "pmu.l3d_cache_refill.count": (8, 0x2A, "l3_refills_per_1k_loads"),
    "pmu.dtlb_walk.count": (8, 0x34, "dtlb_walks_per_1k_loads"),
}
_REQUIRED_METRICS = {_LATENCY, *_PMU_EVENTS}
_BACKING_ORDER = {"base": 0, "mixed": 1, "thp": 2}


def _observations_by_index(metric: dict, context: str) -> dict[int, dict]:
    observations = metric.get("observations")
    if not isinstance(observations, list) or not observations:
        raise CalibrationError(f"{context}: metric {metric.get('name')} has no observations")
    indexed: dict[int, dict] = {}
    for observation in observations:
        index = observation.get("sample_index")
        if not isinstance(index, int) or index < 0:
            raise CalibrationError(f"{context}: invalid sample_index {index!r}")
        if index in indexed:
            raise CalibrationError(f"{context}: duplicate sample_index {index}")
        indexed[index] = observation
    repetitions = metric.get("repetitions")
    if repetitions != len(indexed):
        raise CalibrationError(
            f"{context}: metric {metric.get('name')} repetitions={repetitions} "
            f"but has {len(indexed)} observations"
        )
    return indexed


def _samples_from_record(record: dict, run_label: str) -> list[dict]:
    context = f"{run_label}/buffer={record.get('params', {}).get('buffer_kb')}KiB"
    if record.get("schema_version") != "2.0" or record.get("status") != "ok":
        raise CalibrationError(f"{context}: record must be schema v2 with status=ok")
    if record.get("target", {}).get("target_id") != "redmi-k70pro-01":
        raise CalibrationError(f"{context}: unexpected target")
    probe = record.get("probe", {})
    if probe.get("name") != "ptr_chase" or probe.get("protocol_version") != "1.2":
        raise CalibrationError(f"{context}: ptr_chase protocol 1.2 required")

    params = record.get("params", {})
    buffer_kb = params.get("buffer_kb")
    loads = params.get("loads")
    if not isinstance(buffer_kb, int) or buffer_kb <= 0:
        raise CalibrationError(f"{context}: positive integer buffer_kb required")
    if not isinstance(loads, int) or loads <= 0:
        raise CalibrationError(f"{context}: positive integer loads required")

    metrics = record.get("metrics", [])
    by_name = {metric.get("name"): metric for metric in metrics}
    if len(by_name) != len(metrics) or set(by_name) != _REQUIRED_METRICS:
        raise CalibrationError(
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
            raise CalibrationError(f"{context}: {name} sample_index set does not align")

    samples = []
    for sample_index in sorted(latency_indexes):
        latency = indexed[_LATENCY][sample_index]
        actual = latency.get("page_policy_actual")
        if actual not in _BACKING_ORDER:
            raise CalibrationError(f"{context}/sample={sample_index}: unknown page backing {actual!r}")
        requested = latency.get("page_policy_requested")
        if requested not in {"base-madvise", "thp-madvise"}:
            raise CalibrationError(
                f"{context}/sample={sample_index}: unknown requested page policy {requested!r}"
            )
        sample = {
            "run_label": run_label,
            "buffer_kb": buffer_kb,
            "page_policy_requested": requested,
            "page_policy_actual": actual,
            "sample_index": sample_index,
            "latency_ns": float(latency["value"]),
            "anon_huge_kb": float(latency.get("anon_huge_kb", 0)),
        }
        for name, (expected_type, expected_config, derived_name) in _PMU_EVENTS.items():
            observation = indexed[name][sample_index]
            if (observation.get("pmu_type"), observation.get("pmu_config")) != (
                expected_type,
                expected_config,
            ):
                raise CalibrationError(
                    f"{context}/sample={sample_index}: {name} has unexpected PMU encoding"
                )
            enabled = observation.get("time_enabled_ns")
            running = observation.get("time_running_ns")
            if not isinstance(enabled, int) or not isinstance(running, int) or running <= 0:
                raise CalibrationError(
                    f"{context}/sample={sample_index}: {name} has invalid PMU time"
                )
            if running != enabled:
                raise CalibrationError(
                    f"{context}/sample={sample_index}: {name} is multiplexed "
                    f"(running={running}, enabled={enabled})"
                )
            scale = 1.0 if derived_name == "cycles_per_load" else 1000.0
            sample[derived_name] = float(observation["value"]) / loads * scale
        samples.append(sample)
    return samples


def analyze_records(records: Iterable[dict], run_label: str) -> list[dict]:
    """校验并汇总记录，分组键为 run/buffer/实际页后备。"""
    grouped: dict[tuple[str, int, str, str], list[dict]] = defaultdict(list)
    seen = False
    for record in records:
        seen = True
        for sample in _samples_from_record(record, run_label):
            key = (
                run_label,
                sample["buffer_kb"],
                sample["page_policy_requested"],
                sample["page_policy_actual"],
            )
            grouped[key].append(sample)
    if not seen:
        raise CalibrationError(f"{run_label}: no records")

    summary_fields = (
        "latency_ns",
        "cycles_per_load",
        "l2_refills_per_1k_loads",
        "l3_refills_per_1k_loads",
        "dtlb_walks_per_1k_loads",
        "anon_huge_kb",
    )
    groups = []
    for (label, buffer_kb, requested, actual), samples in grouped.items():
        group = {
            "run_label": label,
            "buffer_kb": buffer_kb,
            "page_policy_requested": requested,
            "page_policy_actual": actual,
            "n": len(samples),
            "sample_indexes": sorted(sample["sample_index"] for sample in samples),
        }
        for field in summary_fields:
            group[field] = summarize([sample[field] for sample in samples])
        groups.append(group)
    return sorted(
        groups,
        key=lambda group: (
            group["run_label"],
            group["buffer_kb"],
            _BACKING_ORDER[group["page_policy_actual"]],
        ),
    )


def _interval(statistics: dict, digits: int) -> str:
    return (
        f"{statistics['median']:.{digits}f} "
        f"[{statistics['p25']:.{digits}f}, {statistics['p75']:.{digits}f}]"
    )


def build_markdown(groups: list[dict]) -> str:
    """生成按 run 分节的可审计 Markdown 表；数字为 median [p25, p75]。"""
    if not groups:
        raise CalibrationError("cannot build report without groups")
    lines = [
        "# SM8650 X4 L2 calibration — sample-aligned summary",
        "",
        "All numeric cells are median [p25, p75]. Page groups use actual backing, not request.",
        "PMU rows are accepted only when time_running_ns == time_enabled_ns for every event.",
        "",
    ]
    labels = list(dict.fromkeys(group["run_label"] for group in groups))
    for label in labels:
        lines += [
            f"## {label}",
            "",
            "| Buffer KiB | Actual backing | n | Latency ns | Cycles/load | "
            "L2 refill/1k loads | L3 refill/1k loads | DTLB walk/1k loads | AnonHuge KiB |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for group in groups:
            if group["run_label"] != label:
                continue
            lines.append(
                f"| {group['buffer_kb']} | {group['page_policy_actual']} | {group['n']} | "
                f"{_interval(group['latency_ns'], 4)} | "
                f"{_interval(group['cycles_per_load'], 3)} | "
                f"{_interval(group['l2_refills_per_1k_loads'], 3)} | "
                f"{_interval(group['l3_refills_per_1k_loads'], 3)} | "
                f"{_interval(group['dtlb_walks_per_1k_loads'], 3)} | "
                f"{_interval(group['anon_huge_kb'], 0)} |"
            )
        lines.append("")
    return "\n".join(lines)


def _load_checked(run_dir: str, run_label: str) -> list[dict]:
    run = load_run(run_dir)
    if run.failed_records:
        raise CalibrationError(f"{run_label}: run contains {len(run.failed_records)} failed records")
    return analyze_records(run.ok_records, run_label)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="base-page run directory")
    parser.add_argument("--thp", required=True, help="THP-request run directory")
    parser.add_argument("--json-out", help="optional deterministic JSON output")
    parser.add_argument("--markdown-out", help="optional Markdown output")
    args = parser.parse_args(argv)
    try:
        groups = _load_checked(args.base, "base-request")
        groups += _load_checked(args.thp, "thp-request")
        markdown = build_markdown(groups)
        if args.json_out:
            Path(args.json_out).write_text(
                json.dumps(groups, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        if args.markdown_out:
            Path(args.markdown_out).write_text(markdown + "\n", encoding="utf-8")
        print(markdown)
        return 0
    except (CalibrationError, FileNotFoundError, KeyError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
