"""Synthetic 边界测试：守住冻结逐轮门限，不能充当设备测量证据。

契约来源：docs/design/2026-10-09-long-load-qualification.md（c93e788）。
"""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from tools.diagnostic.analyze_long_load import audit_raw, main, qualify
except ModuleNotFoundError:
    qualify = None
try:
    from tools.diagnostic.analyze_long_load import audit_environment
except ImportError:
    audit_environment = None


def synthetic_run():
    """返回明确虚构的完整双 epoch/三 footprint/双 member 输入，无文件副作用。"""
    rows = []
    for epoch in (0, 1):
        for mb in (1, 64, 128):
            for serial in (False, True):
                cycles = (20 if mb == 1 else 200) * (2 if serial else 1)
                rows.append({
                    'condition': f'e{epoch}-miss-m{mb}-n0', 'epoch': epoch,
                    'memory_bytes': mb * 1048576, 'serial': serial,
                    'class': 'nop', 'anchor': 'miss', 'n': 0, 'chain': 8,
                    'loop_mod64': 0, 'chase_seed': 42,
                    'iterations': {1: 131072, 64: 524288, 128: 1048576}[mb],
                    'cycles_per_iteration': [cycles] * 3,
                    'counts_per_iteration': {
                        '0x11': [cycles] * 3, '0x8': [4.0] * 3,
                        '0x3': [2.0] * 3, '0x17': [0.02 if mb == 1 else 2.0] * 3,
                        '0x34': [0.0] * 3, '0x37': [0.0 if mb == 1 else 2.0] * 3,
                    },
                })
    return {'mode': 'rob-miss-qualify', 'processes': 6, 'rows': rows}


def synthetic_wide_run():
    """大足迹新 mode 的虚构完整输入；不改变旧64/128夹具。"""
    run = synthetic_run()
    run['mode'] = 'rob-miss-wide-thp'
    for row in run['rows']:
        mb = row['memory_bytes'] // 1048576
        mb = {1: 1, 64: 256, 128: 512}[mb]
        row.update(memory_bytes=mb * 1048576,
                   condition=f'e{row["epoch"]}-miss-m{mb}-n0',
                   iterations=max(131072, mb * 8192))
    return run


