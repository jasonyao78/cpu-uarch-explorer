# SPDX-License-Identifier: Apache-2.0
"""Phase A A1 判据消费入口（任务书 §5.5 的代码形态）。

评审第三轮阻塞项 2 的交付：阈值确定程序、realized 硬门、purity 门、
实际 VA 预测分区、量化 onset 分类、L3 一致性——全部在此模块以纯函数
实现 + 合成金样测试，正式数据到来前判据已可执行、可验证。

纪律：本模块只消费 runner 产物（records / probe.realized），不自建
统计判据之外的数据；所有拒绝命名（fail-closed，不静默跳过）。
"""
from __future__ import annotations

import math

from typing import Any

from .sm8650_tlb import TlbError
from .sm8650_tlb_a1_contract import bind_formal_records, geometry_gate

# 固定规则：floor=1、平台比例=0.8；仅 on 由专用标定块选网格后冻结。
# ONSET_ON 的默认值只供纯函数使用，正式入口必经锚定 frozen 工件。
ONSET_FLOOR_PER_ROUND = 1.0     # 低于此值为"未起"
ONSET_ON_PER_ROUND = 3.0        # 达到此值为"起"（候选操作阈值）
SHARP_MAX_TRANSITION_STEPS = 2  # 锐：floor→on 过渡宽度（W 档数）
DEGRADED_TRANSITION_STEPS = 4   # 退化：过渡宽度超过此值
PLATFORM_MIN_RATIO = 0.8        # 锐：平台中位 ≥ 峰值×此比例


def gate_record(record: dict) -> tuple[bool, str]:
    """最终逐进程几何门；命名拒绝类型/维数/总和/域/purity/实际 hi 违例。

    完整统计/身份/覆盖由 run_a1_adjudication 必经合同承担，不能把此门
    单独通过当成正式矩阵已获准。R3-C/R5-C 软件收口。
    """
    return geometry_gate(record)


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


def classify_onset(median_by_window: dict[int, float],
                   on_threshold: float | None = None) -> dict[str, Any]:
    """量化 onset：左右删失、非单调区间和未按 on 过滤的平台中位。

    平台取首次越线之后、首次连续两点低于 floor 之前的全部点；至少
    两点。过滤低于 on 的平台值会产生选择偏差（R4/P2 软件收口）。
    """
    import math
    import statistics
    if not median_by_window:
        raise TlbError("a1: empty onset curve")
    on = on_threshold if on_threshold is not None else ONSET_ON_PER_ROUND
    if type(on) not in (int, float) or not math.isfinite(on) or on <= ONSET_FLOOR_PER_ROUND:
        raise TlbError("a1: invalid finite on threshold")
    if any(type(w) is not int or w < 0 or type(v) not in (int, float)
           or not math.isfinite(v) for w, v in median_by_window.items()):
        raise TlbError("a1: onset curve needs integer windows and finite values")
    windows = sorted(median_by_window)
    values = median_by_window
    if all(values[w] < on for w in windows):
        return {"kind": "degraded", "onset": None,
                "reason": "never-reaches-on-threshold"}
    star = next(i for i, w in enumerate(windows) if values[w] >= on)
    w_star = windows[star]
    low = [i for i in range(star) if values[windows[i]] < ONSET_FLOOR_PER_ROUND]
    if not low:
        return {"kind": "left-censored", "onset": (None, w_star),
                "reason": "no below-floor observation on low side"}
    drop = next((i for i in range(star + 1, len(windows) - 1)
                 if values[windows[i]] < ONSET_FLOOR_PER_ROUND
                 and values[windows[i + 1]] < ONSET_FLOOR_PER_ROUND), None)
    end = drop if drop is not None else len(windows)
    plateau = [values[w] for w in windows[star + 1:end]]
    if len(plateau) < 2:
        if drop is not None:
            return {"kind": "interval", "onset": (w_star, windows[drop]),
                    "reason": "nonmonotonic drop before platform was established"}
        return {"kind": "right-censored", "onset": (w_star, None),
                "reason": "onset at or near last window; platform unobserved"}
    peak = max(values[w] for w in windows[:end])
    platform_med = statistics.median(plateau)
    if platform_med < max(ONSET_FLOOR_PER_ROUND, peak * PLATFORM_MIN_RATIO):
        return {"kind": "degraded", "onset": None,
                "reason": f"weak platform {platform_med:.2f} (peak {peak:.2f})"}
    transition = star - low[-1] - 1
    kind = "sharp" if transition <= SHARP_MAX_TRANSITION_STEPS else "degraded"
    if transition > DEGRADED_TRANSITION_STEPS:
        return {"kind": "degraded", "onset": None,
                "reason": f"transition {transition} steps too wide"}
    if kind == "sharp" and drop is not None:
        kind = "interval"
    return {"kind": kind,
            "onset": (w_star, windows[drop]) if kind == "interval" else w_star,
            "transition_steps": transition, "platform_median": platform_med}


