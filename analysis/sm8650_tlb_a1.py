# SPDX-License-Identifier: Apache-2.0
"""Phase A A1 判据消费入口（任务书 v1.7 §5.5 的代码形态）。

评审第三轮阻塞项 2 的交付：阈值确定程序、realized 硬门、purity 门、
实际 VA 预测分区、量化 onset 分类、L3 一致性——全部在此模块以纯函数
实现 + 合成金样测试，正式数据到来前判据已可执行、可验证。

纪律：本模块只消费 runner 产物（records / probe.realized），不自建
统计判据之外的数据；所有拒绝命名（fail-closed，不静默跳过）。
"""
from __future__ import annotations

from typing import Any

from .sm8650_tlb import TlbError

# 量化 onset 候选阈值（任务书 v1.7 §5.5：随首块标定复核后正式冻结；
# 程序已固定，数值是唯二待标定项）
ONSET_FLOOR_PER_ROUND = 1.0     # 低于此值为"未起"
ONSET_ON_PER_ROUND = 3.0        # 达到此值为"起"（候选操作阈值）
SHARP_MAX_TRANSITION_STEPS = 2  # 锐：floor→on 过渡宽度（W 档数）
DEGRADED_TRANSITION_STEPS = 4   # 退化：过渡宽度超过此值
PLATFORM_MIN_RATIO = 0.8        # 锐：平台中位 ≥ 峰值×此比例


def gate_record(record: dict) -> tuple[bool, str]:
    """A1 realized 硬门（评审阻塞项 2 的"消费入口"实体）。

    逐项 fail-closed；返回 (通过?, 命名理由)。门项（任务书 §5.5）：
    domain_consistent、scope 特定 active 数、purity（全域折叠判别）、
    审计不变量（adapter 已二次校验，此处为判据入口的最终防线）。
    """
    realized = record.get("probe", {}).get("realized")
    if not realized:
        return False, "missing-realized"
    if realized.get("domain_consistent") is False:
        return False, "mixed-domain"
    params = record.get("params", {})
    scope = int(params.get("set_region_scope", -1))
    regions = int(params.get("set_regions", 4))
    nodes = realized.get("set_target_region_nodes")
    if nodes is None:
        return False, "missing-region-nodes"
    expected_active = regions if scope < 0 else 1
    active = sum(1 for n in nodes if n > 0)
    if active != expected_active:
        return False, f"active-regions {active} != expected {expected_active}"
    if scope >= 0 and nodes[scope] != sum(nodes):
        return False, "scope-isolation-violated"
    # purity 全 scope 检查：隔离用的单区域同样可能跨高字段（生产选址
    # 反例：基址不对齐时 ~25% 跨界），折叠类判别依赖区域 hi 恒定——
    # impure 一律命名降级（RV2-02-3）。
    if realized.get("set_region_vpn_hi_pure") != 1:
        return False, "vpn-hi-impure"
    return True, "ok"


# 双假设预测表（评审 RV2-02-1 修正）：行 = 收集假设 C，列 = 被检验的
# 硬件模型 M。收集约束 C(vpn)=t 下、页的低 16 位经桶取样自由变化：
#   single = M 索引被约束钉死为 t（匹配的模型 → 单硬件 set，onset 锐）；
#   folded = M 索引 = t⊕hi（差一个高位折叠 → {t⊕hi: hi∈实际高字段}，
#     全域收集横跨多硬件 set → onset 退化；隔离收集单 hi 时仍单 set）；
#   multi  = M 索引随低位自由变化（低位耦合差异 → 多硬件 set，退化）。
# 推导：lo8=lo&0xFF、m=lo>>8、hi=vpn>>16&0xFF；H1=lo8、H2=lo8^m、
# H3=lo8^hi、H4=lo8^m^hi。C=H1 → lo8=t；C=H2 → lo8^m=t；
# C=H3 → lo8^hi=t；C=H4 → lo8^m^hi=t。逐对代入即得下表。
_PREDICTION_TABLE = {
    (1, 1): "single", (1, 3): "folded",
    (2, 2): "single", (2, 4): "folded",
    (3, 1): "folded", (3, 3): "single",
    (4, 2): "folded", (4, 4): "single",
}


def predicted_hw_sets(collection_h: int, target: int, model_h: int,
                      vpn_hi_values: list[int]) -> set[int] | None:
    """按**实际** VA 高字段预测"以候选 C 收集的页在硬件模型 M 下的
    硬件 set 集合"。返回 {target}（单 set）/ {target⊕hi}（折叠）/
    None（multi：多 set，预测 onset 退化）。**收集假设与被检验模型
    必须分列**（RV2-02-1：以 H3 选址再用 H3 模型检查，集合必为 {t}）。
    """
    kind = _PREDICTION_TABLE.get((collection_h, model_h), "multi")
    if kind == "single":
        return {target}
    if kind == "folded":
        return {target ^ hi for hi in set(vpn_hi_values)}
    return None


