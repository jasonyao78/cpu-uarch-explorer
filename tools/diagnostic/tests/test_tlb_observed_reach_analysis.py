"""Actual C layout/BPF plans -> interpreted own descriptors; synthetic PMU only."""
import copy,importlib,json,subprocess,unittest
from tools.diagnostic.tests import test_tlb_observed_reach as producer
from tools.diagnostic.tests import test_translation_self as vm
class ObservedReachAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.path=producer.ROOT/'tools/diagnostic/tlb_observed_reach_analysis.py'
  if cls.path.exists():cls.m=importlib.import_module('tools.diagnostic.tlb_observed_reach_analysis');producer.ObservedReachProducer.setUpClass();cls.p=producer.ObservedReachProducer();cls.plans={f'{n}:{r}':cls.p.plan(n,r) for n in (32,1024,1536,1792,2048,2304) for r in (0,1)}
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'p'):producer.ObservedReachProducer.tearDownClass()
 def record(self,c,pid=12345):
  self.assertTrue(self.path.exists(),'observed graph consumer missing');n=int(c['args'][2]);rev=int(c['args'][4]);cfg=self.plans[f'{n}:{rev}'];program=json.loads(subprocess.check_output([str(self.p.binary),'--bpf-plan',str(pid),'7'],text=True));bases=[1<<33,(1<<33)+(1<<30)];pf=[(1<<63)|(0xaaa+i) for i in range(n)];rr=[cfg,program,dict(type='mapping',cpu=7,page_bytes=4096,nodes=n,kprobe_type=6,bases=bases,canonical_base=1<<38,scratch_base=(1<<38)+(1<<30)),dict(type='canonical-before',entries=pf.copy())];previous=[0]*17
  for position in range(2):
   shape=1-position if rev else position
   for node in range(n):
    capture=position*n+node;va=bases[shape]+cfg['strides'][shape]*node;request=[0]*16+[va];bias=0xffff000000000000;rootidx=(va>>30)&511;pmdpa=0x200000+rootidx*4096;ptpa=0x400000+(va>>21)*4096;pmd=bias+pmdpa+8*((va>>21)&511);pte=bias+ptpa+8*((va>>12)&511);vmf=0x90000;root=vm.PGD+8*rootidx;memory={vmf+48:(8,pmd),vmf+88:(8,pte),pmd:(8,ptpa|3),root:(8,pmdpa|3),pte:(8,((0xaaa+node)<<12)|3)};args=dict(pid=pid,context_fields={0:vmf,16:va},additional_memory=memory,allowed_reads=[(vmf+48,8),(vmf+88,8),(pmd,8),(vm.TASK+1440,8),(vm.MM+56,8),(root,8),(pte,8)],output_words=17);entry,_=vm.interpret(program['entry_instructions'],prior=request,**args);positive,_=vm.interpret(program['return_instructions'],prior=entry,**args);pair=[pf[node],pf[node^1]];rr.append(dict(type='observed-read',capture=capture,shape=shape,node=node,selected_va=va,node_word=cfg['next'][node],cpu=7,observer_active=True,foreign=request.copy() if capture==0 else None,previous=previous.copy(),initial=request.copy(),negative=request.copy(),positive=positive.copy(),canonical_before=pair.copy(),canonical_after=pair.copy(),alias_before=[0,0],alias_after=pair.copy()));previous=positive
  rr.extend([dict(type='observer-final',fds_closed=True),dict(type='perf-runtime',cpu=7,observer_closed=True,event_ids=list(range(100,106)))]);budget=cfg['loads'];rates={32:(0,0),1024:(0,0),1536:(0,.6),1792:(0,.8),2048:(.2,.9),2304:(.9,.9)}
  def sample(phase,r,shape):
   loads=budget if phase=='data' else 0;walk=int(rates[n][shape]*loads) if loads else 0;return dict(type='round',phase=phase,round=r,shape=shape,loads=loads,cpu=7,head_returned=True,observer_closed=True,enabled=1000,running=1000,counts=[loads*20+100,loads*4+64,loads if n>32 else 0,walk,loads,0])
  rr.extend(sample('empty-before',r,-1) for r in range(3));rr.extend(sample('data',r,(r+p+rev)%2) for r in range(3) for p in range(2));rr.extend(sample('empty-after',r,-1) for r in range(3));rr.extend(dict(type='graph-final',shape=shape,entries=pf.copy(),words=cfg['next'].copy()) for shape in (0,1));rr.append(dict(type='final',fds_closed=True,canonical_after=pf.copy()));return rr,program
 def rows(self,phase):return [self.m.audit_process(*self.record(c,12345+i),c,self.plans) for i,c in enumerate(self.m.conditions(phase))]
 def test_real_plans_interpreted_binding_and_qualification(self):
  self.assertTrue(self.path.exists(),'observed graph consumer missing');rows=self.rows('qualification');a=self.m.analyze(dict(mode=self.m.MODE,phase='qualification',rows=rows));self.assertEqual(a['status'],'OBSERVED_GRAPH_QUALIFIED');self.assertEqual(a['windows'],36);self.assertFalse(a['physical_capacity_certified'])
 def test_capture_prior_request_foreign_PFN_descriptor_and_window_refuse(self):
  self.assertTrue(self.path.exists(),'observed graph consumer missing');c=self.m.conditions('qualification')[0];rr,p=self.record(c);lastcapture=4+64;firstsample=lastcapture+2
  for kind in ('missing','order','request','foreign','prior','typed','descriptor','pfn','word','observer','ids','mux','sample-order','counts','final'):
   v=copy.deepcopy(rr)
   if kind=='missing':v.pop(4)
   elif kind=='order':v[4:6]=v[4:6][::-1]
   elif kind=='request':v[4]['positive'][16]+=4096
   elif kind=='foreign':v[4]['foreign'][0]=1
   elif kind=='prior':v[5]['previous'][0]=99
   elif kind=='typed':v[4]['positive'][1]=True
   elif kind=='descriptor':v[4]['positive'][11]+=4096
   elif kind=='pfn':v[-1]['canonical_after'][0]+=1
   elif kind=='word':v[-2]['words'][0]+=1
   elif kind=='observer':v[lastcapture]['fds_closed']=False
   elif kind=='ids':v[lastcapture+1]['event_ids'][1]=v[lastcapture+1]['event_ids'][0]
   elif kind=='mux':v[firstsample]['running']=1
   elif kind=='sample-order':v[firstsample:firstsample+2]=v[firstsample:firstsample+2][::-1]
   elif kind=='counts':v[firstsample]['counts'][0]=True
   elif kind=='final':v[-1]['fds_closed']=False
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.m.audit_process(v,p,c,self.plans)
 def test_actual_data_background_fail_prevents_qualification(self):
  self.assertTrue(self.path.exists(),'observed graph consumer missing');rows=self.rows('qualification');rows[0]['samples'][3]['counts'][5]=rows[0]['config']['loads']//1000+1;self.assertEqual(self.m.analyze(dict(mode=self.m.MODE,phase='qualification',rows=rows))['status'],'OBSERVED_GRAPH_NOT_QUALIFIED')
 def test_first_no_capture_cannot_skip_and_old_plan_not_promoted(self):
  self.assertTrue(self.path.exists(),'observed graph consumer missing');c=self.m.conditions('qualification')[0];rr,p=self.record(c);rr[4]['positive']=rr[4]['initial'].copy();rr=rr[:5]+[dict(type='stop',reason='not-excited',captures=1)];self.assertEqual(self.m.audit_process(rr,p,c,self.plans)['status'],'NOT_EXCITED');rr.insert(5,self.record(c)[0][5])
  with self.assertRaises(ValueError):self.m.audit_process(rr,p,c,self.plans)
 def test_mixed_round_point_is_ambiguous_and_censoring_is_explicit(self):
  self.assertTrue(self.path.exists(),'observed graph consumer missing');f=self.m.onset
  self.assertEqual(f([dict(nodes=32,walk_rates=[0,0,0]),dict(nodes=1024,walk_rates=[0,.11,0]),dict(nodes=1536,walk_rates=[.8]*3),dict(nodes=1792,walk_rates=[.8]*3)])['status'],'ambiguous')
  self.assertEqual(f([dict(nodes=32,walk_rates=[.8]*3),dict(nodes=1024,walk_rates=[.8]*3)])['status'],'left-censored')
  self.assertEqual(f([dict(nodes=32,walk_rates=[0]*3),dict(nodes=1024,walk_rates=[.8]*3)])['status'],'right-censored')
  self.assertEqual(f([dict(nodes=32,walk_rates=[0]*3),dict(nodes=1024,walk_rates=[.8]*3),dict(nodes=1536,walk_rates=[0]*3)])['status'],'non-monotone')
if __name__=='__main__':unittest.main()
