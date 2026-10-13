"""Real native plan and typed coverage guards before board measurement."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class Producer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.src=ROOT/'probes/diagnostic/l1_tlb_reach.c';cls.t=tempfile.TemporaryDirectory();cls.bin=Path(cls.t.name)/'p'
  if cls.src.exists():subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11',str(cls.src),'-o',str(cls.bin)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.t.cleanup()
 def test_real_plan_modes_and_registered_grids(self):
  self.assertTrue(self.src.exists(),'L1 reach producer not implemented')
  for mode in ('i','d'):
   for epoch in range(3):
    for phase in ('qualification','scan'):
     p=json.loads(subprocess.check_output([str(self.bin),'--plan',mode,str(epoch),phase]));self.assertEqual(p['events'],[17,8,2,53,1,34] if mode=='i' else [17,8,5,52,3,1]);self.assertEqual(p['nodes'],[32] if phase=='qualification' else ([32,40,44,48,52,56,64,96,112,120,124,128,132,144,160,192] if mode=='i' else [32,64,80,88,92,96,100,104,112,128,160,192]));self.assertEqual(p['strides'],[5,17]);self.assertEqual(p['rounds'],3);self.assertFalse(p['global_policy_mutation'])
 def test_unknown_input_and_host_run_reject(self):
  self.assertTrue(self.src.exists(),'L1 reach producer not implemented')
  for args in (['--plan','i','3','scan'],['--run','d','0','qualification']):
   q=subprocess.run([str(self.bin),*args],capture_output=True,text=True);self.assertNotEqual(q.returncode,0);self.assertEqual(json.loads(q.stdout.splitlines()[-1])['metrics'],{})
