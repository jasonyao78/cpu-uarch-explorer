# SPDX-License-Identifier: Apache-2.0
"""Probe adapter 协议（OI-9 蓝图：ProbeAdapter 最小方法集）。

adapter 只负责两件事：参数 → argv；stdout/stderr → 结构化 metrics。
解析失败抛 ParseError，由上层转成 status=failed + 结构化 failure——
**绝不返回编造的数值**（run-record.v2 允许 failed 记录空 metrics）。
"""

from __future__ import annotations

from typing import Any, Protocol

from runner.errors import ParseError


class ProbeAdapter(Protocol):
    probe_name: str
    protocol_version: str
    implementation_id: str  # "portable" 或 "kernel:<isa>"（ADR-0006 §2）

    def build_argv(self, params: dict[str, Any]) -> list[str]: ...
    def parse_output(self, stdout: str, stderr: str) -> list[dict[str, Any]]: ...


def parse_key_value_lines(stdout: str) -> dict[str, str]:
    """解析 Probe ABI 的 key=value 行（ADR-0006 §3）。"""
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        for token in line.split():
            if "=" in token:
                k, _, v = token.partition("=")
                out[k] = v
    return out


def require_finite_number(fields: dict[str, str], key: str) -> float:
    import math
    raw = fields.get(key)
    if raw is None:
        raise ParseError(f"missing field {key!r} in probe output")
    try:
        value = float(raw)
    except ValueError:
        raise ParseError(f"field {key!r} is not numeric: {raw!r}")
    if not math.isfinite(value):
        raise ParseError(f"field {key!r} is not finite: {raw!r} (refusing to record nan/inf)")
    return value
