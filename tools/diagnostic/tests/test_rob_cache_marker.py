"""Actual C plan: delayed branch, SB and independent architectural marker output."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class CacheMarkerProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.src=ROOT/'probes/diagnostic/rob_cache_marker.c'
  if cls.src.exists():
   cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'marker';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(cls.src),'-o',str(cls.binary)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'temp'):cls.temp.cleanup()
 def plan(self,k):
  self.assertTrue(self.src.exists(),'own cache footprint producer missing');return [json.loads(z) for z in subprocess.check_output([str(self.binary),'--plan','--chain',str(k)],text=True).splitlines()]
 def test_actual_marker_program_and_separate_architectural_output(self):
  for k in (16,32):
   p=self.plan(k);self.assertEqual(len(p),259);self.assertEqual(p[0]['windows'],256);nw,lw=p[1]['words'],p[2]['words'];self.assertEqual(len(lw),k+12);self.assertEqual([(i,a,b) for i,(a,b) in enumerate(zip(nw,lw)) if a!=b],[(k+5,0xd503201f,0xf9400029)]);self.assertEqual(lw[:2],[0xaa1f03e9,0x9e670000]);self.assertEqual(lw[k+3:k+5],[0xb400004c,0x14000002]);self.assertEqual(lw[k+6:],[0xd50330ff,0x9e660000,0xd53b442c,0xf900004c,0xf9000449,0xd65f03c0])
 def test_all_eight_members_balance_at_every_position(self):
  p=self.plan(32);members={(r['control'],r['marker']) for r in p[3:]};self.assertEqual(len(members),8)
  for control,marker in members:
   rr=[r for r in p[3:] if (r['control'],r['marker'])==(control,marker)];self.assertEqual(sorted(r['position'] for r in rr),[p for p in range(8) for _ in range(4)]);self.assertEqual(sorted(r['trial'] for r in rr),list(range(32)))
 def test_run_on_host_and_invalid_grid_named_refusal(self):
  self.plan(16)
  for argv in (['--run','--chain','16'],['--plan','--chain','64']):
   r=subprocess.run([str(self.binary),*argv],text=True,capture_output=True);self.assertNotEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout.splitlines()[-1])['metrics'],{})
if __name__=='__main__':unittest.main()
