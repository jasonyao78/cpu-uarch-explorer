"""Actual head dependency words and immutable private-address-free native plans."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class ColdHead(unittest.TestCase):
 def test_native_head_dependency_and_no_fp(self):
  src=ROOT/'probes/diagnostic/rob_cold_head.c';self.assertTrue(src.exists(),'cold head producer missing')
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(src),'-o',str(b)],check=True)
   for heads in (1,2):
    rr=[json.loads(l) for l in subprocess.check_output([str(b),'--plan','--heads',str(heads),'--palette','issue','--state','cold','--indices','32,3,4,5,6,7']).splitlines()]
    self.assertEqual(rr[0]['heads'],heads)
    for p in rr[1:5]:
     w=p['words'];self.assertEqual(w.count(0xf940008c),1);self.assertEqual(w.count(0xf940018c),heads-1);self.assertNotIn(0x1e61c000,w)
 def test_pre_registered_profile_coverage(self):
  try:m=importlib.import_module('tools.diagnostic.rob_cold_head_analysis')
  except ModuleNotFoundError:self.fail('cold head consumer missing')
  self.assertEqual(len(m.conditions()),16)
  self.assertEqual(m.expected(2,'cache','hot')[0]['events'],[17,8,112,113,3,23])
