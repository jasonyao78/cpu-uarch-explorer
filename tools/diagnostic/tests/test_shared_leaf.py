"""Actual shared producer plan and canonical identity; mock memory never target evidence."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
from tools.diagnostic.tests import test_translation_leaf as fixture
from tools.diagnostic.tests import test_translation_self as vm
class TestSharedLeaf(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  source=fixture.ROOT/'probes/diagnostic/translation_shared_leaf.c';assert source.exists(),'registered shared producer missing'
  assert (fixture.ROOT/'tools/diagnostic/translation_shared_leaf_analysis.py').exists(),'registered shared consumer missing'
  cls.model=importlib.import_module('tools.diagnostic.translation_shared_leaf_analysis');cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'shared'
  subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(cls.binary)],check=True,capture_output=True);cls.plan=json.loads(subprocess.check_output([str(cls.binary),'--plan'],text=True))
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def record(self):
  out,_=vm.interpret(self.plan['instructions'],context_fields={8:fixture.VA,16:fixture.PTE,24:0xaaa443},additional_memory={fixture.PTE:(8,0xaaa003)},allowed_reads=[(fixture.PTE,8)]);w=[(1<<63)|0xaaa,(1<<63)|0xbbb]
  return dict(type='leaf-read',backing='shared-memfd',cpu=7,page_bytes=4096,kprobe_type=7,program=self.plan,initial=[0]*8,negative=[0]*8,positive=out,pagemap_before=w,pagemap_after=w[:],canonical_before=w[:],canonical_after=w[:],fds_closed=True)
 def test_actual_plan_writer_loader_shared_identity(self):
  self.assertEqual(self.plan['backing'],'shared-memfd')
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'stdout.jsonl';p.write_text(json.dumps(self.record())+'\n');d=self.model.audit_process([json.loads(p.read_text())],self.plan);self.assertEqual(d['status'],'SHARED_LEAF_DESCRIPTOR_READ');self.assertTrue(d['canonical_alias_pfn_match'])
 def test_canonical_alias_mismatch_and_types_reject(self):
  for field in ('canonical_before','canonical_after'):
   for value in (True,(1<<63)|0xaab,(1<<63)|(1<<62)|0xaaa):
    r=self.record();r[field][0]=value
    with self.assertRaises(ValueError):self.model.audit_process([r],self.plan)
 def test_non_object_record_is_named_rejection(self):
  for row in (None,True,1):
   with self.assertRaises(ValueError):self.model.audit_process([row],self.plan)
 def test_wrong_backing_not_excited_negative_and_host_boundary(self):
  r=self.record();r['backing']='anonymous'
  with self.assertRaises(ValueError):self.model.audit_process([r],self.plan)
  r=self.record();r['positive']=[0]*8;self.assertEqual(self.model.audit_process([r],self.plan)['status'],'NOT_EXCITED')
  r=self.record();r['negative'][6]=1
  with self.assertRaises(ValueError):self.model.audit_process([r],self.plan)
  q=subprocess.run([str(self.binary),'--run'],text=True,capture_output=True);self.assertNotEqual(q.returncode,0);self.assertEqual(json.loads(q.stdout)['metrics'],{})
if __name__=='__main__':unittest.main()
