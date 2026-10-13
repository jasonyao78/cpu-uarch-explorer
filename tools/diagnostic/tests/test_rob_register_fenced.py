"""Native dynamic words, ARM ABI and no observer memory inside the ROI."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class RegisterMarker(unittest.TestCase):
 def test_real_dynamic_plan_and_unsafe_override_reject(self):
  src=ROOT/'probes/diagnostic/rob_register_fenced_marker.c';self.assertTrue(src.exists(),'register ROI producer missing')
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(src),'-o',str(b)],check=True)
   for ids in ('32,3,4,5,6,7','1,32,5,6,8,9'):
    rr=[json.loads(l) for l in subprocess.check_output([str(b),'--plan','--chain','32','--indices',ids]).splitlines()];self.assertEqual(rr[0]['count_source'],'owned-register-only-roi');self.assertEqual(rr[1]['counter_indices'],[int(x) for x in ids.split(',')]);self.assertEqual(len(rr),261)
   for args in (['--run','--chain','32','--indices','32,3,4,5,6,7'],['--plan','--chain','32','--indices','32,3,3,5,6,7']):
    q=subprocess.run([str(b),*args],capture_output=True,text=True);self.assertNotEqual(q.returncode,0);self.assertEqual(json.loads(q.stdout.splitlines()[-1])['metrics'],{})
 def test_binding_and_recipe_preserve_old_body(self):
  try:m=importlib.import_module('tools.diagnostic.rob_register_fenced_analysis')
  except ModuleNotFoundError:self.fail('register recipe consumer missing')
  words=m.program_words(32,0,[32,3,4,5,6,7]);self.assertEqual(words[:4],[0xa9bc53f3,0xa9015bf5,0xa90263f7,0xa9036bf9]);self.assertEqual(words[-1],0xd65f03c0);self.assertEqual(words.count(0xd50330ff),4)

 def test_warm_keeps_return_and_removes_all_counter_words(self):
  try:m=importlib.import_module('tools.diagnostic.rob_register_fenced_analysis')
  except ModuleNotFoundError:self.fail('register recipe consumer missing')
  for k in (16,32):
   for mode in range(4):
    w=m.program_words(k,mode,[32,3,4,5,6,7]);warm=m.warm_words(k,w);self.assertEqual(len(warm),len(w));self.assertEqual(warm[-5:],w[-5:]);self.assertNotIn(0xd51b9cab,warm);self.assertFalse(any((word&~31) in (0xd53b9d00,0xd53b9d40) for word in warm))
