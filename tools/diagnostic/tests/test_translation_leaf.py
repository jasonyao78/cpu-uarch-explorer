"""Actual kprobe bytecode interpreted independently; kernel memory is simulated here."""
import json,subprocess,tempfile,unittest
from pathlib import Path
from tools.diagnostic.tests import test_translation_self as vm
ROOT=vm.ROOT;VA=0x100000000;PTE=0x60000
class TestLeafBytecode(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  source=ROOT/'probes/diagnostic/translation_self_leaf.c';assert source.exists(),'registered leaf producer is missing'
  cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'leaf'
  subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(cls.binary)],check=True,capture_output=True)
  cls.plan=json.loads(subprocess.check_output([str(cls.binary),'--plan'],text=True));cls.code=cls.plan['instructions']
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def interpret(self,**kw):
  defaults=dict(context_fields={8:VA,16:PTE,24:0xaaa443},additional_memory={PTE:(8,0xaaa003)},allowed_reads=[(PTE,8)]);defaults.update(kw);return vm.interpret(self.code,**defaults)
 def test_positive_reads_only_parameter_owned_leaf(self):
  out,reads=self.interpret();self.assertEqual(out,[6,VA,PTE,0xaaa003,0xaaa443,0,1,12345]);self.assertEqual(reads,[(PTE,8)])
 def test_pid_and_va_filters_precede_any_read(self):
  for kw in (dict(pid=12346),dict(context_fields={8:VA+4096,16:PTE,24:0xaaa443})):
   out,reads=self.interpret(**kw);self.assertEqual(out,[0]*8);self.assertEqual(reads,[])
 def test_first_failure_cannot_be_replaced(self):
  bad,reads=self.interpret(fail_read=1);self.assertEqual(len(reads),1);self.assertEqual(bad[0],1)
  again,reads=self.interpret(prior=bad);self.assertEqual(again,bad);self.assertEqual(reads,[])
 def test_null_pointer_and_jump_boundaries(self):
  out,reads=self.interpret(context_fields={8:VA,16:0,24:0xaaa443});self.assertEqual(reads,[]);self.assertEqual(out[0],1)
  for i,x in enumerate(self.code):
   if x['code']in(0x15,0x55,0x5d):self.assertTrue(0<=i+x['off']+1<len(self.code));self.assertGreaterEqual(x['off'],0)
 def test_host_never_claims_device(self):
  p=subprocess.run([str(self.binary),'--run'],capture_output=True,text=True);self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['metrics'],{})
if __name__=='__main__':unittest.main()
