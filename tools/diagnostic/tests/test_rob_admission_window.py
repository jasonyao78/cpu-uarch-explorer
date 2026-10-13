"""Actual growing-gap code and independently audited branch targets."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class AdmissionWindow(unittest.TestCase):
 def test_actual_branch_and_gap(self):
  src=ROOT/'probes/diagnostic/rob_admission_window.c';self.assertTrue(src.exists(),'admission producer missing')
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(src),'-o',str(b)],check=True)
   rr=[json.loads(l) for l in subprocess.check_output([str(b),'--plan','--chain','32','--gap','768','--filler','sink','--indices','32,3,4,5,6,7']).splitlines()]
   self.assertEqual(rr[0]['gap'],768)
   for p in rr[1:5]:
    w=p['words'];self.assertEqual(w.count(0x8b02003f),768);self.assertLess(len(w)*4,4096)
    j=30+32+4;disp=(w[j]>>5)&0x7ffff;self.assertEqual(j+disp,len(w)-41)
 def test_matrix_coverage_and_recipe(self):
  try:m=importlib.import_module('tools.diagnostic.rob_admission_window_analysis')
  except ModuleNotFoundError:self.fail('admission consumer missing')
  self.assertEqual(len(m.conditions()),84);self.assertTrue(all(c['phase']=='qualification' and c['args'][4]=='0' for c in m.conditions()[:12]));self.assertTrue(all(c['phase']=='scan' and c['args'][4]!='0' for c in m.conditions()[12:]));self.assertEqual(m.expected(32,768,'sink')[0]['fd_envelope'],'four-warm-plus-one-formal')
  with self.assertRaises(ValueError):m.analyze([])
