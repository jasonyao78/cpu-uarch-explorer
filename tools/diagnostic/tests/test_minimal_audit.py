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

class EncodedQualification(unittest.TestCase):
    def test_complete_matched_decoder_matrix_and_identity(self):
        self.assertIn('rob-xor-qualify',driver.MODES)
        rows=driver.conditions('rob-xor-qualify')
        self.assertEqual(len(rows),12)
        self.assertEqual([a for _,a in rows[:6]],list(reversed([a for _,a in rows[6:]])))
        self.assertEqual(len({n for n,_ in rows}),12)
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'exporter';out=Path(tmp)/'out.bin'
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),
                str(ROOT/'docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'),'-o',str(exe)],check=True)
            for name,opts in rows:
                mb=int(opts[opts.index('-m')+1]);mask=opts[opts.index('--pointer-xor')+1]
                self.assertIn('xor'+mask[2:],name)
                self.assertEqual(opts[opts.index('--backing')+1],'4k' if mb==1 else 'thp2m')
                self.assertEqual(int(opts[opts.index('-i')+1]),max(131072,mb*8192))
                config=json.loads(subprocess.check_output([str(exe),*[a for a in opts if a!='--paired'],
                    '--write-asm',str(out)],text=True)); config['paired']=True
                driver.validate_realized('rob-xor-qualify',opts,[config])
                for key,bad in [('pointer_xor','0x1234'),('pointer_xor_requested',1),
                                ('decode_instructions_per_iteration',0),('loop_instructions',4)]:
                    c=dict(config);c[key]=bad
                    with self.subTest(key=key):
                        with self.assertRaises(ValueError):driver.validate_realized('rob-xor-qualify',opts,[c])
                c=dict(config);del c['pointer_xor']
                with self.assertRaises(ValueError):driver.validate_realized('rob-xor-qualify',opts,[c])

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


class BackingObservation(unittest.TestCase):
    def test_bounded_instrumented_reproduction_not_qualification(self):
        rows=driver.conditions('rob-backing-observe')
        self.assertEqual(len(rows),1)
        name,opts=rows[0]
        self.assertEqual(name,'e0-miss-m256-n0')
        self.assertIn('rob-backing-observe',driver.THP_QUALIFICATION_MODES)
        self.assertNotIn('rob-backing-observe',driver.QUALIFICATION_MODES)
        self.assertEqual(opts[opts.index('-m')+1],'256')
        self.assertEqual(opts[opts.index('-i')+1],'2097152')
        self.assertEqual(opts[opts.index('--backing')+1],'thp2m')
        self.assertIn('--paired',opts)
        self.assertEqual(opts[opts.index('-n')+1],'0')
        self.assertEqual(driver.NEW_PROTOCOL['rob-backing-observe'],
                         'docs/design/2026-10-09-backing-observation.md')


