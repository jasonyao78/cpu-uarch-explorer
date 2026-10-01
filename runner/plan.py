# SPDX-License-Identifier: Apache-2.0
"""Plan：ExperimentSpec + platform 配置 → 确定性 case 集合（Plan/Run 分离）。

plan 只做解析与展开，不产生任何副作用（不执行、不写盘），可以先
`python -m runner.cli plan` 预览全部 case 再决定 run。

教训锚点（GB10 评审）：profile 声明 samples=7 但 runner 从不消费——
本模块把 repetitions 直接展开进 case，sample 数量在 plan 阶段即可审计。
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from dataclasses import dataclass, field
from typing import Any

from .errors import RunnerError
from .resolve import ResolvedValue, parse_size_bytes, parse_size_kb, resolve_param

MAX_PROBE_LOADS = (1 << 63) - 1
_PMU_LABEL_RE = re.compile(r"^[a-z0-9_]+$")
# case_id 模板已覆盖的 sweep 参数（见 build_plan 的 case_id 构造）；其余 swept
# 参数一律追加通用 -{name}{value} 段，防止未覆盖参数共享 id
_CASE_ID_COVERED_PARAMS = frozenset(
    {"buffer", "stride", "seed", "hugepage", "thp", "base_pages"})
# 通用 id 段（sweep 键名与 str 值）的字符白名单：段内容直接进 raw 样本文件名
# （artifacts.py 落盘前的 safe_case 净化是内联局部表达式，只替换 "/"与":"），
# 文件系统不安全字符在此 fail-closed
_CASE_ID_VALUE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


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


def _parse_controls(platform: dict, requested_ids: Any = None) -> list[Control]:
    """平台配置的 controls 列表 → Control 对象；未配置任何控制手段时返回
    显式的 none 控制——"没有控制"本身也是必须入档的测量条件。ExperimentSpec
    可用 execution.controls 选择已命名控制；未知、重复或空选择在 plan 期拒绝。"""
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
    by_id = {control.id: control for control in controls}
    if len(by_id) != len(controls):
        raise RunnerError("plan-error", "platform controls contain duplicate ids")
    if requested_ids is None:
        return controls
    if (not isinstance(requested_ids, list) or not requested_ids
            or any(not isinstance(item, str) or not item for item in requested_ids)
            or len(set(requested_ids)) != len(requested_ids)):
        raise RunnerError(
            "plan-error", "execution.controls must be a non-empty list of unique ids",
        )
    unknown = [control_id for control_id in requested_ids if control_id not in by_id]
    if unknown:
        raise RunnerError(
            "plan-error", f"execution.controls contains unknown ids: {unknown!r}",
        )
    return [by_id[control_id] for control_id in requested_ids]


def _binary_flag(name: str, rv: ResolvedValue | None) -> int:
    """解析 ExperimentSpec 的 0/1 开关；拒绝 float/bool/非规范字符串。

    旧配置曾把 hugepage 的 JSON 值写成字符串 "1"，因此兼容规范的
    "0"/"1"，但不允许 int() 把 0.5、True 或 "01" 静默归一化。
    """
    if rv is None:
        return 0
    raw = rv.value
    if type(raw) is int and raw in (0, 1):
        return raw
    if type(raw) is str and raw in ("0", "1"):
        return int(raw)
    raise RunnerError("plan-error", f"{name} must be 0 or 1, got {raw!r}")


def _normalize_pmu_events(rv: ResolvedValue | None) -> list[dict[str, int | str]]:
    """Validate a portable ExperimentSpec PMU list before any probe runs."""
    if rv is None:
        return []
    raw = rv.value
    if not isinstance(raw, list):
        raise RunnerError("plan-error", f"pmu_events must be a list, got {raw!r}")
    normalized: list[dict[str, int | str]] = []
    labels: set[str] = set()
    for index, event in enumerate(raw):
        if not isinstance(event, dict) or set(event) != {"name", "type", "config"}:
            raise RunnerError(
                "plan-error",
                f"pmu_events[{index}] must contain exactly name/type/config",
            )
        label = event["name"]
        if not isinstance(label, str) or not _PMU_LABEL_RE.fullmatch(label):
            raise RunnerError(
                "plan-error", f"pmu_events[{index}].name is unsafe: {label!r}",
            )
        if label in labels:
            raise RunnerError("plan-error", f"pmu_events has duplicate name {label!r}")
        event_type = event["type"]
        if (type(event_type) is not int or event_type < 0
                or event_type > (1 << 32) - 1):
            raise RunnerError(
                "plan-error", f"pmu_events[{index}].type is not uint32: {event_type!r}",
            )
        config_raw = event["config"]
        try:
            config = (int(config_raw, 0) if isinstance(config_raw, str)
                      else config_raw if type(config_raw) is int else None)
        except ValueError:
            config = None
        if config is None or config < 0 or config > (1 << 64) - 1:
            raise RunnerError(
                "plan-error", f"pmu_events[{index}].config is not uint64: {config_raw!r}",
            )
        labels.add(label)
        normalized.append({"name": label, "type": event_type, "config": config})
    return normalized




def _derive_ptr_chase_case_params(params: dict[str, ResolvedValue]) -> dict[str, ResolvedValue]:
    """ptr_chase 形状的语义参数派生（M0-4 从 planner 主循环抽出，逻辑逐字不变）。

    buffer/stride/loads/warmup 在 plan 期完成并可审计；warmup 双语义
    （精确 loads vs ring passes）硬拒绝共存；loads 对齐展开因子 8。
    """
    buffer_kb = parse_size_kb(str(params["buffer"].value))
    stride_b = parse_size_bytes(str(params["stride"].value))
    slots = (buffer_kb * 1024) // stride_b
    if slots < 2:
        raise RunnerError("plan-error", f"buffer {buffer_kb}KB too small for stride {stride_b}B")
    loads_per_slot = int(params.get("loads_per_slot", ResolvedValue(8, "spec-default")).value)
    min_loads = int(params.get("min_loads", ResolvedValue(1 << 22, "spec-default")).value)
    loads = max(min_loads, loads_per_slot * slots)
    loads -= loads % 8  # 对齐展开因子（Probe ABI：loads >= 8 且为 8 的倍数）

    # 新协议按完整 ring pass 表达预热；Probe ABI 仍接收精确 load 数。
    # legacy warmup 仅用于历史配置重放。两种语义同时出现会使记录无法
    # 判定操作者意图，因此在 plan 期硬拒绝。
    warmup_rv = params.get("warmup")
    passes_rv = params.get("warmup_passes")
    if warmup_rv is not None and passes_rv is not None:
        raise RunnerError(
            "plan-error",
            "ptr_chase cannot declare both warmup and warmup_passes",
        )
    if passes_rv is not None:
        if type(passes_rv.value) is not int:  # bool 也不得冒充 int
            raise RunnerError(
                "plan-error",
                f"warmup_passes must be an integer, got {passes_rv.value!r}",
            )
        warmup_passes = passes_rv.value
        if warmup_passes < 1:
            raise RunnerError(
                "plan-error",
                f"warmup_passes must be >= 1, got {warmup_passes}",
            )
        warmup = warmup_passes * slots
        if warmup > MAX_PROBE_LOADS:
            raise RunnerError(
                "plan-error",
                f"derived warmup loads exceed signed 64-bit limit: {warmup}",
            )
    elif warmup_rv is not None:
        if type(warmup_rv.value) is not int:
            raise RunnerError(
                "plan-error",
                f"legacy warmup must be an integer, got {warmup_rv.value!r}",
            )
        warmup = warmup_rv.value
        if warmup < 0:
            raise RunnerError(
                "plan-error", f"legacy warmup must be >= 0, got {warmup}",
            )
    else:
        raise RunnerError(
            "plan-error",
            "ptr_chase requires warmup_passes (current) or warmup (legacy)",
        )

    case_params = {
        "buffer_kb": ResolvedValue(buffer_kb, params["buffer"].source),
        "stride": ResolvedValue(stride_b, params["stride"].source),
        "loads": ResolvedValue(loads, "derived"),
        "warmup": ResolvedValue(
            warmup, "derived" if passes_rv is not None else warmup_rv.source,
        ),
    }
    if passes_rv is not None:
        case_params["warmup_passes"] = ResolvedValue(
            warmup_passes, passes_rv.source,
        )
    return case_params


# M0-4b：TLB set prime+probe 形状的语义参数派生（ptr_chase --tlb-set-mode
# 的证据探针版；方法蓝本 = 原型 l2_set_probe v2.3，差异见探针文件头注释：
# F5 GROUP 原子读 + window_delta 有效性、F4 多区域、G0-3 空窗/scatter 负控）。
# 所有参数被探针 argv 真实消费（MB-03 消费契约），无一仅为身份。
def _derive_tlb_set_case_params(params: dict[str, ResolvedValue]) -> dict[str, ResolvedValue]:
    def _int_param(name: str, default: int | None) -> ResolvedValue:
        rv = params.get(name)
        if rv is None:
            if default is None:
                raise RunnerError("plan-error", f"tlb_set shape requires param {name!r}")
            return ResolvedValue(default, "spec-default")
        if type(rv.value) is not int:
            raise RunnerError(
                "plan-error", f"{name} must be an integer, got {rv.value!r}")
        return rv

    hypothesis_rv = _int_param("set_hypothesis", None)
    hypothesis = hypothesis_rv.value
    if not 1 <= hypothesis <= 4:
        raise RunnerError(
            "plan-error", f"set_hypothesis must be 1..4, got {hypothesis}")
    target_rv = _int_param("set_target", None)
    target = target_rv.value
    if not 0 <= target <= 255:
        raise RunnerError(
            "plan-error", f"set_target must be 0..255, got {target}")
    window_rv = _int_param("set_window", None)
    window = window_rv.value
    if window < 0:
        raise RunnerError(
            "plan-error", f"set_window must be >= 0 (0 = empty window), got {window}")
    rounds_rv = _int_param("set_rounds", 20)
    if rounds_rv.value < 2:
        raise RunnerError(
            "plan-error",
            f"set_rounds must be >= 2 (round 0 cold-start), got {rounds_rv.value}")
    pool_rv = _int_param("set_pool_pages", 65536)
    if pool_rv.value < 1024:
        raise RunnerError(
            "plan-error", f"set_pool_pages must be >= 1024, got {pool_rv.value}")
    filler_rv = _int_param("set_filler_pages", 512)
    if filler_rv.value < 0:
        raise RunnerError(
            "plan-error", f"set_filler_pages must be >= 0, got {filler_rv.value}")
    regions_rv = _int_param("set_regions", 4)
    if not 1 <= regions_rv.value <= 16:
        raise RunnerError(
            "plan-error", f"set_regions must be 1..16, got {regions_rv.value}")
    scatter = params.get("set_scatter")
    scatter_flag = _binary_flag("set_scatter", scatter) if scatter else 0
    if scatter_flag and not 1 <= window <= 256:
        raise RunnerError(
            "plan-error",
            f"set_scatter requires 1 <= set_window <= 256, got {window}")

    case_params = {
        "set_hypothesis": hypothesis_rv,
        "set_target": target_rv,
        "set_window": window_rv,
        "set_rounds": rounds_rv,
        "set_pool_pages": pool_rv,
        "set_filler_pages": filler_rv,
        "set_regions": regions_rv,
    }
    target2 = params.get("set_target2")
    if target2 is not None:
        if type(target2.value) is not int or not 0 <= target2.value <= 255:
            raise RunnerError(
                "plan-error", f"set_target2 must be 0..255, got {target2.value!r}")
        case_params["set_target2"] = ResolvedValue(target2.value, target2.source)
    if scatter is not None:
        case_params["set_scatter"] = ResolvedValue(scatter_flag, scatter.source)
    return case_params


# MB-03（收口复核修订）：允许进通用 case_id 段的 swept 参数必须是
# deriver 真实消费的输入（见 _derive_ptr_chase_case_params）。"仅进 ID
# 不进执行"= 命名不同实验、证据无该维度，一律 leftover 拒绝。
# chains/chain_distribution/node_offset_policy/mapping_span_kb 等未实现
# 的探针语义维度不在此列——原生探针无对应 argv 协议，sweep 它们在
# plan 期受控失败（评审反例：chains=1/2 记录成两个条件、argv 完全相同）。
_CHASE_ID_SEGMENT_PARAMS = frozenset(
    {"loads_per_slot", "min_loads", "warmup", "warmup_passes"})

# M0-4 扩展缝：probe_shape → 语义参数派生函数。新探头形状在此注册；
# planner 主循环只负责 sweep 展开/fixed_params/通用旗标（页策略/PMU/seed）/case 组装。
# tlb_set 与 ptr_chase 共用同一二进制（ptr_chase --tlb-set-mode 模式分发）。
_CASE_DERIVERS = {
    "ptr_chase": _derive_ptr_chase_case_params,
    "tlb_set": _derive_tlb_set_case_params,
}

# 各形状的真实输入契约（MB-03 收口复核：leftover 拒绝按形状判定消费）。
_SHAPE_INPUT_PARAMS = {
    "ptr_chase": {"buffer", "stride", "loads_per_slot", "min_loads",
                  "warmup", "warmup_passes"},
    "tlb_set": {"set_hypothesis", "set_target", "set_target2", "set_window",
                "set_rounds", "set_pool_pages", "set_filler_pages",
                "set_regions", "set_scatter"},
}


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
    for control in _parse_controls(platform, exe.get("controls")):
        for combo in itertools.product(*(sweep[n] for n in sweep_names)):
            sweep_values = dict(zip(sweep_names, combo))
            params: dict[str, ResolvedValue] = {}
            for name in sweep_names:
                params[name] = ResolvedValue(sweep_values[name], "experiment-sweep")
            for name in exe.get("fixed_params", []) or []:
                params[name] = resolve_param(name, cli=cli_overrides, experiment=exp_params,
                                             platform_defaults=platform_defaults,
                                             spec_defaults=spec_defaults)

            # M0-4：probe_shape 派分——descriptor 扩展缝。默认 ptr_chase 保持
            # 战役行为逐字不变；新形状在 _CASE_DERIVERS 注册派生函数。
            shape = exe.get("probe_shape", "ptr_chase")
            deriver = _CASE_DERIVERS.get(shape)
            if deriver is None:
                raise RunnerError(
                    "plan-error",
                    f"unknown probe_shape {shape!r} (supported: "
                    f"{sorted(_CASE_DERIVERS)})",
                )
            case_params = deriver(params)

            # hugepage：实验声明时才进入 case（测量语义参数，measurement-discipline
            # §2）；未声明的实验完全不出现该键——旧配置零影响。
            hp_rv = params.get("hugepage")
            hugepage = _binary_flag("hugepage", hp_rv)
            thp_rv = params.get("thp")
            thp = _binary_flag("thp", thp_rv)
            base_pages_rv = params.get("base_pages")
            base_pages = _binary_flag("base_pages", base_pages_rv)
            if hugepage + thp + base_pages > 1:
                raise RunnerError(
                    "plan-error",
                    "ptr_chase cannot request both; page policies are mutually exclusive",
                )
            if shape == "tlb_set" and (hp_rv is not None or thp_rv is not None):
                # set 索引按 4K 粒度计算：tlb_set 形状强制 base 页，大页请求
                # 在 plan 期命名拒绝（探针侧 -h/-H/-T 同样拒绝，双保险）
                raise RunnerError(
                    "plan-error",
                    "tlb_set shape forces 4K base pages (set index assumes "
                    "4K granule); hugepage/thp requests are not allowed",
                )
            pmu_events_rv = params.get("pmu_events")
            pmu_events = _normalize_pmu_events(pmu_events_rv)
            seed_rv = params.get("seed")
            seed = None
            if seed_rv is not None:
                if type(seed_rv.value) is not int \
                        or not 0 <= seed_rv.value <= (1 << 64) - 1:
                    raise RunnerError(
                        "plan-error",
                        f"seed must be a uint64 integer, got {seed_rv.value!r}",
                    )
                seed = seed_rv.value

            # chase 几何读法只在 ptr_chase 分支内使用（收口复核 MB-03：
            # 通用形状不得隐含 chase 契约，否则新形状 plan 即 KeyError）
            if hp_rv is not None:
                case_params["hugepage"] = ResolvedValue(hugepage, hp_rv.source)
            if thp_rv is not None:
                case_params["thp"] = ResolvedValue(thp, thp_rv.source)
            if base_pages_rv is not None:
                case_params["base_pages"] = ResolvedValue(
                    base_pages, base_pages_rv.source,
                )
            if pmu_events_rv is not None:
                case_params["pmu_events"] = ResolvedValue(
                    pmu_events, pmu_events_rv.source,
                )
            if seed_rv is not None:
                case_params["seed"] = ResolvedValue(seed, seed_rv.source)

            if shape == "ptr_chase":
                buffer_kb = case_params["buffer_kb"].value
                stride_b = int(case_params["stride"].value)
                if pmu_events_rv is not None and "pmu_events" in sweep_names:
                    # 结构化值进不了 chase 模板 ID：swept pmu_events 会让
                    # 仅事件不同的 case 共享同一 id（重复 id 守卫才炸，语义
                    # 不清）——plan 期命名拒绝，走 fixed_params 或通用形状
                    raise RunnerError(
                        "plan-error",
                        "swept pmu_events is not supported for probe_shape "
                        "'ptr_chase' (structured values cannot enter the "
                        "legacy case id template); use fixed_params or a "
                        "generic probe_shape",
                    )
                case_id = (f"{spec['id']}:{control.id}:b{buffer_kb}K-s{stride_b}B"
                           + (f"-seed{seed}" if seed_rv is not None else "")
                           + ("-hp2m" if hugepage else "")
                           + ("-thp" if thp else "")
                           + ("-base" if base_pages else ""))
            else:
                # MB-03（收口复核）：通用形状 case_id = 全部 case_params 的
                # 规范化枚举，无任何 chase 隐含契约。标量 int/str 直接进段；
                # 结构化公共参数（pmu_events 列表等）用 canonical JSON 的
                # sha256 摘要进段（明确的规范化签名，不把列表字符串化成
                # 逐字段片段）；bool fail-closed（与 int 1 不可混淆，MB-06
                # 精神在 ID 层先守住）。
                segs = []
                for name in sorted(case_params):
                    val = case_params[name].value
                    if not _CASE_ID_VALUE_RE.fullmatch(name):
                        raise RunnerError(
                            "plan-error",
                            f"param name {name!r} has unsafe characters",
                        )
                    if type(val) is bool:
                        raise RunnerError(
                            "plan-error",
                            f"param {name!r} is bool; bool must not collapse "
                            "into an int case id segment",
                        )
                    if isinstance(val, (int, str)):
                        if not _CASE_ID_VALUE_RE.fullmatch(str(val)):
                            raise RunnerError(
                                "plan-error",
                                f"param {name!r} value has unsafe characters",
                            )
                        segs.append(f"{name}{val}")
                    elif isinstance(val, (list, dict)):
                        digest = hashlib.sha256(
                            json.dumps(val, sort_keys=True,
                                       separators=(",", ":")).encode(),
                        ).hexdigest()[:12]
                        segs.append(f"{name}h{digest}")
                    else:
                        raise RunnerError(
                            "plan-error",
                            f"param {name!r} value {val!r} cannot form a "
                            "case id segment (int/str or structured required)",
                        )
                case_id = f"{spec['id']}:{control.id}-" + "-".join(segs)
            # chase 形状的通用 id 段（触发案例：tlb-overhead 配置 sweep
            # loads_per_slot 后 24 case 仅 8 个唯一 id，raw 样本按 case id
            # 命名覆盖写 → 样本互覆、manifest id 重复、SHA256 锚定失效）：
            # 只允许 _CHASE_ID_SEGMENT_PARAMS（deriver 真实消费的输入）进段；
            # 段（sweep 键名与 str 值）直接进 raw 样本文件名：artifacts.py
            # 落盘前的 safe_case 净化是内联局部表达式（artifacts.py 中
            # case_id.replace("/", "_").replace(":", "_")，非函数），只替换
            # "/"与":"，唯一性断言又作用于净化前 id——含 "/"、空格等字符的
            # 键名/值会绕过断言后仍在落盘时互覆；白名单（仿 _PMU_LABEL_RE
            # 先例）把这一层残留风险同样 fail-closed 在 plan 期
            id_seg_names = set()
            if shape == "ptr_chase":
                for name in sweep_names:
                    if name in _CASE_ID_COVERED_PARAMS \
                            or name not in _CHASE_ID_SEGMENT_PARAMS:
                        continue
                    id_seg_names.add(name)
                    if not _CASE_ID_VALUE_RE.fullmatch(name):
                        raise RunnerError(
                            "plan-error",
                            f"swept param name {name!r} has unsafe characters, "
                            "cannot form case id segment",
                        )
                    value = params[name].value
                    if type(value) is not int and not isinstance(value, str):
                        raise RunnerError(
                            "plan-error",
                            f"swept param {name!r} has non-scalar value, "
                            f"cannot form case id segment: {value!r}",
                        )
                    if isinstance(value, str) and not _CASE_ID_VALUE_RE.fullmatch(value):
                        raise RunnerError(
                            "plan-error",
                            f"swept param {name!r} case id segment value has unsafe "
                            f"characters: {value!r}",
                        )
                    case_id += f"-{name}{value}"
            # MB-03：未被当前形状真实消费的参数在 plan 期显式拒绝。"消费"
            # = 进入 case_params（deriver 产出或通用旗标处理，证据通道）或
            # 是该形状声明的真实输入（_SHAPE_INPUT_PARAMS）。任何只换名字的
            # 参数（语义未实现/探针无协议）在此受控失败，不得靠进 ID 段放行。
            _consumed = set(case_params) | _SHAPE_INPUT_PARAMS.get(shape, frozenset())
            leftover = sorted(set(params) - _consumed)
            if leftover:
                raise RunnerError(
                    "plan-error",
                    f"probe_shape {shape!r} does not consume params "
                    f"{leftover}; register them in the shape's deriver with "
                    "real probe support or drop them",
                )
            cases.append(Case(id=case_id, probe=probe, control=control,
                              params=tuple(sorted(case_params.items())),
                              repetitions=repetitions))

    # 纵深防御（同一触发案例）：任何未来的 id 碰撞炸在 plan 期，而不是 run 期
    # 由 artifacts 覆盖写静默吞掉样本（铁律 1：失败要响，不许静默降级）。
    ids = [case.id for case in cases]
    if len(set(ids)) != len(ids):
        duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
        raise RunnerError(
            "plan-error",
            f"duplicate case ids (raw samples are named by case id): {duplicates}",
        )

    return Plan(experiment_id=spec["id"], protocol_version=spec["protocol_version"],
                cases=tuple(cases), target=platform["target"])
