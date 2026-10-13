"""Actual emitter/interpreter -> registered 8-node chain; synthetic kernel/PFN only."""
import copy,json,importlib,unittest
from tools.diagnostic.tests import test_translation_persistent as producer
from tools.diagnostic.tests import test_translation_self as vm
class PersistentAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.path=producer.ROOT/'tools/diagnostic/translation_persistent_analysis.py'
  if cls.path.exists():cls.m=importlib.import_module('tools.diagnostic.translation_persistent_analysis');producer.PersistentBytecode.setUpClass();cls.p=producer.PersistentBytecode();cls.plan=cls.p.plan
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'p'):producer.PersistentBytecode.tearDownClass()
 def records(self):
  self.assertTrue(self.path.exists(),'persistent consumer missing');base=producer.VA;pf=[(1<<63)|(0xaaa+i) for i in range(8)];rr=[self.plan,dict(type='mapping',cpu=7,page_bytes=4096,nodes=8,kprobe_type=6,alias_base=base,canonical_base=2<<32,scratch_base=3<<32),dict(type='canonical-before',entries=pf)];previous=[0]*17
  for n in range(8):
   va=base+8192*n;request=[0]*16+[va];pmd=producer.PMD+8*((va>>21)&511);pte=producer.PTE+8*((va>>12)&511);root=vm.PGD+8*((va>>30)&511);memory={producer.VMF+48:(8,pmd),producer.VMF+88:(8,pte),pmd:(8,0x700003),root:(8,0x600003),pte:(8,((0xaaa+n)<<12)|3)};entry,_=self.p.evaluate('entry',va,additional_memory=memory);positive,_=self.p.evaluate('return',va,prior=entry,additional_memory=memory);pair=[pf[n],pf[n^1]];rr.append(dict(type='persistent-read',node=n,selected_va=va,node_word=0x12340000+n,cpu=7,observer_active=True,foreign=request if n==0 else None,previous=previous.copy(),initial=request.copy(),negative=request.copy(),positive=positive.copy(),canonical_before=pair.copy(),canonical_after=pair.copy(),alias_before=[0,0],alias_after=pair.copy()));previous=positive
  rr.append(dict(type='final',fds_closed=True,canonical_after=pf.copy()));return rr
 def test_complete_real_plan_bytecode_chain(self):
  r=self.records();v=self.m.audit_process(r,self.plan);self.assertEqual((v['status'],v['captures']),('OWNED_PERSISTENT_DESCRIPTOR_READ',8));self.assertFalse(v['physical_entries_certified'])
 def test_missing_duplicate_order_request_foreign_sticky_and_identity_refuse(self):
  for kind in ('missing','duplicate','order','request','foreign','sticky','pid','root','pfn','word','typed','fd','prior','extra'):
   r=copy.deepcopy(self.records())
   if kind=='missing':r.pop(3)
   elif kind=='duplicate':r[3]=r[4]
   elif kind=='order':r[3:5]=r[3:5][::-1]
   elif kind=='request':r[4]['positive'][16]+=4096
   elif kind=='foreign':r[3]['foreign'][0]=1
   elif kind=='sticky':r[3]['positive'][13]=1
   elif kind=='pid':r[3]['positive'][3]+=1
   elif kind=='root':r[3]['positive'][11]+=4096
   elif kind=='pfn':r[-1]['canonical_after'][0]+=1
   elif kind=='word':r[3]['node_word']+=1
   elif kind=='typed':r[3]['positive'][1]=True
   elif kind=='fd':r[-1]['fds_closed']=False
   elif kind=='prior':r[4]['previous'][0]=99
   elif kind=='extra':r.append(r[-1])
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.m.audit_process(r,self.plan)
 def test_first_empty_stops_and_cannot_skip_to_later_node(self):
  r=self.records();r[3]['positive']=r[3]['initial'].copy();r=r[:4]+[dict(type='stop',reason='not-excited',captures=1)];self.assertEqual(self.m.audit_process(r,self.plan)['status'],'NOT_EXCITED')
  r.insert(4,self.records()[4])
  with self.assertRaises(ValueError):self.m.audit_process(r,self.plan)
if __name__=='__main__':unittest.main()
