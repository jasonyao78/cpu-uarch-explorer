# SPDX-License-Identifier: Apache-2.0
"""Plan：ExperimentSpec + platform 配置 → 确定性 case 集合（Plan/Run 分离）。

plan 只做解析与展开，不产生任何副作用（不执行、不写盘），可以先
`python -m runner.cli plan` 预览全部 case 再决定 run。

教训锚点（GB10 评审）：profile 声明 samples=7 但 runner 从不消费——
本模块把 repetitions 直接展开进 case，sample 数量在 plan 阶段即可审计。
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from .errors import RunnerError
from .resolve import ResolvedValue, parse_size_bytes, parse_size_kb, resolve_param


@dataclass(frozen=True)
class Control:
    """一次调度控制设置（macOS QoS / Linux taskset 等），对应 environment.control。"""
    id: str
    mechanism: str
    value: str
    command_prefix: tuple[str, ...] = ()


@dataclass(frozen=True)
class Case:
    """一个确定性执行单元：同一参数组合 × 同一控制设置，重复 repetitions 次。"""
    id: str
    probe: str
    control: Control
    params: tuple[tuple[str, ResolvedValue], ...]
    repetitions: int

    def param_value(self, name: str) -> Any:
        return dict(self.params)[name].value


@dataclass(frozen=True)
class Plan:
    experiment_id: str
    protocol_version: str
    cases: tuple[Case, ...]
    target: dict[str, Any] = field(default_factory=dict)


def _parse_controls(platform: dict) -> list[Control]:
    """平台配置的 controls 列表 → Control 对象；未配置任何控制手段时返回
    显式的 none 控制——"没有控制"本身也是必须入档的测量条件。"""
    controls = []
    for c in platform.get("controls", []) or []:
        controls.append(Control(
            id=c["id"],
            mechanism=c["control"]["mechanism"],
            value=c["control"]["value"],
            command_prefix=tuple(c.get("command_prefix", [])),
        ))
    if not controls:  # 无控制手段 = 显式的 none，不是省略
        controls.append(Control(id="uncontrolled", mechanism="none", value=""))
    return controls


def build_plan(spec: dict, platform: dict, cli_overrides: dict | None = None) -> Plan:
    """展开确定性 case 集合：controls × sweep 笛卡尔积，每 case 携带
    repetitions 与参数溯源。所有单位解析/派生计算在此完成——plan 期报错，
    run 期不做参数解释（GB10 静默降级教训的对冲结构）。"""
    cli_overrides = cli_overrides or {}
    exe = spec["execution"]
    probe = exe["probe"]
    if probe not in platform["probes"]:
        raise RunnerError("plan-error", f"platform has no binary mapping for probe {probe!r}")

    spec_defaults = {p["name"]: p["default"] for p in spec.get("parameters", []) if "default" in p}
    platform_defaults = platform.get("defaults", {}) or {}
    exp_params = exe.get("params", {}) or {}

    repetitions_rv = resolve_param("repetitions", cli=cli_overrides, experiment=exp_params,
                                   platform_defaults=platform_defaults, spec_defaults=spec_defaults)
    repetitions = int(repetitions_rv.value)
    if repetitions < 1:
        raise RunnerError("plan-error", f"repetitions must be >= 1, got {repetitions}")

    sweep = exe["sweep"]  # 参数名 → 取值列表（字符串尺寸或数值）
    sweep_names = sorted(sweep)
    if not sweep_names:
        raise RunnerError("plan-error", "execution.sweep is empty")

    cases: list[Case] = []
    for control in _parse_controls(platform):
        for combo in itertools.product(*(sweep[n] for n in sweep_names)):
            sweep_values = dict(zip(sweep_names, combo))
            params: dict[str, ResolvedValue] = {}
            for name in sweep_names:
                params[name] = ResolvedValue(sweep_values[name], "experiment-sweep")
            for name in exe.get("fixed_params", []) or []:
                params[name] = resolve_param(name, cli=cli_overrides, experiment=exp_params,
                                             platform_defaults=platform_defaults,
                                             spec_defaults=spec_defaults)

            # ptr_chase 语义参数计算（buffer/stride/loads）：在 plan 期完成并可审计
            buffer_kb = parse_size_kb(str(params["buffer"].value))
            stride_b = parse_size_bytes(str(params["stride"].value))
            slots = (buffer_kb * 1024) // stride_b
            if slots < 2:
                raise RunnerError("plan-error", f"buffer {buffer_kb}KB too small for stride {stride_b}B")
            loads_per_slot = int(params.get("loads_per_slot", ResolvedValue(8, "spec-default")).value)
            min_loads = int(params.get("min_loads", ResolvedValue(1 << 22, "spec-default")).value)
            loads = max(min_loads, loads_per_slot * slots)
            loads -= loads % 8  # 对齐展开因子（Probe ABI：loads >= 8 且为 8 的倍数）

            case_params = tuple(sorted({
                "buffer_kb": ResolvedValue(buffer_kb, params["buffer"].source),
                "stride": ResolvedValue(stride_b, params["stride"].source),
                "loads": ResolvedValue(loads, "derived"),
                "warmup": ResolvedValue(int(params.get("warmup", ResolvedValue(200000, "spec-default")).value),
                                        params.get("warmup", ResolvedValue(None, "spec-default")).source),
            }.items()))
            case_id = f"{spec['id']}:{control.id}:b{buffer_kb}K-s{stride_b}B"
            cases.append(Case(id=case_id, probe=probe, control=control,
                              params=case_params, repetitions=repetitions))

    return Plan(experiment_id=spec["id"], protocol_version=spec["protocol_version"],
                cases=tuple(cases), target=platform["target"])
