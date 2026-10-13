"""Fixed attempts retain invalid metadata and prevent metric-based picking."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
from tools.diagnostic.tests.test_pmu_own_counter_controller import windows
ROOT=Path(__file__).resolve().parents[3]
class Bounded(unittest.TestCase):
 def m(self):
  try:return importlib.import_module('tools.diagnostic.pmu_bounded_counter_analysis')
  except ModuleNotFoundError:self.fail('bounded consumer missing')
 def fixture(self):
  m=self.m();p=m.expected(0);rr=windows(p)
  for row in rr[2:-1]:
   for v in row['direct_before']+row['direct_after']:v.update(attempted=True,register_read=True)
  rr[-1]['invalid_windows']=0
  return m,rr
 def invalid(self,rr,ordinal):
  row=rr[ordinal+2];row['type']='invalid-window';row['metrics']={};row['failure']={'reason':'metadata-changed'};row['payload_ran']=True;row['direct_after'][0]['sequence_before']=row['direct_after'][0]['sequence_after']=4
 def test_fixed_coverage_one_invalid_not_retry(self):
  m,rr=self.fixture();self.invalid(rr,5);rr[-1]['invalid_windows']=1;v=m.audit_process(rr,rr[0]);self.assertEqual(v['status'],'OWN_DIRECT_COUNTER_QUALIFIED');self.assertEqual(v['invalid_ordinals'],[5]);self.assertEqual(len(v['rows']),23)
 def test_two_invalid_fail_and_fake_invalid_trace_reject(self):
  m,rr=self.fixture();self.invalid(rr,5);self.invalid(rr,8);rr[-1]['invalid_windows']=2;self.assertEqual(m.audit_process(rr,rr[0])['status'],'OWN_DIRECT_COUNTER_NOT_QUALIFIED');rr[7]['direct_after'][0]['sequence_before']=rr[7]['direct_after'][0]['sequence_after']=2
  with self.assertRaises(ValueError):m.audit_process(rr,rr[0])
 def test_actual_v2_plan(self):
  p=ROOT/'probes/diagnostic/pmu_own_counter_bounded.c';self.assertTrue(p.exists(),'bounded producer missing')
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11',str(p),'-o',str(b)],check=True);v=json.loads(subprocess.check_output([str(b),'--plan','0']));self.assertEqual(v['version'],2);self.assertEqual(v['invalid_window_budget'],1);self.assertEqual(v['attempts'],24)
