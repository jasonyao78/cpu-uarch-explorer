"""Actual producer words and register schedule; target PMU evidence is separate."""
import collections,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class TestOrderProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  src=ROOT/'probes/diagnostic/rob_anchor_order.c';assert src.exists(),'registered order producer missing'
  cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'order';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'probes/common'),str(src),'-o',str(cls.binary)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def plan(self,k=32,swap=False,rev=False):
  return [json.loads(x) for x in subprocess.check_output([str(self.binary),'--plan','--chain',str(k),'--slots','swapped' if swap else 'normal',*(['--reverse'] if rev else [])],text=True).splitlines()]
 def test_eight_actual_plans_and_balanced_positions(self):
  for k in (16,32):
   for swap in (False,True):
    for rev in (False,True):
     rr=self.plan(k,swap,rev);self.assertEqual(len(rr),73);cfg=rr[0];self.assertEqual(cfg['iterations'],262144);self.assertEqual(cfg['windows'],64)
     for p in rr[1:9]:
      self.assertEqual(p['loop_offset'],64);self.assertLess(p['code_bytes'],2048);self.assertEqual(p['slot'],2048*((p['condition']%2)^swap));self.assertEqual(p['page'],p['condition']//2)
     for cond in range(8):self.assertEqual(sorted(z['position'] for z in rr[9:] if z['condition']==cond),list(range(8)))
 def test_same_negative_code_and_only_independent_register_order(self):
  rr=self.plan();programs=rr[1:9]
  for i in (0,2,6):self.assertEqual(programs[i]['words'],programs[i+1]['words'])
  b,j=programs[4]['words'],programs[5]['words'];self.assertEqual(collections.Counter(b),collections.Counter(j));self.assertEqual(b[:16],j[:16]);self.assertEqual(b[80:],j[80:]);self.assertEqual(b[16:80],[0x1e61c000]*32+[0x1e61c021]*32);self.assertEqual(j[16:80],[0x1e61c000,0x1e61c021]*32)
  for p in programs:
   w=p['words'];i=w.index(0xd53b442c);self.assertEqual(w[i-2:i],[0x9e66000d,0x9e66002e]);self.assertEqual(w[-5:],[0xf900004d,0xf900044e,0xf9000850,0xd2800000,0xd65f03c0])
 def test_invalid_grid_and_host_measurement_refused(self):
  for args in (['--plan','--chain','24','--slots','normal'],['--run','--chain','16','--slots','normal']):
   p=subprocess.run([str(self.binary),*args],text=True,capture_output=True);self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout.splitlines()[-1])['metrics'],{})
if __name__=='__main__':unittest.main()
