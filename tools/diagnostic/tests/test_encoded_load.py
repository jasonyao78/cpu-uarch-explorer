"""Synthetic软件契约：编码身份/完整矩阵/生产raw接缝，不是设备证据。"""
import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

try:
    from tools.diagnostic import analyze_encoded_load as encoded
except ImportError:
    encoded = None
from tools.diagnostic.analyze_long_load import GATE_SOURCE, qualify as original_qualify
from tools.diagnostic.run_sm8650_minimal import conditions

MODE = 'rob-xor-qualify'
MASKS = ('0x0000000000000000', '0xffff000000000000')
PROTOCOL = 'docs/design/2026-10-09-encoded-load-qualification.md'
BUILD = 'docs/reviews/evidence/2026-10-09-encoded-load/build.json'
PLAN = 'docs/reviews/evidence/2026-10-09-encoded-load/plan.json'
CANONICAL_MODE = 'rob-xor-canonical-qualify'
CANONICAL_MASKS = (MASKS[0], '0x0000000000100000')
CANONICAL_PROTOCOL = 'docs/design/2026-10-09-canonical-load-qualification.md'
CANONICAL_BUILD = 'docs/reviews/evidence/2026-10-09-canonical-load/build.json'
CANONICAL_PLAN = 'docs/reviews/evidence/2026-10-09-canonical-load/plan.json'


def synthetic_run(mode=MODE):
    masks = CANONICAL_MASKS if mode == CANONICAL_MODE else MASKS
    rows = []
    for epoch in (0, 1):
        for mb in (1, 64, 128):
            for mask in masks:
                for serial in (False, True):
                    cycles = (20 if mb == 1 else 200) * (2 if serial else 1)
                    rows.append({'epoch': epoch, 'memory_bytes': mb * 1048576, 'serial': serial,
                                 'condition': f'e{epoch}-xor{mask[2:]}-miss-m{mb}-n0',
                                 'class': 'nop', 'anchor': 'miss', 'n': 0, 'chain': 8,
                                 'loop_mod64': 0, 'chase_seed': 42, 'iterations': max(131072, mb * 8192),
                                 'pointer_xor_requested': True, 'pointer_xor': mask,
                                 'decode_instructions_per_iteration': 2, 'loop_instructions': 6, 'code_bytes': 92,
                                 'cycles_per_iteration': [cycles] * 3,
                                 'counts_per_iteration': {'0x11': [cycles] * 3, '0x8': [6] * 3,
                                                         '0x3': [2] * 3, '0x17': [0 if mb == 1 else 2] * 3,
                                                         '0x34': [0] * 3, '0x37': [0 if mb == 1 else 2] * 3}})
    return {'mode': mode, 'processes': 12, 'rows': rows, 'max_cpu_c_range': [40, 40]}


def row(run, mask=MASKS[0], epoch=0, mb=64, serial=False):
    return next(r for r in run['rows'] if (r['pointer_xor'], r['epoch'], r['memory_bytes'], r['serial'])
                == (mask, epoch, mb * 1048576, serial))


class EncodedLoadTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(encoded, 'independent encoded consumer is not implemented')

    def test_complete_matrix_scores_two_masks_separately(self):
        result = encoded.qualify(synthetic_run())
        self.assertEqual((result['processes'], result['windows']), (12, 72))
        self.assertEqual(list(result['encodings']), list(MASKS))
        for mask in MASKS:
            q = result['encodings'][mask]
            self.assertEqual((q['processes'], q['windows']), (6, 36))
            self.assertEqual(q['qualified_footprints_mib'], [64, 128])
        self.assertEqual(len(result['mask_contrasts']), 12)
        self.assertTrue(result['qualified'])

    def test_one_encoding_cannot_rescue_the_other(self):
        run = synthetic_run()
        for r in run['rows']:
            if r['pointer_xor'] == MASKS[1] and r['memory_bytes'] > 1048576:
                r['counts_per_iteration']['0x37'] = [1.7, 1.7, 1.7]
        result = encoded.qualify(run)
        self.assertEqual(result['encodings'][MASKS[0]]['qualified_footprints_mib'], [64, 128])
        self.assertEqual(result['encodings'][MASKS[1]]['qualified_footprints_mib'], [])
        self.assertEqual(result['qualified_conditions'], [{'pointer_xor': MASKS[0], 'footprint_mib': n} for n in (64, 128)])
        for c in result['mask_contrasts']:
            if c['memory_bytes'] > 1048576:
                for value in c['counts_per_iteration_nonzero_minus_zero']['0x37']:
                    self.assertAlmostEqual(value, -0.3)

    def test_original_gate_source_closed_intervals_and_bad_round_retained(self):
        run = synthetic_run()
        row(run, mb=64)['counts_per_iteration']['0x37'][0] = 1.79999
        result = encoded.qualify(run)
        q = result['encodings'][MASKS[0]]
        self.assertEqual(q['gate_source'], GATE_SOURCE)
        self.assertEqual(q['qualified_footprints_mib'], [128])
        self.assertIn('P.round0.LL_miss_rate', q['candidates'][0]['failed_gates'])
        self.assertTrue(q['candidates'][2]['qualified'])

    def test_headroom_uses_same_epoch_same_mask_hot_control(self):
        run = synthetic_run()
        for serial in (False, True):
            r = row(run, mb=1, serial=serial)
            r['cycles_per_iteration'] = r['counts_per_iteration']['0x11'] = [60 * (2 if serial else 1)] * 3
        q = encoded.qualify(run)['encodings']
        self.assertEqual([c['parallel_cycle_floor'] for c in q[MASKS[0]]['candidates']], [240, 240, 171, 171])
        self.assertEqual([c['parallel_cycle_floor'] for c in q[MASKS[1]]['candidates']], [171] * 4)

    def test_complete_identity_and_code_metadata_are_mandatory(self):
        mutations = [('pointer_xor_requested', None), ('pointer_xor_requested', 1), ('pointer_xor_requested', False),
                     ('pointer_xor', '0x0'), ('pointer_xor', '0xFFFF000000000000'),
                     ('decode_instructions_per_iteration', 0), ('decode_instructions_per_iteration', 2.0),
                     ('loop_instructions', 4), ('code_bytes', 84), ('condition', 'e0-miss-m1-n0')]
        for key, value in mutations:
            run = synthetic_run(); run['rows'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                encoded.qualify(run)
        for key in ('pointer_xor_requested', 'pointer_xor', 'decode_instructions_per_iteration', 'loop_instructions'):
            run = synthetic_run(); del run['rows'][0][key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                encoded.qualify(run)

    def test_missing_duplicate_wrong_process_and_old_relabel_rejected(self):
        for kind in ('missing-mask', 'missing-member', 'duplicate', 'count', 'old-mode'):
            run = synthetic_run()
            if kind == 'missing-mask': run['rows'] = [r for r in run['rows'] if r['pointer_xor'] == MASKS[0]]
            elif kind == 'missing-member': run['rows'].pop()
            elif kind == 'duplicate': run['rows'][-1] = copy.deepcopy(run['rows'][0])
            elif kind == 'count': run['processes'] = 6
            else: run['mode'] = 'rob-miss-qualify-thp'
            with self.subTest(kind=kind), self.assertRaises(ValueError): encoded.qualify(run)

    def test_nonfinite_and_invalid_rounds_rejected_without_pooling(self):
        for value in (float('nan'), float('inf'), -1, True):
            run = synthetic_run(); row(run)['counts_per_iteration']['0x37'][0] = value
            with self.subTest(value=value), self.assertRaises(ValueError): encoded.qualify(run)
        run = synthetic_run(); row(run)['cycles_per_iteration'].pop()
        with self.assertRaises(ValueError): encoded.qualify(run)

    def test_full_synthetic_raw_accepts_plan_code_backing_and_retains_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            path, summary, blobs = self.raw_fixture(Path(directory))
            with patch.object(encoded, '_git_blob', side_effect=lambda c, p: blobs[c, p]), \
                 patch('tools.diagnostic.summarize_sm8650_minimal.summarize', return_value=summary['runs'][0]):
                result = encoded.audit_raw(path, summary)
            self.assertTrue(result['passed'])
            self.assertEqual(len(result['processes']), 12)
            self.assertEqual(sum(len(p['windows']) for p in result['processes']), 72)
            self.assertEqual(result['retired_minus_generated_kernel_range'], [240, 240])
            self.assertEqual(result['plan_path'], PLAN)
            self.assertEqual(result['environment_endpoints_count'], 26)

    def test_raw_plan_digest_shape_source_and_summary_binding_are_strict(self):
        for kind in ('plan-sha', 'plan-shape', 'driver', 'source', 'summary', 'stopped'):
            with tempfile.TemporaryDirectory() as directory:
                path, summary, blobs = self.raw_fixture(Path(directory))
                audited_run = copy.deepcopy(summary['runs'][0])
                manifest = json.loads((path / 'manifest.json').read_text())
                if kind == 'plan-sha': manifest['plan_sha256'] = 'wrong'
                elif kind == 'plan-shape':
                    plan = json.loads(blobs['synthetic-launch', PLAN]); plan['windows'] = 36
                    blobs['synthetic-launch', PLAN] = json.dumps(plan).encode()
                    manifest['plan_sha256'] = self.digest(blobs['synthetic-launch', PLAN])
                    build = json.loads(blobs['synthetic-launch', BUILD]); build['plan_sha256'] = manifest['plan_sha256']
                    blobs['synthetic-launch', BUILD] = json.dumps(build).encode()
                    manifest['build_evidence_sha256'] = self.digest(blobs['synthetic-launch', BUILD])
                elif kind == 'driver': (path / 'driver.py').write_text('drift')
                elif kind == 'source': blobs['synthetic-source', 'probes/common/rob_backing.h'] = b'drift'
                elif kind == 'summary': summary['runs'][0]['mode'] = 'old-mode'
                else: manifest['status'] = 'stopped'
                (path / 'manifest.json').write_text(json.dumps(manifest))
                with patch.object(encoded, '_git_blob', side_effect=lambda c, p: blobs[c, p]), \
                     patch('tools.diagnostic.summarize_sm8650_minimal.summarize', return_value=audited_run), \
                     self.subTest(kind=kind), self.assertRaises((ValueError, AssertionError)):
                    encoded.audit_raw(path, summary)

    def test_raw_code_backing_counts_and_pair_order_cannot_be_forged(self):
        for kind in ('code-mask', 'code-tail', 'backing', 'negative', 'retired', 'pair', 'env'):
            with tempfile.TemporaryDirectory() as directory:
                path, summary, blobs = self.raw_fixture(Path(directory))
                m = json.loads((path / 'manifest.json').read_text()); entry = m['results'][0]
                stdout = path / (entry['name'] + '.stdout.jsonl')
                records = [json.loads(s) for s in stdout.read_text().splitlines()]
                if kind.startswith('code'):
                    p = path / (entry['name'] + '-parallel.bin'); data = bytearray(p.read_bytes())
                    position = 9 * 4 if kind == 'code-mask' else 17 * 4
                    data[position:position + 4] = struct.pack('<I', 0xd503201f); p.write_bytes(data)
                    entry['generated_code']['parallel']['sha256'] = self.digest(data)
                elif kind == 'backing': records[2]['backing_after']['anon_huge_kb'] = 1
                elif kind == 'negative': records[2]['metrics']['0x37'] = -1
                elif kind == 'retired': records[2]['metrics']['0x8'] += 100000000
                elif kind == 'pair': records[2]['pair_step'] = 1
                else:
                    e = json.loads((path / 'final-environment.json').read_text())
                    e['snapshot']['cpufreq']['policy7']['min_khz'] += 1
                    (path / 'final-environment.json').write_text(json.dumps(e))
                stdout.write_text('\n'.join(json.dumps(r) for r in records) + '\n')
                entry['stdout_sha256'] = self.digest(stdout.read_bytes())
                (path / 'manifest.json').write_text(json.dumps(m))
                with patch.object(encoded, '_git_blob', side_effect=lambda c, p: blobs[c, p]), \
                     patch('tools.diagnostic.summarize_sm8650_minimal.summarize', return_value=summary['runs'][0]), \
                     self.subTest(kind=kind), self.assertRaises((ValueError, AssertionError)):
                    encoded.audit_raw(path, summary)

    def test_cli_technical_failure_never_writes_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); src = root / 'summary.json'; dst = root / 'qualification.json'
            src.write_text(json.dumps({'runs': [synthetic_run()]}))
            with patch.object(encoded, 'audit_raw', side_effect=ValueError('synthetic audit failure')):
                with self.assertRaisesRegex(ValueError, 'synthetic audit failure'):
                    encoded.main([str(src), '--raw', str(root), '--output', str(dst)])
            self.assertFalse(dst.exists())

    def test_registered_plan_matches_committed_json_and_producer_without_echoing_it(self):
        root = Path(__file__).resolve().parents[3]
        self.assertEqual(encoded.registered_plan(), json.loads((root / PLAN).read_text()))
        self.assertEqual(encoded.registered_plan()['conditions'], [{'name': n, 'args': a} for n, a in conditions(MODE)])
        forward = [c['name'][3:] for c in encoded.registered_plan()['conditions'][:6]]
        reverse = [c['name'][3:] for c in encoded.registered_plan()['conditions'][6:]]
        self.assertEqual(reverse, forward[::-1])

    def test_self_consistent_wrong_plan_and_result_order_are_rejected(self):
        for kind in ('extra', 'numeric-type', 'forward-epoch1', 'reordered-results'):
            with tempfile.TemporaryDirectory() as directory:
                path, summary, blobs = self.raw_fixture(Path(directory))
                m = json.loads((path / 'manifest.json').read_text())
                plan = json.loads(blobs['synthetic-launch', PLAN])
                if kind == 'extra': plan['new_unfrozen_option'] = True
                elif kind == 'numeric-type': plan['windows'] = 72.0
                elif kind == 'forward-epoch1': plan['conditions'][6:] = plan['conditions'][6:][::-1]
                else: m['results'][:2] = m['results'][:2][::-1]
                blobs['synthetic-launch', PLAN] = json.dumps(plan).encode()
                m['plan_sha256'] = self.digest(blobs['synthetic-launch', PLAN])
                build = json.loads(blobs['synthetic-launch', BUILD]); build['plan_sha256'] = m['plan_sha256']
                blobs['synthetic-launch', BUILD] = json.dumps(build).encode()
                m['build_evidence_sha256'] = self.digest(blobs['synthetic-launch', BUILD])
                (path / 'manifest.json').write_text(json.dumps(m))
                with patch.object(encoded, '_git_blob', side_effect=lambda c, p: blobs[c, p]), \
                     self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'plan|coverage/order'):
                    encoded.audit_raw(path, summary)

    def test_thp_initial_and_every_window_actual_coverage_are_hard_gates(self):
        for kind in ('initial', 'before', 'after', 'rss', 'swap', 'nh', 'page-size'):
            with tempfile.TemporaryDirectory() as directory:
                path, summary, blobs = self.raw_fixture(Path(directory))
                m = json.loads((path / 'manifest.json').read_text()); entry = m['results'][2]
                stdout = path / (entry['name'] + '.stdout.jsonl')
                records = [json.loads(s) for s in stdout.read_text().splitlines()]
                if kind == 'initial': records[1]['backing_info']['anon_huge_kb'] -= 2048
                elif kind in ('before', 'after'): records[-1]['backing_' + kind]['anon_huge_kb'] -= 2048
                elif kind == 'rss': records[1]['backing_info']['rss_kb'] -= 4
                elif kind == 'swap': records[1]['backing_info']['swap_kb'] = 4
                elif kind == 'nh': records[1]['backing_info']['no_huge'] = True
                else: records[1]['backing_page_bytes'] = 4096
                stdout.write_text('\n'.join(json.dumps(r) for r in records) + '\n')
                entry['stdout_sha256'] = self.digest(stdout.read_bytes())
                (path / 'manifest.json').write_text(json.dumps(m))
                with patch.object(encoded, '_git_blob', side_effect=lambda c, p: blobs[c, p]), \
                     self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'backing|runtime/coverage'):
                    encoded.audit_raw(path, summary)

    def test_pmu_mux_ids_types_and_generated_config_are_hard_gates(self):
        for kind in ('event-bool', 'event-id-bool', 'duplicate-id', 'cpu-bool', 'enabled-float', 'mux', 'count-bool', 'export-config'):
            with tempfile.TemporaryDirectory() as directory:
                path, summary, blobs = self.raw_fixture(Path(directory))
                m = json.loads((path / 'manifest.json').read_text()); entry = m['results'][0]
                stdout = path / (entry['name'] + '.stdout.jsonl')
                records = [json.loads(s) for s in stdout.read_text().splitlines()]
                if kind == 'event-bool': records[0]['events'][0] = True
                elif kind == 'event-id-bool': records[1]['event_ids'][0] = True
                elif kind == 'duplicate-id': records[1]['event_ids'][-1] = 1
                elif kind == 'cpu-bool': records[1]['cpu'] = True
                elif kind == 'enabled-float': records[2]['enabled'] = 1100.0
                elif kind == 'mux': records[2]['running'] = 1099
                elif kind == 'count-bool': records[2]['metrics']['0x34'] = False
                else: entry['generated_code']['parallel']['config']['serial'] = 0
                stdout.write_text('\n'.join(json.dumps(r) for r in records) + '\n')
                entry['stdout_sha256'] = self.digest(stdout.read_bytes())
                (path / 'manifest.json').write_text(json.dumps(m))
                with patch.object(encoded, '_git_blob', side_effect=lambda c, p: blobs[c, p]), \
                     self.subTest(kind=kind), self.assertRaises(ValueError):
                    encoded.audit_raw(path, summary)

    def test_scientific_failure_writes_all_masks_values_and_technical_receipt(self):
        run = synthetic_run()
        for r in run['rows']:
            if r['memory_bytes'] > 1048576: r['counts_per_iteration']['0x37'] = [1.7] * 3
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); src = root / 'summary.json'; dst = root / 'qualification.json'
            src.write_text(json.dumps({'runs': [run]}))
            receipt = {'passed': True, 'synthetic_test_receipt': 'not-device-evidence'}
            with patch.object(encoded, 'audit_raw', return_value=receipt):
                encoded.main([str(src), '--raw', str(root), '--output', str(dst)])
            result = json.loads(dst.read_text())
            self.assertFalse(result['qualified'])
            self.assertEqual(result['technical_acceptance'], receipt)
            self.assertEqual(result['scientific_qualification'], 'not-qualified')
            self.assertEqual(sum(len(q['candidates']) for q in result['encodings'].values()), 8)
            self.assertEqual(len(result['mask_contrasts']), 12)
            self.assertEqual(result['encodings'][MASKS[0]]['candidates'][0]['members']['P']['rounds'][0]['counts_per_iteration']['0x37'], 1.7)

    def test_canonical_fixed_profile_scores_two_registered_masks(self):
        result = encoded.qualify(synthetic_run(CANONICAL_MODE))
        self.assertEqual(result['mode'], CANONICAL_MODE)
        self.assertEqual(list(result['encodings']), list(CANONICAL_MASKS))
        self.assertEqual(result['qualified_conditions'], [{'pointer_xor': mask, 'footprint_mib': n}
                                                        for mask in CANONICAL_MASKS for n in (64, 128)])
        self.assertTrue(all(q['mode'] == CANONICAL_MODE and q['gate_source'] == GATE_SOURCE
                            for q in result['encodings'].values()))

    def test_profiles_reject_the_other_mask_or_unregistered_runtime_mask(self):
        for mode, other in ((MODE, CANONICAL_MASKS[1]), (CANONICAL_MODE, MASKS[1])):
            run = synthetic_run(mode)
            prior = run['rows'][2]['pointer_xor']
            for r in run['rows']:
                if r['pointer_xor'] == prior:
                    r['pointer_xor'] = other
                    r['condition'] = r['condition'].replace(prior[2:], other[2:])
            with self.subTest(mode=mode), self.assertRaises(ValueError): encoded.qualify(run)
        run = synthetic_run(CANONICAL_MODE); run['mode'] = 'runtime-custom-profile'
        with self.assertRaises(ValueError): encoded.qualify(run)

    def test_old_actual_public_qualification_and_raw_receipt_stay_identical(self):
        root = Path(__file__).resolve().parents[3]
        qpath = root / 'docs/reviews/evidence/2026-10-09-encoded-load/qualification.json'
        if not qpath.exists(): self.skipTest('archived public encoded qualification not available')
        q = json.loads(qpath.read_text())
        summary = json.loads((root / 'docs/reviews/evidence/2026-10-09-encoded-load/summary.json').read_text())
        expected = {k: v for k, v in q.items() if k not in ('summary_input', 'data_origin', 'technical_acceptance', 'scientific_qualification')}
        self.assertEqual(encoded.qualify(summary['runs'][0]), expected)
        raw = root / 'data/private' / q['technical_acceptance']['raw_directory']
        if raw.exists(): self.assertEqual(encoded.audit_raw(raw, summary), q['technical_acceptance'])

    def test_canonical_plan_matches_real_registered_plan_and_producer(self):
        root = Path(__file__).resolve().parents[3]
        actual = json.loads((root / CANONICAL_PLAN).read_text())
        self.assertEqual(encoded.registered_plan(CANONICAL_MODE), actual)
        self.assertEqual(actual['conditions'], [{'name': n, 'args': a} for n, a in conditions(CANONICAL_MODE)])
        self.assertEqual(actual['masks'], list(CANONICAL_MASKS))
        self.assertEqual([c['name'][3:] for c in actual['conditions'][6:]],
                         [c['name'][3:] for c in actual['conditions'][:6]][::-1])

    def test_canonical_raw_uses_only_its_registered_paths_and_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path, summary, blobs = self.raw_fixture(Path(directory), mode=CANONICAL_MODE)
            with patch.object(encoded, '_git_blob', side_effect=lambda c, p: blobs[c, p]), \
                 patch('tools.diagnostic.summarize_sm8650_minimal.summarize', return_value=summary['runs'][0]):
                accepted = encoded.audit_raw(path, summary)
            self.assertEqual(accepted['protocol_path'], CANONICAL_PROTOCOL)
            self.assertEqual(accepted['build_evidence_path'], CANONICAL_BUILD)
            self.assertEqual(accepted['plan_path'], CANONICAL_PLAN)
        for key, old_path in (('protocol_path', PROTOCOL), ('build_evidence_path', BUILD), ('plan_path', PLAN), ('mode', MODE)):
            with tempfile.TemporaryDirectory() as directory:
                path, summary, blobs = self.raw_fixture(Path(directory), mode=CANONICAL_MODE)
                m = json.loads((path / 'manifest.json').read_text()); m[key] = old_path
                (path / 'manifest.json').write_text(json.dumps(m))
                with patch.object(encoded, '_git_blob', side_effect=lambda c, p: blobs[c, p]), \
                     self.subTest(key=key), self.assertRaises(ValueError): encoded.audit_raw(path, summary)

    def test_cli_infers_canonical_or_requires_matching_explicit_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); src = root / 'summary.json'; dst = root / 'qualification.json'
            src.write_text(json.dumps({'runs': [synthetic_run(CANONICAL_MODE)]}))
            with patch.object(encoded, 'audit_raw', return_value={'passed': True, 'synthetic_test_receipt': True}):
                encoded.main([str(src), '--raw', str(root), '--output', str(dst)])
                self.assertEqual(json.loads(dst.read_text())['mode'], CANONICAL_MODE)
                dst.unlink()
                with self.assertRaises(ValueError):
                    encoded.main([str(src), '--raw', str(root), '--mode', MODE, '--output', str(dst)])
                self.assertFalse(dst.exists())

    @staticmethod
    def digest(data): return hashlib.sha256(data).hexdigest()

    def raw_fixture(self, path, mode=MODE):
        """完整虚构raw；只替换git blob/生产summarizer，执行其余真实新auditor。"""
        run = synthetic_run(mode)
        masks = CANONICAL_MASKS if mode == CANONICAL_MODE else MASKS
        protocol, build_path, plan_path = ((CANONICAL_PROTOCOL, CANONICAL_BUILD, CANONICAL_PLAN)
                                           if mode == CANONICAL_MODE else (PROTOCOL, BUILD, PLAN))
        registered = [{'name': n, 'args': a} for n, a in conditions(mode)]
        plan = {'mode': mode, 'conditions': registered, 'processes': 12, 'windows': 72,
                'member_windows': 3, 'masks': list(masks)}
        profile_policy = {'preconditions': {'wakefulness': ['Dozing'], 'screen_on': False,
                                           'force_idle': True, 'active_camera': False, 'services': {},
                                           'cpufreq_governor': 'walt', 'cpufreq_max_khz': {'policy7': 3302400},
                                           'max_cpu_temp_c': 90},
                          'stable_fields': ['cpufreq.*.min_khz']}
        snapshot = {'power': {'wakefulness': 'Dozing', 'screen_on': False},
                    'device_idle': {'force_idle': True}, 'camera': {'active': False}, 'services': {},
                    'thermal': {'max_cpu_c': 40},
                    'cpufreq': {'policy7': {'governor': 'walt', 'min_khz': 672000, 'max_khz': 3302400}}}
        blobs = {('synthetic-launch', plan_path): json.dumps(plan).encode(),
                 ('synthetic-launch', protocol): b'synthetic registered protocol',
                 ('synthetic-launch', 'tools/diagnostic/run_sm8650_minimal.py'): b'synthetic committed driver',
                 ('synthetic-launch', 'configs/platforms/redmi-k70pro-01.json'): json.dumps({'environment_profiles': {'charging-thermal': {'measurement_environment': profile_policy}}}).encode()}
        root = Path(__file__).resolve().parents[3]
        blobs[GATE_SOURCE['commit'], GATE_SOURCE['path']] = subprocess.check_output(['git', 'show', GATE_SOURCE['commit'] + ':' + GATE_SOURCE['path']], cwd=root)
        source = {}
        for p in ('docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c', 'probes/common/perf_group_read.h', 'probes/common/rob_backing.h'):
            b = ('synthetic-source:' + p).encode(); source[p] = self.digest(b)
            blobs['synthetic-source', p] = blobs['synthetic-launch', p] = b
        build = {'source_commit': 'synthetic-source', 'binaries': {'rob_window_probe': 'synthetic-binary'},
                 'source_sha256': source, 'plan_path': plan_path, 'plan_sha256': self.digest(blobs['synthetic-launch', plan_path])}
        blobs['synthetic-launch', build_path] = json.dumps(build).encode()
        m = {'mode': mode, 'status': 'complete', 'source_head': 'synthetic-launch', 'binary_source_head': 'synthetic-source',
             'binary_sha256': 'synthetic-binary', 'driver_sha256': self.digest(blobs['synthetic-launch', 'tools/diagnostic/run_sm8650_minimal.py']),
             'protocol_path': protocol, 'protocol_sha256': self.digest(blobs['synthetic-launch', protocol]),
             'build_evidence_path': build_path, 'build_evidence_sha256': self.digest(blobs['synthetic-launch', build_path]),
             'plan_path': plan_path, 'plan_sha256': build['plan_sha256'], 'conditions': registered, 'results': [],
             'midr': '0x410fd821', 'base_page_bytes': 4096}
        (path / 'driver.py').write_bytes(blobs['synthetic-launch', 'tools/diagnostic/run_sm8650_minimal.py'])
        (path / 'environment-policy.json').write_text(json.dumps(profile_policy))
        names = ['initial', 'final'] + [c['name'] + '-' + suffix for c in registered for suffix in ('pre', 'post')]
        for name in names:
            (path / (name + '-environment.json')).write_text(json.dumps({'snapshot': snapshot, 'violations': [], 'warnings': []}))
        for c in registered:
            r = next(r for r in run['rows'] if r['condition'] == c['name'])
            mb = r['memory_bytes'] // 1048576; huge = mb > 1
            config = {k: r[k] for k in ('class', 'anchor', 'n', 'chain', 'iterations', 'memory_bytes', 'chase_seed', 'loop_mod64',
                                       'pointer_xor_requested', 'pointer_xor', 'decode_instructions_per_iteration', 'loop_instructions', 'code_bytes')}
            config.update(type='config', version=2, rounds=3, paired=True, serial=False, asymmetric=False,
                          fsqrt_operand_bits='0x3ff0000000000000', loop_offset=64, branch_offset=84,
                          anchors_per_iteration=2, fillers_per_iteration=0, pmu_type=8, exclude_kernel=True, exclude_hv=True,
                          events=[17, 8, 3, 23, 52, 55], backing_requested='thp2m' if huge else '4k')
            info = {'kernel_page_kb': 4, 'mmu_page_kb': 4, 'anon_huge_kb': mb * 1024 if huge else 0,
                    'rss_kb': mb * 1024, 'swap_kb': 0, 'no_huge': not huge}
            runtime = {'type': 'runtime', 'cpu': 7, 'fpcr': 0, 'loop_address_mod64': 0, 'event_ids': list(range(1, 7)),
                       'ring_nodes': r['memory_bytes'] // 64, 'distinct_lines_per_call': r['memory_bytes'] // 64,
                       'mapping_4k_verified': not huge, 'backing_verified': True,
                       'backing_page_bytes': 2097152 if huge else 4096, 'backing_info': info}
            rounds = []
            for number, serial, step in ((0, False, 0), (0, True, 1), (1, True, 0), (1, False, 1), (2, False, 0), (2, True, 1)):
                member = next(x for x in run['rows'] if x['condition'] == c['name'] and x['serial'] == serial)
                counts = {k: int(v[number] * r['iterations']) for k, v in member['counts_per_iteration'].items()}
                counts['0x8'] = 6 * r['iterations'] + 17 + 240
                member['counts_per_iteration']['0x8'][number] = counts['0x8'] / r['iterations']
                rounds.append({'type': 'round', 'round': number, 'serial': serial, 'pair_step': step,
                               'ns': 1000, 'enabled': 1100, 'running': 1100, 'metrics': counts,
                               'backing_verified': True, 'backing_before': copy.deepcopy(info), 'backing_after': copy.deepcopy(info)})
            stdout = path / (c['name'] + '.stdout.jsonl')
            stdout.write_text('\n'.join(json.dumps(x) for x in [config, runtime, *rounds]) + '\n')
            (path / (c['name'] + '.stderr.log')).write_text('')
            generated = {}
            for member in ('parallel', 'serial'):
                mask = int(r['pointer_xor'], 16)
                words = [0xaa0203ee, 0xd2822230, 0xf2a00010, 0xf2c00010, 0xf2e00010,
                         0xd2844451, 0xf2a00011, 0xf2c00011, 0xf2e00011]
                words += [0xd280000c | ((mask & 65535) << 5)]
                words += [0xf280000c | (((mask >> shift) & 65535) << 5) | ((shift // 16) << 21) for shift in (16, 32, 48)]
                words += [0xd503201f] * 3
                words += [0xf9400000, 0xca0c0000, 0xf9400000 if member == 'serial' else 0xf9400021,
                          0xca0c0000 if member == 'serial' else 0xca0c0021, 0xf1000463, 0x54ffff61, 0xd65f03c0]
                data = struct.pack('<23I', *words)
                (path / (c['name'] + '-' + member + '.bin')).write_bytes(data)
                generated[member] = {'sha256': self.digest(data), 'config': dict(config, paired=False, serial=member == 'serial')}
            m['results'].append({'name': c['name'], 'exit_code': 0, 'timed_out': False,
                                 'stdout_sha256': self.digest(stdout.read_bytes()), 'generated_code': generated})
        (path / 'manifest.json').write_text(json.dumps(m))
        return path, {'runs': [run]}, blobs


if __name__ == '__main__': unittest.main()
