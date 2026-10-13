"""Actual persistent BPF emitter, independently interpreted; simulated memory only."""
import json,subprocess,tempfile,unittest
from tools.diagnostic.tests import test_translation_self as vm
ROOT=vm.ROOT;VA=1<<32;VMF=0x90000;BIAS=0xffff000000000000;PMD=BIAS+0x600000;PTE=BIAS+0x700000
class PersistentBytecode(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.src=ROOT/'probes/diagnostic/translation_persistent_read.c'
  if cls.src.exists():
   cls.temp=tempfile.TemporaryDirectory();cls.binary=__import__('pathlib').Path(cls.temp.name)/'persistent';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(cls.src),'-o',str(cls.binary)],check=True,capture_output=True);cls.plan=json.loads(subprocess.check_output([str(cls.binary),'--plan'],text=True));cls.libpath=__import__('pathlib').Path(cls.temp.name)/'gate.dylib';subprocess.run(['clang','-shared','-fPIC','-std=c11','-O2','-Wall','-Wextra','-Werror',str(cls.src),'-o',str(cls.libpath)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'temp'):cls.temp.cleanup()
 def evaluate(self,member,va=VA,**kw):
  self.assertTrue(self.src.exists(),'persistent production emitter missing');pmd=PMD+8*((va>>21)&511);pte=PTE+8*((va>>12)&511);root=vm.PGD+8*((va>>30)&511);memory={VMF+48:(8,pmd),VMF+88:(8,pte),pmd:(8,0x700003),root:(8,0x600003),pte:(8,0xaaa003)};defaults=dict(context_fields={0:VMF,16:va},additional_memory=memory,allowed_reads=[(VMF+48,8),(VMF+88,8),(pmd,8),(vm.TASK+1440,8),(vm.MM+56,8),(root,8),(pte,8)],output_words=17,prior=[0]*16+[va]);defaults.update(kw);return vm.interpret(self.plan[member+'_instructions'],**defaults)
 def test_dynamic_input_changes_root_index_without_loading_new_program(self):
  for va in (1<<30,1<<32,(7<<30)+4096,(127<<30)+4096,(511<<30)+4096):
   entry,reads=self.evaluate('entry',va);self.assertEqual(entry[:5],[11,1,0,12345,va]);self.assertEqual(reads[-1],(vm.PGD+8*((va>>30)&511),8));ret,reads=self.evaluate('return',va,prior=entry);self.assertEqual(ret[:3],[13,1,1]);self.assertEqual(ret[12],0xaaa003);self.assertEqual(ret[16],va)
 def test_foreign_PID_wrong_VA_unpaired_or_missing_map_never_kernel_read(self):
  for kw in (dict(pid=12346),dict(context_fields={0:VMF,16:VA+4096}),dict(map_present=False)):
   out,reads=self.evaluate('entry',**kw);self.assertEqual(out,[0]*16+[VA]);self.assertEqual(reads,[])
  out,reads=self.evaluate('return');self.assertEqual(out,[0]*16+[VA]);self.assertEqual(reads,[])
 def test_sticky_first_error_and_duplicate_are_preserved(self):
  for stage in range(1,7):
   entry,reads=self.evaluate('entry',fail_read=stage);self.assertEqual(entry[13],(1<<64)-14);ret,reads=self.evaluate('return',prior=entry);self.assertEqual(ret,entry);self.assertEqual(reads,[]);again,reads=self.evaluate('entry',prior=entry);self.assertEqual(again,entry);self.assertEqual(reads,[])
  entry,_=self.evaluate('entry');bad,reads=self.evaluate('entry',prior=entry);self.assertEqual(bad[0],99);self.assertEqual(bad[13],(1<<64)-17);self.assertEqual(reads,[])
 def test_actual_plan_shape_and_host_refusal(self):
  self.evaluate('entry');self.assertEqual(self.plan['value_bytes'],136);self.assertEqual(self.plan['request_word'],16);self.assertEqual(len(self.plan['entry_instructions']),102);self.assertEqual(len(self.plan['return_instructions']),32);r=subprocess.run([str(self.binary),'--run'],text=True,capture_output=True);self.assertNotEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['metrics'],{})
 def test_actual_C_registration_and_capture_gate_prevent_bad_advance(self):
  import ctypes as ct
  self.evaluate('entry');lib=ct.CDLL(str(self.libpath));ptr=ct.POINTER(ct.c_uint64);reg=lib.persistent_registration_gate;reg.argtypes=[ptr,ct.c_bool];reg.restype=ct.c_uint;gate=lib.persistent_capture_gate;gate.argtypes=[ct.c_uint,ct.c_uint64,ct.c_uint64,ct.c_uint64]+[ptr]*7;gate.restype=ct.c_uint
  arr=lambda v:(ct.c_uint64*len(v))(*v);zero=[0]*17;request=[0]*16+[VA];entry,_=self.evaluate('entry');positive,_=self.evaluate('return',prior=entry);cb=[(1<<63)|0xaaa,(1<<63)|0xbbb];empty=[0,0];args=[12345,VA,0x12340000,0x12340000,arr(cb),arr(cb),arr(empty),arr(cb),arr(request),arr(request),arr(positive)]
  self.assertEqual(reg(arr(zero),True),0);self.assertEqual(reg(arr(positive),False),0);self.assertEqual(gate(*args),0)
  for index in (0,1,2,13,14,15,16):
   bad=positive.copy();bad[index]=0 if index in (0,1,2,16) else 1;self.assertEqual(reg(arr(bad),False),1)
  for index in (0,1,2,3,4,6,7,8,11,12,13,14,15,16):
   bad=positive.copy();bad[index]^=1;v=args.copy();v[-1]=arr(bad);self.assertEqual(gate(*v),1)
  v=args.copy();v[-1]=arr(request);self.assertEqual(gate(*v),2)
if __name__=='__main__':unittest.main()
