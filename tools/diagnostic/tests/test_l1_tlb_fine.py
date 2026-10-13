"""Fine grids are emitted by a real producer; no posthoc rebucketing old raw."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class Fine(unittest.TestCase):
 def test_real_fine_plan(self):
  src=ROOT/'probes/diagnostic/l1_tlb_fine.c';self.assertTrue(src.exists(),'fine producer missing')
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11',str(src),'-o',str(b)],check=True)
   for mode in ('i','d'):
    v=json.loads(subprocess.check_output([str(b),'--plan',mode,'0','scan']));self.assertEqual(v['version'],2);self.assertEqual(v['nodes'],[32,46,47,48,49,50,51,52,56] if mode=='i' else [32,94,95,96,97,98,99,100,104])
 def test_new_fine_floor_not_legacy_threshold(self):
  try:m=importlib.import_module('tools.diagnostic.l1_tlb_fine_analysis')
  except ModuleNotFoundError:self.fail('fine consumer missing')
  self.assertEqual(m.fine_onset([(48,0.0004,0.0005),(49,0.008,0.009),(50,.02,.03)])['interval'],[48,49]);self.assertEqual(m.fine_onset([(48,0.0004,0.0005),(49,.0009,.008),(50,.02,.03)])['status'],'ambiguous')
