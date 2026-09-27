# SPDX-License-Identifier: Apache-2.0
"""ptr_chase adapter：指针追逐内存延迟探针（probes/cache-mem/ptr_chase.cpp）。

Probe ABI（与源码头部注释一致）：
  argv:  -b buffer_kb -s stride_bytes -n loads -w warmup [-B|-h|-H|-T]
  stdout: buffer_kb=.. .. latency_ns=.. warmup_loads=..
          warmup_passes_effective=.. warmup_state=.. page_policy=.. page_kb=..
  退出码: 0 成功 / 1 输入或环境错误 / 2 能力不支持（hugepage 无平台能力或
          strict 模式缺页池；fallback 非 strict 模式下成功但标注 fallback-4k）

measurement-discipline §2：请求页策略与实际 backing 必须分字段保存；
page_policy 随 metric 入档（requested/actual 双记录原则）。
"""

from __future__ import annotations

import re
from typing import Any

from runner.errors import ParseError

from .base import parse_key_value_lines, require_finite_number

_PMU_LABEL_RE = re.compile(r"^[a-z0-9_]+$")
_PMU_SUFFIXES = (
    "_time_enabled_ns", "_time_running_ns", "_config", "_count", "_type",
)


def _binary_flag(params: dict[str, Any], name: str) -> int:
    raw = params.get(name, 0)
    if type(raw) is int and raw in (0, 1):
        return raw
    if type(raw) is str and raw in ("0", "1"):
        return int(raw)
    raise ParseError(f"{name} must be 0 or 1, got {raw!r}")


def _pmu_events(params: dict[str, Any]) -> list[dict[str, int | str]]:
    raw = params.get("pmu_events", [])
    if not isinstance(raw, list):
        raise ParseError(f"pmu_events must be a list, got {raw!r}")
    normalized: list[dict[str, int | str]] = []
    labels: set[str] = set()
    for index, event in enumerate(raw):
        if not isinstance(event, dict) or set(event) != {"name", "type", "config"}:
            raise ParseError(f"pmu_events[{index}] must contain exactly name/type/config")
        label = event["name"]
        event_type = event["type"]
        config = event["config"]
        if not isinstance(label, str) or not _PMU_LABEL_RE.fullmatch(label):
            raise ParseError(f"pmu_events[{index}].name is unsafe: {label!r}")
        if label in labels:
            raise ParseError(f"pmu_events has duplicate name {label!r}")
        if type(event_type) is not int or not 0 <= event_type <= (1 << 32) - 1:
            raise ParseError(f"pmu_events[{index}].type is not uint32: {event_type!r}")
        if type(config) is not int or not 0 <= config <= (1 << 64) - 1:
            raise ParseError(f"pmu_events[{index}].config is not uint64: {config!r}")
        labels.add(label)
        normalized.append({"name": label, "type": event_type, "config": config})
    return normalized


def _require_uint(fields: dict[str, str], key: str, maximum: int) -> int:
    raw = fields.get(key)
    if raw is None or not raw.isdigit():
        raise ParseError(f"field {key!r} must be an unsigned integer: {raw!r}")
    value = int(raw)
    if value > maximum:
        raise ParseError(f"field {key!r} exceeds {maximum}: {raw!r}")
    return value


