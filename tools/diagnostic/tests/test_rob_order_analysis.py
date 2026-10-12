"""Actual plans -> complete typed windows -> registered order contrast; synthetic PMU only."""
import copy,importlib,json,unittest
from tools.diagnostic.tests import test_rob_order as fixture
class TestOrderAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  assert (fixture.ROOT/'tools/diagnostic/rob_order_analysis.py').exists(),'registered order consumer missing'
  cls.m=importlib.import_module('tools.diagnostic.rob_order_analysis');fixture.TestOrderProducer.setUpClass();cls.actual=fixture.TestOrderProducer();cls.registered={cls.m.plan_key(k,s,v):cls.actual.plan(k,s,v) for k in (16,32) for s in (False,True) for v in (False,True)}
 @classmethod
 def tearDownClass(cls):fixture.TestOrderProducer.tearDownClass()
 def rows(self,delay=29):
  rows=[]
  for c in self.m.conditions('qualification'):
   k,swap,rev=self.m.identity(c);p=self.registered[self.m.plan_key(k,swap,rev)];base=0x10000000;pm=[(1<<63)|i for i in range(10,14)];runtime=dict(type='runtime',cpu=7,fpcr=0,code_base=base,code_pagemap_before=pm,event_ids=[101,102,103,104,105,106]);rr=[]
   for schedule in p[9:]:
    cond=schedule['condition'];cycles=19 if cond//2==0 else 13*2*k+16 if cond//2==1 else 13*k+17+(delay if cond==4 and k==32 else 0) if cond//2==2 else 33
    prog=p[1+cond];ir=self.m.ITERATIONS*prog['loop_instructions']+21
    rr.append(dict(schedule,type='round',code_address=base+4096*prog['page']+prog['slot'],code_matches_plan=True,result_bits=[0x3ff0000000000000]*2,status_raw=0,gpr_result=0,ns=1000000,enabled=2000000,running=2000000,counts=[cycles*self.m.ITERATIONS,ir,ir,0,0,0]))
   records=[*p[:9],runtime,*rr,dict(type='code-final',code_base=base,code_pagemap_after=pm)]
   rows.append(self.m.audit_process(records,c,self.registered))
  return rows
 def run_fixture(self,delay=29):return dict(mode=self.m.MODE,phase='qualification',processes=12,rows=self.rows(delay))
 def test_actual_eight_plans_and_primary_positive(self):
  self.m.validate_plan(self.registered);a=self.m.analyze(self.run_fixture());self.assertEqual(a['status'],'BLOCKED_ANCHOR_ORDER_DELAY');self.assertEqual(a['windows'],768);self.assertFalse(a['physical_entries_certified'])
 def test_negative_reverse_and_mixed_are_distinct(self):
  self.assertEqual(self.m.analyze(self.run_fixture(0))['status'],'ORDER_CONTRAST_NOT_CHANGED_AT_REGISTERED_MEDIAN_SCALE');self.assertEqual(self.m.analyze(self.run_fixture(-29))['status'],'INTERLEAVED_ANCHOR_ORDER_DELAY');self.assertEqual(self.m.analyze(self.run_fixture(5))['status'],'INCONCLUSIVE')
 def test_types_order_code_pfn_results_and_window_coverage_reject(self):
  c=self.m.conditions('qualification')[0];row=self.rows()[0];records=[row['config'],*row['programs'],row['runtime'],*row['samples'],row['final']]
  for kind in ('window-order','window-missing','pfn-migration','same-page','result','typed','mux','code','slot'):
   bad=copy.deepcopy(records)
   if kind=='window-order':bad[-3:-1]=bad[-3:-1][::-1]
   if kind=='window-missing':bad.pop(10)
   if kind=='pfn-migration':bad[-1]['code_pagemap_after'][0]+=1
   if kind=='same-page':bad[9]['code_pagemap_before'][1]=bad[9]['code_pagemap_before'][0]
   if kind=='result':bad[10]['result_bits'][0]=0
   if kind=='typed':bad[10]['counts'][0]=True
   if kind=='mux':bad[10]['running']=1
   if kind=='code':bad[5]['words'][16]^=1
   if kind=='slot':bad[10]['code_address']+=2048
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.m.audit_process(bad,c,self.registered)
 def test_gate_failure_not_rescued_and_no_scan(self):
  run=self.run_fixture();run['rows'][0]['samples'][0]['counts'][5]=self.m.ITERATIONS//1000+1;self.assertEqual(self.m.analyze(run)['status'],'CONTROL_NOT_QUALIFIED')
  with self.assertRaises(ValueError):self.m.conditions('scan')
if __name__=='__main__':unittest.main()
