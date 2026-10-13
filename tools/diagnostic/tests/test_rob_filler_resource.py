"""Actual producer recipes and visible work-completion boundaries."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class FillerResource(unittest.TestCase):
 def test_actual_recipe_and_completion_boundary(self):
  src=ROOT/'probes/diagnostic/rob_filler_resource.c';self.assertTrue(src.exists(),'resource producer missing')
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(src),'-o',str(b)],check=True)
   rr=[json.loads(l) for l in subprocess.check_output([str(b),'--plan','--chain','64','--filler','12','--indices','32,3,4,5,6,7']).splitlines()]
   self.assertEqual(rr[0]['chain'],64);self.assertEqual(rr[0]['filler'],12)
   for p in rr[1:5]:
    self.assertEqual(p['words'][-37],0xd50330ff);self.assertEqual(p['words'].count(0x8b040129),64);self.assertLess(p['code_bytes'],4096)
 def test_consumer_native_comparison_and_full_coverage(self):
  try:m=importlib.import_module('tools.diagnostic.rob_filler_resource_analysis')
  except ModuleNotFoundError:self.fail('resource consumer missing')
  self.assertEqual(len(m.conditions()),16);self.assertEqual(m.expected(32,4)[0]['windows'],256)
  with self.assertRaises(ValueError):m.analyze([])
