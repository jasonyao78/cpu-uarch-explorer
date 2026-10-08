# SPDX-License-Identifier: Apache-2.0
"""A1 判据消费入口金样（合成输入）：硬门 / 预测分区 / 量化 onset / H 判定 / L3。"""
import unittest

from analysis.sm8650_tlb import TlbError
from analysis.sm8650_tlb_a1 import (adjudicate_h, check_l3_consistency,
                                    classify_onset, freeze_thresholds,
                                    gate_record, predicted_hw_sets, run_a1_adjudication)


def _record(scope=-1, regions=4, nodes=None, pure=1, consistent=None):
    # 仅供几何纯函数测试；不作为正式 producer 证据。
    params = {"set_hypothesis": 1, "set_target": 7, "set_window": 12,
        "set_rounds": 20, "set_pool_pages": 65536, "set_filler_pages": 512,
        "set_regions": regions, "set_region_scope": scope, "set_nsets": 0, "seed": 42}
    counts = nodes if nodes is not None else ([3] * regions if scope < 0 else [12] + [0] * (regions - 1))
    realized = {**params, "mode": "tlbset", "page_kb": "4", "scatter": 0,
        "set_domain": "multi-region", "set_target_region_nodes": counts,
        "set_active_regions": sum(n > 0 for n in counts),
        "set_region_vpn_hi": list(range(5, 5 + regions)), "set_region_vpn_hi_pure": pure}
    if consistent is not None:
        realized["domain_consistent"] = consistent
    return {"params": params, "probe": {"realized": realized}}


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
        from pathlib import Path
        from analysis.tests.a1_production_fixture import freeze_fixture
        with tempfile.TemporaryDirectory() as tmp:
            records = self._build(tmp)
            frozen = freeze_fixture(Path(tmp) / 'calibration')
            out = run_a1_adjudication(records, frozen)
            self.assertEqual(out['n_records'], 128)
            self.assertEqual(out['h_star'], 1)  # synthetic, not a hardware conclusion

    def test_permutation_invariant_full(self):
        import json, random, tempfile
        from pathlib import Path
        from analysis.tests.a1_production_fixture import freeze_fixture
        with tempfile.TemporaryDirectory() as tmp:
            records = self._build(tmp)
            frozen = freeze_fixture(Path(tmp) / 'calibration')
            baseline = run_a1_adjudication(records, frozen)
            random.Random(3).shuffle(records)
            shuffled = run_a1_adjudication(records, frozen)
            self.assertEqual(baseline['h_star'], 1)
            self.assertEqual(json.dumps(shuffled, sort_keys=True), json.dumps(baseline, sort_keys=True))

    def test_neighboring_target_plan_is_rejected(self):
        import tempfile
        from pathlib import Path
        from analysis.tests.a1_production_fixture import freeze_fixture
        with tempfile.TemporaryDirectory() as tmp:
            records = self._build(tmp, ('set_target', {200: 201}))
            frozen = freeze_fixture(Path(tmp) / 'calibration')
            with self.assertRaisesRegex(TlbError, 'exact coverage'):
                run_a1_adjudication(records, frozen)

    def test_neighboring_window_plan_is_rejected(self):
        import tempfile
        from pathlib import Path
        from analysis.tests.a1_production_fixture import freeze_fixture
        with tempfile.TemporaryDirectory() as tmp:
            records = self._build(tmp, ('set_window', {8: 100, 12: 200}))
            frozen = freeze_fixture(Path(tmp) / 'calibration')
            with self.assertRaisesRegex(TlbError, 'window grid'):
                run_a1_adjudication(records, frozen)


if __name__ == "__main__":
    unittest.main()
