"""Actual native contract and pure guard rejects before register access."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class CounterProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.t=tempfile.TemporaryDirectory();cls.bin=Path(cls.t.name)/'p';cls.src=ROOT/'probes/diagnostic/pmu_own_counter.c'
  if cls.src.exists():subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11',str(cls.src),'-o',str(cls.bin)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.t.cleanup()
 def test_actual_plan_and_unknown_input(self):
  self.assertTrue(self.src.exists(),'owned direct producer missing')
  for e in range(3):
   p=json.loads(subprocess.check_output([str(self.bin),'--plan',str(e)]));self.assertEqual(p['events'],[17,8,112,113]);self.assertEqual(p['config1'],3);self.assertEqual(p['iterations'],8192);self.assertEqual(p['rounds'],8);self.assertTrue(p['owned_direct_read'])
  q=subprocess.run([str(self.bin),'--run','0'],capture_output=True,text=True);self.assertNotEqual(q.returncode,0);self.assertEqual(json.loads(q.stdout.splitlines()[-1])['metrics'],{})
 def test_guard_and_wrap_actual_C(self):
  h=ROOT/'probes/common/perf_user_counter.h';self.assertTrue(h.exists(),'owned counter guard missing');p=Path(self.t.name)/'guard.c';p.write_text('#include "'+str(h)+'"\n#include <assert.h>\nint main(void){struct pu_metadata m={2,2,3,64,1,0};assert(!pu_guard(1,&m));assert(pu_guard(0,&m));m.index=0;assert(pu_guard(1,&m));m.index=33;assert(pu_guard(1,&m));m.index=32;m.width=32;assert(pu_guard(1,&m));m.width=64;m.last=4;assert(pu_guard(1,&m));m.first=3;m.last=3;assert(pu_guard(1,&m));m.first=m.last=2;m.cap=0;assert(pu_guard(1,&m));assert(pu_delta(UINT64_MAX-2,5)==8);assert(pu_total(UINT64_MAX-2,5)==2);return 0;}\n');b=Path(self.t.name)/'g';subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror',str(p),'-o',str(b)],check=True);subprocess.run([str(b)],check=True)
