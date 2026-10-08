# SPDX-License-Identifier: Apache-2.0
"""A1 判据消费入口金样（合成输入）：硬门 / 预测分区 / 量化 onset / H 判定 / L3。"""
import unittest

from analysis.sm8650_tlb import TlbError
from analysis.sm8650_tlb_a1 import (adjudicate_h, check_l3_consistency,
                                    classify_onset, freeze_thresholds,
                                    gate_record, predicted_hw_sets, run_a1_adjudication)


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


def _chain_record(h, scope, seed, target, window, value, exp="x-a1-l1"):
    # 生产形态：records 全带 set_target 默认键，归层靠 experiment_id
    params = {"set_hypothesis": h, "set_region_scope": scope, "seed": seed,
              "set_target": target,
              "set_window": window, "set_regions": 4}
    return {"experiment_id": exp, "params": params,
            "probe": {"realized": {
                "set_target_region_nodes": (
                    [3, 3, 3, 3] if scope < 0
                    else [0] * scope + [12] + [0] * (3 - scope)),
                "set_region_vpn_hi_pure": 1}},
            "metrics": [{"name": "pmu.l2d_tlb_refill.count", "value": value}]}


class TestFullChain(unittest.TestCase):
    FROZEN = {"frozen": True, "on_threshold": 2.0}

    def _l1_l2(self):
        recs = []
        for seed, exp in ((42, "x-a1-l1-main"), (1337, "x-a1-l2-repro")):
            for scope in (-1, 0, 1):
                for w, v in ((6, 0.2), (8, 2.5), (10, 6.5), (12, 7.0)):
                    recs.append(_chain_record(1, scope, seed, 7, w, v, exp=exp))
        return recs

    def _l3(self, h=1):
        # 生产网格 W={8,12} 两点
        return [_chain_record(h, -1, 42, t, w, v, exp="x-a1-l3-target")
                for t in (7, 42, 100, 200)
                for w, v in ((8, 4.0), (12, 6.5))]

    def test_permutation_invariance(self):
        import random
        a = run_a1_adjudication(self._l1_l2() + self._l3(), self.FROZEN)
        recs = self._l1_l2() + self._l3()
        random.seed(7); random.shuffle(recs)
        b = run_a1_adjudication(recs, self.FROZEN)
        self.assertEqual(a, b)
        self.assertEqual(a["per_hypothesis"][1]["verdict"], "supported")

    def test_frozen_threshold_propagates(self):
        # on=2.0 贯穿：8 档 4.0 在 on=2.0 下判 on、on=3.0 下不判 → 曲线形态随冻结值变
        recs = self._l1_l2() + self._l3()
        r2 = run_a1_adjudication(recs, {"frozen": True, "on_threshold": 2.0})
        r3 = run_a1_adjudication(recs, {"frozen": True, "on_threshold": 3.0})
        self.assertEqual(r2["on_threshold"], 2.0)
        self.assertNotEqual(
            r2["per_hypothesis"][1]["classes"],
            r3["per_hypothesis"][1]["classes"])

    def test_missing_seed_layer_rejected(self):
        recs = [r for r in self._l1_l2() + self._l3() if r["params"]["seed"] == 42]
        with self.assertRaisesRegex(TlbError, "2 seeds"):
            run_a1_adjudication(recs, self.FROZEN)

    def test_missing_l3_rejected(self):
        with self.assertRaisesRegex(TlbError, "exact coverage"):
            run_a1_adjudication(self._l1_l2(), self.FROZEN)

    def test_l3_uniform_suspect_not_passed(self):
        # 四 target 全退化 → l3_pass=False → 无 H*
        bad_l3 = [_chain_record(1, -1, 42, t, w, 0.3, exp="x-a1-l3-target")
                  for t in (7, 42, 100, 200)
                  for w in (8, 12)]
        r = run_a1_adjudication(self._l1_l2() + bad_l3, self.FROZEN)
        self.assertIsNone(r["h_star"])

    def test_l2_onset_match_ignores_platform_noise(self):
        # 平台中位微差（6.75 vs 6.85）不影响复现判定（onset 比较）
        recs = self._l1_l2() + self._l3()
        for r in recs:
            if r["experiment_id"].endswith("l2-repro") and r["params"]["set_window"] == 12:
                r["metrics"][0]["value"] = 7.2
        out = run_a1_adjudication(recs, self.FROZEN)
        self.assertTrue(out["per_hypothesis"][1]["reproducible"])


