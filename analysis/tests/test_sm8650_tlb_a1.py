# SPDX-License-Identifier: Apache-2.0
"""A1 判据消费入口金样（合成输入）：硬门 / 预测分区 / 量化 onset / H 判定 / L3。"""
import unittest

from analysis.sm8650_tlb import TlbError
from analysis.sm8650_tlb_a1 import (adjudicate_h, check_l3_consistency,
                                    classify_onset, freeze_thresholds,
                                    gate_record, predicted_hw_sets,
                                    run_a1_adjudication)


def _record(scope=-1, regions=4, nodes=None, pure=1, consistent=None):
    realized = {
        "set_target_region_nodes": nodes if nodes is not None else (
            [3, 3, 3, 3] if scope < 0 else [12, 0, 0, 0]),
        "set_region_vpn_hi_pure": pure,
    }
    if consistent is not None:
        realized["domain_consistent"] = consistent
    return {"params": {"set_region_scope": scope, "set_regions": regions},
            "probe": {"realized": realized}}


class TestGate(unittest.TestCase):
    def test_all_scope_pure_passes(self):
        ok, why = gate_record(_record())
        self.assertTrue(ok, why)

    def test_isolated_expected_active_one(self):
        ok, why = gate_record(_record(scope=1, nodes=[0, 12, 0, 0]))
        self.assertTrue(ok, why)
        ok, why = gate_record(_record(scope=1, nodes=[3, 3, 3, 3]))
        self.assertFalse(ok)
        self.assertIn("active", why)

    def test_impure_rejected_all_scopes(self):
        # RV2-02-3：隔离单区域同样可能跨高字段（生产选址反例）——
        # purity=0 全 scope 命名降级
        for scope, nodes in ((-1, [3, 3, 3, 3]), (0, [12, 0, 0, 0]),
                             (1, [0, 12, 0, 0])):
            ok, why = gate_record(_record(scope=scope, nodes=nodes, pure=0))
            self.assertFalse(ok)
            self.assertEqual(why, "vpn-hi-impure")

    def test_mixed_domain_and_missing_rejected(self):
        ok, why = gate_record(_record(consistent=False))
        self.assertFalse(ok); self.assertEqual(why, "mixed-domain")
        rec = _record()
        del rec["probe"]["realized"]["set_target_region_nodes"]
        ok, why = gate_record(rec)
        self.assertFalse(ok)


class TestPrediction(unittest.TestCase):
    def test_collection_model_distinct(self):
        # RV2-02-1：收集假设与被检验模型分列——以 H3 选址 + H3 模型
        # 检查，集合必为 {7}（匹配模型恒单 set）
        his = [5, 6, 7, 8]
        self.assertEqual(predicted_hw_sets(3, 7, 3, his), {7})
        self.assertEqual(predicted_hw_sets(1, 7, 1, his), {7})
        # 交叉：H3 收集的页在 H1 模型下 = {t⊕hi}（全域多 set → 退化）
        self.assertEqual(predicted_hw_sets(3, 7, 1, his),
                         {7 ^ 5, 7 ^ 6, 7 ^ 7, 7 ^ 8})
        # 低位耦合差异 → multi（None）
        self.assertIsNone(predicted_hw_sets(1, 7, 2, his))
        # 隔离（单 hi）时 folded 退化为单 set
        self.assertEqual(predicted_hw_sets(3, 7, 1, [5]), {7 ^ 5})


class TestOnsetClassification(unittest.TestCase):
    def test_sharp(self):
        r = classify_onset({6: 0.2, 8: 4.0, 10: 6.5, 12: 7.0})
        self.assertEqual(r["kind"], "sharp")
        self.assertEqual(r["onset"], 8)

    def test_weak_platform_degraded(self):
        # RV2-02-2：平台仅为峰值 37.5%（3.0/8.0）→ 退化，不判锐
        r = classify_onset({6: 0.2, 8: 8.0, 10: 3.0, 12: 3.0})
        self.assertEqual(r["kind"], "degraded")

    def test_right_censored_not_sharp(self):
        # RV2-02-2：末点越线 / 越线后平台不可观测 → 右删失
        r = classify_onset({6: 0.2, 8: 0.3, 10: 0.2, 12: 4.0})
        self.assertEqual(r["kind"], "right-censored")
        r = classify_onset({8: 4.0})
        self.assertEqual(r["kind"], "left-censored")

    def test_degraded_never_on(self):
        self.assertEqual(classify_onset({6: 0.1, 8: 0.2, 10: 0.1})["kind"],
                         "degraded")

    def test_nonmonotonic_interval(self):
        r = classify_onset({6: 0.2, 8: 4.0, 10: 6.0, 12: 6.5, 14: 0.1, 16: 0.0})
        self.assertEqual(r["kind"], "interval")
        self.assertEqual(r["onset"], (8, 14))


