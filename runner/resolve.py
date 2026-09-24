# SPDX-License-Identifier: Apache-2.0
"""参数解析与溯源（OI-9 蓝图：ResolvedValue{value, source}）。

教训锚点（2026-09-24 评审实证，GB10 runner.py）：working-set 的 MiB/KiB
单位不被识别时静默降级为默认 1024KB。本模块的反模式禁令：
**未知单位必须报错，绝不回落默认值。**
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .errors import RunnerError

# 1024 进制单位语义（KB/MB/GB 在本仓一律按二进制解释，写入文档与报告）；
# 新增单位须同步更新本表与测试。未知后缀 = 硬错误。
_SIZE_FACTORS_BYTES = {
    "B": 1,
    "KB": 1024, "MB": 1024**2, "GB": 1024**3,
    "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3,
}

_SIZE_RE = re.compile(r"^\s*(\d+)\s*([A-Za-z]+)\s*$")


def parse_size_bytes(text: str) -> int:
    """把 '64MiB' / '512KB' / '4096B' 解析为字节数；未知单位抛 RunnerError。"""
    m = _SIZE_RE.match(text)
    if not m:
        raise RunnerError("param-parse", f"invalid size literal: {text!r} "
                                         f"(expect <integer><unit>, units: {sorted(_SIZE_FACTORS_BYTES)})")
    number, unit = int(m.group(1)), m.group(2)
    if unit not in _SIZE_FACTORS_BYTES:
        raise RunnerError("param-parse", f"unknown size unit {unit!r} in {text!r}; "
                                         f"known units: {sorted(_SIZE_FACTORS_BYTES)}. "
                                         f"Refusing to fall back to a default (silent downgrade is forbidden).")
    return number * _SIZE_FACTORS_BYTES[unit]


def parse_size_kb(text: str) -> int:
    """解析为整数 KB（ptr_chase -b 的口径）；不足 1KB 或不能整除时报错。"""
    b = parse_size_bytes(text)
    if b == 0 or b % 1024 != 0:
        raise RunnerError("param-parse", f"size {text!r} must be a positive multiple of 1KB")
    return b // 1024


@dataclass(frozen=True)
class ResolvedValue:
    """参数值 + 来源溯源。source ∈ cli / experiment / platform-default / spec-default。"""

    value: Any
    source: str

    def __repr__(self) -> str:  # plan 预览可直接读
        return f"{self.value!r}({self.source})"


def resolve_param(name: str, *, cli: dict, experiment: dict,
                  platform_defaults: dict, spec_defaults: dict) -> ResolvedValue:
    """优先级：CLI > experiment > platform-default > spec-default。

    四层都没有时报错——参数不存在与参数取默认值是两件必须区分的事。
    """
    for source, layer in (("cli", cli), ("experiment", experiment),
                          ("platform-default", platform_defaults), ("spec-default", spec_defaults)):
        if name in layer:
            return ResolvedValue(layer[name], source)
    raise RunnerError("param-missing", f"parameter {name!r} has no value in any layer "
                                       f"(cli/experiment/platform-default/spec-default)")
