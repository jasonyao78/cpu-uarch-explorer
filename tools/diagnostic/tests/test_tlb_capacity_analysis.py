"""Production-plan capacity contracts; synthetic counts are software evidence.

The current C++ producer exports both matrices. Geometry uses the existing real
history collector fixture because capacity calls that same production selector.
No fabricated PMU/backing value here is a device measurement.
"""
import copy
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from tools.diagnostic.tests import test_tlb_history_analysis as geometry_fixture

ROOT = Path(__file__).resolve().parents[3]
try:
    analysis = importlib.import_module('tools.diagnostic.tlb_capacity_analysis')
except ModuleNotFoundError:
    analysis = None


class ProductionCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        geometry_fixture.ProductionPlan.setUpClass.__func__(cls)
        compiler = shutil.which('clang++') or shutil.which('g++')
        exe = Path(cls.tmp.name)/'capacity-host'
        subprocess.run([compiler,'-std=c++17','-O2','-I',str(ROOT/'probes/common'),
                        str(ROOT/'probes/diagnostic/tlb_capacity.cpp'),'-o',str(exe)],check=True)
        cls.plan = {key:[json.loads(line) for line in subprocess.check_output(
            [str(exe),'--plan',*(['--reverse'] if reverse else [])],text=True).splitlines()]
            for reverse,key in ((False,'forward'),(True,'reverse'))}

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def api(self):
        self.assertIsNotNone(analysis,'TLB capacity audit and analysis are not implemented')
        return analysis

    @staticmethod
    def default_count(cell,index,epoch):
        if cell['kind']==0 or cell['f']==0 or cell['h']==2: return 0
        if cell['kind']==1: return 2 if cell['w']>=9 else 0
        return int(cell['k']>=8)

    def raw(self,reverse=False,count=None,epoch=0):
        plan = self.plan['reverse' if reverse else 'forward']
        rows = [copy.deepcopy(plan[0]),copy.deepcopy(self.geometry)]
        count = count or self.default_count
        for cell in plan[1:]:
            for stage in ('before','after'):
                rows.append({'type':'backing','cell':cell['cell'],'stage':stage,'base_page_bytes':4096,'anon_huge_kb':0})
            for index in range(cell['rounds']):
                row = {k:v for k,v in cell.items() if k not in ('type','rounds')}
                walk = count(cell,index,epoch)
                row.update(type='round',round=index,trial_position=0,enabled=1000,running=1000,
                           counts=[100,walk,walk,walk+1,walk,0])
                rows.append(row)
        return rows

    def run_data(self,count=None):
        rows = []
        for epoch in range(5):
            cells = self.api().audit_capacity(self.raw(bool(epoch%2),count,epoch),bool(epoch%2),self.plan)
            rows.extend(dict(c,epoch=f'epoch-{epoch}') for c in cells)
        return {'mode':'tlb-capacity','tlb_target':100,'processes':5,'rows':rows}

    def test_real_plan_complete_forward_reverse_and_public_only(self):
        frozen = ROOT/'docs/reviews/evidence/2026-10-09-tlb-capacity/plan.json'
        self.assertTrue(frozen.is_file(),'registered production plan is required')
        self.assertEqual(self.plan,json.loads(frozen.read_text()))
        for reverse in (False,True):
            cells = self.api().audit_capacity(self.raw(reverse),reverse,self.plan)
            self.assertEqual(len(cells),94)
            self.assertEqual(sum(len(c['samples']) for c in cells),2080)
            self.assertEqual([c['cell'] for c in cells],[c['cell'] for c in self.plan['reverse' if reverse else 'forward'][1:]])
            for key in ('pool_base','target_pages','filler_pages',str(self.geometry['pool_base'])):
                self.assertNotIn(key,json.dumps(cells))

    def test_plan_metadata_missing_duplicate_and_physical_order_rejected(self):
        for mutation in ('missing','duplicate','unknown','failure','metadata','order','backing','geometry','plan'):
            rows = self.raw(); plan = copy.deepcopy(self.plan)
            if mutation=='missing': rows.pop()
            if mutation=='duplicate': rows.append(copy.deepcopy(rows[-1]))
            if mutation=='unknown': rows[-1]={'type':'unknown'}
            if mutation=='failure': rows[-1]={'type':'failure','metrics':{},'failure':{'reason':'synthetic'}}
            if mutation=='metadata': next(r for r in rows if r['type']=='round')['k']=1
            if mutation=='order':
                indices=[i for i,r in enumerate(rows) if r['type']=='round']; rows[indices[0]],rows[indices[16]]=rows[indices[16]],rows[indices[0]]
            if mutation=='backing': rows[2]['cell']='wrong'
            if mutation=='geometry': rows[1]['target_pages'][0].reverse()
            if mutation=='plan': plan['forward'][2]=copy.deepcopy(plan['forward'][1])
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError): self.api().audit_capacity(rows,False,plan)

    def test_new_victim_samples_reject_old_latin_metadata(self):
        for field,value in (('round',1),('victim',1),('trial_position',1),('w',8),('k',12),('direction',2)):
            rows=self.raw(); sample=next(r for r in rows if r['type']=='round' and r['kind']==2); sample[field]=value
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.api().audit_capacity(rows,False,self.plan)

    def test_config_counts_mux_and_backing_rejected(self):
        for field,value in (('link_slots',4),('cells',38),('windows',800),('reverse',True),('seed',42)):
            rows=self.raw(); rows[0][field]=value
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.api().audit_capacity(rows,False,self.plan)
        for field,value in (('enabled',0),('running',999),('counts',[1]*5),('counts',[1,0,0,0,-1,0]),('counts',[True]*6)):
            rows=self.raw(); next(r for r in rows if r['type']=='round')[field]=value
            with self.subTest(field=field):
                with self.assertRaises(ValueError): self.api().audit_capacity(rows,False,self.plan)
        rows=self.raw(); rows[2]['anon_huge_kb']=2048
        with self.assertRaises(ValueError): self.api().audit_capacity(rows,False,self.plan)

    def test_bounded_intervals_require_same_epoch_both_orders(self):
        result=self.api().analyze_capacity(self.run_data())
        self.assertTrue(result['working_set_joint']['passed'])
        self.assertEqual(result['working_set_joint']['interval'],[8,9])
        self.assertTrue(result['victim_joint']['passed'])
        self.assertEqual(result['victim_joint']['interval'],[7,8])
        self.assertEqual(len(result['trajectory']),200)
        self.assertEqual(len(result['victim_cells']),240)
        self.assertEqual(result['windows'],10400)
        def mismatched(cell,index,epoch):
            if cell['kind']==1 and cell['f']==128 and cell['h']==1:
                threshold=10 if (epoch,cell['direction']) in ((0,0),(4,1)) else 9
                return 2 if cell['w']>=threshold else 0
            if cell['kind']==2 and cell['h']==1:
                threshold=9 if (epoch,cell['direction']) in ((0,0),(4,1)) else 8
                return int(cell['k']>=threshold)
            return self.default_count(cell,index,epoch)
        result=self.api().analyze_capacity(self.run_data(mismatched))
        self.assertFalse(result['working_set_joint']['passed']); self.assertFalse(result['victim_joint']['passed'])
        self.assertEqual(max(c['epochs'] for c in result['working_set_joint']['interval_counts']),3)

    def test_working_set_tail_and_three_point_stability(self):
        def count(cell,index,epoch):
            value=self.default_count(cell,index,epoch)
            if cell['kind']==1 and cell['f']==128:
                if index<16: return 8
                if cell['w']==6 and index>=24: return value+1
            return value
        result=self.api().analyze_capacity(self.run_data(count))
        self.assertTrue(result['working_set_joint']['passed'])
        curve=next(c for c in result['working_set'] if c['f']==128)
        self.assertFalse(curve['all_points_stable']); self.assertTrue(curve['interval_points_stable'])
        self.assertEqual(curve['points'][0]['a_drift'],1)
        def unstable(cell,index,epoch):
            value=self.default_count(cell,index,epoch)
            if cell['kind']==1 and cell['f']==128 and cell['w']==8 and cell['h']==1 and index>=24:
                return int(index<29)
            return value
        result=self.api().analyze_capacity(self.run_data(unstable))
        self.assertFalse(result['working_set_joint']['passed'])
        self.assertTrue(all('preparation-drift' in c['issues'] for c in result['working_set'] if c['f']==128))

    def test_left_right_and_no_response_are_censored(self):
        for threshold,status in ((6,'left-censored'),(12,'right-end-unconfirmed'),(99,'no-response-observed')):
            def count(cell,index,epoch):
                if cell['kind']==1 and cell['f']==128 and cell['h']==1: return 2 if cell['w']>=threshold else 0
                return self.default_count(cell,index,epoch)
            result=self.api().analyze_capacity(self.run_data(count))
            self.assertFalse(result['working_set_joint']['passed'])
            self.assertEqual({c['status'] for c in result['working_set'] if c['f']==128},{status})
            self.assertEqual(result['working_set_joint']['consistent_censoring'][0]['epochs'],5)
            if status=='no-response-observed':
                for curve in result['working_set']:
                    if curve['f']==128: self.assertEqual(curve.get('threshold_returns'),[])

    def test_threshold_return_blocks_but_small_above_threshold_drop_does_not(self):
        def returned(cell,index,epoch):
            value=self.default_count(cell,index,epoch)
            if cell['h']==1 and ((cell['kind']==1 and cell['w']==11) or (cell['kind']==2 and cell['k']==10)): return 0
            return value
        result=self.api().analyze_capacity(self.run_data(returned))
        self.assertFalse(result['working_set_joint']['passed']); self.assertFalse(result['victim_joint']['passed'])
        self.assertTrue(all('nonmonotonic-response-return' in c['issues'] for c in result['victim_response']))
        def small_drop(cell,index,epoch):
            value=self.default_count(cell,index,epoch)
            if cell['kind']==2 and cell['h']==1 and cell['k']>=9: return int(index%4!=0)
            return value
        result=self.api().analyze_capacity(self.run_data(small_drop))
        self.assertTrue(result['victim_joint']['passed'])
        self.assertTrue(all(c['adjacent_decreases'] for c in result['victim_response']))

    def test_victim_whole_curve_contamination_drift_and_multiple_walks(self):
        for issue in ('baseline-contamination','preparation-drift','single-load-window-residual'):
            def count(cell,index,epoch):
                if cell['kind']==2 and cell['h']==1:
                    if issue=='baseline-contamination' and cell['k']==0: return int(index%4==0)
                    if issue=='preparation-drift' and cell['k']==2: return int(index<5)
                    if issue=='single-load-window-residual' and cell['k']==2 and index==0: return 2
                return self.default_count(cell,index,epoch)
            result=self.api().analyze_capacity(self.run_data(count))
            self.assertFalse(result['victim_joint']['passed'])
            self.assertTrue(all(issue in c['issues'] for c in result['victim_response']))
        def boundary(cell,index,epoch):
            if cell['kind']==2 and cell['h']==1 and cell['k']==0: return int(index<2)
            return self.default_count(cell,index,epoch)
        self.assertTrue(self.api().analyze_capacity(self.run_data(boundary))['victim_joint']['passed'])

    def test_public_missing_duplicate_relabeling_and_order(self):
        original=self.run_data(); expected=self.api().analyze_capacity(original)
        shuffled=copy.deepcopy(original); shuffled['rows'].reverse()
        self.assertEqual(self.api().analyze_capacity(shuffled),expected)
        for mutation in ('missing','duplicate','epoch','target','mode','sample','metadata'):
            run=copy.deepcopy(original)
            if mutation=='missing': run['rows'].pop()
            if mutation=='duplicate': run['rows'][-1]=copy.deepcopy(run['rows'][0])
            if mutation=='epoch': run['rows'][0]['epoch']='epoch-5'
            if mutation=='target': run['tlb_target']=200
            if mutation=='mode': run['mode']='tlb-history'
            if mutation=='sample': run['rows'][0]['samples'].pop()
            if mutation=='metadata': run['rows'][0]['k']=1
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError): self.api().analyze_capacity(run)

    def test_four_joint_epochs_pass_without_pooling_the_conflicting_fifth(self):
        def count(cell,index,epoch):
            if epoch==4 and cell['h']==1:
                if cell['kind']==1 and cell['f']==128: return 2 if cell['w']>=10 else 0
                if cell['kind']==2: return int(cell['k']>=9)
            return self.default_count(cell,index,epoch)
        result=self.api().analyze_capacity(self.run_data(count))
        self.assertTrue(result['working_set_joint']['passed']); self.assertTrue(result['victim_joint']['passed'])
        self.assertEqual(result['working_set_joint']['interval'],[8,9])
        self.assertEqual(result['victim_joint']['interval'],[7,8])
        self.assertEqual(result['working_set_joint']['epoch_results'][-1]['interval'],[9,10])

    def test_inclusive_working_set_and_victim_threshold_boundaries(self):
        def count(cell,index,epoch):
            value=self.default_count(cell,index,epoch)
            if cell['kind']==1 and cell['f']==128 and cell['h']==1:
                if cell['w']==8 and index>=24: return int(index<28)  # drift=.5, late difference=.5
                if cell['w']>=9: return 1  # Both high points are exactly 1.
            if cell['kind']==2 and cell['h']==1:
                if cell['k']==7: return int(index%2==0 and index!=0)  # 7/16=.4375, drift=.125
                if cell['k']>=8: return int(index%2==0)  # .5, with equal halves
            return value
        result=self.api().analyze_capacity(self.run_data(count))
        self.assertTrue(result['working_set_joint']['passed']); self.assertTrue(result['victim_joint']['passed'])

    def test_c_family_contamination_drift_and_residual_also_block_the_curve(self):
        for issue in ('baseline-contamination','preparation-drift','single-load-window-residual'):
            def count(cell,index,epoch):
                if cell['kind']==2 and cell['h']==2:
                    if issue=='baseline-contamination' and cell['k']==0: return int(index in (0,1,8))
                    if issue=='preparation-drift' and cell['k']==1: return int(index<5)
                    if issue=='single-load-window-residual' and cell['k']==1 and index==0: return 2
                return self.default_count(cell,index,epoch)
            result=self.api().analyze_capacity(self.run_data(count))
            self.assertFalse(result['victim_joint']['passed'])
            self.assertTrue(all(issue in c['issues'] for c in result['victim_response']))

    def test_nonzero_background_positions_are_not_hidden(self):
        run=self.run_data()
        floor=next(c for c in run['rows'] if c['kind']==0)
        floor['samples'][0]['counts'][2]=1; floor['samples'][0]['counts'][4]=1
        trace=next(c for c in run['rows'] if c['kind']==1)
        trace['samples'][3]['counts'][5]=1; trace['samples'][3]['counts'][2]+=1
        result=self.api().analyze_capacity(run)
        self.assertEqual(result['diagnostics']['floor_nonzero'],[
            {'epoch':floor['epoch'],'cell':floor['cell'],'round':0,'counts':floor['samples'][0]['counts']}])
        self.assertEqual(result['diagnostics']['iwalk_nonzero'][0]['round'],3)
        self.assertTrue(result['diagnostics']['all_windows_l2_equals_data_plus_instruction'])


if __name__=='__main__': unittest.main()