class LongLoadTests(unittest.TestCase):
    """所有数字均 synthetic，只证明计算器契约，不证明硬件资格。"""

    def setUp(self):
        self.assertTrue(callable(qualify), 'qualification analyzer is not implemented')

    def test_complete_synthetic_candidate_passes_separate_cells(self):
        result = qualify(synthetic_run())
        self.assertTrue(result['qualified'])
        self.assertEqual(len(result['candidates']), 4)
        self.assertEqual(result['windows'], 36)
        self.assertTrue(all(c['qualified'] for c in result['candidates']))

    def test_one_bad_round_is_not_rescued_by_mean_or_other_epoch(self):
        run = synthetic_run()
        run['rows'][2]['counts_per_iteration']['0x37'] = [1.7, 2.1, 2.2]
        result = qualify(run)
        self.assertFalse(result['all_candidates_qualified'])
        self.assertEqual(result['qualified_footprints_mib'], [128])
        failed = [c for c in result['candidates'] if not c['qualified']]
        self.assertEqual([(c['epoch'], c['memory_bytes']) for c in failed], [(0, 64 * 1048576)])
        self.assertEqual(failed[0]['failed_gates'], ['P.round0.LL_miss_rate'])

    def test_one_footprint_qualifies_only_when_both_epochs_pass(self):
        run = synthetic_run()
        run['rows'][2]['counts_per_iteration']['0x34'] = [1] * 3
        result = qualify(run)
        self.assertTrue(result['qualified'])
        self.assertEqual(result['smallest_qualified_footprint_mib'], 128)
        run['rows'][10]['counts_per_iteration']['0x34'] = [1] * 3
        result = qualify(run)
        self.assertFalse(result['qualified'])
        self.assertEqual(result['qualified_footprints_mib'], [])

    def test_all_three_refill_rates_use_closed_frozen_interval(self):
        for event in ('0x3', '0x17', '0x37'):
            with self.subTest(event=event):
                run = synthetic_run()
                for row in run['rows']:
                    if row['memory_bytes'] > 1048576:
                        row['counts_per_iteration'][event] = [1.8, 2.0, 2.2]
                self.assertTrue(qualify(run)['qualified'])
                run['rows'][2]['counts_per_iteration'][event][2] = 2.20001
                self.assertFalse(qualify(run)['candidates'][0]['qualified'])

    def test_walk_is_roundwise_and_inclusive(self):
        run = synthetic_run()
        run['rows'][2]['counts_per_iteration']['0x34'] = [0.02, 0, 0]
        self.assertTrue(qualify(run)['qualified'])
        run['rows'][2]['counts_per_iteration']['0x34'][0] = 0.02001
        self.assertIn('P.round0.datawalk_rate', qualify(run)['candidates'][0]['failed_gates'])

    def test_stability_is_range_over_member_median(self):
        run = synthetic_run()
        row = run['rows'][2]
        row['cycles_per_iteration'] = row['counts_per_iteration']['0x11'] = [200, 240, 240]
        cell = qualify(run)['candidates'][0]
        self.assertAlmostEqual(cell['members']['P']['cycle_range_over_median'], 1 / 6)
        self.assertIn('P.cycle_stability', cell['failed_gates'])

    def test_each_ratio_is_serial_over_parallel(self):
        run = synthetic_run()
        row = run['rows'][3]
        row['cycles_per_iteration'] = row['counts_per_iteration']['0x11'] = [320, 400, 480]
        cell = qualify(run)['candidates'][0]
        self.assertEqual(cell['serial_over_parallel'], [1.6, 2, 2.4])
        self.assertFalse(any('paired_ratio' in g for g in cell['failed_gates']))
        row['cycles_per_iteration'][0] = 319
        self.assertIn('round0.paired_ratio', qualify(run)['candidates'][0]['failed_gates'])

    def test_miss_difference_uses_mean_of_two_member_means(self):
        run = synthetic_run()
        run['rows'][3]['counts_per_iteration']['0x37'] = [1.8] * 3
        cell = qualify(run)['candidates'][0]
        self.assertAlmostEqual(cell['miss_mean_relative_difference']['0x37'], 0.2 / 1.9)
        self.assertIn('paired.LL_miss_mean_difference', cell['failed_gates'])

    def test_headroom_uses_same_epoch_hot_and_absolute_floor(self):
        run = synthetic_run()
        for row in run['rows'][:2]:
            cycles = 60 * (2 if row['serial'] else 1)
            row['cycles_per_iteration'] = row['counts_per_iteration']['0x11'] = [cycles] * 3
        cells = qualify(run)['candidates']
        self.assertEqual([c['parallel_cycle_floor'] for c in cells], [240, 240, 171, 171])
        self.assertIn('P.cycle_headroom', cells[0]['failed_gates'])
        self.assertNotIn('P.cycle_headroom', cells[2]['failed_gates'])

    def test_one_hot_serial_ll_round_rejects_both_same_epoch_candidates(self):
        run = synthetic_run()
        run['rows'][1]['counts_per_iteration']['0x37'] = [0, 0.1, 0]
        self.assertTrue(qualify(run)['qualified'])
        run['rows'][1]['counts_per_iteration']['0x37'][1] = 0.10001
        cells = qualify(run)['candidates']
        self.assertEqual([c['qualified'] for c in cells], [False, False, True, True])
        self.assertIn('hot.S.round1.LL_miss_rate', cells[0]['failed_gates'])

    def test_missing_duplicate_and_wrong_process_coverage_rejected(self):
        for mutation in ('missing', 'duplicate', 'processes'):
            run = synthetic_run()
            if mutation == 'missing':
                run['rows'].pop()
            elif mutation == 'duplicate':
                run['rows'][-1] = copy.deepcopy(run['rows'][0])
            else:
                run['processes'] = 5
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                qualify(run)

    def test_metadata_cannot_silently_change_excitation(self):
        for key, value in (('condition', 'wrong'), ('iterations', 131072),
                           ('chase_seed', 43), ('loop_mod64', 32), ('n', 1),
                           ('anchor', 'fsqrt'), ('class', 'add'), ('serial', 1)):
            run = synthetic_run()
            run['rows'][2][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                qualify(run)

    def test_nonfinite_negative_zero_cycles_and_round_count_rejected(self):
        for value in (math.nan, math.inf, -1, 0):
            run = synthetic_run()
            run['rows'][2]['cycles_per_iteration'][0] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                qualify(run)
        run = synthetic_run()
        run['rows'][2]['counts_per_iteration']['0x34'][0] = math.nan
        with self.assertRaises(ValueError):
            qualify(run)
        run = synthetic_run()
        run['rows'][2]['counts_per_iteration']['0x3'].pop()
        with self.assertRaises(ValueError):
            qualify(run)

    def test_cycle_alias_mismatch_is_rejected(self):
        run = synthetic_run()
        run['rows'][2]['counts_per_iteration']['0x11'][0] += 1
        with self.assertRaises(ValueError):
            qualify(run)

    def test_future_thp_mode_requires_explicit_selection_and_keeps_gate_source(self):
        run = synthetic_run()
        run['mode'] = 'rob-miss-qualify-thp'
        with self.assertRaises(ValueError):
            qualify(run)
        result = qualify(run, mode='rob-miss-qualify-thp')
        self.assertTrue(result['qualified'])
        self.assertEqual(result['gate_source']['commit'], 'c93e788a31c077f5575ef6139157b8fe3185bc0f')

    def test_wide_thp_requires_explicit_mode_and_full_new_shape(self):
        run = synthetic_wide_run()
        with self.assertRaises(ValueError):
            qualify(run)
        try:
            result = qualify(run, mode='rob-miss-wide-thp')
        except ValueError as exc:
            self.fail(f'explicit wide shape is not supported: {exc}')
        self.assertTrue(result['qualified'])
        self.assertEqual(result['qualified_footprints_mib'], [256, 512])
        self.assertEqual([(c['epoch'], c['memory_bytes'] // 1048576) for c in result['candidates']],
                         [(0, 256), (0, 512), (1, 256), (1, 512)])
        self.assertEqual(result['thresholds'], qualify(synthetic_run())['thresholds'])
        self.assertEqual(result['gate_source'], qualify(synthetic_run())['gate_source'])
        self.assertEqual((result['processes'], result['windows']), (6, 36))

    def test_old_footprints_cannot_be_relabelled_wide_or_reverse(self):
        run = synthetic_run()
        run['mode'] = 'rob-miss-wide-thp'
        with self.assertRaises(ValueError):
            qualify(run, mode='rob-miss-wide-thp')
        run = synthetic_wide_run()
        run['mode'] = 'rob-miss-qualify-thp'
        with self.assertRaises(ValueError):
            qualify(run, mode='rob-miss-qualify-thp')

    def test_wide_incomplete_or_old_iteration_count_cannot_pass(self):
        for mutation in ('missing', 'duplicate', 'iterations', 'mixed-footprint'):
            run = synthetic_wide_run()
            if mutation == 'missing':
                run['rows'].pop()
            elif mutation == 'duplicate':
                run['rows'][-1] = copy.deepcopy(run['rows'][0])
            elif mutation == 'iterations':
                run['rows'][2]['iterations'] = 524288
            else:
                run['rows'][2].update(memory_bytes=64 * 1048576, condition='e0-miss-m64-n0', iterations=524288)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                qualify(run, mode='rob-miss-wide-thp')

    def test_wide_scientific_gate_is_not_relaxed_for_larger_footprint(self):
        run = synthetic_wide_run()
        run['rows'][2]['counts_per_iteration']['0x37'][0] = 1.79999
        try:
            result = qualify(run, mode='rob-miss-wide-thp')
        except ValueError as exc:
            self.fail(f'explicit wide scientific gates are not implemented: {exc}')
        self.assertEqual(result['qualified_footprints_mib'], [512])
        self.assertIn('P.round0.LL_miss_rate', result['candidates'][0]['failed_gates'])

    def test_archived_4k_and_thp_pure_outputs_stay_identical(self):
        root = Path(__file__).resolve().parents[3]
        for directory in ('2026-10-09-long-load-4k', '2026-10-09-long-load-thp'):
            path = root / 'docs/reviews/evidence' / directory
            run = json.loads((path / 'summary.json').read_text())['runs'][0]
            archived = json.loads((path / 'qualification.json').read_text())
            actual = qualify(run, mode=run['mode'])
            with self.subTest(directory=directory):
                self.assertEqual(actual, {key: archived[key] for key in actual})

    def test_zero_miss_means_are_rejected_without_nonfinite_json(self):
        run = synthetic_run()
        for row in run['rows'][2:4]:
            row['counts_per_iteration']['0x37'] = [0] * 3
        cell = qualify(run)['candidates'][0]
        self.assertIsNone(cell['miss_mean_relative_difference']['0x37'])
        self.assertIn('paired.LL_miss_mean_difference', cell['failed_gates'])
        json.dumps(cell, allow_nan=False)

    def test_audited_raw_mismatch_cannot_reuse_summary(self):
        # 只替换已有 auditor 的返回值，以隔离新增的精确摘要绑定防线。
        with patch('tools.diagnostic.summarize_sm8650_minimal.summarize', return_value=synthetic_run()):
            with self.assertRaisesRegex(ValueError, 'summary differs'):
                audit_raw(Path('/synthetic/no-device'), {'runs': []})

    def test_cli_does_not_publish_when_technical_audit_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary, output = root / 'summary.json', root / 'qualification.json'
            summary.write_text(json.dumps({'runs': [synthetic_run()]}))
            with patch('tools.diagnostic.analyze_long_load.audit_raw', side_effect=ValueError('synthetic audit failure')):
                with self.assertRaisesRegex(ValueError, 'synthetic audit failure'):
                    main([str(summary), '--raw', str(root), '--output', str(output)])
            self.assertFalse(output.exists())

    def test_saved_environment_policy_cannot_relax_launch_policy(self):
        self.assertTrue(callable(audit_environment), 'environment binding is not implemented')
        policy, envs = self.synthetic_environment()
        relaxed = copy.deepcopy(policy)
        relaxed['preconditions']['max_cpu_temp_c'] = 99
        with self.assertRaisesRegex(ValueError, 'policy differs'):
            audit_environment(envs, relaxed, policy)

    def test_environment_flags_cannot_hide_snapshot_drift(self):
        self.assertTrue(callable(audit_environment), 'environment binding is not implemented')
        policy, envs = self.synthetic_environment()
        audit_environment(envs, policy, policy)
        envs['final-environment.json']['snapshot']['cpufreq']['policy7']['min_khz'] += 1
        with self.assertRaisesRegex(ValueError, 'stability failure'):
            audit_environment(envs, policy, policy)

    @staticmethod
    def synthetic_environment():
        """构造无设备的纯环境策略与端点，用来检验重算和来源绑定。"""
        policy = {'preconditions': {'wakefulness': ['Dozing'], 'screen_on': False,
                                   'force_idle': False, 'active_camera': False,
                                   'services': {'mi_thermald': 'running'},
                                   'cpufreq_governor': 'walt', 'cpufreq_max_khz': {'policy7': 2745600},
                                   'max_cpu_temp_c': 90},
                  'stable_fields': ['airplane_mode', 'cpufreq.*.min_khz']}
        snapshot = {'power': {'wakefulness': 'Dozing', 'screen_on': False},
                    'device_idle': {'force_idle': False}, 'camera': {'active': False},
                    'services': {'mi_thermald': 'running'}, 'thermal': {'max_cpu_c': 40},
                    'airplane_mode': False,
                    'cpufreq': {'policy7': {'governor': 'walt', 'min_khz': 672000, 'max_khz': 2745600}}}
        return policy, {name: {'snapshot': copy.deepcopy(snapshot), 'violations': [], 'warnings': []}
                        for name in ('initial-environment.json', 'final-environment.json')}


if __name__ == '__main__':
    unittest.main()
