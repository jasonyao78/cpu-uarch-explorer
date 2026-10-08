# SPDX-License-Identifier: Apache-2.0
"""冻结工件与生产消费接缝；所有正例经真实 plan/run_plan/写盘/回读。"""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from analysis.sm8650_tlb import TlbError
from analysis.sm8650_tlb_a1 import run_a1_adjudication
from analysis.tests.test_sm8650_tlb_a1_contract import produce_a1


class TestA1FreezeArtifact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        cls.records = produce_a1(cls.root / 'formal')

    def test_bare_boolean_is_not_an_auditable_freeze(self):
        with self.assertRaisesRegex(TlbError, 'unanchored'):
            run_a1_adjudication(self.records, {'frozen': True, 'on_threshold': 2.0})

    def test_real_calibration_freeze_and_consume(self):
        from analysis.tests.a1_production_fixture import freeze_fixture
        frozen = freeze_fixture(self.root / 'cal')
        self.assertTrue(frozen['frozen'])
        self.assertEqual(frozen['on_threshold'], 2.0)
        self.assertEqual(run_a1_adjudication(self.records, frozen)['h_star'], 1)

    def test_frozen_value_not_just_rehashed_claim(self):
        from analysis.tests.a1_production_fixture import freeze_fixture
        from analysis.sm8650_tlb_a1_freeze import artifact_digest
        frozen = freeze_fixture(self.root / 'tamper')
        frozen['on_threshold'] = 3.0
        frozen['artifact_sha256'] = artifact_digest(frozen)
        with self.assertRaisesRegex(TlbError, 'differs from calibration'):
            run_a1_adjudication(self.records, frozen)

    def test_calibration_file_drift_and_missing_file(self):
        from analysis.tests.a1_production_fixture import freeze_fixture
        for filename in ('records.jsonl', 'run-manifest.json', 'artifacts.jsonl'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                frozen = freeze_fixture(tmp)
                path = Path(tmp) / 'floor' / filename
                path.write_text(path.read_text() + '\n')
                with self.assertRaisesRegex(TlbError, 'input drift'):
                    run_a1_adjudication(self.records, frozen)
                path.unlink()
                with self.assertRaisesRegex(TlbError, 'unavailable'):
                    run_a1_adjudication(self.records, frozen)

    def test_configuration_and_code_drift(self):
        import shutil
        from analysis.tests.a1_production_fixture import freeze_fixture
        from analysis.sm8650_tlb_a1_freeze import (CODE_PATHS, CONFIG_PATHS,
            REPO_ROOT, verify_frozen_artifact)
        frozen = freeze_fixture(self.root / 'source-drift')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (*CODE_PATHS, *CONFIG_PATHS):
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REPO_ROOT / rel, dest)
            for rel, reason in ((CODE_PATHS[0], 'code_sha256'), (CONFIG_PATHS[0], 'config_sha256')):
                path = root / rel
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                with self.assertRaisesRegex(TlbError, reason):
                    verify_frozen_artifact(frozen, self.records, repo_root=root)
                path.write_bytes(original)

    def test_provenance_and_regime_drift(self):
        from analysis.tests.a1_production_fixture import freeze_fixture
        frozen = freeze_fixture(self.root / 'provenance')
        changes = (
            lambda r: r['probe']['artifact'].__setitem__('sha256', 'a' * 64),
            lambda r: r['probe']['git'].__setitem__('dirty', True),
            lambda r: r['environment'].pop('state_snapshot'),
            lambda r: r['environment']['state_snapshot']['policy_result'].__setitem__('valid', False),
            lambda r: r['environment']['state_snapshot']['before']['device_idle'].__setitem__('charging', False),
        )
        for change in changes:
            records = copy.deepcopy(self.records)
            change(records[0])
            with self.subTest(change=change), self.assertRaisesRegex(TlbError, 'provenance|environment|regime'):
                run_a1_adjudication(records, frozen)

    def test_calibration_is_disjoint_from_formal(self):
        from analysis.tests.a1_production_fixture import freeze_fixture
        from analysis.sm8650_tlb_a1_freeze import load_audited_run, verify_frozen_artifact
        frozen = freeze_fixture(self.root / 'disjoint')
        calibration, _ = load_audited_run(self.root / 'disjoint' / 'floor')
        with self.assertRaisesRegex(TlbError, 'overlap'):
            verify_frozen_artifact(frozen, calibration)
        records = copy.deepcopy(self.records)
        records[0]['metrics'][0]['observations'][0]['raw_sample_ref'] = frozen['calibration']['floor']['raw_refs'][0]
        with self.assertRaisesRegex(TlbError, 'overlap'):
            verify_frozen_artifact(frozen, records)

    def test_stop_is_auditable_but_cannot_be_consumed(self):
        from analysis.tests.a1_production_fixture import freeze_fixture
        frozen = freeze_fixture(self.root / 'stop', scatter=[1.1] * 10)
        self.assertFalse(frozen['frozen'])
        self.assertIn('artifact_sha256', frozen)
        self.assertIn('calibration', frozen)
        with self.assertRaisesRegex(TlbError, 'not frozen'):
            run_a1_adjudication(self.records, frozen)

    def test_real_frozen_two_vs_three_reaches_classifier(self):
        import re
        from analysis.tests.a1_production_fixture import freeze_fixture
        def output(case, index, stdout):
            p = {k: v.value for k, v in case.params}
            if p['set_hypothesis'] == 1 and p['set_window'] == 8:
                return re.sub(r'pmu_l2d_tlb_refill_count=\S+', 'pmu_l2d_tlb_refill_count=2.5', stdout)
            return stdout
        records = produce_a1(self.root / 'threshold-formal', output)
        two = freeze_fixture(self.root / 'two')
        three = freeze_fixture(self.root / 'three', floor=[2.6] * 10)
        self.assertEqual((two['on_threshold'], three['on_threshold']), (2.0, 3.0))
        a, b = (run_a1_adjudication(records, frozen) for frozen in (two, three))
        self.assertNotEqual(a['per_hypothesis'], b['per_hypothesis'])
        self.assertEqual((a['on_threshold'], b['on_threshold']), (2.0, 3.0))

    def test_l2_amplitude_noise_does_not_break_reproduction(self):
        import re
        from analysis.tests.a1_production_fixture import freeze_fixture
        def output(case, index, stdout):
            p = {k: v.value for k, v in case.params}
            if p['seed'] != 42 and p['set_hypothesis'] == 1 and p['set_window'] == 12:
                return re.sub(r'pmu_l2d_tlb_refill_count=\S+', 'pmu_l2d_tlb_refill_count=6.7', stdout)
            return stdout
        records = produce_a1(self.root / 'noise-formal', output)
        result = run_a1_adjudication(records, freeze_fixture(self.root / 'noise-cal'))
        self.assertEqual(result['h_star'], 1)

    def test_all_l3_below_never_supports(self):
        import re
        from analysis.tests.a1_production_fixture import freeze_fixture
        def output(case, index, stdout):
            p = {k: v.value for k, v in case.params}
            if 'a1-l3' in case.id:
                return re.sub(r'pmu_l2d_tlb_refill_count=\S+', 'pmu_l2d_tlb_refill_count=0.2', stdout)
            return stdout
        # case id carries the plan experiment id; assert the filter took effect.
        records = produce_a1(self.root / 'l3-below', output)
        l3 = [r for r in records if r['experiment_id'].endswith('l3-target')]
        self.assertTrue(all(next(m['value'] for m in r['metrics'] if m['name'] == 'pmu.l2d_tlb_refill.count') < 1 for r in l3))
        result = run_a1_adjudication(records, freeze_fixture(self.root / 'l3-cal'))
        self.assertIsNone(result['h_star'])

    def test_nonfinite_calibration_rejected(self):
        from analysis.sm8650_tlb_a1 import freeze_thresholds
        for values, scatter in (([float('nan')], 0), ([0], float('inf'))):
            with self.assertRaisesRegex(TlbError, 'finite'):
                freeze_thresholds(values, scatter)

    def test_cli_freeze_immutable_and_full_consume(self):
        from analysis.tests.a1_production_fixture import freeze_fixture
        from analysis.sm8650_tlb_a1_cli import main
        root = self.root / 'cli-cal'
        freeze_fixture(root)
        dest = root / 'frozen.json'
        argv = ['freeze', '--floor-run', str(root/'floor'), '--scatter-run', str(root/'scatter'), '--out', str(dest)]
        self.assertEqual(main(argv), 0)
        self.assertEqual(main(argv), 0)
        bad = json.loads(dest.read_text()); bad['on_threshold'] = 4
        dest.write_text(json.dumps(bad))
        self.assertEqual(main(argv), 1)
        dest.unlink()
        self.assertEqual(main(argv), 0)
        out = root/'adjudication.json'
        argv = ['adjudicate', '--frozen-file', str(dest), '--out', str(out)]
        for layer in ('l1-main', 'l2-repro', 'l3-target'):
            argv += ['--run', str(self.root/'formal'/layer)]
        self.assertEqual(main(argv), 0)
        self.assertEqual(json.loads(out.read_text())['n_records'], 128)

    def test_artifact_reference_closure_and_ignored_schema(self):
        from analysis.tests.a1_production_fixture import freeze_fixture
        from analysis.sm8650_tlb_a1_freeze import freeze_a1_from_runs
        for kind in ('raw-samples', 'probe-binary', 'old-schema'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                freeze_fixture(tmp)
                if kind == 'old-schema':
                    path = Path(tmp)/'floor'/'records.jsonl'
                    with path.open('a') as stream:
                        stream.write(json.dumps({'schema_version':'1.0'})+'\n')
                else:
                    path = Path(tmp)/'floor'/'artifacts.jsonl'
                    entries = [json.loads(l) for l in path.read_text().splitlines()]
                    entries = [e for e in entries if e['kind'] != kind]
                    path.write_text(''.join(json.dumps(e)+'\n' for e in entries))
                with self.assertRaisesRegex(TlbError, 'closure'):
                    freeze_a1_from_runs(Path(tmp)/'floor', Path(tmp)/'scatter')
