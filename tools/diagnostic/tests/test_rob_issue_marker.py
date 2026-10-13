"""Actual producer near/far tap instruction stream, not target evidence."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class IssueProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.src=ROOT/'probes/diagnostic/rob_issue_marker.c';cls.tmp=tempfile.TemporaryDirectory();cls.bin=Path(cls.tmp.name)/'producer'
  if cls.src.exists():subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'probes/common'),str(cls.src),'-o',str(cls.bin)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def plan(self,k):
  self.assertTrue(self.src.exists(),'production issue marker missing');return [json.loads(l) for l in subprocess.check_output([str(self.bin),'--plan','--chain',str(k)],text=True).splitlines()]
 def test_actual_program_architectural_marker_and_sealed_skip(self):
  for k in (16,32):
   cfg,nop,taps,*schedule=self.plan(k);a,b=nop['words'],taps['words'];self.assertEqual(cfg['events'],[17,8,112,113,34,1]);self.assertEqual(cfg['windows'],144);self.assertEqual(cfg['groups'],0)
   self.assertEqual(b[:3],[0xaa1f03e9,0x9e670000,0xaa0403e6]);self.assertEqual(b[3:3+k],[0x1e61c000]*k)
   self.assertEqual(b[k+3:k+5],[0x9e66000c,0xb500022c]);self.assertEqual(b[k+5:k+13],[0xf9400029+(j*8<<10) for j in range(8)]);self.assertEqual(b[k+13:k+21],[0xf9000046+(j*8<<10) for j in range(8)])
   self.assertEqual([i for i,(x,y) in enumerate(zip(a,b)) if x!=y],list(range(k+5,k+21)));self.assertEqual(b[k+21:],[0xd50330ff,0x9e660000,0xd53b442c,0xf900006c,0xf9000469,0xd65f03c0]);self.assertEqual(len(schedule),144)
 def test_actual_schedule_all_positions_balanced(self):
  for ctl in ('architect','bypass','speculate'):
   for marker in ('nop','taps'):
    s=[r for r in self.plan(16)[3:] if r['control']==ctl and r['marker']==marker];self.assertEqual(len(s),24);self.assertEqual(sorted(r['position'] for r in s),[j for j in range(6) for _ in range(4)])
 def test_unregistered_grid_and_host_run_refuse(self):
  self.plan(16)
  for args in (['--plan','--chain','64'],['--run','--chain','16']):
   p=subprocess.run([str(self.bin),*args],capture_output=True,text=True);self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout.splitlines()[-1])['metrics'],{})
