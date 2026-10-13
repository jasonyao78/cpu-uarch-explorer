"""Actual one-shot program/plans, synthetic seven-PMU qualification and typed refusals."""
import copy,importlib,json,subprocess,unittest
from tools.diagnostic.tests import test_rob_spec_marker as producer
class SpecMarkerAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.path=producer.ROOT/'tools/diagnostic/rob_spec_marker_analysis.py'
  if cls.path.exists():
   cls.m=importlib.import_module('tools.diagnostic.rob_spec_marker_analysis');producer.SpecMarkerProducer.setUpClass();cls.actual=producer.SpecMarkerProducer();cls.plans={str(k):cls.actual.plan(k) for k in (16,32)}
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'actual'):producer.SpecMarkerProducer.tearDownClass()
 def test_registered_consumer_exists(self):self.assertTrue(self.path.exists(),'spec marker consumer missing')
 def rows(self):
  self.assertTrue(self.path.exists(),'spec marker consumer missing');rows=[]
  for c in self.m.conditions('qualification'):
   k=int(c['args'][2]);plan=self.plans[str(k)];runtime=dict(type='runtime',cpu=7,fpcr=0,hwcap_sb=True,code_base=1<<32,marker_base=2<<32,code_pagemap_before=(1<<63)|0xabc,marker_pagemap_before=(1<<63)|0xdef,event_ids=list(range(100,107)));samples=[]
   for schedule in plan[3:]:
    ctl=schedule['control'];ld=schedule['marker']=='load';spec=10+int(ld and ctl!='bypass');ret=10+int(ld and ctl=='architect');bm=int(ctl=='speculate');samples.append(dict(schedule,type='round',result_bits=schedule['test_bits'],status_raw=0,code_base=1<<32,code_matches_plan=True,enabled=1000,running=1000,counts=[500,100+k,spec,ret,bm,80+k,0]))
   rr=[*plan[:3],runtime,*samples,dict(type='final',code_pagemap_after=runtime['code_pagemap_before'],marker_pagemap_after=runtime['marker_pagemap_before'],fds_closed=True)];rows.append(self.m.audit_process(rr,c,self.plans))
  return rows
 def matrix(self):return dict(mode=self.m.MODE,phase='qualification',processes=6,rows=self.rows())
 def test_actual_plans_and_complete_positive(self):
  self.assertTrue(self.path.exists(),'spec marker consumer missing');self.m.validate_plan(self.plans);a=self.m.analyze(self.matrix());self.assertEqual((a['status'],a['windows']),('SPECULATIVE_MARKER_QUALIFIED',648));self.assertFalse(a['physical_capacity_certified'])
 def test_missing_order_type_result_code_counter_and_pfn_reject(self):
  self.assertTrue(self.path.exists(),'spec marker consumer missing');c=self.m.conditions('qualification')[0];row=self.rows()[0];rr=[row['config'],*row['programs'],row['runtime'],*row['samples'],row['final']]
  for kind in ('missing','order','typed','result','code','counter','pfn','sb'):
   bad=copy.deepcopy(rr)
   if kind=='missing':bad.pop(4)
   if kind=='order':bad[4:6]=bad[4:6][::-1]
   if kind=='typed':bad[4]['counts'][2]=True
   if kind=='result':bad[4]['result_bits']^=1
   if kind=='code':bad[2]['words'][10]^=1
   if kind=='counter':bad[3]['event_ids'][-1]=bad[3]['event_ids'][0]
   if kind=='pfn':bad[-1]['code_pagemap_after']+=1
   if kind=='sb':bad[3]['hwcap_sb']=False
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.m.audit_process(bad,c,self.plans)
 def test_failed_signals_and_training_no_capacity_scan(self):
  self.assertTrue(self.path.exists(),'spec marker consumer missing');matrix=self.matrix()
  for sample in matrix['rows'][0]['samples']:
   if sample['control']=='speculate' and sample['marker']=='load':sample['counts'][2]-=1
  self.assertEqual(self.m.analyze(matrix)['status'],'MARKER_NOT_QUALIFIED')
  matrix=self.matrix()
  for sample in matrix['rows'][0]['samples']:
   if sample['control']=='speculate':sample['counts'][4]=0
  self.assertEqual(self.m.analyze(matrix)['status'],'MARKER_NOT_QUALIFIED')
  with self.assertRaises(ValueError):self.m.conditions('scan')
if __name__=='__main__':unittest.main()
