"""Actual C schedules + synthetic external counters; never target evidence."""
import copy,json,unittest
from tools.diagnostic.tests import test_rob_issue_marker as producer
from tools.diagnostic import rob_issue_marker_analysis as m
class IssueAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):producer.IssueProducer.setUpClass();cls.actual=producer.IssueProducer();cls.plans={str(k):cls.actual.plan(k) for k in (16,32)}
 @classmethod
 def tearDownClass(cls):producer.IssueProducer.tearDownClass()
 def rows(self):
  rows=[]
  for c in m.conditions('qualification'):
   k=int(c['args'][2]);p=self.plans[str(k)];runtime=dict(type='runtime',cpu=7,fpcr=0,hwcap_sb=True,code_base=1<<32,near_base=2<<32,far_base=3<<32,output_base=4<<32,pagemap_before=[(1<<63)|x for x in (10,20,30,40)],event_ids=list(range(100,106)));samples=[]
   for s in p[3:]:
    taps=s['marker']=='taps';active=taps and s['control']!='bypass';arch=m.MARKER if taps and s['control']=='architect' else 0;samples.append(dict(s,type='round',result_bits=s['test_bits'],status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8,code_base=1<<32,code_matches_plan=True,enabled=1000,running=1000,counts=[500,k+100,20+8*active,20+8*active,int(s['control']=='speculate'),4]))
   rr=[*p[:3],runtime,*samples,dict(type='final',pagemap_after=runtime['pagemap_before'][:],fds_closed=True)];rows.append(m.audit_process(rr,c,self.plans))
  return rows
 def matrix(self):return dict(mode=m.MODE,phase='qualification',processes=6,rows=self.rows())
 def test_actual_plan_positive_independent_calibration(self):
  m.validate_plan(self.plans);a=m.analyze(self.matrix());self.assertEqual((a['status'],a['windows']),('ISSUE_MARKER_QUALIFIED',864));self.assertEqual(a['processes'][0]['thresholds'],dict(near=4,far=4));self.assertFalse(a['physical_capacity_certified'])
 def test_counts_missing_bad_architecture_pfn_ids_and_words_reject(self):
  row=self.rows()[0];rr=[row['config'],*row['programs'],row['runtime'],*row['samples'],row['final']]
  for kind in ('missing','duplicate','order','words','typed','ids','pfn','alias','mux','near','far','fpsr','bits'):
   bad=copy.deepcopy(rr)
   if kind=='missing':bad.pop(4)
   elif kind=='duplicate':bad.insert(4,bad[4])
   elif kind=='order':bad[4:6]=bad[4:6][::-1]
   elif kind=='words':bad[2]['words'][21]^=1
   elif kind=='typed':bad[5]['counts'][2]=True
   elif kind=='ids':bad[3]['event_ids'][1]=bad[3]['event_ids'][0]
   elif kind=='pfn':bad[-1]['pagemap_after'][1]+=1
   elif kind=='alias':bad[3]['near_base']=bad[3]['far_base']
   elif kind=='mux':bad[5]['running']-=1
   elif kind=='near':bad[5]['near_architectural']^=1
   elif kind=='far':bad[5]['far_architectural_words'][7]^=1
   elif kind=='fpsr':bad[5]['status_raw']=1
   elif kind=='bits':bad[5]['result_bits']^=1
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(bad,m.conditions('qualification')[0],self.plans)
 def test_near_absence_or_far_absence_does_not_pass(self):
  for event in (2,3):
   x=self.matrix()
   for z in x['rows'][0]['samples']:
    if z['control']=='speculate' and z['marker']=='taps':z['counts'][event]-=8
   a=m.analyze(x);self.assertEqual(a['status'],'ISSUE_MARKER_NOT_QUALIFIED');self.assertFalse(a['processes'][0]['qualified'])
 def test_m_cannot_select_its_threshold_or_hide_unexcited_windows(self):
  x=self.matrix();row=x['rows'][0]
  for z in row['samples']:
   if z['control']=='speculate' and z['marker']=='taps' and z['trial']>=8:z['counts'][2]-=8;z['counts'][3]-=8
  a=m.analyze(x);p=a['processes'][0];self.assertEqual(p['thresholds'],dict(near=4,far=4));self.assertEqual((len(p['eligible_trials']),len(p['deltas']['speculate']['0x70'])),(8,24));self.assertEqual(p['eligible_rate'],8/24)
  for z in row['samples']:
   if z['control']=='speculate':z['counts'][4]=0
  self.assertEqual(m.analyze(x)['status'],'ISSUE_MARKER_NOT_QUALIFIED')
 def test_unsupported_zero_event_background_tail_and_arch_control_fail(self):
  for mode in ('zero','background','positive','branch'):
   x=self.matrix()
   for z in x['rows'][0]['samples']:
    if mode=='zero':z['counts'][3]=0
    elif mode=='background' and z['marker']=='taps':z['counts'][5]+=2
    elif mode=='positive' and z['control']=='architect' and z['marker']=='taps':z['counts'][2]-=8
    elif mode=='branch' and z['control']=='bypass':z['counts'][4]=1
   with self.subTest(mode=mode):self.assertEqual(m.analyze(x)['status'],'ISSUE_MARKER_NOT_QUALIFIED')
  with self.assertRaises(ValueError):m.conditions('scan')
