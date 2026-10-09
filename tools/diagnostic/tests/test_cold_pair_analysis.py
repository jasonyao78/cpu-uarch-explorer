"""Synthetic纯资格/身份契约；不是producer输出或目标板测量证据。"""
import copy
import itertools
import math
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

try:
    from tools.diagnostic import analyze_cold_pair as cold
except ImportError:
    cold = None

MODE = 'rob-cold-pair-qualify'
EVENTS = ('0x11', '0x8', '0x3', '0x17', '0x34', '0x37')
BASE = list(itertools.product((0, 4096), (0, 1), ('P', 'S', 'E'), ('hot', 'cold')))


def synthetic_run():
    """归一化pure输入；没有手写config/runtime/backing等生产记录。"""
    rows = []
    for epoch in (0, 1):
        for trial in range(64):
            offset = trial % 24
            order = BASE[offset:] + BASE[:offset]
            if (trial + epoch) % 2: order.reverse()
            for mask, swap, member, state in order:
                hot = {'P': 7, 'S': 8, 'E': 6}[member]
                delta = {'P': 6, 'S': 12, 'E': 0}[member]
                counts = {'0x11': 200, '0x8': 40, '0x3': 0, '0x17': 0, '0x34': 0, '0x37': 0}
                if state == 'cold' and member != 'E':
                    counts.update({'0x11': 600, '0x3': 2, '0x17': 2, '0x37': 2})
                rows.append({'epoch': epoch, 'trial': trial, 'mask': mask, 'swap': swap,
                             'member': member, 'state': state,
                             'ticks': hot + (delta if state == 'cold' else 0), 'counts': counts})
    return {'mode': MODE, 'processes': 2, 'rows': rows}


def matching(run, **identity):
    return [r for r in run['rows'] if all(r[k] == v for k, v in identity.items())]


class ColdPairAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(cold, 'new single-shot consumer is not implemented')

    def test_independent_left_rotation_reverse_order_and_complete_coverage(self):
        self.assertEqual(cold.trial_order(0, 0), BASE)
        self.assertEqual(cold.trial_order(1, 0), BASE[::-1])
        self.assertEqual(cold.trial_order(0, 1), (BASE[1:] + BASE[:1])[::-1])
        self.assertEqual(cold.trial_order(1, 1), BASE[1:] + BASE[:1])
        cells = cold.audit_cells(synthetic_run())
        self.assertEqual(len(cells), 3072)
        self.assertEqual(len({key[:2] for key in cells}), 128)

    def test_complete_synthetic_candidate_has_four_independent_cells_per_mask(self):
        q = cold.qualify(synthetic_run())
        self.assertEqual((q['processes'], q['windows']), (2, 3072))
        self.assertEqual(q['qualified_masks'], [0, 4096])
        self.assertEqual(len(q['candidates']), 8)
        self.assertTrue(all(c['qualified'] for c in q['candidates']))
        c = q['candidates'][0]
        self.assertEqual(c['members']['P']['delta_ticks'], [6] * 64)
        self.assertEqual(c['members']['S']['delta_ticks'], [12] * 64)
        self.assertEqual(c['serial_over_parallel_delta_median'], 2)
        self.assertEqual(c['members']['P']['count_delta_means']['0x37'], 2)

    def test_missing_duplicate_wrong_mode_process_and_order_are_rejected(self):
        for kind in ('missing', 'duplicate', 'mode', 'processes', 'order'):
            run = synthetic_run()
            if kind == 'missing': run['rows'].pop()
            elif kind == 'duplicate': run['rows'][-1] = copy.deepcopy(run['rows'][0])
            elif kind == 'mode': run['mode'] = 'rob-xor-qualify'
            elif kind == 'processes': run['processes'] = 1
            else: run['rows'][:2] = run['rows'][:2][::-1]
            with self.subTest(kind=kind), self.assertRaises(ValueError): cold.qualify(run)

    def test_identity_types_and_allowed_dimensions_are_strict(self):
        cases = [('epoch', False), ('epoch', 2), ('trial', 64), ('trial', 0.0), ('mask', True),
                 ('mask', '0x1000'), ('mask', 1048576), ('swap', False), ('swap', 2),
                 ('member', 'parallel'), ('state', False), ('ticks', -1), ('ticks', True),
                 ('ticks', math.inf), ('ticks', math.nan), ('ticks', 3.0)]
        for key, value in cases:
            run = synthetic_run(); run['rows'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): cold.qualify(run)

    def test_event_set_counts_and_per_window_retired_range_are_hard_gates(self):
        for event, value in (('0x37', -1), ('0x37', True), ('0x37', 2.0), ('0x37', 2**64),
                             ('0x11', 0), ('0x8', 28), ('0x8', 1030)):
            run = synthetic_run(); run['rows'][0]['counts'][event] = value
            with self.subTest(event=event, value=value), self.assertRaises(ValueError): cold.qualify(run)
        for event in ('0x34', 'unexpected'):
            run = synthetic_run()
            if event == '0x34': del run['rows'][0]['counts'][event]
            else: run['rows'][0]['counts'][event] = 0
            with self.subTest(event=event), self.assertRaises(ValueError): cold.qualify(run)

    def test_zero_ticks_and_negative_differences_are_retained(self):
        run = synthetic_run()
        for r in matching(run, member='E'): r['ticks'] = 0
        r = matching(run, epoch=0, mask=0, swap=0, member='P', state='cold', trial=0)[0]
        r['ticks'] = 0; r['counts']['0x37'] = 0
        q = cold.qualify(run); p = q['candidates'][0]['members']['P']
        self.assertEqual(p['delta_ticks'][0], -7)
        self.assertEqual(p['delta_counts']['0x37'][0], 0)
        self.assertEqual(q['candidates'][0]['members']['E']['hot_ticks'], [0] * 64)
        self.assertEqual(q['candidates'][0]['members']['E']['cold_ticks'], [0] * 64)

    def test_one_cell_cannot_be_rescued_by_other_swap_epoch_or_mask(self):
        run = synthetic_run()
        for r in matching(run, epoch=0, mask=0, swap=1, member='P', state='cold'): r['ticks'] = 9
        q = cold.qualify(run)
        self.assertEqual(q['qualified_masks'], [4096])
        rejected = next(c for c in q['candidates'] if (c['mask'], c['epoch'], c['swap']) == (0, 0, 1))
        self.assertIn('P.delta_ticks_median', rejected['failed_gates'])
        self.assertTrue(next(c for c in q['candidates'] if (c['mask'], c['epoch'], c['swap']) == (0, 1, 1))['qualified'])

    def test_empty_hot_and_cold_tick_medians_are_checked_separately(self):
        run = synthetic_run()
        for r in matching(run, epoch=0, mask=0, swap=0, member='E', state='hot'): r['ticks'] = 10
        for r in matching(run, epoch=0, mask=0, swap=0, member='E', state='cold'): r['ticks'] = 9
        q = cold.qualify(run); c = q['candidates'][0]
        self.assertIn('E.hot_ticks_median', c['failed_gates'])
        self.assertNotIn('E.cold_ticks_median', c['failed_gates'])
        self.assertEqual(c['empty_tick_upper_bound'], 9)
        self.assertEqual(c['members']['E']['delta_ticks'], [-1] * 64)

    def test_quantile_is_linear_type7_and_mad_is_unscaled(self):
        self.assertAlmostEqual(cold.linear_quantile(list(range(64)), .9), 56.7)
        run = synthetic_run()
        for r in matching(run, epoch=0, mask=0, swap=0, member='P', state='cold'):
            r['ticks'] = 12 if r['trial'] < 32 else 14
        c = cold.qualify(run)['candidates'][0]
        self.assertEqual(c['members']['P']['delta_ticks_median'], 6)
        self.assertEqual(c['members']['P']['delta_ticks_mad'], 1)
        self.assertAlmostEqual(c['members']['P']['delta_mad_over_median'], 1 / 6)

    def test_empty_abs_quantile_and_event_sentinels_keep_negative_values(self):
        run = synthetic_run()
        for r in matching(run, epoch=0, mask=0, swap=0, member='E', state='cold'):
            if r['trial'] >= 56: r['ticks'] = 3
            r['counts']['0x3'] = 0
        for r in matching(run, epoch=0, mask=0, swap=0, member='E', state='hot'): r['counts']['0x3'] = 1
        c = cold.qualify(run)['candidates'][0]
        self.assertIn('E.delta_ticks_abs_q90', c['failed_gates'])
        self.assertIn('E.L1_count_delta_mean', c['failed_gates'])
        self.assertEqual(c['members']['E']['count_delta_means']['0x3'], -1)
        self.assertEqual(c['members']['E']['delta_ticks'][-8:], [-3] * 8)

    def test_miss_rates_are_arithmetic_means_and_empty_is_not_subtracted(self):
        run = synthetic_run()
        for r in matching(run, epoch=0, mask=0, swap=0, member='E', state='cold'):
            r['ticks'] += 1
            r['counts']['0x37'] = int(r['trial'] < 32)
        c = cold.qualify(run)['candidates'][0]
        self.assertTrue(c['qualified'])
        self.assertEqual(c['members']['P']['delta_ticks_median'], 6)
        self.assertEqual(c['members']['P']['count_delta_means']['0x37'], 2)
        self.assertEqual(c['members']['E']['count_delta_means']['0x37'], .5)

    def test_nonpositive_parallel_difference_has_null_ratio_and_no_nonfinite(self):
        run = synthetic_run()
        for r in matching(run, epoch=0, mask=0, swap=0, member='P', state='cold'): r['ticks'] = 7
        c = cold.qualify(run)['candidates'][0]
        self.assertIsNone(c['serial_over_parallel_delta_median'])
        self.assertIsNone(c['members']['P']['delta_mad_over_median'])
        self.assertIn('paired.delta_median_ratio', c['failed_gates'])
        self.assertIn('P.delta_mad_over_median', c['failed_gates'])

    def test_tick_floor_ratio_and_mad_closed_boundaries(self):
        for p, s, expected in ((3, 6, True), (2, 4, False), (6, 9, True), (6, 15, True),
                               (6, 8, False), (6, 16, False)):
            run = synthetic_run()
            for member, delta in (('P', p), ('S', s)):
                hot = {'P': 7, 'S': 8}[member]
                for r in matching(run, epoch=0, mask=0, swap=0, member=member, state='cold'): r['ticks'] = hot + delta
            with self.subTest(p=p, s=s): self.assertEqual(cold.qualify(run)['candidates'][0]['qualified'], expected)
        run = synthetic_run()
        for r in matching(run, epoch=0, mask=0, swap=0, member='P', state='cold'):
            r['ticks'] = 11 if r['trial'] < 32 else 13
        c = cold.qualify(run)['candidates'][0]
        self.assertEqual(c['members']['P']['delta_mad_over_median'], .2)
        self.assertTrue(c['qualified'])
        for r in matching(run, epoch=0, mask=0, swap=0, member='P', state='cold'):
            r['ticks'] = 11 if r['trial'] < 32 else 12
        # median=4.5/MAD=.5 remains valid; deliberately widen both halves to MAD1.5.
        for r in matching(run, epoch=0, mask=0, swap=0, member='P', state='cold'):
            r['ticks'] = 10 if r['trial'] < 32 else 13
        self.assertIn('P.delta_mad_over_median', cold.qualify(run)['candidates'][0]['failed_gates'])

    def test_load_count_mean_walk_and_retired_gates_use_frozen_values(self):
        for base, high_trials, passed in ((1, 32, True), (1, 31, False), (2, 32, True), (2, 33, False)):
            run = synthetic_run()
            for r in matching(run, epoch=0, mask=0, swap=0, member='P', state='cold'):
                r['counts']['0x37'] = base + int(r['trial'] < high_trials)
            c = cold.qualify(run)['candidates'][0]
            with self.subTest(base=base, high_trials=high_trials):
                self.assertEqual('P.LL_count_delta_mean' not in c['failed_gates'], passed)
        for event, value, expected in (('0x34', 6, True), ('0x34', 7, False), ('0x8', 44, True), ('0x8', 45, False)):
            run = synthetic_run()
            for r in matching(run, epoch=0, mask=0, swap=0, member='P', state='cold'):
                r['counts'][event] = value if event == '0x8' else int(r['trial'] < value)
            c = cold.qualify(run)['candidates'][0]
            gate = 'P.retired_delta_abs_median' if event == '0x8' else 'P.datawalk_count_delta_mean'
            with self.subTest(event=event, value=value): self.assertEqual(gate not in c['failed_gates'], expected)

    def test_empty_closed_quantile_and_mean_bounds(self):
        for ticks, high_trials, passed in ((8, 32, True), (9, 32, False)):
            run = synthetic_run()
            for r in matching(run, epoch=0, mask=0, swap=0, member='E', state='cold'):
                r['ticks'] = ticks if r['trial'] >= 56 else 6
                r['counts']['0x17'] = int(r['trial'] < high_trials)
            c = cold.qualify(run)['candidates'][0]
            with self.subTest(ticks=ticks): self.assertEqual('E.delta_ticks_abs_q90' not in c['failed_gates'], passed)
            self.assertNotIn('E.L2_count_delta_mean', c['failed_gates'])
        run = synthetic_run()
        for r in matching(run, epoch=0, mask=0, swap=0, member='E', state='cold'):
            r['counts']['0x17'] = int(r['trial'] < 33)
        self.assertIn('E.L2_count_delta_mean', cold.qualify(run)['candidates'][0]['failed_gates'])

    def test_pmu_cycles_do_not_replace_internal_ticks_or_enable_empty_subtraction(self):
        run = synthetic_run()
        for r in matching(run, member='P', state='cold'): r['counts']['0x11'] = 1
        for r in matching(run, member='S', state='cold'): r['counts']['0x11'] = 10000
        q = cold.qualify(run)
        self.assertEqual(q['qualified_masks'], [0, 4096])
        self.assertTrue(all(c['serial_over_parallel_delta_median'] == 2 for c in q['candidates']))
        self.assertFalse(q['empty_subtracted'])
        self.assertEqual(q['candidates'][0]['members']['P']['delta_counts']['0x11'], [-199] * 64)

    def test_internal_ticks_must_fit_the_producer_uint64_type(self):
        run = synthetic_run(); run['rows'][0]['ticks'] = 2**64
        with self.assertRaises(ValueError): cold.qualify(run)

    def test_gate_uses_declared_threshold_table(self):
        # 只在本synthetic测试临时替换模块表，核“输出门表与实际评分”接线。
        with patch.dict(cold.THRESHOLDS, {'load_delta_ticks_median_min': 7}):
            q = cold.qualify(synthetic_run())
        self.assertEqual(q['thresholds']['load_delta_ticks_median_min'], 7)
        gate = next(g for g in q['candidates'][0]['gates'] if g['gate'] == 'P.delta_ticks_median')
        self.assertEqual(gate['lower'], 7)
        self.assertFalse(gate['passed'])

    def test_returned_threshold_metadata_does_not_mutate_future_gates(self):
        q = cold.qualify(synthetic_run())
        q['thresholds']['load_refill_delta_mean'][0] = 0
        later = cold.qualify(synthetic_run())
        self.assertEqual(later['thresholds']['load_refill_delta_mean'], [1.5, 2.5])


