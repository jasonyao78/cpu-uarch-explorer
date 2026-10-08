# SPDX-License-Identifier: Apache-2.0
"""R3-C/R5-C：正式计划生产记录的最终身份、审计、样本和覆盖防线。

正例仅从真实配置→planner→run_plan→adapter→writer→load_run 生成。
负例在读回副本中模拟损坏/缺失/重复，纯曲线测试不冒充生产证据。
全部外部执行为合成传输；不运行 adb、目标二进制或 PMU。
"""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest

from analysis.tests.a1_production_fixture import freeze_fixture
from analysis.load import load_run
from analysis.sm8650_tlb import TlbError
from analysis.sm8650_tlb_a1 import (classify_l3_two_point, classify_onset,
                                    freeze_thresholds, gate_record,
                                    run_a1_adjudication)
from runner.tests.tlb_set_fixtures import A1_LAYERS, a1_plan, run_synthetic_plan


def produce_a1(root, output_filter=None):
    """返回真实 producer 的 128 条成功记录；零成功不可作测试输入。"""
    records = []
    for layer in A1_LAYERS:
        plan, platform = a1_plan(layer)
        directory = Path(root) / layer
        summary, calls = run_synthetic_plan(plan, platform, directory, output_filter)
        loaded = load_run(directory)
        if summary['ok'] != len(plan.cases) or loaded.failed_records:
            raise AssertionError(f'producer failed: {summary}')
        if len(loaded.ok_records) != len(plan.cases) or calls != len(plan.cases) * 10:
            raise AssertionError('producer case/sample count mismatch')
        records.extend(loaded.ok_records)
    if len(records) != 128:
        raise AssertionError('full production matrix required')
    return records