class TestAdjudicateH(unittest.TestCase):
    def test_h1_pattern_supported(self):
        curve = {-1: {6: 0.2, 8: 4.0, 10: 6.5, 12: 7.0},
                 0: {6: 0.2, 8: 4.2, 10: 6.6, 12: 7.1},
                 1: {6: 0.3, 8: 4.1, 10: 6.4, 12: 6.9}}
        r = adjudicate_h(curve, [5, 6, 7, 8], hypothesis=1)
        self.assertEqual(r["verdict"], "supported")

    def test_h3_pattern_folds(self):
        all_scope = {6: 0.3, 8: 0.4, 10: 0.5, 12: 0.4}      # 全域退化
        iso = {6: 0.2, 8: 4.0, 10: 6.5, 12: 7.0}            # 隔离锐
        # 自检验（C=M=H3）预测 {7}；但行为证据（全域退化+隔离锐）与
        # 单 set 预测矛盾 → 至少不是 supported；判定需交叉检验支撑
        r = adjudicate_h({-1: all_scope, 0: iso, 1: iso},
                         [5, 6, 7, 8], hypothesis=3)
        self.assertIn(r["verdict"], ("suspect", "inconsistent", "folds-high-bits"))


class TestL3(unittest.TestCase):
    def test_consistency(self):
        ok = check_l3_consistency({t: {"verdict": "supported"} for t in (7, 42, 100, 200)})
        self.assertTrue(ok["consistent"])
        with self.assertRaisesRegex(TlbError, "4 targets"):
            check_l3_consistency({7: {"verdict": "supported"},
                                  42: {"verdict": "suspect"}})

    def test_empty_l3_rejected(self):
        # RV2-02-3/R4：覆盖不足（含空输入）一律拒绝
        with self.assertRaisesRegex(TlbError, "4 targets"):
            check_l3_consistency({})


if __name__ == "__main__":
    unittest.main()


class TestFreezeThresholds(unittest.TestCase):
    def test_happy_path_freezes(self):
        r = freeze_thresholds([0.0, 0.2, 0.0, 0.4, 0.2], scatter_mid=0.0)
        self.assertTrue(r["frozen"])
        self.assertEqual(r["on_threshold"], 2.0)

    def test_stop_rules(self):
        r = freeze_thresholds([0.0, 5.0, 0.0, 8.0], scatter_mid=0.0)
        self.assertEqual(r["stop"], "floor-noisy")
        r = freeze_thresholds([0.0, 0.1, 0.0], scatter_mid=2.0)
        self.assertEqual(r["stop"], "filler-exclusion-broken")
        r = freeze_thresholds([4.0, 4.2, 3.8], scatter_mid=0.0)
        self.assertEqual(r["stop"], "no-grid-value")


class TestRound4(unittest.TestCase):
    def test_left_censored_not_sharp(self):
        r = classify_onset({6: 4.0, 8: 4.0, 10: 4.0, 12: 4.0})
        self.assertEqual(r["kind"], "left-censored")

    def test_adjudicate_requires_full_scope_coverage(self):
        with self.assertRaisesRegex(TlbError, "coverage"):
            adjudicate_h({-1: {6: 0.2, 8: 4.0, 10: 6.5, 12: 7.0},
                          0: {6: 0.2, 8: 4.2, 10: 6.6, 12: 7.1}},
                         [5, 6, 7, 8], hypothesis=1)

    def test_l3_requires_four_targets(self):
        with self.assertRaisesRegex(TlbError, "4 targets"):
            check_l3_consistency({7: {"verdict": "supported"}})

    def test_frozen_threshold_wired(self):
        # 同一曲线：on=2.0 时 3.0 值点判 on，on=3.0 时不判 → 接线生效
        curve = {6: 0.2, 8: 2.5, 10: 2.5, 12: 6.5, 14: 7.0}
        self.assertEqual(classify_onset(curve, on_threshold=2.0)["kind"], "sharp")
        self.assertEqual(classify_onset(curve, on_threshold=3.0)["kind"],
                         "right-censored")

    def test_run_a1_requires_frozen(self):
        with self.assertRaisesRegex(TlbError, "not frozen"):
            run_a1_adjudication([], {"frozen": False, "stop": "floor-noisy"})
