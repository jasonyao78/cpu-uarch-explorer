"""Actual C cycle/layout and exact reused BPF; simulated kernel is not target evidence."""
import ctypes,json,subprocess,tempfile,unittest
from pathlib import Path
from tools.diagnostic.tests import test_translation_install as install
ROOT=install.ROOT
class DescriptorGraphProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.src=ROOT/'probes/diagnostic/tlb_descriptor_graph.c'
  if cls.src.exists():
   cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'graph';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11',str(cls.src),'-o',str(cls.binary)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'temp'):cls.temp.cleanup()
 def test_registered_actual_source(self):self.assertTrue(self.src.exists(),'descriptor graph producer missing')
 def plan(self):
  self.assertTrue(self.src.exists(),'descriptor graph producer missing');return json.loads(subprocess.check_output([str(self.binary),'--plan'],text=True))
 def test_actual_cycle_and_equal_histogram(self):
  p=self.plan();self.assertEqual(p['kernel_words'],[0xf9400000,0x9b092800,0xf1000508,0x54ffffa1]);self.assertEqual(p['nodes'],32);self.assertEqual(sorted(p['order']),list(range(32)));seen=[];head=p['order'][0]
  for j in range(32):seen.append(head);head=p['next'][head]
  self.assertEqual(seen,p['order']);self.assertEqual(head,p['order'][0]);self.assertEqual(p['loads'],512);self.assertEqual(p['packed_stride'],8192);self.assertEqual(p['spaced_stride'],2097152+8192)
  self.assertEqual([(j*p['packed_stride']//4096)%256 for j in range(32)],[(j*p['spaced_stride']//4096)%256 for j in range(32)])
 def test_same_actual_installation_words_and_filter_failures(self):
  self.assertTrue(self.src.exists(),'descriptor graph producer missing');install.TestInstallBytecode.setUpClass()
  try:
   p=json.loads(subprocess.check_output([str(self.binary),'--bpf-plan','12345',str(1<<32),'7'],text=True));self.assertEqual(p,install.TestInstallBytecode.plan)
  finally:install.TestInstallBytecode.tearDownClass()
 def test_host_measurement_refuses(self):
  self.assertTrue(self.src.exists(),'descriptor graph producer missing');p=subprocess.run([str(self.binary),'--run'],text=True,capture_output=True);self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout.splitlines()[-1])['metrics'],{})
 def test_actual_capture_gate_rejects_first_bad_state(self):
  self.assertTrue(self.src.exists(),'descriptor graph producer missing');library=Path(self.temp.name)/'gate.dylib';subprocess.run(['clang','-shared','-fPIC','-std=c11','-O2',str(self.src),'-o',str(library)],check=True,capture_output=True);gate=ctypes.CDLL(str(library));self.assertTrue(hasattr(gate,'graph_capture_gate'),'actual producer gate missing')
  fn=gate.graph_capture_gate;U=ctypes.c_uint64;P=ctypes.POINTER(U);fn.argtypes=[U,ctypes.c_uint,U,U,*([P]*7)];fn.restype=ctypes.c_uint;install.TestInstallBytecode.setUpClass()
  try:
   fixture=install.TestInstallBytecode();entry,_=fixture.evaluate('entry');out,_=fixture.evaluate('return',prior=entry);pm=[(1<<63)|0xaaa,(1<<63)|0xbbb]
   def call(pos=out,word=2,neg=None,after=pm):return fn(1<<32,12345,2,word,(U*2)(*pm),(U*2)(*after),(U*2)(0,0),(U*2)(*pm),(U*16)(*([0]*16)),(U*16)(*(neg or [0]*16)),(U*16)(*pos))
   self.assertEqual(call(),0);self.assertEqual(call(pos=[0]*16),2)
   for index,value in ((0,11),(1,2),(2,0),(3,12346),(6,install.PMD+8),(12,0xbbb003),(13,(1<<64)-14)):
    bad=out[:];bad[index]=value;self.assertEqual(call(pos=bad),1)
   bad=[0]*16;bad[1]=1;self.assertEqual(call(neg=bad),1);self.assertEqual(call(word=3),1);self.assertEqual(call(after=[pm[0]+1,pm[1]]),1)
  finally:install.TestInstallBytecode.tearDownClass()
if __name__=='__main__':unittest.main()
