"""Registered matrix and real C cell producer agree, including all rotations."""
import importlib
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]

class ColdDriver(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT/'tools/diagnostic/run_sm8650_cold_pair.py').exists(),'cold-pair driver missing')
        return importlib.import_module('tools.diagnostic.run_sm8650_cold_pair')

    def test_registered_processes_are_bounded(self):
        driver=self.module();plan=driver.plan()
        self.assertEqual(plan['mode'],'rob-cold-pair-qualify');self.assertEqual(plan['windows'],3072)
        self.assertEqual(plan['processes'],2)
        self.assertEqual(plan['conditions'],[{'name':'epoch-0','args':['--epoch','0','-n','0','--trials','64','--pin','7','--pmu-type','8']},
                                             {'name':'epoch-1','args':['--epoch','1','-n','0','--trials','64','--pin','7','--pmu-type','8']}])

    def test_complete_real_c_producer_order(self):
        driver=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'cells.c';exe=Path(tmp)/'cells'
            src.write_text('#define main producer_main\n#include "'+str(ROOT/'probes/diagnostic/rob_cold_pair.c')+'"\n#undef main\nint main(void){for(unsigned e=0;e<2;++e)for(unsigned t=0;t<64;++t)for(unsigned p=0;p<24;++p){struct cell c=cell_at(e,t,p);printf("%u %u %u %u %s %s\\n",e,t,c.mask,c.swap,names[c.member],c.cold?"cold":"hot");}return 0;}\n')
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(src),'-o',str(exe)],check=True)
            rows=[]
            for line in subprocess.check_output([str(exe)],text=True).splitlines():
                e,t,m,s,member,state=line.split();rows.append(dict(epoch=int(e),trial=int(t),mask=int(m),swap=int(s),member=member,state=state))
            expected=driver.matrix(0)+driver.matrix(1)
            self.assertEqual(rows,expected);self.assertEqual(len(rows),3072)
            self.assertEqual(len({tuple(r.values()) for r in rows}),3072)
            for epoch in (0,1):
                for trial in (0,1,23,24,63):
                    base=list(itertools.product((0,4096),(0,1),('P','S','E'),('hot','cold')))
                    base=base[trial%24:]+base[:trial%24]
                    if (trial+epoch)%2:base.reverse()
                    self.assertEqual([tuple(r[k] for k in ('mask','swap','member','state')) for r in driver.matrix(epoch) if r['trial']==trial],base)
            for bad in (True,-1,2,0.0):
                with self.assertRaises(ValueError):driver.matrix(bad)

    def test_real_config_export_matches_request_and_rejects_type_drift(self):
        driver=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'exporter';out=Path(tmp)/'code.bin'
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/rob_cold_pair.c'),'-o',str(exe)],check=True)
            for epoch in (0,1):
                for mask,member in itertools.product((0,4096),('P','S','E')):
                    actual=json.loads(subprocess.check_output([str(exe),*driver.plan()['conditions'][epoch]['args'],'--mask',str(mask),'--member',member,'--write-asm',str(out)],text=True))
                    driver.validate_config(actual,epoch,{'mask':mask,'member':member})
                    for key,bad in (('n',False),('epoch',bool(epoch)),('code_bytes',True),('node_offsets',[0,4097]),('masks',[0,1])):
                        with self.subTest(key=key):
                            v=actual.copy();v[key]=bad
                            with self.assertRaises(ValueError):driver.validate_config(v,epoch,{'mask':mask,'member':member})

    def test_uint64_measurement_wire_bounds(self):
        # Only external PMU/runtime values are synthetic. Real config and C order
        # are exercised above; this is a typed-wire negative test, not board data.
        driver=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'exporter';out=Path(tmp)/'code.bin'
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/rob_cold_pair.c'),'-o',str(exe)],check=True)
            config=json.loads(subprocess.check_output([str(exe),*driver.plan()['conditions'][0]['args'],'--write-asm',str(out)],text=True));config.pop('export')
        backing={'kernel_page_kb':4,'mmu_page_kb':4,'anon_huge_kb':0,'rss_kb':8,'swap_kb':0,'no_huge':True}
        runtime={'type':'runtime','cpu':7,'cache_line_bytes':64,'mapping_alignment_verified':True,'raw_self_pointer_verified':True,'code_address_mod64':0,'cache_maintenance_completed':True,'cntfrq_hz':19200000,'event_ids':[1,2,3,4,5,6],'initial_backing':backing}
        records=[config,runtime]+[dict(type='round',**c,ticks=0,enabled=100,running=100,metrics={'0x11':100,'0x8':29,'0x3':0,'0x17':0,'0x34':0,'0x37':0}) for c in driver.matrix(0)]+[{'type':'backing-final','backing':backing}]
        driver.validate(records,0)
        for key in driver.EVENTS:
            records[2]['metrics'][key]=2**64
            with self.subTest(key=key),self.assertRaises(ValueError):driver.validate(records,0)
            records[2]['metrics'][key]=29 if key=='0x8' else 100 if key=='0x11' else 0
        runtime['event_ids'][-1]=2**64
        with self.assertRaises(ValueError):driver.validate(records,0)
        runtime['event_ids'][-1]=6
        records[2]['enabled']=records[2]['running']=2**64
        with self.assertRaises(ValueError):driver.validate(records,0)