class TestProductionChain(unittest.TestCase):
    """Real checked-in plans → run_plan/adapter → disk → load_run → A1.

    Only external execution and binary registration are synthetic. No record is
    handwritten and no ID is supplied after loading. Pure classifier fixtures
    above remain unit tests and are not called production-chain evidence.
    """

    def _build(self, tmp, l3_change=None):
        import dataclasses
        from pathlib import Path
        from analysis.load import load_run
        from runner.tests.tlb_set_fixtures import A1_LAYERS, a1_plan, run_synthetic_plan
        records = []
        calls = 0
        for layer in A1_LAYERS:
            plan, platform = a1_plan(layer)
            if layer == "l3-target" and l3_change is not None:
                key, mapping = l3_change
                cases = tuple(dataclasses.replace(case, params=tuple(
                    (k, dataclasses.replace(rv, value=mapping.get(rv.value, rv.value)))
                    if k == key else (k, rv) for k, rv in case.params))
                    for case in plan.cases)
                plan = dataclasses.replace(plan, cases=cases)
            run_dir = Path(tmp) / layer
            summary, count = run_synthetic_plan(plan, platform, run_dir)
            run = load_run(run_dir)
            expected = 32 if layer == "l3-target" else 48
            self.assertEqual(len(plan.cases), expected)
            self.assertEqual(summary["ok"], expected, summary)
            self.assertEqual(summary["failed"], 0, summary)
            self.assertEqual(len(run.ok_records), expected)
            self.assertEqual(run.failed_records, [])
            self.assertEqual(count, expected * 10)
            for record in run.ok_records:
                self.assertEqual(record.get("experiment_id"), plan.experiment_id)
                self.assertEqual(sum(record["probe"]["realized"]["set_target_region_nodes"]),
                                 record["params"]["set_window"])
                self.assertTrue(gate_record(record)[0])
                for metric in record["metrics"]:
                    self.assertEqual(metric["repetitions"], 10)
                    self.assertEqual(len(metric["observations"]), 10)
            records.extend(run.ok_records)
            calls += count
        self.assertEqual(len(records), 128)
        self.assertEqual(calls, 1280)
        return records

    def test_full_128_positive(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            records = self._build(tmp)
        frozen = freeze_thresholds([0.0, 0.2, 0.0, 0.4, 0.2], scatter_mid=0.0)
        out = run_a1_adjudication(records, frozen)
        self.assertEqual(out["n_records"], 128)
        self.assertEqual(out["h_star"], 1)  # synthetic response, not a hardware conclusion

    def test_permutation_invariant_full(self):
        import json
        import random
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            records = self._build(tmp)
        frozen = freeze_thresholds([0.0, 0.2, 0.0, 0.4, 0.2], scatter_mid=0.0)
        baseline = run_a1_adjudication(records, frozen)
        random.Random(3).shuffle(records)
        shuffled = run_a1_adjudication(records, frozen)
        self.assertEqual(baseline["h_star"], 1)
        self.assertEqual(shuffled, baseline)
        self.assertEqual(json.dumps(shuffled, sort_keys=True, separators=(",", ":")),
                         json.dumps(baseline, sort_keys=True, separators=(",", ":")))

    def test_neighboring_target_plan_is_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            records = self._build(tmp, ("set_target", {200: 201}))
        with self.assertRaisesRegex(TlbError, "exact coverage"):
            run_a1_adjudication(records, freeze_thresholds([0.0, 0.2, 0.0], 0.0))

    def test_neighboring_window_plan_is_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            records = self._build(tmp, ("set_window", {8: 100, 12: 200}))
        with self.assertRaisesRegex(TlbError, "window grid"):
            run_a1_adjudication(records, freeze_thresholds([0.0, 0.2, 0.0], 0.0))


class TestR9(unittest.TestCase):
    def test_l3_exact_target_and_window_guards(self):
        recs = TestFullChain()._l1_l2() + TestFullChain()._l3()
        # target 201 冒充 200 → 拒
        bad = [r for r in recs if not (r["params"].get("set_target") == 200
                                       and "l3" in r["experiment_id"])]
        bad.append(_chain_record(1, -1, 42, 201, 8, 4.0, exp="x-a1-l3-target"))
        bad.append(_chain_record(1, -1, 42, 201, 12, 6.5, exp="x-a1-l3-target"))
        with self.assertRaisesRegex(TlbError, "exact coverage"):
            run_a1_adjudication(bad, {"frozen": True, "on_threshold": 3.0})

    def test_l3_window_grid_guard(self):
        recs = [r for r in (TestFullChain()._l1_l2() + TestFullChain()._l3())
                if "l3" not in r["experiment_id"]]
        for t in (7, 42, 100, 200):
            recs.append(_chain_record(1, -1, 42, t, 100, 4.0, exp="x-a1-l3-target"))
            recs.append(_chain_record(1, -1, 42, t, 200, 6.5, exp="x-a1-l3-target"))
        with self.assertRaisesRegex(TlbError, "window grid"):
            run_a1_adjudication(recs, {"frozen": True, "on_threshold": 3.0})



if __name__ == "__main__":
    unittest.main()