class PtrChaseAdapter:
    probe_name = "ptr_chase"
    protocol_version = "1.2"
    implementation_id = "portable"

    def build_argv(self, params: dict[str, Any]) -> list[str]:
        """参数 dict → probe argv。缺参数/类型错误抛 ParseError（plan 期已校验，
        此处是最后一道防线）。hugepage 非 0 时加 -h（fallback 允许）；
        thp 非 0 时加 -T；base_pages 非 0 时加 -B；三类页请求互斥。"""
        try:
            buffer_kb = int(params["buffer_kb"])
            stride = int(params["stride"])
            loads = int(params["loads"])
            warmup = int(params["warmup"])
        except (KeyError, TypeError, ValueError) as e:
            raise ParseError(f"ptr_chase argv build failed: {e}")
        hugepage = _binary_flag(params, "hugepage")
        thp = _binary_flag(params, "thp")
        base_pages = _binary_flag(params, "base_pages")
        if hugepage + thp + base_pages > 1:
            raise ParseError("ptr_chase page policies are mutually exclusive")
        argv = ["-b", str(buffer_kb), "-s", str(stride),
                "-n", str(loads), "-w", str(warmup)]
        if hugepage:
            argv.append("-h")
        if thp:
            argv.append("-T")
        if base_pages:
            argv.append("-B")
        for event in _pmu_events(params):
            argv.extend([
                "--pmu-event",
                f"{event['name']}:{event['type']}:{event['config']}",
            ])
        return argv

    def parse_output(self, stdout: str, stderr: str) -> list[dict[str, Any]]:
        """stdout key=value → metrics 列表。缺 latency_ns、非数值、nan/inf
        一律抛 ParseError（绝不编造数值，空 metrics + failure 是合法出路）。
        page_policy 存在时随 metric 入档（§2 显式标注纪律）。"""
        fields = parse_key_value_lines(stdout)
        if not fields:
            raise ParseError(f"no key=value lines in probe output; stderr={stderr.strip()!r}")
        latency = require_finite_number(fields, "latency_ns")
        metric: dict[str, Any] = {"name": "latency_ns", "value": latency, "unit": "ns"}
        warmup_keys = {"warmup_loads", "warmup_passes_effective", "warmup_state"}
        present_warmup_keys = warmup_keys.intersection(fields)
        if present_warmup_keys:
            if present_warmup_keys != warmup_keys:
                missing = sorted(warmup_keys - present_warmup_keys)
                raise ParseError(f"incomplete warmup audit fields; missing {missing}")
            raw_loads = fields["warmup_loads"]
            if not raw_loads.isdigit():
                raise ParseError(f"warmup_loads must be a non-negative integer: {raw_loads!r}")
            warmup_loads = int(raw_loads)
            warmup_passes = require_finite_number(fields, "warmup_passes_effective")
            if warmup_passes < 0:
                raise ParseError(
                    f"warmup_passes_effective must be non-negative: {warmup_passes!r}"
                )
            warmup_state = fields["warmup_state"]
            if warmup_state not in ("warm", "cold-warm0"):
                raise ParseError(f"invalid warmup_state: {warmup_state!r}")
            expected_state = "cold-warm0" if warmup_loads == 0 else "warm"
            if warmup_state != expected_state:
                raise ParseError(
                    f"warmup_state {warmup_state!r} contradicts "
                    f"warmup_loads={warmup_loads}"
                )
            metric.update({
                "warmup_loads": warmup_loads,
                "warmup_passes_effective": warmup_passes,
                "warmup_state": warmup_state,
            })
        if "page_policy" in fields:
            metric["page_policy"] = fields["page_policy"]
        page_audit_keys = {
            "page_policy_requested", "page_policy_actual", "anon_huge_kb",
        }
        present_page_audit_keys = page_audit_keys.intersection(fields)
        if present_page_audit_keys:
            if present_page_audit_keys != page_audit_keys:
                missing = sorted(page_audit_keys - present_page_audit_keys)
                raise ParseError(f"incomplete page backing fields; missing {missing}")
            requested = fields["page_policy_requested"]
            if requested not in (
                "default", "base-madvise", "hugetlb-fallback", "hugetlb-strict",
                "thp-madvise",
            ):
                raise ParseError(f"invalid page_policy_requested: {requested!r}")
            actual = fields["page_policy_actual"]
            if actual not in ("platform-default", "base", "thp", "mixed", "hugetlb-2m"):
                raise ParseError(f"invalid page_policy_actual: {actual!r}")
            raw_anon_huge_kb = fields["anon_huge_kb"]
            if not raw_anon_huge_kb.isdigit():
                raise ParseError(
                    f"anon_huge_kb must be a non-negative integer: {raw_anon_huge_kb!r}"
                )
            metric.update({
                "page_policy_requested": requested,
                "page_policy_actual": actual,
                "anon_huge_kb": int(raw_anon_huge_kb),
            })
        if "page_kb" in fields:
            raw_page_kb = fields["page_kb"]
            if not raw_page_kb.isdigit():
                raise ParseError(f"page_kb must be a non-negative integer: {raw_page_kb!r}")
            metric["page_kb"] = int(raw_page_kb)
        labels: list[str] = []
        seen_labels: set[str] = set()
        for key in fields:
            if not key.startswith("pmu_"):
                continue
            label = None
            for suffix in _PMU_SUFFIXES:
                if key.endswith(suffix):
                    label = key[len("pmu_"):-len(suffix)]
                    break
            if label is None or not _PMU_LABEL_RE.fullmatch(label):
                raise ParseError(f"invalid PMU output field: {key!r}")
            if label not in seen_labels:
                seen_labels.add(label)
                labels.append(label)

        metrics = [metric]
        for label in labels:
            prefix = f"pmu_{label}_"
            event_type = _require_uint(fields, prefix + "type", (1 << 32) - 1)
            config = _require_uint(fields, prefix + "config", (1 << 64) - 1)
            count = _require_uint(fields, prefix + "count", (1 << 64) - 1)
            enabled = _require_uint(
                fields, prefix + "time_enabled_ns", (1 << 64) - 1,
            )
            running = _require_uint(
                fields, prefix + "time_running_ns", (1 << 64) - 1,
            )
            if running == 0:
                raise ParseError(f"PMU event {label!r} has zero running time")
            if running > enabled:
                raise ParseError(
                    f"PMU event {label!r} running time exceeds enabled time"
                )
            metrics.append({
                "name": f"pmu.{label}.count",
                "value": count,
                "unit": "events",
                "pmu_type": event_type,
                "pmu_config": config,
                "time_enabled_ns": enabled,
                "time_running_ns": running,
            })
        return metrics