def adjudicate_h(curve_by_scope: dict[int, dict[int, float]],
                 vpn_hi_values: list[int], hypothesis: int,
                 target: int = 7,
                 on_threshold: float | None = None) -> dict[str, Any]:
    """单候选 H 的 A1 判定（L1 主规则）。

    curve_by_scope：{scope: {W: m}}。规则（任务书 §5.5）：全域与隔离
    onset 一致（|ΔW*|≤1 且均锐）→ 支持；全域退化且隔离锐 → 该 H 折叠
    高位（与预测分区互证）；全域锐 → 不折叠；否则存疑。
    """
    required_scopes = (-1, 0, 1)
    missing = [sc for sc in required_scopes if sc not in curve_by_scope]
    if missing:
        raise TlbError(f"a1: L1 coverage incomplete, missing scopes {missing}")
    classes = {scope: classify_onset(curve, on_threshold=on_threshold)
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
    if len(per_target) < 4:
        raise TlbError(
            f"a1: L3 requires 4 targets, got {len(per_target)}")
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
    if (not floor_samples or any(type(v) not in (int, float) or not math.isfinite(v) for v in floor_samples)
            or type(scatter_mid) not in (int, float) or not math.isfinite(scatter_mid)):
        raise TlbError("a1: freeze_thresholds needs finite floor/scatter samples")
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
    sharp = classify_onset({6: 0.2, 8: 4.0, 10: 6.5, 12: 7.0}, on_threshold=on)
    never = classify_onset({6: 0.1, 8: 0.2, 10: 0.1, 12: 0.2}, on_threshold=on)
    weak = classify_onset({6: 0.2, 8: 8.0, 10: 3.0, 12: 3.0}, on_threshold=on)
    cens = classify_onset({6: 0.2, 8: 0.3, 12: 4.0}, on_threshold=on)
    return (sharp["kind"] == "sharp" and never["kind"] == "degraded"
            and weak["kind"] == "degraded" and cens["kind"] == "right-censored")


def run_a1_adjudication(records: list[dict], frozen: dict,
                        expected_l3_targets: tuple = (7, 42, 100, 200),
                        expected_l3_windows: tuple = (8, 12)) -> dict[str, Any]:
    """正式 plan → 完整记录合同 → L1/L2/L3 → H*；拒绝未知/缺失/重复。

    层角色绑定 experiment_id 和完整条件，不根据默认键或 seed 排序猜测。
    每个进程的实际高字段独立计算 C×M 预测，结果附 case_audit；域内 VA
    重分配允许变化，混域/跨界/不完整统计仍拒绝。R3-C/R5-C 收口。
    """
    if not isinstance(frozen, dict) or frozen.get("frozen") is not True:
        raise TlbError(f"a1: thresholds not frozen: {frozen}")
    if expected_l3_targets != (7, 42, 100, 200) or expected_l3_windows != (8, 12):
        raise TlbError("a1: registered formal coverage cannot be overridden")
    from .sm8650_tlb_a1_freeze import verify_frozen_artifact
    bound = bind_formal_records(records)
    verify_frozen_artifact(frozen, records)
    on = frozen["on_threshold"]
    curves, high_fields, audit = {}, {}, []
    for case, record, metrics in bound:
        p = case.params
        h, target, scope, window = (p[k] for k in
            ("set_hypothesis", "set_target", "set_region_scope", "set_window"))
        key = case.layer, h, target
        curves.setdefault(key, {}).setdefault(scope, {})[window] = metrics["pmu.l2d_tlb_refill.count"]["value"]
        realized = record["probe"]["realized"]
        by_sample = ({s["sample_index"]: s["realized"] for s in realized["samples"]}
                     if "samples" in realized else None)
        obs = sorted(metrics["pmu.l2d_tlb_refill.count"]["observations"], key=lambda o: o["sample_index"])
        processes = []
        for observation in obs:
            index = observation["sample_index"]
            r = by_sample[index] if by_sample is not None else realized
            nodes = r["set_target_region_nodes"]
            hi = sorted({r["set_region_vpn_hi"][i] for i, n in enumerate(nodes) if n})
            high_fields.setdefault(key, set()).update(hi)
            predictions = {model: predicted_hw_sets(h, target, model, hi) for model in (1, 2, 3, 4)}
            processes.append({"sample_index": index, "raw_sample_ref": observation["raw_sample_ref"],
                "vpn_hi": hi, "region_vpn_hi": r["set_region_vpn_hi"], "nodes": nodes,
                "predicted_by_model": {model: sorted(v) if v is not None else None
                                       for model, v in predictions.items()}})
        audit.append({"case_id": case.case_id, "layer": case.layer,
            "experiment_id": case.experiment_id, "params": p,
            "record_run_id": record["run_id"], "processes": processes})
    per_h = {}
    for h in (1, 2, 3, 4):
        main_key, repro_key = ("l1", h, 7), ("l2", h, 7)
        vm = adjudicate_h(curves[main_key], sorted(high_fields[main_key]), h, on_threshold=on)
        vr = adjudicate_h(curves[repro_key], sorted(high_fields[repro_key]), h, on_threshold=on)
        wm, wr = vm["classes"][-1]["onset"], vr["classes"][-1]["onset"]
        # R6-C 关闭维持：比较 verdict 和全域 onset，不比较平台振幅噪声。
        reproducible = (vm["verdict"] == vr["verdict"]
                        and type(wm) in (int, float) and type(wr) in (int, float)
                        and abs(wm - wr) <= 1)
        shapes = {target: classify_l3_two_point(curves[("l3", h, target)][-1], on)
                  for target in (7, 42, 100, 200)}
        l3_pass = len(set(shapes.values())) == 1 and set(shapes.values()) <= {"crossing", "both-above"}
        per_h[h] = {"verdict": vm["verdict"], "reproducible": reproducible,
            "l3_pass": l3_pass, "l3_shapes": shapes, "classes": vm["classes"],
            "repro_classes": vr["classes"], "predicted_hw_sets": vm["predicted_hw_sets"]}
    supported = [h for h, r in per_h.items() if r["verdict"] == "supported"
                 and r["reproducible"] and r["l3_pass"]]
    return {"per_hypothesis": per_h, "on_threshold": on, "n_records": len(bound),
        "h_star": supported[0] if len(supported) == 1 else None,
        "supported_hypotheses": supported,
        "h_star_status": "unique" if len(supported) == 1 else
            "equivalent-on-test-domain" if supported else "none-supported",
        "case_audit": audit}


def classify_l3_two_point(curve: dict[int, float], on: float) -> str:
    """L3 两点形态分类（任务书 v1.8.2 预注册，R8 修订）：两点网格不能做
    onset 定位，L3 的证据形态 = 四 target **相互一致**且非全低于阈值。
    返回 both-below/crossing/both-above/falling；falling 有独立拒绝标签。"""
    if len(curve) != 2:
        raise TlbError(f"a1: L3 two-point rule needs exactly 2 windows, "
                       f"got {sorted(curve)}")
    ws = sorted(curve)
    lo, hi = curve[ws[0]] >= on, curve[ws[1]] >= on
    return "both-above" if (lo and hi) else "crossing" if hi else "falling" if lo else "both-below"
