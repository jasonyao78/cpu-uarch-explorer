# SPDX-License-Identifier: Apache-2.0
"""ptr_chase adapter：指针追逐内存延迟探针（probes/cache-mem/ptr_chase.cpp）。

Probe ABI（与源码头部注释一致）：
  argv:  -b buffer_kb -s stride_bytes -n loads -w warmup
  stdout: buffer_kb=.. stride=.. loads=.. elapsed_ns=.. latency_ns=..
  退出码: 0 成功 / 1 输入或环境错误 / 2 能力不支持（保留）
"""

from __future__ import annotations

from typing import Any

from runner.errors import ParseError

from .base import parse_key_value_lines, require_finite_number


class PtrChaseAdapter:
    probe_name = "ptr_chase"
    protocol_version = "1.0"
    implementation_id = "portable"

    def build_argv(self, params: dict[str, Any]) -> list[str]:
        try:
            buffer_kb = int(params["buffer_kb"])
            stride = int(params["stride"])
            loads = int(params["loads"])
            warmup = int(params["warmup"])
        except (KeyError, TypeError, ValueError) as e:
            raise ParseError(f"ptr_chase argv build failed: {e}")
        return ["-b", str(buffer_kb), "-s", str(stride),
                "-n", str(loads), "-w", str(warmup)]

    def parse_output(self, stdout: str, stderr: str) -> list[dict[str, Any]]:
        fields = parse_key_value_lines(stdout)
        if not fields:
            raise ParseError(f"no key=value lines in probe output; stderr={stderr.strip()!r}")
        latency = require_finite_number(fields, "latency_ns")
        return [{"name": "latency_ns", "value": latency, "unit": "ns"}]
