"""Actual C plans: odd-stride matched VPN histogram and complete ordinal circuits."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class ObservedReachProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.src=ROOT/'probes/diagnostic/tlb_observed_reach.c'
  if cls.src.exists():
   cls.tmp=tempfile.TemporaryDirectory();cls.binary=Path(cls.tmp.name)/'reach';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(cls.src),'-o',str(cls.binary)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'tmp'):cls.tmp.cleanup()
 def plan(self,n=32,reverse=0):
  self.assertTrue(self.src.exists(),'descriptor-bound PMU graph producer missing');return json.loads(subprocess.check_output([str(self.binary),'--plan','--nodes',str(n),'--reverse',str(reverse)],text=True))
 def test_real_plan_cycle_and_complete_candidate_histogram(self):
  for n in (32,1024,1536,1792,2048,2304):
   for reverse in (0,1):
    p=self.plan(n,reverse);self.assertEqual((p['nodes'],p['captures'],p['windows']),(n,2*n,12));self.assertEqual(p['strides'],[12288,2109440]);self.assertEqual(p['kernel_words'],[0xf9400000,0x9b092800,0xf1000508,0x54ffffa1]);self.assertEqual(sorted(p['order']),list(range(n)));self.assertEqual(p['loads']%n,0);self.assertGreaterEqual(p['loads'],1048576);head=p['order'][0];v=head;seen=[]
    for _ in range(n):seen.append(v);v=p['next'][v]
    self.assertEqual(v,head);self.assertEqual(seen,p['order']);h=[]
    for stride in p['strides']:
     bins=[0]*256
     for i in range(n):bins[(stride//4096*i)%256]+=1
     h.append(bins)
    self.assertEqual(h[0],h[1]);self.assertEqual(len([v for v in h[0] if v]),min(n,256))
    if n>=256:self.assertEqual(set(h[0]),{n//256})
 def test_reverse_is_same_physical_order_for_both_shapes(self):
  for n in (32,2304):
   a,b=self.plan(n,0),self.plan(n,1);self.assertEqual(a['order'][::-1],b['order']);self.assertEqual(a['events'],[17,8,5,52,3,1]);self.assertEqual(a['base_alignment'],1<<33)
 def test_original_persistent_BPF_emitter_is_actual_shared_component(self):
  self.plan();p=json.loads(subprocess.check_output([str(self.binary),'--bpf-plan','12345','7'],text=True));self.assertEqual((len(p['entry_instructions']),len(p['return_instructions'])),(102,32));self.assertEqual(p['value_bytes'],136)
 def test_invalid_grid_and_host_run_refuse_without_fake_metrics(self):
  self.plan()
  for args in (['--run','--nodes','32','--reverse','0'],['--plan','--nodes','96','--reverse','0'],['--plan','--nodes','32','--reverse','2']):
   p=subprocess.run([str(self.binary),*args],text=True,capture_output=True);self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['metrics'],{})
if __name__=='__main__':unittest.main()
