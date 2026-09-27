# SPDX-License-Identifier: Apache-2.0
"""ptr_chase adapter：指针追逐内存延迟探针（probes/cache-mem/ptr_chase.cpp）。

Probe ABI（与源码头部注释一致）：
  argv:  -b buffer_kb -s stride_bytes -n loads -w warmup [-h|-H]
  stdout: buffer_kb=.. .. latency_ns=.. warmup_loads=..
          warmup_passes_effective=.. warmup_state=.. page_policy=.. page_kb=..
  退出码: 0 成功 / 1 输入或环境错误 / 2 能力不支持（hugepage 无平台能力或
          strict 模式缺页池；fallback 非 strict 模式下成功但标注 fallback-4k）

measurement-discipline §2：hugepage 是 Linux 正式测量前提；fallback 必须
显式可见——page_policy 随 metric 入档（requested/actual 双记录原则）。
"""

from __future__ import annotations

from typing import Any

from runner.errors import ParseError

from .base import parse_key_value_lines, require_finite_number


class PtrChaseAdapter:
    probe_name = "ptr_chase"
    protocol_version = "1.1"
    implementation_id = "portable"

    def build_argv(self, params: dict[str, Any]) -> list[str]:
        """参数 dict → probe argv。缺参数/类型错误抛 ParseError（plan 期已校验，
        此处是最后一道防线）。hugepage 非 0 时加 -h（fallback 允许）。"""
        try:
            buffer_kb = int(params["buffer_kb"])
            stride = int(params["stride"])
            loads = int(params["loads"])
            warmup = int(params["warmup"])
            hugepage = int(params.get("hugepage", 0))
        except (KeyError, TypeError, ValueError) as e:
            raise ParseError(f"ptr_chase argv build failed: {e}")
        argv = ["-b", str(buffer_kb), "-s", str(stride),
                "-n", str(loads), "-w", str(warmup)]
        if hugepage:
            argv.append("-h")
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
        return [metric]
