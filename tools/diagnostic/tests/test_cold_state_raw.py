"""Actual registered C/config/code/order and synthetic external measurement state.

No handwritten config or order; immutable Git/source chain is exercised. These
controlled temporary files are software contract tests, never device evidence.
"""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from tools.diagnostic import analyze_cold_state as model
from tools.diagnostic.tests.test_cold_state import synthetic_run
MODE='rob-cold-state'
MEMBERS=('P','S','E')
class ColdStateRawTests(unittest.TestCase):
    """Real registered host producer/code/order; measurement state is synthetic only."""
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.root = Path(__file__).resolve().parents[3]
        cls.launch = subprocess.check_output(['git', 'rev-parse', 'dfb37fd'], cwd=cls.root, text=True).strip()
        cls.build_path = 'docs/reviews/evidence/2026-10-10-cold-state/build.json'
        cls.plan_path = 'docs/reviews/evidence/2026-10-10-cold-state/plan.json'
        cls.protocol_path = 'docs/design/2026-10-10-cold-state-injection.md'
        cls.driver_path = 'tools/diagnostic/run_sm8650_cold_pair.py'
        cls.blob = staticmethod(lambda commit, path: subprocess.check_output(['git', 'show', commit + ':' + path], cwd=cls.root))
        cls.build = json.loads(cls.blob(cls.launch, cls.build_path))
        cls.plan = json.loads(cls.blob(cls.launch, cls.plan_path))
        # Compile immutable registered source/header blobs, never a handwritten exporter.
        for rel in cls.build['source_sha256']:
            (Path(cls.folder.name) / Path(rel).name).write_bytes(cls.blob(cls.build['source_commit'], rel))
        source = Path(cls.folder.name) / 'rob_cold_pair.c'
        cls.exe = Path(cls.folder.name) / 'exporter'
        command = ['clang', '-O2', '-Wall', '-Wextra', '-Werror', '-I', cls.folder.name]
        subprocess.run([*command, str(source), '-o', str(cls.exe)], check=True)
        cls.configs, cls.exports = {}, {}
        for epoch, condition in enumerate(cls.plan['conditions']):
            args = condition['args']
            result = subprocess.run([str(cls.exe), *args], capture_output=True, text=True)
            records = [json.loads(line) for line in result.stdout.splitlines()]
            if not result.returncode or records[-1]['failure']['reason'] != 'measurement-requires-linux-aarch64':
                raise AssertionError('host measurement must fail explicitly')
            cls.configs[epoch] = records[0]
            for mask, member in itertools.product((0, 4096), MEMBERS):
                output = Path(cls.folder.name) / f'{epoch}-{mask}-{member}.bin'
                result = subprocess.run([str(cls.exe), *args, '--mask', str(mask), '--member', member,
                                         '--write-asm', str(output)], capture_output=True, text=True, check=True)
                cls.exports[epoch, mask, member] = json.loads(result.stdout), output.read_bytes()
        harness = Path(cls.folder.name) / 'order.c'
        harness.write_text('#define main producer_main\n#include "' + str(source) + '"\n#undef main\n'
                           'int main(void){for(unsigned e=0;e<2;e++)for(unsigned t=0;t<64;t++)for(unsigned p=0;p<48;p++){'
                           'struct cell c=cell_at_single_cold(e,t,p);printf("%u %u %u %u %s %s\\n",'
                           'e,t,c.mask,c.swap,names[c.member],states[c.cooling]);}return 0;}\n')
        order_exe = Path(cls.folder.name) / 'order'
        subprocess.run([*command, str(harness), '-o', str(order_exe)], check=True)
        cls.order = []
        for line in subprocess.check_output([str(order_exe)], text=True).splitlines():
            epoch, trial, mask, swap, member, state = line.split()
            cls.order.append(dict(epoch=int(epoch), trial=int(trial), mask=int(mask), swap=int(swap), member=member, state=state))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def setUp(self):
        self.assertTrue(hasattr(model, 'audit_raw'), 'new profile raw audit is not implemented')

    @staticmethod
    def sha(blob):
        return hashlib.sha256(blob).hexdigest()

    def fixture(self, path):
        """Actual registered source/config/export/order; external measurement stub only.

These files are test-controlled synthetic raw, not data/private target evidence.
Real committed Git source/protocol/build/plan bindings remain unmocked.
"""
        profile = json.loads(self.blob(self.launch, 'configs/platforms/redmi-k70pro-01.json'))
        policy = copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment'])
        policy['preconditions']['cpufreq_governor'] = 'walt'
        snapshot = {'power': {'wakefulness': 'Dozing', 'screen_on': False},
                    'device_idle': {'force_idle': False}, 'camera': {'active': False},
                    'services': {'mi_thermald': 'running'}, 'airplane_mode': True,
                    'thermal': {'max_cpu_c': 40},
                    'cpufreq': {name: {'governor': 'walt', 'min_khz': 672000, 'max_khz': value}
                                for name, value in policy['preconditions']['cpufreq_max_khz'].items()}}
        manifest = {'mode': MODE, 'status': 'complete', 'target': 'redmi-k70pro-01',
                    'source_branch': 'synthetic-raw-only', 'source_head': self.launch,
                    'binary_source_head': self.build['source_commit'],
                    'binary_sha256': self.build['binaries']['rob_cold_pair'],
                    'source_sha256': self.build['source_sha256'],
                    'driver_sha256': self.sha(self.blob(self.launch, self.driver_path)),
                    'protocol_path': self.protocol_path, 'protocol_sha256': self.sha(self.blob(self.launch, self.protocol_path)),
                    'build_evidence_path': self.build_path, 'build_evidence_sha256': self.sha(self.blob(self.launch, self.build_path)),
                    'plan_path': self.plan_path, 'plan_sha256': self.build['plan_sha256'],
                    'conditions': self.plan['conditions'], 'midr': '0x410fd821', 'base_page_bytes': 4096, 'results': []}
        (path / 'driver.py').write_bytes(self.blob(self.launch, self.driver_path))
        (path / 'environment-policy.json').write_text(json.dumps(policy))
        for name in ('initial', 'final', 'epoch-0-pre', 'epoch-0-post', 'epoch-1-pre', 'epoch-1-post'):
            (path / (name + '-environment.json')).write_text(json.dumps({'snapshot': snapshot, 'violations': [], 'warnings': []}))
        backing = {'kernel_page_kb': 4, 'mmu_page_kb': 4, 'anon_huge_kb': 0, 'rss_kb': 8, 'swap_kb': 0, 'no_huge': True}
        cells = {tuple(r[k] for k in ('epoch', 'trial', 'mask', 'swap', 'member', 'state')): r for r in synthetic_run()['rows']}
        for epoch in (0, 1):
            name = f'epoch-{epoch}'
            runtime = {'type': 'runtime', 'cpu': 7, 'cntfrq_hz': 19200000, 'cache_line_bytes': 64,
                       'mapping_alignment_verified': True, 'raw_self_pointer_verified': True,
                       'code_address_mod64': 0, 'cache_maintenance_completed': True,
                       'initial_backing': backing, 'event_ids': [1, 2, 3, 4, 5, 6]}
            rounds = []
            for identity in self.order:
                if identity['epoch'] != epoch: continue
                cell = cells[tuple(identity[k] for k in ('epoch', 'trial', 'mask', 'swap', 'member', 'state'))]
                rounds.append(dict(type='round', **identity, ticks=cell['ticks'], enabled=100, running=100, metrics=cell['counts']))
            records = [copy.deepcopy(self.configs[epoch]), runtime, *rounds, {'type': 'backing-final', 'backing': backing}]
            stdout = path / (name + '.stdout.jsonl')
            stdout.write_text('\n'.join(json.dumps(r) for r in records) + '\n')
            (path / (name + '.stderr.log')).write_text('')
            exports = {}
            for mask, member in itertools.product((0, 4096), MEMBERS):
                config, code = self.exports[epoch, mask, member]
                key = f'm{mask}-{member}'; (path / (name + '-' + key + '.bin')).write_bytes(code)
                exports[key] = {'sha256': self.sha(code), 'config': copy.deepcopy(config)}
            manifest['results'].append({'name': name, 'exit_code': 0, 'timed_out': False,
                                        'stdout_sha256': self.sha(stdout.read_bytes()), 'generated_code': exports})
        (path / 'manifest.json').write_text(json.dumps(manifest))
        return manifest

    def test_actual_registered_plan_config_all_12_exports_and_6144_c_order(self):
        from tools.diagnostic import run_sm8650_cold_pair as driver
        self.assertEqual(model.registered_plan(), self.plan)
        self.assertEqual(model.registered_plan(), driver.plan('singlecold'))
        expected = [dict(epoch=e, trial=t, mask=m, swap=s, member=u, state=c)
                    for e in (0, 1) for t in range(64) for m, s, u, c in model.trial_order(e, t)]
        self.assertEqual(self.order, expected)
        for epoch, mask, member in itertools.product((0, 1), (0, 4096), MEMBERS):
            config, code = self.exports[epoch, mask, member]
            self.assertEqual(model.generated_code(mask, member), code)
            self.assertEqual(model._config(epoch), self.configs[epoch])
            self.assertEqual(config, dict(self.configs[epoch], export={'mask': mask, 'member': member}))

    def test_complete_synthetic_raw_has_all_original_windows_and_technical_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); self.fixture(path); result = model.audit_raw(path)
            self.assertEqual(result['run']['rows'], synthetic_run()['rows'])
            technical = result['technical_acceptance']
            self.assertTrue(technical['passed'])
            self.assertEqual(technical['environment_endpoints_count'], 6)
            self.assertEqual(len(technical['all_raw_sha256']), 25)
            self.assertEqual(sum(len(p['windows']) for p in technical['processes']), 6144)
            self.assertEqual(technical['processes'][0]['actual_config'], self.configs[0])

    def test_rehashed_typed_config_runtime_round_and_code_corruption_reject(self):
        for kind in ('config-bool', 'profile-flag', 'identity', 'missing', 'duplicate', 'order', 'mux', 'timing-bool',
                     'ticks', 'count', 'cycles', 'IR', 'clock', 'event-id', 'backing', 'export-config', 'export-code'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory); manifest = self.fixture(path); entry = manifest['results'][0]
                stdout = path / 'epoch-0.stdout.jsonl'; records = [json.loads(line) for line in stdout.read_text().splitlines()]
                if kind == 'config-bool': records[0]['exclude_kernel'] = 1
                elif kind == 'profile-flag': records[0]['single_cold_requested'] = 1
                elif kind == 'identity': records[2]['swap'] = False
                elif kind == 'missing': records.pop(2)
                elif kind == 'duplicate': records[3] = copy.deepcopy(records[2])
                elif kind == 'order': records[2:4] = records[2:4][::-1]
                elif kind == 'mux': records[2]['running'] = 99
                elif kind == 'timing-bool': records[2]['enabled'] = True; records[2]['running'] = True
                elif kind == 'ticks': records[2]['ticks'] = 2**64
                elif kind == 'count': records[2]['metrics']['0x37'] = 2**64
                elif kind == 'cycles': records[2]['metrics']['0x11'] = 0
                elif kind == 'IR': records[2]['metrics']['0x8'] = 1030
                elif kind == 'clock': records[1]['cntfrq_hz'] = True
                elif kind == 'event-id': records[1]['event_ids'][0] = True
                elif kind == 'backing': records[-1]['backing']['rss_kb'] = 9
                elif kind == 'export-config': entry['generated_code']['m0-S']['config']['single_cold_requested'] = 1
                elif kind == 'export-code':
                    f = path / 'epoch-0-m0-P.bin'; code = bytearray(f.read_bytes()); code[20 * 4] ^= 1
                    f.write_bytes(code); entry['generated_code']['m0-P']['sha256'] = self.sha(code)
                stdout.write_text('\n'.join(json.dumps(r) for r in records) + '\n')
                entry['stdout_sha256'] = self.sha(stdout.read_bytes()); (path / 'manifest.json').write_text(json.dumps(manifest))
                with self.subTest(kind=kind), self.assertRaises(ValueError): model.audit_raw(path)

    def test_mode_paths_source_driver_plan_status_and_result_binding_reject(self):
        for field, value in [('mode', 'rob-cold-pair-qualify'), ('protocol_path', 'docs/design/2026-10-09-cold-pair-qualification.md'),
                             ('build_evidence_path', 'docs/reviews/evidence/2026-10-09-cold-pair/build.json'),
                             ('plan_path', 'docs/reviews/evidence/2026-10-09-cold-pair/plan.json'), ('plan_sha256', 'bad'),
                             ('binary_source_head', 'bad'), ('binary_sha256', 'bad'), ('driver_sha256', 'bad'), ('status', 'stopped')]:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory); manifest = self.fixture(path); manifest[field] = value
                (path / 'manifest.json').write_text(json.dumps(manifest))
                with self.subTest(field=field), self.assertRaises(ValueError): model.audit_raw(path)
        for kind in ('source-sha', 'missing-export', 'exit', 'timeout', 'stdout-sha', 'stderr', 'driver'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory); manifest = self.fixture(path)
                if kind == 'source-sha': manifest['source_sha256'] = dict(manifest['source_sha256'], unexpected='bad')
                elif kind == 'missing-export': del manifest['results'][0]['generated_code']['m4096-P']
                elif kind == 'exit': manifest['results'][0]['exit_code'] = 1
                elif kind == 'timeout': manifest['results'][0]['timed_out'] = True
                elif kind == 'stdout-sha': manifest['results'][0]['stdout_sha256'] = 'bad'
                elif kind == 'stderr': (path / 'epoch-0.stderr.log').write_text('unexpected')
                else: (path / 'driver.py').write_text('drift')
                (path / 'manifest.json').write_text(json.dumps(manifest))
                with self.subTest(kind=kind), self.assertRaises(ValueError): model.audit_raw(path)

    def test_environment_exact_policy_missing_endpoint_and_hidden_drift_reject(self):
        for kind in ('policy', 'missing', 'flags', 'drift'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory); self.fixture(path)
                if kind == 'policy':
                    f = path / 'environment-policy.json'; obj = json.loads(f.read_text()); obj['preconditions']['max_cpu_temp_c'] = 100
                else:
                    f = path / 'final-environment.json'; obj = json.loads(f.read_text())
                    if kind == 'flags': obj['warnings'] = ['synthetic warning']
                    elif kind == 'drift': obj['snapshot']['cpufreq']['policy7']['min_khz'] += 1
                if kind == 'missing': f.unlink()
                else: f.write_text(json.dumps(obj))
                with self.subTest(kind=kind), self.assertRaises(ValueError): model.audit_raw(path)

    def test_actual_source_drift_and_rehashed_typed_plan_shape_reject(self):
        original = model._git_blob
        for source in self.build['source_sha256']:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory); self.fixture(path)
                def drift(commit, rel):
                    return b'synthetic source drift' if commit == self.build['source_commit'] and rel == source else original(commit, rel)
                with self.subTest(source=source), patch.object(model, '_git_blob', side_effect=drift), self.assertRaises(ValueError):
                    model.audit_raw(path)
        for kind in ('mask', 'bool-process', 'flag', 'member-order'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory); manifest = self.fixture(path)
                plan = copy.deepcopy(self.plan); build = copy.deepcopy(self.build)
                if kind == 'mask': plan['masks'][0] = 1
                elif kind == 'bool-process': plan['processes'] = 2.0
                elif kind == 'flag': plan['conditions'][0]['args'].remove('--single-cold')
                else: plan['members'][-2:] = plan['members'][-2:][::-1]
                plan_blob = json.dumps(plan).encode(); build['plan_sha256'] = self.sha(plan_blob)
                build_blob = json.dumps(build).encode()
                manifest['plan_sha256'] = build['plan_sha256']; manifest['build_evidence_sha256'] = self.sha(build_blob)
                (path / 'manifest.json').write_text(json.dumps(manifest))
                def altered(commit, rel):
                    if commit == self.launch and rel == self.plan_path: return plan_blob
                    if commit == self.launch and rel == self.build_path: return build_blob
                    return original(commit, rel)
                with self.subTest(kind=kind), patch.object(model, '_git_blob', side_effect=altered), self.assertRaises(ValueError):
                    model.audit_raw(path)

    def test_cli_real_synthetic_raw_audit_failure_publishes_neither_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); manifest = self.fixture(path); manifest['status'] = 'stopped'
            (path / 'manifest.json').write_text(json.dumps(manifest))
            summary, output = path / 'summary.json', path / 'model.json'
            with self.assertRaises(ValueError):
                model.main([str(path), '--summary-output', str(summary), '--output', str(output)])
            self.assertFalse(summary.exists()); self.assertFalse(output.exists())

    def test_cli_scientific_negative_keeps_all_values_and_never_authorizes_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); manifest = self.fixture(path)
            stdout = path / 'epoch-0.stdout.jsonl'; records = [json.loads(line) for line in stdout.read_text().splitlines()]
            for row in records[2:-1]:
                if row['member'] == 'P' and row['state'] == 'cold': row['ticks'] = 100
            stdout.write_text('\n'.join(json.dumps(r) for r in records) + '\n')
            manifest['results'][0]['stdout_sha256'] = self.sha(stdout.read_bytes()); (path / 'manifest.json').write_text(json.dumps(manifest))
            summary, output = path / 'summary.json', path / 'model.json'
            model.main([str(path), '--summary-output', str(summary), '--output', str(output)])
            result = json.loads(output.read_text())
            self.assertFalse(result['all_models_compatible']); self.assertFalse(result['n_scan_authorized'])
            self.assertEqual(len(json.loads(summary.read_text())['runs'][0]['rows']), 6144)
            self.assertEqual(sum(len(p['windows']) for p in result['technical_acceptance']['processes']), 6144)

    def test_old_actual_public_qualification_unchanged_and_rejected_as_new_profile(self):
        from tools.diagnostic import analyze_cold_pair as old
        path = self.root / 'docs/reviews/evidence/2026-10-09-cold-pair'
        run = json.loads((path / 'summary.json').read_text())['runs'][0]
        archived = json.loads((path / 'qualification.json').read_text()); original = old.qualify(run)
        self.assertEqual(original, {key: archived[key] for key in original})
        with self.assertRaises(ValueError): model.analyze(run)


if __name__=='__main__':unittest.main()
