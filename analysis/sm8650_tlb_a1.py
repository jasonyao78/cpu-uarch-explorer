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
PLATFORM_MIN_RATIO = 0.8        # 锐：其后平台 ≥ 过渡峰值的此比例


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
    if scope < 0 and realized.get("set_region_vpn_hi_pure") != 1:
        # 全域 case 才要求纯度；隔离 case 只用一个区域，不涉及折叠判别
        return False, "vpn-hi-impure"
    return True, "ok"


def predicted_hw_sets(hypothesis: int, target: int,
                      vpn_hi_values: list[int]) -> set[int]:
    """按**实际** VA 高字段计算候选 H 收集页的预测硬件 set 集合。

    H1/H2 不折叠高位 → 全域收集仍是单硬件 set {t}；H3/H4 折叠
    VPN[23:16] → 全域收集横跨 {t⊕hi : hi ∈ 实际高字段集合}（每个纯区域
    一个 hi 值）。隔离收集（单 hi）时恒为单 set——编号置换不改变冲突
    结构（评审 PA-04 数学事实），这正是全域/隔离配对判别式的理论核。
    """
    hi_set = set(vpn_hi_values)
    if hypothesis in (1, 2):
        return {target}
    if hypothesis == 3:
        return {target ^ hi for hi in hi_set}
    if hypothesis == 4:
        # H4 折叠 VPN[23:16] 到 8-bit 索引：预测 = {t⊕hi}（同 H3 结构，
        # 与 H2 的低位耦合区分靠 onset 形态而非本函数）
        return {target ^ hi for hi in hi_set}
    raise TlbError(f"a1: unknown hypothesis {hypothesis!r}")


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
    # 过渡宽度：从首个 <floor 的 W 到 w_star 的档数（不含端点）
    low = [w for w in windows if values[w] < ONSET_FLOOR_PER_ROUND and w < w_star]
    transition = 0
    if low:
        prev = low[-1]
        idx_prev, idx_star = windows.index(prev), windows.index(w_star)
        transition = idx_star - idx_prev - 1
    # 平台：w_star 之后连续 ≥on 的段峰值
    platform_peak = values[w_star]
    for w in windows[windows.index(w_star) + 1:]:
        if values[w] >= ONSET_ON_PER_ROUND:
            platform_peak = max(platform_peak, values[w])
        else:
            break
    if transition > DEGRADED_TRANSITION_STEPS:
        return {"kind": "degraded", "onset": None,
                "reason": f"transition {transition} steps too wide"}
    if platform_peak < ONSET_ON_PER_ROUND * PLATFORM_MIN_RATIO:
        return {"kind": "degraded", "onset": None, "reason": "no-platform"}
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
            "transition_steps": transition, "platform_peak": platform_peak}


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
    predicted = predicted_hw_sets(hypothesis, target, vpn_hi_values)

    def _w(cls):
        o = cls["onset"]
        return o[0] if isinstance(o, tuple) else o

    iso_sharp = isolated and all(c["kind"] == "sharp" for c in isolated)
    if all_scope is None:
        return {"hypothesis": hypothesis, "verdict": "insufficient",
                "classes": classes, "predicted_hw_sets": sorted(predicted)}
    if all_scope["kind"] == "sharp" and iso_sharp:
        delta = max(abs(_w(all_scope) - _w(c)) for c in isolated)
        if delta <= 1 and len(predicted) == 1:
            return {"hypothesis": hypothesis, "verdict": "supported",
                    "classes": classes, "predicted_hw_sets": sorted(predicted)}
        return {"hypothesis": hypothesis, "verdict": "inconsistent",
                "classes": classes, "predicted_hw_sets": sorted(predicted)}
    if all_scope["kind"] == "degraded" and iso_sharp and len(predicted) > 1:
        return {"hypothesis": hypothesis, "verdict": "folds-high-bits",
                "classes": classes, "predicted_hw_sets": sorted(predicted)}
    return {"hypothesis": hypothesis, "verdict": "suspect",
            "classes": classes, "predicted_hw_sets": sorted(predicted)}


def check_l3_consistency(per_target: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """L3 一致性：H* 需四 target 判定一致（任务书 §5.5）。"""
    verdicts = {t: r["verdict"] for t, r in per_target.items()}
    distinct = set(verdicts.values())
    return {"consistent": len(distinct) <= 1, "verdicts": verdicts,
            "targets": sorted(per_target)}