def classify_onset(median_by_window: dict[int, float]) -> dict[str, Any]:
    """量化 onset 分类（任务书 §5.5 操作定义）。

    输入：每 case 10 进程 per-round 均值的中位 m(W)。
    锐：存在 floor→on 过渡宽度 ≤2 档且其后平台 ≥ 峰值 80%；
    退化：全程 <on 或宽度 >4 档或平台缺失；非单调 → onset 区间。
    """
    if not median_by_window:
        raise TlbError("a1: empty onset curve")
    windows = sorted(median_by_window)
    values = {w: median_by_window[w] for w in windows}
    if all(v < ONSET_ON_PER_ROUND for v in values.values()):
        return {"kind": "degraded", "onset": None,
                "reason": "never-reaches-on-threshold"}
    on_windows = [w for w in windows if values[w] >= ONSET_ON_PER_ROUND]
    w_star = on_windows[0]
    peak = max(values.values())
    # 右删失（RV2-02-2）：末点越线或越线后不足两个平台点 → 不能判锐
    post = [w for w in windows if w > w_star]
    plateau_vals = [values[w] for w in post if values[w] >= ONSET_ON_PER_ROUND]
    if not post or len(plateau_vals) < 2:
        return {"kind": "right-censored", "onset": (w_star, None),
                "reason": "onset at or near last window; platform unobserved"}
    # 平台强度（RV2-02-2 修正：旧条件 ON×0.8 恒不成立）。平台中位必须
    # ≥ max(地板, 峰值×平台比)——平台仅为峰值 37.5% 的曲线必须退化。
    import statistics
    platform_med = statistics.median(plateau_vals)
    if platform_med < max(ONSET_FLOOR_PER_ROUND, peak * PLATFORM_MIN_RATIO):
        return {"kind": "degraded", "onset": None,
                "reason": f"weak platform {platform_med:.2f} "
                          f"(peak {peak:.2f})"}
    # 过渡宽度：从首个 <floor 的 W 到 w_star 的档数（不含端点）
    low = [w for w in windows if values[w] < ONSET_FLOOR_PER_ROUND and w < w_star]
    transition = 0
    if low:
        prev = low[-1]
        idx_prev, idx_star = windows.index(prev), windows.index(w_star)
        transition = idx_star - idx_prev - 1
    if transition > DEGRADED_TRANSITION_STEPS:
        return {"kind": "degraded", "onset": None,
                "reason": f"transition {transition} steps too wide"}
    kind = "sharp" if transition <= SHARP_MAX_TRANSITION_STEPS else "degraded"
    # 非单调 → onset 区间（首个 on 到其后连续两点 <floor 的 W）
    onset_lo, onset_hi = w_star, w_star
    if kind == "sharp":
        for i, w in enumerate(windows):
            if w <= w_star or values[w] >= ONSET_FLOOR_PER_ROUND:
                continue
            nxt = windows[i + 1] if i + 1 < len(windows) else None
            if nxt is not None and values[nxt] < ONSET_FLOOR_PER_ROUND:
                onset_hi = w
                break
        if onset_hi != onset_lo:
            kind = "interval"
    return {"kind": kind, "onset": (onset_lo, onset_hi) if onset_hi != onset_lo else w_star,
            "transition_steps": transition, "platform_median": platform_med}


def adjudicate_h(curve_by_scope: dict[int, dict[int, float]],
                 vpn_hi_values: list[int], hypothesis: int,
                 target: int = 7) -> dict[str, Any]:
    """单候选 H 的 A1 判定（L1 主规则）。

    curve_by_scope：{scope: {W: m}}。规则（任务书 §5.5）：全域与隔离
    onset 一致（|ΔW*|≤1 且均锐）→ 支持；全域退化且隔离锐 → 该 H 折叠
    高位（与预测分区互证）；全域锐 → 不折叠；否则存疑。
    """
    classes = {scope: classify_onset(curve)
               for scope, curve in curve_by_scope.items()}
    all_scope = classes.get(-1)
    isolated = [classes[s] for s in sorted(classes) if s >= 0]
    # 自检验：以候选 H 收集、检验硬件模型 = H 自身（A1 的 H* 判定问题）
    predicted = predicted_hw_sets(hypothesis, target, hypothesis,
                                  vpn_hi_values)

    def _w(cls):
        o = cls["onset"]
        return o[0] if isinstance(o, tuple) else o

    iso_sharp = isolated and all(c["kind"] == "sharp" for c in isolated)
    multi = predicted is None
    if all_scope is None:
        return {"hypothesis": hypothesis, "verdict": "insufficient",
                "classes": classes, "predicted_hw_sets": None if multi else sorted(predicted)}
    if all_scope["kind"] == "sharp" and iso_sharp:
        delta = max(abs(_w(all_scope) - _w(c)) for c in isolated)
        if delta <= 1 and not multi and len(predicted) == 1:
            return {"hypothesis": hypothesis, "verdict": "supported",
                    "classes": classes, "predicted_hw_sets": sorted(predicted)}
        return {"hypothesis": hypothesis, "verdict": "inconsistent",
                "classes": classes, "predicted_hw_sets": None if multi else sorted(predicted)}
    if all_scope["kind"] == "degraded" and iso_sharp and (
            multi or len(predicted) > 1):
        return {"hypothesis": hypothesis, "verdict": "folds-high-bits",
                "classes": classes, "predicted_hw_sets": None if multi else sorted(predicted)}
    return {"hypothesis": hypothesis, "verdict": "suspect",
            "classes": classes, "predicted_hw_sets": None if multi else sorted(predicted)}