class SingletonDriver(unittest.TestCase):
    def test_actual_singleton_matrix_and_config_are_request_bound(self):
        import inspect
        driver=importlib.import_module('tools.diagnostic.run_sm8650_cold_pair')
        self.assertIn('profile',inspect.signature(driver.plan).parameters)
        plan=driver.plan('singletons')
        self.assertEqual((plan['mode'],plan['windows'],plan['cells_per_trial']),('rob-cold-load-model',5120,40))
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'cells.c';exe=Path(tmp)/'cells'
            src.write_text('#define main producer_main\n#include "'+str(ROOT/'probes/diagnostic/rob_cold_pair.c')+'"\n#undef main\nint main(void){for(unsigned e=0;e<2;++e)for(unsigned t=0;t<64;++t)for(unsigned p=0;p<40;++p){struct cell c=cell_at_profile(e,t,p,true);printf("%u %u %u %u %s %s\\n",e,t,c.mask,c.swap,names[c.member],c.cold?"cold":"hot");}return 0;}\n')
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(src),'-o',str(exe)],check=True)
            rows=[]
            for line in subprocess.check_output([str(exe)],text=True).splitlines():
                e,t,m,s,member,state=line.split();rows.append(dict(epoch=int(e),trial=int(t),mask=int(m),swap=int(s),member=member,state=state))
            self.assertEqual(rows,driver.matrix(0,'singletons')+driver.matrix(1,'singletons'))
            self.assertEqual(len(rows),5120)
            out=Path(tmp)/'code.bin';export=Path(tmp)/'export'
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/rob_cold_pair.c'),'-o',str(export)],check=True)
            c=json.loads(subprocess.check_output([str(export),*plan['conditions'][0]['args'],'--mask','4096','--member','A','--write-asm',str(out)],text=True))
            driver.validate_config(c,0,{'mask':4096,'member':'A'},'singletons')
            with self.assertRaises(ValueError):driver.validate_config(c,0,{'mask':4096,'member':'A'})
            c['singletons_requested']=1
            with self.assertRaises(ValueError):driver.validate_config(c,0,{'mask':4096,'member':'A'},'singletons')

    def test_complete_profile_stream_rejects_missing_duplicate_and_wrong_type(self):
        import copy
        driver=importlib.import_module('tools.diagnostic.run_sm8650_cold_pair')
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'exporter';out=Path(tmp)/'code.bin'
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/rob_cold_pair.c'),'-o',str(exe)],check=True)
            c=json.loads(subprocess.check_output([str(exe),*driver.plan('singletons')['conditions'][0]['args'],'--write-asm',str(out)],text=True));c.pop('export')
        info={'kernel_page_kb':4,'mmu_page_kb':4,'anon_huge_kb':0,'rss_kb':8,'swap_kb':0,'no_huge':True}
        runtime={'type':'runtime','cpu':7,'cntfrq_hz':19200000,'cache_line_bytes':64,
                 'mapping_alignment_verified':True,'raw_self_pointer_verified':True,'code_address_mod64':0,
                 'cache_maintenance_completed':True,'event_ids':[1,2,3,4,5,6],'initial_backing':info}
        rr=[dict(type='round',**r,ticks=0,enabled=100,running=100,
             metrics={'0x11':100,'0x8':29,'0x3':0,'0x17':0,'0x34':0,'0x37':0}) for r in driver.matrix(0,'singletons')]
        records=[c,runtime,*rr,{'type':'backing-final','backing':info}]
        driver.validate(records,0,'singletons')
        for kind in ('missing','duplicate','type','wrong-flag','wrong-profile'):
            bad=copy.deepcopy(records)
            if kind=='missing':bad.pop(10)
            elif kind=='duplicate':bad[10]=bad[9]
            elif kind=='type':bad[10]['trial']=True
            elif kind=='wrong-flag':bad[0]['singletons_requested']=1
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                driver.validate(bad,0,'pair' if kind=='wrong-profile' else 'singletons')

if __name__=='__main__':unittest.main()
