"""Self-descriptor contract tests from actual producer plans and independently interpreted words."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
from tools.diagnostic.tests import test_translation_self as fixture
ROOT=fixture.ROOT
class TestSelfConsumer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  assert (ROOT/'tools/diagnostic/translation_self_analysis.py').exists(),'registered self-read consumer is missing'
  cls.model=importlib.import_module('tools.diagnostic.translation_self_analysis');cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'plan'
  subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'probes/diagnostic/translation_self_read.c'),'-o',str(cls.binary)],check=True,capture_output=True)
  cls.plan=json.loads(subprocess.check_output([str(cls.binary),'--plan'],text=True))
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def record(self):
  outs=[fixture.interpret(self.plan['instructions'])[0] for _ in range(3)];out=outs[-1];out[7]=sum(x[7] for x in outs)
  return dict(type='self-read',cpu=7,page_bytes=4096,va=[3<<30,4<<30],program=self.plan,initial=[0]*8,negative=[0]*8,positive=out,fds_closed=True)
 def test_real_plan_writer_loader_positive(self):
  folder=Path(self.temp.name)/'raw';folder.mkdir(exist_ok=True);p=folder/'actual.stdout.jsonl';p.write_text(json.dumps(self.record())+'\n')
  result=self.model.audit_process([json.loads(l) for l in p.read_text().splitlines()],self.plan)
  self.assertEqual(result['status'],'SELF_ROOT_DESCRIPTOR_READ');self.assertEqual(result['root_table_descriptors'],2);self.assertEqual(result['leaf_cont_state'],'UNKNOWN')
 def test_types_coverage_and_failure_fields_not_rescued(self):
  for field,value in [('cpu',True),('fds_closed',1),('positive',[6,12345,0,fixture.PGD,0xabc003,0xdef003,0,3])]:
   r=self.record();r[field]=value
   with self.assertRaises(ValueError):self.model.audit_process([r],self.plan)
  for rows in ([],[self.record(),self.record()]):
   with self.assertRaises(ValueError):self.model.audit_process(rows,self.plan)
 def test_negative_foreign_pid_capture_rejects(self):
  r=self.record();r['negative'][7]=1
  with self.assertRaises(ValueError):self.model.audit_process([r],self.plan)
 def test_root_indices_owner_pid_and_actual_instructions_reject(self):
  for change in ('pid','instruction','va','desc'):
   r=self.record();r['program']=json.loads(json.dumps(self.plan))
   if change=='pid':r['positive'][1]=54321
   if change=='instruction':r['program']['instructions'][1]['imm']=178
   if change=='va':r['va'][1]=3<<30
   if change=='desc':r['positive'][5]=0xdef001
   with self.assertRaises(ValueError):self.model.audit_process([r],self.plan)
 def test_capability_denial_keeps_empty_metrics(self):
  r=dict(type='failure',metrics={},failure=dict(reason='bpf-program-load',errno=13));x=self.model.audit_process([r],None);self.assertEqual(x['status'],'CAPABILITY_UNAVAILABLE');self.assertEqual(x['failure'],r['failure'])
  r['metrics']={'cycles':1}
  with self.assertRaises(ValueError):self.model.audit_process([r],None)
if __name__=='__main__':unittest.main()
