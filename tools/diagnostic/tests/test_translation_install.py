"""Actual entry/return BPF words; simulated own page-table hierarchy is software evidence only."""
import json,subprocess,tempfile,unittest
from pathlib import Path
from tools.diagnostic.tests import test_translation_self as vm
ROOT=vm.ROOT;VA=1<<32;VMF=0x90000;BIAS=0xffff000000000000;PMD=BIAS+0x600000;PTE=BIAS+0x700000
class TestInstallBytecode(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  src=ROOT/'probes/diagnostic/translation_install_read.c';assert src.exists(),'registered installation producer missing'
  cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'install';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(cls.binary)],check=True,capture_output=True);cls.plan=json.loads(subprocess.check_output([str(cls.binary),'--plan'],text=True))
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def evaluate(self,member,**kw):
  memory={VMF+48:(8,PMD),VMF+88:(8,PTE),PMD:(8,0x700003),vm.PGD+32:(8,0x600003),PTE:(8,0xaaa003)}
  defaults=dict(context_fields={0:VMF,16:VA},additional_memory=memory,allowed_reads=[(VMF+48,8),(VMF+88,8),(PMD,8),(vm.TASK+1440,8),(vm.MM+56,8),(vm.PGD+32,8),(PTE,8)],output_words=16);defaults.update(kw);return vm.interpret(self.plan[member+'_instructions'],**defaults)
 def test_pair_actual_root_parent_leaf_association(self):
  entry,er=self.evaluate('entry');self.assertEqual(entry[0:5],[11,1,0,12345,VA]);self.assertEqual(len(er),6)
  returned,rr=self.evaluate('return',prior=entry);self.assertEqual(returned[:3],[13,1,1]);self.assertEqual(returned[6:9],[PMD,PTE,0x700003]);self.assertEqual(returned[11:14],[0x600003,0xaaa003,0]);self.assertEqual(rr,[(PTE,8)])
 def test_pid_va_and_unpaired_return_do_not_read_kernel(self):
  for kw in (dict(pid=12346),dict(context_fields={0:VMF,16:VA+4096})):
   out,reads=self.evaluate('entry',**kw);self.assertEqual(out,[0]*16);self.assertEqual(reads,[])
  out,reads=self.evaluate('return');self.assertEqual(out,[0]*16);self.assertEqual(reads,[])
 def test_read_failures_remain_sticky_through_return_or_duplicate(self):
  for stage in range(1,7):
   entry,reads=self.evaluate('entry',fail_read=stage);self.assertEqual(len(reads),stage);self.assertEqual(entry[13],(1<<64)-14)
   ret,reads=self.evaluate('return',prior=entry);self.assertEqual(ret,entry);self.assertEqual(reads,[])
  entry,_=self.evaluate('entry');failed,_=self.evaluate('return',prior=entry,fail_read=1);again,reads=self.evaluate('return',prior=failed);self.assertEqual(again,failed);self.assertEqual(reads,[])
 def test_duplicate_entry_is_not_overwritten_and_jump_bounds(self):
  entry,_=self.evaluate('entry');out,reads=self.evaluate('entry',prior=entry);self.assertEqual(out[0],99);self.assertEqual(out[13],(1<<64)-17);self.assertEqual(reads,[])
  for member in ('entry','return'):
   code=self.plan[member+'_instructions']
   for i,x in enumerate(code):
    if x['code']in(0x15,0x55,0x5d):self.assertTrue(0<=i+x['off']+1<len(code));self.assertGreaterEqual(x['off'],0)
 def test_host_measurement_boundary(self):
  p=subprocess.run([str(self.binary),'--run'],text=True,capture_output=True);self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['metrics'],{})
if __name__=='__main__':unittest.main()
