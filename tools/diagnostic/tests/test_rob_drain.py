"""Actual generated retirement-boundary words and output-before-reset contract."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class TestDrainProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  src=ROOT/'probes/diagnostic/rob_fp_drain.c';assert src.exists(),'registered drain producer missing'
  cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'drain';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'probes/common'),str(src),'-o',str(cls.binary)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def plan(self,mode,anchor,chain,g=0,reverse=False):
  args=['--plan','--anchor',anchor,'--drain',mode,'--g',str(g),'--chain',str(chain)]+(['--reverse'] if reverse else [])
  return [json.loads(x) for x in subprocess.check_output([str(self.binary),*args],text=True).splitlines()]
 def test_real_32_plans_and_ir_boundary(self):
  for mode in ('fpcr','fpsr'):
   for chain in (16,32):
    for anchor,g in [('none',0),('serial',0),('independent',0),('none',64)]:
     for rev in (False,True):
      c,p,*schedule=self.plan(mode,anchor,chain,g,rev);self.assertEqual(c['drain'],mode);self.assertEqual(p['loop_offset'],64);self.assertEqual(p['loop_instructions'],4*g+(2*chain if anchor!='none' else 0)+9);self.assertEqual(p['prologue_instructions'],16);self.assertEqual([x['round'] for x in schedule],list(range(8))[::(-1 if rev else 1)])
 def test_only_sysreg_encoding_differs(self):
  for anchor,g in [('none',0),('serial',0),('independent',0),('none',64)]:
   a=self.plan('fpcr',anchor,16,g)[1]['words'];b=self.plan('fpsr',anchor,16,g)[1]['words'];diff=[(x,y) for x,y in zip(a,b) if x!=y];self.assertEqual(diff,[(0xd53b440c,0xd53b442c)])
 def test_capture_before_reset_and_owned_buffer_epilogue(self):
  w=self.plan('fpsr','independent',32)[1]['words'];i=w.index(0xd53b442c)
  self.assertEqual(w[i-2:i],[0x9e66000d,0x9e66002e]);self.assertEqual(w[i+1:i+5],[0xaa0c03f0,0xca0f018c,0x9e670180,0x9e670181]);self.assertEqual(w[-5:],[0xf900004d,0xf900044e,0xf9000850,0xd2800000,0xd65f03c0])
 def test_outside_qualification_grid_and_host_measurement_refuse(self):
  for args in (['--plan','--anchor','independent','--drain','fpsr','--g','64','--chain','16'],['--run','--anchor','none','--drain','fpsr','--g','0','--chain','16']):
   p=subprocess.run([str(self.binary),*args],text=True,capture_output=True);self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout.splitlines()[-1])['metrics'],{})
if __name__=='__main__':unittest.main()