def check_l3_consistency(per_target: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """L3 一致性：H* 需四 target 判定一致（任务书 §5.5）。"""
    if not per_target:
        raise TlbError("a1: L3 consistency check on empty input")
    verdicts = {t: r["verdict"] for t, r in per_target.items()}
    distinct = set(verdicts.values())
    return {"consistent": len(distinct) <= 1, "verdicts": verdicts,
            "targets": sorted(per_target)}


_THRESHOLD_GRID = (2.0, 3.0, 4.0, 5.0)
_FLOOR_NOISE_STOP = 1.0     # 空窗底噪 MAD 超此 → 环境不稳，STOP
_SCATTER_CEILING = 1.0      # 无冲突同窗 0x2d 中位超此 → filler 排除破，STOP
_PILOT_ONSET_MAGNITUDE = 6.0  # pilot 实测 onset 段 0x2d ≈ 6/轮（§5.4）


def freeze_thresholds(floor_samples: list[float],
                      scatter_mid: float) -> dict:
    """两阶段标定·阈值冻结决策表（评审 RV2-02-4）。

    输入 = **标定块**数据（CALIBRATION 标签，与正式判定数据隔离）：
    floor_samples = 空窗底噪 0x2d per-round 值；scatter_mid = 无冲突同窗
    W=8 的 0x2d 中位。STOP 规则（任一命中 → 返回 STOP，不进正式矩阵）：
      floor-noisy            底噪 MAD > 1.0（环境不稳）
      filler-exclusion-broken scatter_mid > 1.0（filler 未排除目标 set）
      no-grid-value          候选网格无一满足双约束
      synthetic-validation-failed 网格耗尽仍无法通过合成曲线验证
    选择规则：网格中最小值 g 满足 g ≥ floor_med + 5×MAD(floor) 且
    g ≤ 0.5×pilot onset 幅度；随后用内置合成曲线形态验证分类标签，
    失败则取下一档网格值。
    """
    import statistics
    if not floor_samples:
        raise TlbError("a1: freeze_thresholds needs floor samples")
    floor_med = statistics.median(floor_samples)
    floor_mad = statistics.median([abs(v - floor_med) for v in floor_samples])
    if floor_mad > _FLOOR_NOISE_STOP:
        return {"frozen": False, "stop": "floor-noisy", "floor_mad": floor_mad}
    if scatter_mid > _SCATTER_CEILING:
        return {"frozen": False, "stop": "filler-exclusion-broken",
                "scatter_mid": scatter_mid}
    low_bound = floor_med + 5.0 * floor_mad
    high_bound = 0.5 * _PILOT_ONSET_MAGNITUDE
    candidates = [g for g in _THRESHOLD_GRID
                  if g >= low_bound and g <= high_bound]
    if not candidates:
        return {"frozen": False, "stop": "no-grid-value",
                "low_bound": low_bound, "high_bound": high_bound}
    for on in candidates:
        if _synthetic_suite_validates(on):
            return {"frozen": True, "on_threshold": on,
                    "floor_median": floor_med, "floor_mad": floor_mad,
                    "validated": "synthetic-suite"}
    return {"frozen": False, "stop": "synthetic-validation-failed",
            "candidates": candidates}


def _synthetic_suite_validates(on: float) -> bool:
    """合成曲线形态验证：用候选 on 阈值，分类器必须正确标记四种
    已知形态（锐 / 退化-不起 / 退化-弱平台 / 右删失）。"""
    saved = globals()["ONSET_ON_PER_ROUND"]
    try:
        globals()["ONSET_ON_PER_ROUND"] = on
        sharp = classify_onset({6: 0.2, 8: 4.0, 10: 6.5, 12: 7.0})
        never = classify_onset({6: 0.1, 8: 0.2, 10: 0.1, 12: 0.2})
        weak = classify_onset({6: 0.2, 8: 8.0, 10: 3.0, 12: 3.0})
        cens = classify_onset({6: 0.2, 8: 0.3, 12: 4.0})
    finally:
        globals()["ONSET_ON_PER_ROUND"] = saved
    return (sharp["kind"] == "sharp" and never["kind"] == "degraded"
            and weak["kind"] == "degraded" and cens["kind"] == "right-censored")
