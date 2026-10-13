"""Real sink/live/zero instruction identities and exact dynamic recipes."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class SinkUnit(unittest.TestCase):
 def test_actual_producer_modes_and_palette(self):
  src=ROOT/'probes/diagnostic/rob_sink_unit.c';self.assertTrue(src.exists(),'sink unit producer missing')
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(src),'-o',str(b)],check=True)
   rr=[json.loads(l) for l in subprocess.check_output([str(b),'--plan','--count','16','--indices','32,3,4,5,6,7']).splitlines()];self.assertEqual(rr[0]['events'],[17,8,58,59,115,1]);self.assertEqual([z['unit'] for z in rr[1:5]],['nop','sink','live','zero']);self.assertEqual(rr[2]['words'].count(0x8b02003f),16);self.assertEqual(rr[3]['words'].count(0x8b020029),16);self.assertEqual(rr[4]['words'].count(0xd2800009),16)
 def test_recipe_role_and_unit_scope(self):
  try:m=importlib.import_module('tools.diagnostic.rob_sink_unit_analysis')
  except ModuleNotFoundError:self.fail('unit consumer missing')
  p=m.expected(32);self.assertEqual(p[0]['count'],32);self.assertNotIn('chain',p[0]);self.assertEqual(p[2]['unit'],'sink')