class CollapseQualification(unittest.TestCase):
    def test_collapse_record_placement_and_actual_observation(self):
        """合成记录只测合同；采数另用真实probe全链，不代替设备证据。"""
        self.assertTrue(callable(getattr(audit,'validate_collapse',None)), '缺少collapse消费门')
        info={'kernel_page_kb':4,'mmu_page_kb':4,'anon_huge_kb':262144,
              'rss_kb':262144,'swap_kb':0,'no_huge':False}
        config={'type':'config','memory_bytes':268435456,'backing_requested':'thp2m','collapse_requested':True}
        record={'type':'backing-collapse','memory_bytes':268435456,'pmd_bytes':2097152,
                'return_code':0,'errno':0,'before_status':'coverage-mismatch',
                'after_status':'verified','before':dict(info,anon_huge_kb=229376),'after':info}
        runtime={'type':'runtime','backing_info':info}
        rows=[config,record,runtime]
        audit.validate_collapse(config,rows)
        for bad in ([config,runtime,record],[config,record,record,runtime],[config,runtime],
                    [config,dict(record,return_code=-1),runtime],
                    [config,dict(record,errno=12),runtime],
                    [config,dict(record,after_status='coverage-mismatch'),runtime],
                    [config,dict(record,after=dict(info,anon_huge_kb=229376)),runtime]):
            with self.subTest(bad=bad):
                with self.assertRaises((AssertionError,ValueError)):audit.validate_collapse(config,bad)
        with self.assertRaises((AssertionError,ValueError)):
            audit.validate_collapse(dict(config,collapse_requested=False),rows)
        audit.validate_collapse({'type':'config'},[{'type':'config'}])

    def test_complete_matrix_and_realized_collapse_identity(self):
        rows=driver.conditions('rob-collapse-qualify')
        self.assertEqual(len(rows),4)
        self.assertEqual([int(a[a.index('-m')+1]) for _,a in rows],[1,256,256,1])
        for _,a in rows:
            mb=int(a[a.index('-m')+1])
            self.assertEqual('--collapse' in a,mb==256)
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'exporter';out=Path(tmp)/'out.bin'
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),
                str(ROOT/'docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'),'-o',str(exe)],check=True)
            opts=rows[1][1];export=[a for a in opts if a!='--paired']
            config=json.loads(subprocess.check_output([str(exe),*export,'--write-asm',str(out)],text=True))
            config['paired']=True
            driver.validate_realized('rob-collapse-qualify',opts,[config])
            del config['collapse_requested']
            with self.assertRaises(ValueError):driver.validate_realized('rob-collapse-qualify',opts,[config])


