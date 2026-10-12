"""Actual installation plan→writer→strict hierarchy consumer; memory fixture is synthetic."""
import importlib,json,tempfile,unittest
from pathlib import Path
from tools.diagnostic.tests import test_translation_install as fixture
class TestInstallAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  assert (fixture.ROOT/'tools/diagnostic/translation_install_analysis.py').exists(),'registered installation consumer missing'
  cls.model=importlib.import_module('tools.diagnostic.translation_install_analysis');fixture.TestInstallBytecode.setUpClass();cls.actual=fixture.TestInstallBytecode();cls.plan=fixture.TestInstallBytecode.plan
 @classmethod
 def tearDownClass(cls):fixture.TestInstallBytecode.tearDownClass()
 def record(self):
  entry,_=self.actual.evaluate('entry');out,_=self.actual.evaluate('return',prior=entry);wire=[(1<<63)|0xaaa,(1<<63)|0xbbb]
  return dict(type='install-read',cpu=7,page_bytes=4096,kprobe_type=7,program=self.plan,initial=[0]*16,negative=[0]*16,positive=out,alias_before=[0]*2,alias_after=wire,canonical_before=wire[:],canonical_after=wire[:],fds_closed=True)
 def test_real_plan_writer_reader_two_level_identity(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'stdout.jsonl';p.write_text(json.dumps(self.record())+'\n');d=self.model.audit_process([json.loads(p.read_text())],self.plan);self.assertEqual(d['status'],'OWNED_SHARED_DESCRIPTOR_HIERARCHY_READ');self.assertTrue(d['two_level_relation_equal']);self.assertTrue(d['leaf_pfn_matches_canonical'])
 def test_parent_bias_index_and_leaf_identity_cannot_be_rescued(self):
  for field in (6,7,8,11,12):
   r=self.record();r['positive'][field]+=4096
   with self.subTest(field=field),self.assertRaises(ValueError):self.model.audit_process([r],self.plan)
 def test_pair_failure_duplicates_types_and_nonobjects_reject(self):
  for field,value in [(0,11),(1,2),(2,0),(13,(1<<64)-14),(1,True)]:
   r=self.record();r['positive'][field]=value
   with self.assertRaises(ValueError):self.model.audit_process([r],self.plan)
  for row in (None,True,1):
   with self.assertRaises(ValueError):self.model.audit_process([row],self.plan)
 def test_unexcited_denied_and_negative_are_separate(self):
  r=self.record();r['positive']=[0]*16;self.assertEqual(self.model.audit_process([r],self.plan)['status'],'NOT_EXCITED')
  r=self.record();r['negative'][1]=1
  with self.assertRaises(ValueError):self.model.audit_process([r],self.plan)
  r=dict(type='failure',metrics={},failure=dict(reason='perf-kprobe-open',errno=1));self.assertEqual(self.model.audit_process([r],None)['status'],'CAPABILITY_UNAVAILABLE')
if __name__=='__main__':unittest.main()
