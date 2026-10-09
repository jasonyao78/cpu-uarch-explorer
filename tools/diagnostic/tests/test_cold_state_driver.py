"""Four-state fixed plan and typed producer/transport seams."""
import copy
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.diagnostic import run_sm8650_cold_pair as d
ROOT=Path(__file__).resolve().parents[3]

class ColdStateDriver(unittest.TestCase):
    def test_fixed_plan_matrix_and_flag(self):
        try:plan=d.plan('singlecold')
        except ValueError as ex:self.fail('four-state profile not registered: '+str(ex))
        self.assertEqual((plan['mode'],plan['windows'],plan['cells_per_trial']),('rob-cold-state',6144,48))
        self.assertEqual(plan['states'],['hot','first-cold','second-cold','cold'])
        self.assertEqual(plan['state_cold_slot_masks'],[0,1,2,3])
        for e,c in enumerate(plan['conditions']):
            self.assertEqual(c['args'],['--epoch',str(e),'-n','0','--trials','64','--pin','7','--pmu-type','8','--single-cold'])
            expected=[]
            for t in range(64):
                base=list(itertools.product((0,4096),(0,1),('P','S','E'),plan['states']))
                base=base[t%48:]+base[:t%48]
                if (t+e)%2:base.reverse()
                expected.extend(dict(epoch=e,trial=t,mask=m,swap=s,member=u,state=state) for m,s,u,state in base)
            self.assertEqual(d.matrix(e,'singlecold'),expected)

    def test_actual_config_then_complete_synthetic_wire_and_corruption(self):
        try:plan=d.plan('singlecold')
        except ValueError as ex:self.fail('four-state profile not registered: '+str(ex))
        with tempfile.TemporaryDirectory() as folder:
            exe=Path(folder)/'exporter';out=Path(folder)/'code.bin'
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/rob_cold_pair.c'),'-o',str(exe)],check=True)
            c=json.loads(subprocess.check_output([str(exe),*plan['conditions'][0]['args'],'--write-asm',str(out)],text=True));c.pop('export')
        info={'kernel_page_kb':4,'mmu_page_kb':4,'anon_huge_kb':0,'rss_kb':8,'swap_kb':0,'no_huge':True}
        runtime={'type':'runtime','cpu':7,'cntfrq_hz':19200000,'cache_line_bytes':64,'mapping_alignment_verified':True,'raw_self_pointer_verified':True,'code_address_mod64':0,'cache_maintenance_completed':True,'event_ids':[1,2,3,4,5,6],'initial_backing':info}
        records=[c,runtime]+[dict(type='round',**r,ticks=0,enabled=100,running=100,metrics={'0x11':100,'0x8':29,'0x3':0,'0x17':0,'0x34':0,'0x37':0}) for r in d.matrix(0,'singlecold')]+[{'type':'backing-final','backing':info}]
        d.validate(records,0,'singlecold')
        for kind in ('missing','duplicate','order','bool-flag','bool-slots','old-profile','state'):
            bad=copy.deepcopy(records)
            if kind=='missing':bad.pop(10)
            elif kind=='duplicate':bad[10]=bad[9]
            elif kind=='order':bad[10],bad[11]=bad[11],bad[10]
            elif kind=='bool-flag':bad[0]['single_cold_requested']=1
            elif kind=='bool-slots':bad[0]['state_cold_slot_masks']=[False,1,2,3]
            elif kind=='state':bad[10]['state']='first'
            with self.subTest(kind=kind),self.assertRaises(ValueError):d.validate(bad,0,'pair' if kind=='old-profile' else 'singlecold')

if __name__=='__main__':unittest.main()