class ColdPairRawTests(unittest.TestCase):
    """真实host config/code/order + synthetic测量stub；绝非目标板证据。"""
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.root = Path(__file__).resolve().parents[3]
        source = cls.root / 'probes/diagnostic/rob_cold_pair.c'
        cls.exe = Path(cls.folder.name) / 'exporter'
        common = cls.root / 'probes/common'
        subprocess.run(['clang', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(common), str(source), '-o', str(cls.exe)], check=True)
        cls.configs, cls.exports = {}, {}
        for epoch in (0, 1):
            args = ['--epoch', str(epoch), '-n', '0', '--trials', '64', '--pin', '7', '--pmu-type', '8']
            p = subprocess.run([str(cls.exe), *args], capture_output=True, text=True)
            actual = [json.loads(line) for line in p.stdout.splitlines()]
            cls.configs[epoch] = actual[0]
            if not p.returncode or actual[-1]['failure']['reason'] != 'measurement-requires-linux-aarch64':
                raise AssertionError('host must export config then reject measurement')
            for mask, member in itertools.product((0, 4096), ('P', 'S', 'E')):
                out = Path(cls.folder.name) / f'{epoch}-{mask}-{member}.bin'
                p = subprocess.run([str(cls.exe), *args, '--mask', str(mask), '--member', member, '--write-asm', str(out)],
                                   capture_output=True, text=True, check=True)
                cls.exports[epoch, mask, member] = json.loads(p.stdout), out.read_bytes()
        # 调实际C cell_at，全3072条producer身份，不手写生产顺序。
        harness = Path(cls.folder.name) / 'order.c'; exe = harness.with_suffix('')
        harness.write_text('#define main producer_main\n#include "' + str(source) + '"\n#undef main\n'
                           'int main(void){for(unsigned e=0;e<2;e++)for(unsigned t=0;t<64;t++)for(unsigned p=0;p<24;p++){'
                           'struct cell c=cell_at(e,t,p);printf("{\\\"epoch\\\":%u,\\\"trial\\\":%u,\\\"mask\\\":%u,\\\"swap\\\":%u,\\\"member\\\":\\\"%s\\\",\\\"state\\\":\\\"%s\\\"}\\n",'
                           'e,t,c.mask,c.swap,names[c.member],c.cold?"cold":"hot");}return 0;}\n')
        subprocess.run(['clang', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(common), str(harness), '-o', str(exe)], check=True)
        cls.order = [json.loads(line) for line in subprocess.check_output([str(exe)], text=True).splitlines()]

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    @staticmethod
    def sha(blob): return hashlib.sha256(blob).hexdigest()

    def fixture(self, path):
        """真实config/export/order，其余明确synthetic-raw-only，git读取mock。"""
        from tools.diagnostic import run_sm8650_cold_pair as driver
        plan = driver.plan()
        policy = {'preconditions': {'wakefulness': ['Dozing'], 'screen_on': False, 'force_idle': True,
                                   'active_camera': False, 'services': {}, 'cpufreq_governor': 'walt',
                                   'cpufreq_max_khz': {'policy7': 3302400}, 'max_cpu_temp_c': 90},
                  'stable_fields': ['cpufreq.*.min_khz']}
        snapshot = {'power': {'wakefulness': 'Dozing', 'screen_on': False}, 'device_idle': {'force_idle': True},
                    'camera': {'active': False}, 'services': {}, 'thermal': {'max_cpu_c': 40},
                    'cpufreq': {'policy7': {'governor': 'walt', 'min_khz': 672000, 'max_khz': 3302400}}}
        blobs = {('synthetic-launch', driver.DRIVER): (self.root / driver.DRIVER).read_bytes(),
                 ('synthetic-launch', driver.PROTOCOL): (self.root / driver.PROTOCOL).read_bytes(),
                 ('synthetic-launch', driver.PLAN): json.dumps(plan).encode(),
                 ('synthetic-launch', driver.PROFILE): json.dumps({'environment_profiles': {'charging-thermal': {'measurement_environment': policy}}}).encode()}
        sources = {}
        for rel in ('probes/diagnostic/rob_cold_pair.c', 'probes/common/perf_group_read.h', 'probes/common/rob_backing.h'):
            blob = (self.root / rel).read_bytes(); sources[rel] = self.sha(blob)
            blobs['synthetic-launch', rel] = blobs['synthetic-source', rel] = blob
        binary = self.sha(self.exe.read_bytes())
        build = {'source_commit': 'synthetic-source', 'source_sha256': sources,
                 'binaries': {'rob_cold_pair': binary}, 'plan_path': driver.PLAN,
                 'plan_sha256': self.sha(blobs['synthetic-launch', driver.PLAN])}
        blobs['synthetic-launch', driver.BUILD] = json.dumps(build).encode()
        manifest = {'mode': MODE, 'status': 'complete', 'target': 'redmi-k70pro-01', 'source_branch': 'synthetic-only',
                    'source_head': 'synthetic-launch', 'binary_source_head': 'synthetic-source', 'binary_sha256': binary,
                    'source_sha256': sources, 'driver_sha256': self.sha(blobs['synthetic-launch', driver.DRIVER]),
                    'protocol_path': driver.PROTOCOL, 'protocol_sha256': self.sha(blobs['synthetic-launch', driver.PROTOCOL]),
                    'build_evidence_path': driver.BUILD, 'build_evidence_sha256': self.sha(blobs['synthetic-launch', driver.BUILD]),
                    'plan_path': driver.PLAN, 'plan_sha256': build['plan_sha256'], 'conditions': plan['conditions'],
                    'midr': '0x410fd821', 'base_page_bytes': 4096, 'results': []}
        (path / 'driver.py').write_bytes(blobs['synthetic-launch', driver.DRIVER])
        (path / 'environment-policy.json').write_text(json.dumps(policy))
        for name in ('initial', 'final', 'epoch-0-pre', 'epoch-0-post', 'epoch-1-pre', 'epoch-1-post'):
            (path / (name + '-environment.json')).write_text(json.dumps({'snapshot': snapshot, 'violations': [], 'warnings': []}))
        normalized = synthetic_run()
        by_key = {(r['epoch'], r['trial'], r['mask'], r['swap'], r['member'], r['state']): r for r in normalized['rows']}
        backing = {'kernel_page_kb': 4, 'mmu_page_kb': 4, 'anon_huge_kb': 0, 'rss_kb': 8, 'swap_kb': 0, 'no_huge': True}
        for epoch in (0, 1):
            name = 'epoch-' + str(epoch)
            runtime = {'type': 'runtime', 'cpu': 7, 'cntfrq_hz': 19200000, 'cache_line_bytes': 64,
                       'mapping_alignment_verified': True, 'raw_self_pointer_verified': True,
                       'code_address_mod64': 0, 'cache_maintenance_completed': True,
                       'initial_backing': backing, 'event_ids': [1, 2, 3, 4, 5, 6]}
            rounds = []
            for identity in self.order:
                if identity['epoch'] != epoch: continue
                key = tuple(identity[k] for k in ('epoch', 'trial', 'mask', 'swap', 'member', 'state'))
                r = by_key[key]
                rounds.append(dict(type='round', **identity, ticks=r['ticks'], enabled=100, running=100, metrics=r['counts']))
            records = [self.configs[epoch], runtime, *rounds, {'type': 'backing-final', 'backing': backing}]
            stdout = path / (name + '.stdout.jsonl')
            stdout.write_text('\n'.join(json.dumps(r) for r in records) + '\n')
            (path / (name + '.stderr.log')).write_text('')
            generated = {}
            for mask, member in itertools.product((0, 4096), ('P', 'S', 'E')):
                config, code = self.exports[epoch, mask, member]
                key = f'm{mask}-{member}'; (path / (name + '-' + key + '.bin')).write_bytes(code)
                generated[key] = {'sha256': self.sha(code), 'config': copy.deepcopy(config)}
            manifest['results'].append({'name': name, 'exit_code': 0, 'timed_out': False, 'wall_seconds': 1,
                                        'stdout_sha256': self.sha(stdout.read_bytes()), 'generated_code': generated})
        (path / 'manifest.json').write_text(json.dumps(manifest))
        return manifest, blobs

    def test_actual_config_six_exports_and_all_3072_order_match_independent_consumer(self):
        from tools.diagnostic import run_sm8650_cold_pair as driver
        self.assertEqual(cold.registered_plan(), driver.plan())
        actual_plan = self.root / driver.PLAN
        self.assertEqual(cold.registered_plan(), json.loads(actual_plan.read_text()))
        for epoch in (0, 1):
            actual = [r for r in self.order if r['epoch'] == epoch]
            expected = [{'epoch': epoch, 'trial': t, 'mask': m, 'swap': s, 'member': u, 'state': state}
                        for t in range(64) for m, s, u, state in cold.trial_order(epoch, t)]
            self.assertEqual(actual, expected)
            for mask, member in itertools.product((0, 4096), ('P', 'S', 'E')):
                _, code = self.exports[epoch, mask, member]
                self.assertEqual(cold.generated_code(mask, member), code)

    def test_complete_synthetic_raw_retains_actual_config_code_and_all_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); _, blobs = self.fixture(path)
            with patch.object(cold, '_git_blob', side_effect=lambda c, p: blobs[c, p]): result = cold.audit_raw(path)
            self.assertEqual(result['run']['rows'], synthetic_run()['rows'])
            self.assertEqual(len(result['run']['rows']), 3072)
            technical = result['technical_acceptance']
            self.assertTrue(technical['passed'])
            self.assertEqual(technical['environment_endpoints_count'], 6)
            self.assertEqual(sum(len(p['windows']) for p in technical['processes']), 3072)
            self.assertEqual(technical['processes'][0]['actual_config'], self.configs[0])

    def test_fixture_export_mutation_cannot_poison_later_real_producer_config(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            m, _ = self.fixture(Path(first))
            m['results'][0]['generated_code']['m0-P']['config']['exclude_kernel'] = 1
            fresh, _ = self.fixture(Path(second))
            self.assertIs(fresh['results'][0]['generated_code']['m0-P']['config']['exclude_kernel'], True)

    def test_rehashed_raw_corruption_and_missing_complete_block_are_rejected(self):
        for kind in ('stopped', 'source', 'driver', 'plan', 'order', 'config', 'mux', 'clock', 'event-id',
                     'backing', 'count-range', 'cycles', 'ticks', 'export-config', 'export-code', 'environment'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory); m, blobs = self.fixture(path); entry = m['results'][0]
                stdout = path / 'epoch-0.stdout.jsonl'; records = [json.loads(line) for line in stdout.read_text().splitlines()]
                if kind == 'stopped': m['status'] = 'stopped'
                elif kind == 'source': blobs['synthetic-source', 'probes/common/rob_backing.h'] = b'drift'
                elif kind == 'driver': (path / 'driver.py').write_text('drift')
                elif kind == 'plan': m['plan_sha256'] = 'drift'
                elif kind == 'order': records[2:4] = records[2:4][::-1]
                elif kind == 'config': records[0]['exclude_kernel'] = 1
                elif kind == 'mux': records[2]['running'] = 99
                elif kind == 'clock': records[1]['cntfrq_hz'] = True
                elif kind == 'event-id': records[1]['event_ids'][0] = True
                elif kind == 'backing': records[-1]['backing']['rss_kb'] = 9
                elif kind == 'count-range': records[2]['metrics']['0x37'] = 2**64
                elif kind == 'cycles': records[2]['metrics']['0x11'] = 0
                elif kind == 'ticks': records[2]['ticks'] = 2**64
                elif kind == 'export-config': entry['generated_code']['m0-P']['config']['exclude_kernel'] = 1
                elif kind == 'export-code':
                    p = path / 'epoch-0-m0-P.bin'; code = bytearray(p.read_bytes()); code[16 * 4] ^= 1
                    p.write_bytes(code); entry['generated_code']['m0-P']['sha256'] = self.sha(code)
                else:
                    env = json.loads((path / 'final-environment.json').read_text())
                    env['snapshot']['cpufreq']['policy7']['min_khz'] += 1
                    (path / 'final-environment.json').write_text(json.dumps(env))
                stdout.write_text('\n'.join(json.dumps(r) for r in records) + '\n')
                entry['stdout_sha256'] = self.sha(stdout.read_bytes()); (path / 'manifest.json').write_text(json.dumps(m))
                with patch.object(cold, '_git_blob', side_effect=lambda c, p: blobs[c, p]), \
                     self.subTest(kind=kind), self.assertRaises(ValueError): cold.audit_raw(path)

    def test_cli_failure_publishes_neither_artifact_and_scientific_negative_retains_all(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); summary = path / 'summary.json'; qpath = path / 'qualification.json'
            with patch.object(cold, 'audit_raw', side_effect=ValueError('synthetic technical rejection')):
                with self.assertRaises(ValueError): cold.main([str(path), '--summary-output', str(summary), '--output', str(qpath)])
            self.assertFalse(summary.exists()); self.assertFalse(qpath.exists())
            run = synthetic_run()
            for r in matching(run, member='P', state='cold'): r['ticks'] = 7
            with patch.object(cold, 'audit_raw', return_value={'run': run, 'technical_acceptance': {'passed': True, 'synthetic_only': True}}):
                cold.main([str(path), '--summary-output', str(summary), '--output', str(qpath)])
            self.assertEqual(len(json.loads(summary.read_text())['runs'][0]['rows']), 3072)
            q = json.loads(qpath.read_text()); self.assertFalse(q['qualified']); self.assertEqual(len(q['candidates']), 8)
            self.assertEqual(q['technical_acceptance'], {'passed': True, 'synthetic_only': True})


if __name__ == '__main__': unittest.main()
