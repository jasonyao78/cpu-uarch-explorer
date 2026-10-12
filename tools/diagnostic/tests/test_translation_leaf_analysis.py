"""Actual leaf plan+VM output through writer/reader; simulated helper data is software only."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
from tools.diagnostic.tests import test_translation_leaf as fixture
class TestLeafAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  assert (fixture.ROOT/'tools/diagnostic/translation_leaf_analysis.py').exists(),'registered leaf consumer missing'
  cls.model=importlib.import_module('tools.diagnostic.translation_leaf_analysis');fixture.TestLeafBytecode.setUpClass();cls.actual=fixture.TestLeafBytecode();cls.plan=fixture.TestLeafBytecode.plan
 @classmethod
 def tearDownClass(cls):fixture.TestLeafBytecode.tearDownClass()
 def record(self):
  output,_=self.actual.interpret();entries=[(1<<63)|0xaaa,(1<<63)|0xbbb]
  return dict(type='leaf-read',cpu=7,page_bytes=4096,kprobe_type=7,program=self.plan,initial=[0]*8,negative=[0]*8,positive=output,pagemap_before=entries,pagemap_after=entries[:],fds_closed=True)
 def test_actual_plan_writer_loader(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'probe.stdout.jsonl';p.write_text(json.dumps(self.record())+'\n');d=self.model.audit_process([json.loads(p.read_text())],self.plan);self.assertEqual(d['status'],'SELF_LEAF_DESCRIPTOR_READ');self.assertEqual(d['observed_cont_scope'],'COW-trigger-entry-only')
 def test_not_excited_is_named_and_not_positive(self):
  r=self.record();r['positive']=[0]*8;self.assertEqual(self.model.audit_process([r],self.plan)['status'],'NOT_EXCITED')
 def test_identity_types_negative_capture_and_partial_failure(self):
  for kind in ('pfn','wire-swap','migration','negative','hit-duplicate','type','partial','wrong-va'):
   r=self.record()
   if kind=='pfn':r['positive'][3]+=4096
   elif kind=='wire-swap':r['pagemap_after'][0]|=1<<62
   elif kind=='migration':r['pagemap_after'][0]+=1
   elif kind=='negative':r['negative'][6]=1
   elif kind=='hit-duplicate':r['positive'][6]=2
   elif kind=='type':r['positive'][6]=True
   elif kind=='partial':r['positive'][0]=1;r['positive'][5]=(1<<64)-14
   elif kind=='wrong-va':r['positive'][1]+=4096
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.model.audit_process([r],self.plan)
 def test_permission_denial_and_missing_extra_records(self):
  d=dict(type='failure',metrics={},failure=dict(reason='perf-kprobe-open',errno=1));self.assertEqual(self.model.audit_process([d],None)['status'],'CAPABILITY_UNAVAILABLE')
  for rr in ([],[self.record(),self.record()]):
   with self.assertRaises(ValueError):self.model.audit_process(rr,self.plan)
if __name__=='__main__':unittest.main()
