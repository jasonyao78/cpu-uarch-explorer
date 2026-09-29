# SPDX-License-Identifier: Apache-2.0
"""ptr_chase adapter：指针追逐内存延迟探针（probes/cache-mem/ptr_chase.cpp）。

Probe ABI（与源码头部注释一致）：
  argv:  -b buffer_kb -s stride_bytes -n loads -w warmup [-S seed]
         [-B|-h|-H|-T] [--pmu-event label:type:config]...
  stdout: buffer_kb=.. .. latency_ns=.. warmup_loads=..
          warmup_passes_effective=.. warmup_state=.. page_policy=.. page_kb=..
          page_policy_actual_before/after=.. anon_huge_kb_before/after=..
          page_backing_endpoints_equal=1（两端观测一致，不代表连续观测）
          vma_base=0x…（建链缓冲区起始 VA，ASLR 布局观测，路线 A）
          seed=N（链洗牌种子，默认 42；访问序列是实验变量，必须入档）
  退出码: 0 成功 / 1 输入或环境错误 / 2 能力不支持（hugepage 无平台能力或
          strict 模式缺页池；fallback 非 strict 模式下成功但标注 fallback-4k）

measurement-discipline §2：请求页策略与实际 backing 必须分字段保存；
page_policy 随 metric 入档（requested/actual 双记录原则）。新输出还在
warmup 后/测量前与 timed/PMU 窗后做端点审计；parser 继续接受旧捕获。
"""

from __future__ import annotations

import re
from typing import Any

from runner.errors import ParseError

from .base import parse_key_value_lines, require_finite_number

_PMU_LABEL_RE = re.compile(r"^[a-z0-9_]+$")
_VMA_BASE_RE = re.compile(r"^0x[0-9a-f]+$")
_PMU_SUFFIXES = (
    "_time_enabled_ns", "_time_running_ns", "_config", "_count", "_type",
)
_PAGE_BACKINGS = ("platform-default", "base", "thp", "mixed", "hugetlb-2m")


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
        if "seed" in params:
            raw_seed = params["seed"]
            if type(raw_seed) is not int or raw_seed < 0 \
                    or raw_seed > (1 << 64) - 1:
                raise ParseError(f"seed must be a uint64 integer: {raw_seed!r}")
            argv.extend(["-S", str(raw_seed)])
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
            if actual not in _PAGE_BACKINGS:
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
        window_audit_keys = {
            "page_policy_actual_before", "page_policy_actual_after",
            "anon_huge_kb_before", "anon_huge_kb_after",
            "page_backing_endpoints_equal",
        }
        present_window_audit_keys = window_audit_keys.intersection(fields)
        if present_window_audit_keys:
            if present_window_audit_keys != window_audit_keys:
                missing = sorted(window_audit_keys - present_window_audit_keys)
                raise ParseError(
                    f"incomplete measurement-window page backing fields; missing {missing}"
                )
            if present_page_audit_keys != page_audit_keys:
                raise ParseError(
                    "measurement-window page backing fields require the legacy "
                    "requested/actual/anon_huge_kb fields"
                )
            before = fields["page_policy_actual_before"]
            after = fields["page_policy_actual_after"]
            if before not in _PAGE_BACKINGS or after not in _PAGE_BACKINGS:
                raise ParseError(
                    f"invalid measurement-window page backing: {before!r}/{after!r}"
                )
            raw_before_kb = fields["anon_huge_kb_before"]
            raw_after_kb = fields["anon_huge_kb_after"]
            if not raw_before_kb.isdigit() or not raw_after_kb.isdigit():
                raise ParseError(
                    "measurement-window anon_huge_kb values must be non-negative "
                    f"integers: {raw_before_kb!r}/{raw_after_kb!r}"
                )
            before_kb = int(raw_before_kb)
            after_kb = int(raw_after_kb)
            endpoints_equal = _require_uint(
                fields, "page_backing_endpoints_equal", 1,
            )
            if endpoints_equal != 1 or before != after or before_kb != after_kb:
                raise ParseError(
                    "successful ptr_chase output requires equal page-backing "
                    "observations at both measurement-window endpoints"
                )
            if before != metric["page_policy_actual"] \
                    or before_kb != metric["anon_huge_kb"]:
                raise ParseError(
                    "measurement-window page backing contradicts legacy summary fields"
                )
            metric.update({
                "page_policy_actual_before": before,
                "page_policy_actual_after": after,
                "anon_huge_kb_before": before_kb,
                "anon_huge_kb_after": after_kb,
                "page_backing_endpoints_equal": endpoints_equal,
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
        if "seed" in fields:
            # 链洗牌种子随每条 metric 入档（样本级溯源：地址相关预取/索引
            # 共振判别依赖逐样本 seed）。
            seed = _require_uint(fields, "seed", (1 << 64) - 1)
            for item in metrics:
                item["seed"] = seed
        if "vma_base" in fields:
            # 建链缓冲区起始 VA 随每条 metric 入档（SM8650 TLB 任务书路线 A：
            # order_seed 之外的布局观测依赖逐样本 VA；保持 hex 字符串不转
            # int，避免 reader 误当数值聚合）。
            vma_base = fields["vma_base"]
            if not _VMA_BASE_RE.fullmatch(vma_base):
                raise ParseError(
                    f"vma_base must be a lowercase hex address: {vma_base!r}")
            for item in metrics:
                item["vma_base"] = vma_base
        return metrics