class MissQualification(unittest.TestCase):
    def test_allocation_is_fully_visited_and_order_balanced(self):
        rows=driver.conditions('rob-miss-qualify')
        self.assertEqual(len(rows),6)
        sizes=[]
        for name,opts in rows:
            value=lambda k:int(opts[opts.index(k)+1])
            mb=value('-m'); sizes.append(mb)
            self.assertGreaterEqual(value('-i')*2,mb*1024*1024//64)
            self.assertIn('0x37',opts)
        self.assertEqual(sizes,[1,64,128,128,64,1])
    def test_real_memory_shape_cannot_be_relabeled(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'exporter';code=Path(tmp)/'code.bin'
            subprocess.run(['clang','-O2','-I',str(ROOT/'probes/common'),str(ROOT/'docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'),'-o',str(exe)],check=True)
            opts=['-t','nop','-n','0','-a','miss','-m','64','--pmu-type','8']
            config=json.loads(subprocess.check_output([str(exe),*opts,'--write-asm',str(code)],text=True))
            driver.validate_realized('rob-miss-qualify',opts,[config])
            config['memory_bytes']=16*1024*1024
            with self.assertRaises(ValueError): driver.validate_realized('rob-miss-qualify',opts,[config])


class ThpQualification(unittest.TestCase):
    def test_full_footprints_and_explicit_backing(self):
        rows=driver.conditions('rob-miss-qualify-thp')
        self.assertEqual(len(rows),6)
        self.assertEqual([int(a[a.index('-m')+1]) for _,a in rows],[1,64,128,128,64,1])
        for _,opts in rows:
            mb=int(opts[opts.index('-m')+1])
            self.assertEqual(opts[opts.index('--backing')+1], '4k' if mb==1 else 'thp2m')
            self.assertGreaterEqual(int(opts[opts.index('-i')+1])*2,mb*1048576//64)
    def test_real_backing_cannot_be_relabeled(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'exporter';code=Path(tmp)/'code.bin'
            subprocess.run(['clang','-O2','-I',str(ROOT/'probes/common'),str(ROOT/'docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'),'-o',str(exe)],check=True)
            opts=driver.conditions('rob-miss-qualify-thp')[1][1]
            export_opts=[o for o in opts if o!='--paired']
            config=json.loads(subprocess.check_output([str(exe),*export_opts,'--write-asm',str(code)],text=True)); config['paired']=True
            driver.validate_realized('rob-miss-qualify-thp',opts,[config])
            config['backing_requested']='4k'
            with self.assertRaises(ValueError): driver.validate_realized('rob-miss-qualify-thp',opts,[config])


class FixedFootprint(unittest.TestCase):
    def test_rebuilds_complete_two_epoch_qualification(self):
        rows=driver.conditions('rob-miss-fixed-thp')
        self.assertEqual([n for n,_ in rows],['e0-miss-m1-n0','e0-miss-m256-n0','e1-miss-m256-n0','e1-miss-m1-n0'])
        for _,opts in rows:
            mb=int(opts[opts.index('-m')+1])
            self.assertEqual(int(opts[opts.index('-i')+1]),max(131072,mb*8192))
            self.assertEqual(opts[opts.index('--backing')+1], '4k' if mb==1 else 'thp2m')


class CapacityMatrix(unittest.TestCase):
    def test_capacity_uses_registered_target_and_own_binary(self):
        self.assertEqual(driver.conditions('tlb-capacity'),[(f'epoch-{i}',['100']+(['--reverse'] if i%2 else [])) for i in range(5)])
        self.assertEqual(driver.binary_name('tlb-capacity'),'tlb_capacity')


class WideFootprints(unittest.TestCase):
    def test_full_wide_matrix_keeps_hot_control(self):
        rows=driver.conditions('rob-miss-wide-thp')
        self.assertEqual(len(rows),6)
        self.assertEqual([int(a[a.index('-m')+1]) for _,a in rows],[1,256,512,512,256,1])
        for _,opts in rows:
            mb=int(opts[opts.index('-m')+1])
            self.assertEqual(opts[opts.index('--backing')+1], '4k' if mb==1 else 'thp2m')
            self.assertEqual(int(opts[opts.index('-i')+1]),max(131072,mb*8192))


class RegisteredEvidence(unittest.TestCase):
    def test_new_mode_cannot_omit_or_substitute_build(self):
        for mode in ('tlb-history','rob-miss-qualify-thp','rob-miss-wide-thp'):
            m={'mode':mode,'protocol_path':driver.NEW_PROTOCOL[mode]}
            for path in (None,driver.BUILD_EVIDENCE):
                if path is not None: m['build_evidence_path']=path
                with self.assertRaises(AssertionError): audit.require_registered_evidence(m)
            m['build_evidence_path']='docs/reviews/evidence/'+driver.NEW_EVIDENCE[mode]+'/build.json'
            audit.require_registered_evidence(m)
            m['protocol_path']=driver.OLD_PROTOCOL
            with self.assertRaises(AssertionError): audit.require_registered_evidence(m)
    def test_legacy_manifest_shape_stays_readable(self):
        audit.require_registered_evidence({'mode':'rob-qualify'})


class BackingConsumption(unittest.TestCase):
    def fixture(self):
        info={'rss_kb':65536,'swap_kb':0,'anon_huge_kb':65536,'kernel_page_kb':4,'mmu_page_kb':4,'no_huge':False}
        runtime={'backing_verified':True,'backing_page_bytes':2097152,'mapping_4k_verified':False,'backing_info':copy.deepcopy(info)}
        rounds=[{'backing_verified':True,'backing_before':copy.deepcopy(info),'backing_after':copy.deepcopy(info)} for _ in range(6)]
        return {'backing_requested':'thp2m','memory_bytes':67108864},runtime,rounds
    def test_kernel_4k_field_does_not_deny_full_thp(self):
        audit.validate_backing(*self.fixture())
    def test_partial_post_or_requested_drift_cannot_pass(self):
        for mutation in ('partial','rss','swap','missing','request'):
            c,r,rr=self.fixture()
            if mutation=='partial': rr[-1]['backing_after']['anon_huge_kb']-=2048
            elif mutation=='rss': r['backing_info']['rss_kb']-=4
            elif mutation=='swap': rr[1]['backing_before']['swap_kb']=4
            elif mutation=='missing': del rr[2]['backing_verified']
            else: c['backing_requested']='4k'
            with self.assertRaises((AssertionError,KeyError)): audit.validate_backing(c,r,rr)


class HistoryMatrix(unittest.TestCase):
    def test_only_registered_target_and_epoch_order(self):
        self.assertEqual(driver.conditions('tlb-history'),[(f'epoch-{i}',['100']+(['--reverse'] if i%2 else [])) for i in range(5)])

if __name__=='__main__': unittest.main()
