"""守住同映射state512与requested→realized地址链；锚点 cold-head-interleaved v2.0。"""
import copy, importlib, json, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class Interleaved(unittest.TestCase):
 def native(self):
  src=ROOT/'probes/diagnostic/rob_cold_head_interleaved.c'
  self.assertTrue(src.exists(),'interleaved producer missing')
  return src
 def test_native_state512_and_actual_head_layout(self):
  src=self.native()
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'p'
   subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(src),'-o',str(b)],check=True)
   for h in (1,2):
    for p in ('issue','cache'):
     for offset in (0,1024):
      args=['--plan','--heads',str(h),'--palette',p,'--head-offset',str(offset),'--indices','32,3,4,5,6,7']
      rr=[json.loads(l) for l in subprocess.check_output([str(b),*args]).splitlines()]
      self.assertEqual(rr[0]['windows'],512);self.assertEqual(rr[0]['head_offset'],offset)
      schedule=rr[5:];self.assertEqual(len(schedule),512)
      self.assertEqual(len({(s['trial'],s['state'],s['control'],s['fence'],s['marker']) for s in schedule}),512)
      self.assertEqual([s['state'] for s in schedule[:16]],['hot']*8+['cold']*8)
      self.assertEqual(schedule[8*16]['state'],'hot');self.assertEqual(schedule[8*16]['control'],'speculate');self.assertEqual(schedule[8*16]['marker'],'taps');self.assertEqual(schedule[8*16+8]['state'],'cold')
      for z in rr[1:5]:
       self.assertEqual(z['words'].count(0xf940008c),1);self.assertEqual(z['words'].count(0xf940018c),h-1)
   harness=Path(t)/'layout.c'
   harness.write_text('#define main probe_main\n#include "'+str(src)+'"\n#undef main\nint main(void){return head_address(0x1000,1024)!=0x1400 || head_address(0x2000,0)!=0x2000;}\n')
   subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(harness),'-o',str(b)],check=True)
   subprocess.run([str(b)],check=True)
 def test_consumer_native_registration(self):
  try:m=importlib.import_module('tools.diagnostic.rob_cold_head_interleaved_analysis')
  except ModuleNotFoundError:self.fail('interleaved consumer missing')
  self.assertEqual(len(m.conditions()),16)
  for c in m.conditions():
   rr=m.expected(int(c['args'][2]),c['args'][4],int(c['args'][6]))
   self.assertEqual(len(rr),517)
   self.assertEqual(len({(z['trial'],z['state'],z['control'],z['marker'],z['fence']) for z in rr[5:]}),512)
  with self.assertRaises(ValueError):m.analyze([])
 def test_packet_state_collision_coverage_and_old256(self):
  from tools.diagnostic import owned_roi_packets as packets
  from tools.diagnostic import rob_cold_head_analysis as old
  schedule=old.expected(1,'issue','cold')[5:]
  schedule=[dict(s,position=s['position']+8*i,state=state) for s in schedule for i,state in enumerate(('hot','cold'))]
  rows=[dict(type=kind,trial=s['trial'],position=s['position'],state=s['state'],**({'ordinal':j} if kind=='warm-roi' else {})) for s in schedule for j,kind in enumerate(['warm-roi']*4+['round'])]
  result=packets.decode(rows,schedule);self.assertEqual(len(result['valid']),512)
  self.assertEqual(result,packets.decode(list(reversed(rows)),schedule))
  for bad in (rows[:-1],rows+[rows[0]],[dict(rows[0],state='cold'),*rows[1:]]):
   with self.assertRaises(ValueError):packets.decode(bad,schedule)
  packets.final_counts(dict(attempted_packets=512,valid_packets=512,invalid_packets=0),result)
  with self.assertRaises(ValueError):packets.final_counts(dict(attempted_packets=256,valid_packets=512,invalid_packets=0),result)

 def test_controller_resolves_exact_frozen_protocol(self):
  from tools.diagnostic import run_sm8650_rob_cold_head_interleaved as driver
  from tools.diagnostic import rob_cold_head_interleaved_analysis as model
  self.assertEqual(driver.PROTOCOL,model.PROTOCOL)
  self.assertTrue((ROOT/driver.PROTOCOL).is_file())
  self.assertEqual(driver.DRIVER,model.DRIVER)
