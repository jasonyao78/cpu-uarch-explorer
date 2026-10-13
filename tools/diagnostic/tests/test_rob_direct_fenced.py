"""Actual producer words and absolute own FD validation at the new boundary."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
from tools.diagnostic import rob_fenced_issue_analysis as old
ROOT=Path(__file__).resolve().parents[3]
class DirectMarker(unittest.TestCase):
 def test_real_program_same_pc_fences(self):
  src=ROOT/'probes/diagnostic/rob_direct_fenced_marker.c';self.assertTrue(src.exists(),'direct ROI producer missing')
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(src),'-o',str(b)],check=True)
   for k in (16,32):
    rr=[json.loads(l) for l in subprocess.check_output([str(b),'--plan','--chain',str(k)]).splitlines()];self.assertEqual(rr[0]['count_source'],'owned-direct-roi');self.assertEqual(rr[0]['perf_config1'],3);self.assertEqual(rr[1:5],old.expected(k)[1:5]);self.assertEqual(rr[5:],old.expected(k)[5:])
 def test_metadata_and_absolute_fd_binding(self):
  try:m=importlib.import_module('tools.diagnostic.rob_direct_fenced_analysis')
  except ModuleNotFoundError:self.fail('direct ROI consumer missing')
  with self.assertRaises(ValueError):m.check_roi({})
  v=[]
  for i in range(6):v.append(dict(sequence_before=2,sequence_after=2,index=32 if i==0 else i,width=64,cap=True,offset=0,hardware=110,total=110))
  z=dict(roi_before=v,roi_after=[dict(x,hardware=130,total=130) for x in v],kernel_before=[100]*6,kernel_after=[140]*6,counts=[20]*6,fd_counts=[40]*6)
  m.check_roi(z);z['roi_after'][0]['index']=0
  with self.assertRaises(ValueError):m.check_roi(z)
