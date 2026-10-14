"""真实compile-time palette wrapper与实际512 PC出口合同，锚点 packet-cache v1.0。"""
import json,subprocess,tempfile,unittest,importlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class PacketCache(unittest.TestCase):
 def test_actual_native_cache_wrapper_and_reject_issue(self):
  src=ROOT/'probes/diagnostic/rob_cold_head_packet_cache.c';self.assertTrue(src.exists(),'packet cache wrapper missing')
  with tempfile.TemporaryDirectory() as td:
   b=Path(td)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(src),'-o',str(b)],check=True)
   for h in (1,2):
    args=['--plan','--heads',str(h),'--palette','cache','--head-offset','1024','--branch-layout','packet','--indices','32,3,4,5,6,7'];rr=[json.loads(l) for l in subprocess.check_output([str(b),*args]).splitlines()]
    m=importlib.import_module('tools.diagnostic.rob_cold_head_packet_cache_analysis');self.assertEqual(rr,m.expected(h,'cache',1024,'packet'));self.assertEqual(rr[0]['events'],[17,8,112,113,3,23]);self.assertEqual(len({z['code_offset'] for z in rr[5:]}),512)
    args[4]='issue';p=subprocess.run([str(b),*args],capture_output=True);self.assertNotEqual(p.returncode,0)
 def test_controller_registry_contract(self):
  try:m=importlib.import_module('tools.diagnostic.rob_cold_head_packet_cache_analysis');d=importlib.import_module('tools.diagnostic.run_sm8650_rob_cold_head_packet_cache')
  except ModuleNotFoundError:self.fail('cache consumer/controller missing')
  self.assertEqual(m.PROTOCOL,d.PROTOCOL);self.assertTrue((ROOT/d.PROTOCOL).exists());self.assertEqual(len(m.conditions()),4)
  with self.assertRaises(ValueError):m.analyze([])
