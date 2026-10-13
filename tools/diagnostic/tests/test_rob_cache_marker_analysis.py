"""Actual C plans and synthetic cache/timer state; never hardware evidence."""
import copy,importlib,unittest
from tools.diagnostic.tests import test_rob_cache_marker as producer
class CacheMarkerAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.path=producer.ROOT/'tools/diagnostic/rob_cache_marker_analysis.py'
  if cls.path.exists():
   cls.m=importlib.import_module('tools.diagnostic.rob_cache_marker_analysis');producer.CacheMarkerProducer.setUpClass();cls.actual=producer.CacheMarkerProducer();cls.plans={str(k):cls.actual.plan(k) for k in (16,32)}
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'actual'):producer.CacheMarkerProducer.tearDownClass()
 def rows(self):
  self.assertTrue(self.path.exists(),'cache marker consumer missing');rows=[]
  for c in self.m.conditions('qualification'):
   k=int(c['args'][2]);plan=self.plans[str(k)];runtime=dict(type='runtime',cpu=7,fpcr=0,hwcap_sb=True,dc_timer_available=True,cntfrq=19200000,ctr_el0=0x8444c004,addresses=[i<<32 for i in (1,2,3)],pagemap_before=[(1<<63)|v for v in (0xabc,0xdef,0x123)]);samples=[]
   for s in plan[3:]:
    hit=s['control']=='cal-hot' or s['control'] in ('architect','speculate') and s['marker']=='load';a=self.m.MARKER if s['control']=='architect' and s['marker']=='load' else 0;samples.append(dict(s,type='round',result_bits=s['test_bits'],status_raw=0,architectural_marker=a,probe_word=self.m.MARKER,ticks=2 if hit else 10,code_matches_plan=True,code_base=1<<32))
   rr=[*plan[:3],runtime,*samples,dict(type='final',pagemap_after=list(runtime['pagemap_before']),fds_closed=True)];rows.append(self.m.audit_process(rr,c,self.plans))
  return rows
 def matrix(self):return dict(mode=self.m.MODE,phase='qualification',processes=6,rows=self.rows())
 def test_actual_C_and_positive_calibration_only_threshold(self):
  a=self.m.analyze(self.matrix());self.assertEqual((a['status'],a['windows']),('CACHE_SPECULATIVE_MARKER_QUALIFIED',1536));self.assertTrue(all(z['threshold_ticks']==6 for z in a['processes']));self.assertFalse(a['physical_capacity_certified'])
 def test_missing_duplicate_order_typed_marker_PFN_refuses(self):
  r=self.rows()[0];rr=[r['config'],*r['programs'],r['runtime'],*r['samples'],r['final']]
  for kind in ('missing','duplicate','order','typed','marker','pfn','word','timer','address'):
   v=copy.deepcopy(rr)
   if kind=='missing':v.pop(4)
   elif kind=='duplicate':v[4]=v[5]
   elif kind=='order':v[4:6]=v[4:6][::-1]
   elif kind=='typed':v[4]['ticks']=True
   elif kind=='marker':v[4]['architectural_marker']=self.m.MARKER
   elif kind=='pfn':v[-1]['pagemap_after'][0]+=1
   elif kind=='word':v[1]['words'][0]^=1
   elif kind=='timer':v[3]['cntfrq']=0
   elif kind=='address':v[3]['addresses'][1]=v[3]['addresses'][0]
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.m.audit_process(v,self.m.conditions('qualification')[0],self.plans)
 def test_uncalibrated_wrong_path_and_noop_hit_cannot_pass(self):
  for kind in ('calibration','not-executed','noop-hit'):
   r=self.matrix()
   for s in r['rows'][0]['samples']:
    if kind=='calibration' and s['control']=='cal-cold':s['ticks']=3
    elif kind=='not-executed' and s['control']=='speculate' and s['marker']=='load':s['ticks']=10
    elif kind=='noop-hit' and s['control']=='speculate' and s['marker']=='nop':s['ticks']=2
   with self.subTest(kind=kind):self.assertEqual(self.m.analyze(r)['status'],'CACHE_MARKER_NOT_QUALIFIED')
  with self.assertRaises(ValueError):self.m.conditions('scan')
if __name__=='__main__':unittest.main()
