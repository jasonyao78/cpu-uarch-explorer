"""Four-state mathematics: synthetic only; actual C/transport tested separately."""
import copy
import itertools
import math
import unittest
from unittest.mock import patch
try:
    from tools.diagnostic import analyze_cold_state as model
except ImportError:
    model=None
STATES=('hot','first-cold','second-cold','cold')
BASE=list(itertools.product((0,4096),(0,1),('P','S','E'),STATES))

def synthetic_run():
    rows=[]
    for e in (0,1):
        for t in range(64):
            order=BASE[t%48:]+BASE[:t%48]
            if (e+t)%2:order.reverse()
            for m,s,u,state in order:
                i=STATES.index(state);miss=(0,1,1,2)[i] if u!='E' else 0
                ticks=1 if u=='E' else (1,11,15,15 if u=='P' else 25)[i]
                counts={'0x11':200,'0x8':92,'0x3':miss,'0x17':miss,'0x34':0,'0x37':miss}
                rows.append(dict(epoch=e,trial=t,mask=m,swap=s,member=u,state=state,ticks=ticks,counts=counts))
    return dict(mode='rob-cold-state',processes=2,rows=rows)

def select(run,**keys):return [r for r in run['rows'] if all(r[k]==v for k,v in keys.items())]

class ColdStateTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(model,'four-state consumer missing')
    def test_fixed_full_order_and_plan(self):
        from tools.diagnostic import run_sm8650_cold_pair as d
        self.assertEqual(model.registered_plan(),d.plan('singlecold'))
        self.assertEqual(model.trial_order(0,0),BASE)
        self.assertEqual(model.trial_order(1,0),BASE[::-1])
        self.assertEqual(len(model.audit_cells(synthetic_run())),6144)
    def test_gold_same_code_model_and_no_scan(self):
        result=model.analyze(synthetic_run())
        self.assertEqual(result['windows'],6144);self.assertFalse(result['n_scan_authorized'])
        self.assertNotIn('qualified_masks',result);self.assertEqual(len(result['candidates']),8)
        for c in result['candidates']:
            self.assertTrue(c['stimulus_passed']);self.assertTrue(c['model_compatible'])
            for m in ('P','S'):self.assertEqual(c['residuals'][m]['values'],[0]*64)
    def test_serial_negative_residual_kept_and_cell_not_rescued(self):
        run=synthetic_run()
        for r in select(run,epoch=0,mask=0,swap=0,member='S',state='cold'):r['ticks']=18
        result=model.analyze(run);c=result['candidates'][0]
        self.assertEqual(c['residuals']['S']['values'],[-7]*64)
        self.assertFalse(c['model_compatible']);self.assertEqual(sum(c['model_compatible'] for c in result['candidates']),7)
    def test_parallel_max_before_subtraction_and_serial_hot_base(self):
        run=synthetic_run()
        for r in run['rows']:
            if r['member']=='P':r['ticks']=(9,10,11,11)[STATES.index(r['state'])]
            if r['member']=='S':r['ticks']=(9,19,23,33)[STATES.index(r['state'])]
        c=model.analyze(run)['candidates'][0]
        self.assertEqual(c['residuals']['P']['values'],[0]*64)
        self.assertEqual(c['residuals']['S']['values'],[0]*64)
    def test_closed_band_and_negative_q90_tail(self):
        run=synthetic_run()
        for r in select(run,member='S',state='cold'):r['ticks']+=1 if r['trial']<32 else 3
        c=model.analyze(run)['candidates'][0];self.assertTrue(c['model_compatible'])
        self.assertEqual(c['residuals']['S']['median'],2);self.assertEqual(c['residuals']['S']['abs_q90'],3)
        for r in select(run,member='P',state='cold'):r['ticks']-=4 if r['trial']>=56 else 0
        c=model.analyze(run)['candidates'][0];self.assertFalse(c['model_compatible'])
        self.assertEqual(c['residuals']['P']['abs_q90'],4)
        self.assertAlmostEqual(model.describe(list(range(64)))['q90'],56.7)
    def test_empty_sentinel_not_subtracted_from_model_or_counts(self):
        run=synthetic_run()
        for r in select(run,member='E',state='first-cold'):r['ticks']=5;r['counts']['0x17']=2
        c=model.analyze(run)['candidates'][0]
        self.assertFalse(c['stimulus_passed']);self.assertTrue(c['model_compatible'])
        self.assertEqual(c['members']['P']['first-cold']['count_delta_means']['0x17'],1)
    def test_hot_raw_refills_gate_and_l1_disclosure_only(self):
        run=synthetic_run()
        for r in select(run,member='P'):r['counts']['0x3']=99
        self.assertTrue(model.analyze(run)['candidates'][0]['stimulus_passed'])
        for r in select(run,member='P'):r['counts']['0x17']+=1;r['counts']['0x37']+=1
        c=model.analyze(run)['candidates'][0];self.assertFalse(c['stimulus_passed'])
        self.assertIn('P.hot.LL_count_mean',c['failed_gates'])
    def test_zero_ticks_signed_differences_and_negative_walk_fail(self):
        run=synthetic_run()
        for r in select(run,member='P',state='first-cold'):r['ticks']=0
        for r in select(run,member='P',state='hot'):r['counts']['0x34']=1
        c=model.analyze(run)['candidates'][0]
        self.assertEqual(c['members']['P']['first-cold']['delta_ticks']['values'],[-1]*64)
        self.assertFalse(c['stimulus_passed']);self.assertIn('P.first-cold.walk_count_delta_abs_mean',c['failed_gates'])
    def test_missing_duplicate_order_oldprofile_and_type_fail(self):
        for kind in ('missing','duplicate','order','profile'):
            run=synthetic_run()
            if kind=='missing':run['rows'].pop()
            elif kind=='duplicate':run['rows'][1]=run['rows'][0]
            elif kind=='order':run['rows'][0:2]=run['rows'][0:2][::-1]
            else:run['mode']='rob-cold-load-model'
            with self.subTest(kind=kind),self.assertRaises(ValueError):model.analyze(run)
        for key,v in [('epoch',False),('trial',64),('mask',True),('swap',True),('state','first'),('ticks',True),('ticks',-1),('ticks',2**64),('ticks',math.nan)]:
            run=synthetic_run();run['rows'][0][key]=v
            with self.subTest(key=key,v=v),self.assertRaises(ValueError):model.analyze(run)
        for event,v in [('0x37',True),('0x11',0),('0x8',28)]:
            run=synthetic_run();run['rows'][0]['counts'][event]=v
            with self.subTest(event=event,v=v),self.assertRaises(ValueError):model.analyze(run)
    def test_every_threshold_consumed(self):
        cases=[('model_residual_median_abs_max',0,'S.residual_abs_median'),('model_residual_abs_q90_max',0,'S.residual_abs_q90'),('delta_ticks_median_min',11,'P.first-cold.delta_ticks_median'),('single_refill_delta_mean',[1.01,2],'P.first-cold.LL_count_delta_mean'),('both_refill_delta_mean',[2.01,3],'P.cold.LL_count_delta_mean'),('walk_delta_mean_abs_max',0,'P.first-cold.walk_count_delta_abs_mean'),('hot_refill_mean_max',0,'P.hot.LL_count_mean'),('empty_delta_median_abs_max',0,'E.first-cold.delta_ticks_abs_median'),('empty_delta_abs_q90_max',0,'E.first-cold.delta_ticks_abs_q90'),('empty_count_delta_abs_mean_max',0,'E.first-cold.LL_count_delta_abs_mean')]
        for key,value,gate in cases:
            run=synthetic_run()
            if key.startswith('model_'):
                for r in select(run,member='S',state='cold'):r['ticks']+=1
            if key.startswith('empty_'):
                for r in select(run,member='E',state='first-cold'):r['ticks']+=1;r['counts']['0x37']=int(r['trial']<16)
            if key=='walk_delta_mean_abs_max':
                for r in select(run,member='P',state='first-cold'):r['counts']['0x34']=int(r['trial']<6)
            if key=='hot_refill_mean_max':
                for r in select(run,member='P'):r['counts']['0x37']+=int(r['trial']<16)
            self.assertNotIn(gate,model.analyze(run)['candidates'][0]['failed_gates'])
            limits=copy.deepcopy(model.THRESHOLDS);limits[key]=value
            with self.subTest(key=key),patch.object(model,'THRESHOLDS',limits):self.assertIn(gate,model.analyze(run)['candidates'][0]['failed_gates'])

class ActualColdStateConfig(unittest.TestCase):
    def test_real_c_config_matches_consumer_not_hand_written(self):
        import json
        from pathlib import Path
        import subprocess
        import tempfile
        from tools.diagnostic import run_sm8650_cold_pair as d
        root=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as folder:
            exe=Path(folder)/'producer';out=Path(folder)/'code.bin'
            subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(root/'probes/common'),str(root/'probes/diagnostic/rob_cold_pair.c'),'-o',str(exe)],check=True)
            for epoch in (0,1):
                c=json.loads(subprocess.check_output([str(exe),*d.plan('singlecold')['conditions'][epoch]['args'],'--write-asm',str(out)],text=True));c.pop('export')
                self.assertEqual(c,model._config(epoch))

if __name__=='__main__':unittest.main()
