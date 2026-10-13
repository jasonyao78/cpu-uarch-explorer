"""Actual delayed-branch/SB marker words, plans and original bit results."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class SpecMarkerProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.src=ROOT/'probes/diagnostic/rob_speculative_marker.c'
  if cls.src.exists():
   cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'marker';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'probes/common'),str(cls.src),'-o',str(cls.binary)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'temp'):cls.temp.cleanup()
 def test_actual_producer_exists(self):self.assertTrue(self.src.exists(),'retirement-blocked marker producer missing')
 def plan(self,k=32):
  self.assertTrue(self.src.exists(),'retirement-blocked marker producer missing');return [json.loads(x) for x in subprocess.check_output([str(self.binary),'--plan','--chain',str(k)],text=True).splitlines()]
 def test_only_marker_word_differs_and_branch_sb_retires_correct_path(self):
  for k in (16,32):
   p=self.plan(k);self.assertEqual(len(p),111);cfg,nop,load=p[:3];self.assertEqual(cfg['events'],[17,8,112,6,34,59,1]);self.assertEqual(cfg['groups'],0);self.assertEqual(cfg['windows'],108)
   nw,lw=nop['words'],load['words'];self.assertEqual([(i,a,b) for i,(a,b) in enumerate(zip(nw,lw)) if a!=b],[(k+4,0xd503201f,0xf9400029)]);self.assertEqual(lw[0],0x9e670000);self.assertEqual(lw[1:1+k],[0x1e61c000]*k);self.assertEqual(lw[k+1],0x9e66000c);self.assertEqual(lw[k+2],0xb400004c);self.assertEqual(lw[k+3],0x14000002);self.assertEqual(lw[k+5:],[0xd50330ff,0x9e660000,0xd53b442c,0xf900004c,0xd65f03c0]);self.assertEqual(sorted({r['trial'] for r in p[3:]}),list(range(18)))
 def test_actual_schedule_balances_each_member(self):
  p=self.plan();schedule=p[3:]
  for control in ('architect','bypass','speculate'):
   for marker in ('nop','load'):
    rows=[r for r in schedule if r['control']==control and r['marker']==marker];self.assertEqual(len(rows),18);self.assertEqual(sorted(r['position'] for r in rows),[j for j in range(6) for _ in range(3)])
 def test_bad_grid_and_host_measurement_refuse(self):
  for argv in (['--plan','--chain','8'],['--run','--chain','16']):
   self.assertTrue(self.src.exists(),'retirement-blocked marker producer missing');p=subprocess.run([str(self.binary),*argv],text=True,capture_output=True);self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout.splitlines()[-1])['metrics'],{})
if __name__=='__main__':unittest.main()
