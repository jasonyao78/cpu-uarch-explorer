"""Integrity regressions on real saved stdout; no device access.

Private replay cases skip on machines without the named original batch. Public
matrix/config contracts below always run. These tests are software evidence.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.diagnostic import run_sm8650_minimal as driver
from tools.diagnostic import summarize_sm8650_minimal as audit

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT/'data/private/20261008T223309Z-tlb'

class Matrix(unittest.TestCase):
    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError): driver.conditions('misspelled')

    def test_target100_closed_matrix(self):
        rows=driver.conditions('tlb-confirm100')
        self.assertEqual(rows, [(f'epoch-{i}', ['100']+(['--reverse'] if i%2 else [])) for i in range(5)])

    def test_fine_matrix_identity_and_order(self):
        rows=driver.conditions('rob-fine')
        self.assertEqual(len(rows),114)
        self.assertEqual(len(set(n for n,_ in rows)),114)
        def identity(opts):
            return tuple(opts[opts.index(k)+1] for k in ('-t','-a','--chain','--align','-n'))
        e0=[identity(o) for n,o in rows if n.startswith('e0-')]
        e1=[identity(o) for n,o in rows if n.startswith('e1-')]
        self.assertEqual(e0,list(reversed(e1)))
        for cls in ('add','fadd'):
            self.assertEqual({int(o[o.index('-n')+1]) for _,o in rows if o[o.index('-t')+1]==cls},{0,128,640})

    def test_requested_alignment_checked_against_real_exporter(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'exporter'; code=Path(tmp)/'code.bin'
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),
                            str(ROOT/'docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'),'-o',str(exe)],check=True)
            opts=['-t','nop','-n','640','-a','fsqrt','--chain','16','--align','32','--pmu-type','8']
            config=json.loads(subprocess.check_output([str(exe),*opts,'--write-asm',str(code)],text=True))
            driver.validate_realized('rob-fine',opts,[config])
            bad=copy.deepcopy(config); bad['loop_mod64']=0
            with self.assertRaises(ValueError): driver.validate_realized('rob-fine',opts,[bad])

@unittest.skipUnless(RAW.is_dir(), 'original private batch unavailable')
class RealReplay(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)
        for p in RAW.iterdir():
            if p.is_file(): (self.path/p.name).symlink_to(p)
        self.m=json.loads((RAW/'manifest.json').read_text())
    def tearDown(self): self.tmp.cleanup()
    def save(self):
        p=self.path/'manifest.json'; p.unlink(); p.write_text(json.dumps(self.m))
    def test_legacy_replay_still_accepted(self):
        self.assertEqual(len(audit.summarize(self.path)['rows']),200)
    def test_relabel_target100_rejected(self):
        self.m['tlb_target']=100
        for c in self.m['conditions']: c['args'][0]='100'
        self.save()
        with self.assertRaises((ValueError,AssertionError)): audit.summarize(self.path)
    def test_duplicate_epoch_cannot_replace_five_epochs(self):
        self.m['conditions']=[self.m['conditions'][0]]*5
        self.m['results']=[self.m['results'][0]]*5
        for p in self.path.glob('epoch-*-environment.json'):
            if not p.name.startswith('epoch-0-'): p.unlink()
        self.save()
        with self.assertRaises((ValueError,AssertionError)): audit.summarize(self.path)
    def test_saved_driver_must_match_launch_commit(self):
        p=self.path/'driver.py'; p.unlink(); p.write_bytes(b'# substituted driver\n')
        self.m['driver_sha256']=hashlib.sha256(p.read_bytes()).hexdigest(); self.save()
        with self.assertRaises((ValueError,AssertionError)): audit.summarize(self.path)

if __name__=='__main__': unittest.main()