class TestA1FinalContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.records = produce_a1(cls.tmp.name)
        cls.frozen = freeze_fixture(Path(cls.tmp.name) / 'calibration')

    def assert_rejected(self, change, reason):
        records = copy.deepcopy(self.records)
        change(records)
        with self.assertRaisesRegex(TlbError, reason):
            run_a1_adjudication(records, self.frozen)

    def test_full_producer_positive_and_permutation(self):
        original = run_a1_adjudication(self.records, self.frozen)
        shuffled = copy.deepcopy(self.records)
        random.Random(9).shuffle(shuffled)
        permuted = run_a1_adjudication(shuffled, self.frozen)
        self.assertEqual(original['h_star'], 1)
        self.assertEqual(json.dumps(original, sort_keys=True),
                         json.dumps(permuted, sort_keys=True))

    def test_duplicate_record_rejected_even_if_identical(self):
        self.assert_rejected(lambda rs: rs.append(copy.deepcopy(rs[0])), 'duplicate')

    def test_missing_window_and_hypothesis_rejected(self):
        for predicate in (
            lambda r: r['experiment_id'].endswith('l1-main')
                      and r['params']['set_hypothesis'] == 1
                      and r['params']['set_region_scope'] == -1
                      and r['params']['set_window'] == 10,
            lambda r: r['params']['set_hypothesis'] == 4,
        ):
            with self.subTest(predicate=predicate):
                self.assert_rejected(lambda rs: rs.__setitem__(slice(None),
                    [r for r in rs if not predicate(r)]), 'coverage')

    def test_complete_identity_and_layer_role(self):
        mutations = (
            lambda r: r['params'].__setitem__('set_filler_pages', 1024),
            lambda r: r['params'].__setitem__('base_pages', True),
            lambda r: r['params'].__setitem__('unknown_condition', 'different'),
            lambda r: r.__setitem__('experiment_id',
                'ptr-chase-sm8650-x4-tlb-a1-l2-repro'),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assert_rejected(lambda rs: mutation(rs[0]), 'identity|descriptor')

    def test_missing_and_duplicate_observation_rejected(self):
        def missing(rs):
            rs[0]['metrics'][0]['observations'].pop()
        def duplicate(rs):
            obs = rs[0]['metrics'][0]['observations']
            obs[-1] = copy.deepcopy(obs[0])
        for change in (missing, duplicate):
            with self.subTest(change=change):
                self.assert_rejected(change, 'observations|sample')

    def test_median_must_match_observations(self):
        def change(rs):
            m = next(m for m in rs[0]['metrics'] if m['name'] == 'pmu.l2d_tlb_refill.count')
            m['value'] += 0.1
        self.assert_rejected(change, 'median')

    def test_event_and_round_qualification_required(self):
        def missing(rs):
            rs[0]['metrics'] = [m for m in rs[0]['metrics']
                                if m['name'] != 'pmu.cycles.count']
        def invalid_rounds(rs):
            m = next(m for m in rs[0]['metrics'] if m['name'] == 'window_mux_rounds')
            m['observations'][0]['value'] = 1
        for change in (missing, invalid_rounds):
            with self.subTest(change=change):
                self.assert_rejected(change, 'metric|round|median')

    def test_failed_record_and_nonfinite_value_rejected(self):
        self.assert_rejected(lambda rs: rs[0].__setitem__('status', 'failed'), 'status')
        self.assert_rejected(lambda rs: rs[0]['metrics'][0].__setitem__('value', float('nan')),
                             'finite|median')

    def test_geometry_missing_malformed_or_inconsistent_rejected(self):
        fields = (
            ('set_target_region_nodes', None),
            ('set_target_region_nodes', [2, 2, 2]),
            ('set_target_region_nodes', [True, 2, 2, 1]),
            ('set_target_region_nodes', [2, 2, 2, 2]),
            ('set_target_region_nodes', [2, 2, 3, -1]),
            ('set_region_vpn_hi', None),
            ('set_region_vpn_hi', [5, 6, 7]),
            ('set_region_vpn_hi', [5, 6, 7, 256]),
            ('set_region_vpn_hi', [5, 5, 5, 5]),
            ('set_region_vpn_hi_pure', True),
            ('set_active_regions', 3),
            ('set_domain', 'single-region-fallback'),
        )
        for key, value in fields:
            with self.subTest(key=key, value=value):
                record = copy.deepcopy(self.records[0])
                record['probe']['realized'][key] = value
                ok, reason = gate_record(record)
                self.assertFalse(ok, reason)
                self.assertIsInstance(reason, str)

    def test_malformed_containers_are_named_errors(self):
        for key in ("probe", "environment", "params", "metrics"):
            with self.subTest(key=key):
                self.assert_rejected(lambda rs: rs[0].__setitem__(key, None),
                                     "identity|metric|probe|params|descriptor")

    def test_metric_units_cannot_change_the_estimator(self):
        def change(rs):
            metric = next(m for m in rs[0]["metrics"] if m["name"] == "pmu.l2d_tlb_refill.count")
            metric["unit"] = "events-per-load"
        self.assert_rejected(change, "unit")

    def test_per_case_and_per_process_va_are_retained(self):
        def varying_va(case, sample, stdout):
            return stdout.replace('set_region_vpn_hi=5,6,7,8',
                'set_region_vpn_hi=' + ','.join(str(x + sample) for x in (5, 6, 7, 8)))
        with tempfile.TemporaryDirectory() as tmp:
            records = produce_a1(tmp, varying_va)
        out = run_a1_adjudication(records, self.frozen)
        self.assertEqual(out['h_star'], 1)
        self.assertEqual(len(out['case_audit']), 128)
        for case in out['case_audit']:
            self.assertEqual(len(case['processes']), 10)
            self.assertNotEqual(case['processes'][0]['vpn_hi'],
                                case['processes'][-1]['vpn_hi'])


class TestA1ShapeEdges(unittest.TestCase):
    def test_platform_uses_all_observations_without_threshold_filter(self):
        result = classify_onset({6: 0.2, 8: 8.0, 10: 7.0, 12: 2.9, 14: 7.0, 16: 2.9},
                                on_threshold=3.0)
        self.assertEqual(result['kind'], 'degraded')

    def test_l3_falling_has_own_rejection_label(self):
        self.assertEqual(classify_l3_two_point({8: 4.0, 12: 0.2}, 2.0), 'falling')


if __name__ == '__main__':
    unittest.main()
