# SPDX-License-Identifier: Apache-2.0
"""A1 判据消费入口金样（合成输入）：硬门 / 预测分区 / 量化 onset / H 判定 / L3。"""
import unittest

from analysis.sm8650_tlb import TlbError
from analysis.sm8650_tlb_a1 import (adjudicate_h, check_l3_consistency,
                                    classify_onset, gate_record,
                                    predicted_hw_sets)


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

    def test_impure_all_scope_rejected_isolated_ok(self):
        ok, _ = gate_record(_record(scope=-1, pure=0))
        self.assertFalse(ok)
        ok, _ = gate_record(_record(scope=0, pure=0))  # 隔离不涉折叠
        self.assertTrue(ok)

    def test_mixed_domain_and_missing_rejected(self):
        ok, why = gate_record(_record(consistent=False))
        self.assertFalse(ok); self.assertEqual(why, "mixed-domain")
        rec = _record()
        del rec["probe"]["realized"]["set_target_region_nodes"]
        ok, why = gate_record(rec)
        self.assertFalse(ok)


class TestPrediction(unittest.TestCase):
    def test_fold_vs_unfold_prediction(self):
        his = [5, 6, 7, 8]
        self.assertEqual(predicted_hw_sets(1, 7, his), {7})
        self.assertEqual(predicted_hw_sets(3, 7, his), {7 ^ 5, 7 ^ 6, 7 ^ 7, 7 ^ 8})
        self.assertEqual(predicted_hw_sets(3, 7, [5]), {7 ^ 5})  # 隔离 = 单 set


class TestOnsetClassification(unittest.TestCase):
    def test_sharp(self):
        r = classify_onset({6: 0.2, 8: 4.0, 10: 6.5, 12: 7.0})
        self.assertEqual(r["kind"], "sharp")
        self.assertEqual(r["onset"], 8)

    def test_degraded_never_on(self):
        self.assertEqual(classify_onset({6: 0.1, 8: 0.2, 10: 0.1})["kind"],
                         "degraded")

    def test_nonmonotonic_interval(self):
        r = classify_onset({6: 0.2, 8: 4.0, 10: 6.0, 12: 0.1, 14: 0.0})
        self.assertEqual(r["kind"], "interval")
        self.assertEqual(r["onset"], (8, 12))


class TestAdjudicateH(unittest.TestCase):
    def test_h1_pattern_supported(self):
        curve = {-1: {6: 0.2, 8: 4.0, 10: 6.5},
                 0: {6: 0.2, 8: 4.2, 10: 6.6},
                 1: {6: 0.3, 8: 4.1, 10: 6.4}}
        r = adjudicate_h(curve, [5, 6, 7, 8], hypothesis=1)
        self.assertEqual(r["verdict"], "supported")

    def test_h3_pattern_folds(self):
        all_scope = {6: 0.3, 8: 0.4, 10: 0.5, 12: 0.4}   # 全域退化
        iso = {6: 0.2, 8: 4.0, 10: 6.5}                   # 隔离锐
        r = adjudicate_h({-1: all_scope, 0: iso, 1: iso},
                         [5, 6, 7, 8], hypothesis=3)
        self.assertEqual(r["verdict"], "folds-high-bits")
        self.assertEqual(len(r["predicted_hw_sets"]), 4)


class TestL3(unittest.TestCase):
    def test_consistency(self):
        ok = check_l3_consistency({t: {"verdict": "supported"} for t in (7, 42, 100, 200)})
        self.assertTrue(ok["consistent"])
        bad = check_l3_consistency({7: {"verdict": "supported"}, 42: {"verdict": "suspect"}})
        self.assertFalse(bad["consistent"])


if __name__ == "__main__":
    unittest.main()
