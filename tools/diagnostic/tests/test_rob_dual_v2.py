"""Actual unchanged C producer, revised sentinel role; never relabel v1 raw."""
import copy,unittest
from pathlib import Path
from tools.diagnostic.tests import test_rob_dual as previous
class DualAnalysis(previous.DualAnalysis):
 def model(self):
  from tools.diagnostic import rob_dual_v2_analysis
  return rob_dual_v2_analysis
 def test_zero_control_relative_noise_is_scaled_to_anchor_signal(self):
  m=self.model();run=self.run_fixture()
  for r in run['rows']:
   if r['config']['anchor']=='none' and r['config']['n']==0:
    for s in r['samples']:s['counts'][0]=131072
    r['samples'][0]['counts'][0]=147456
  self.assertEqual(m.analyze(run)['status'],'dual-anchor-overlap-qualified')
  from tools.diagnostic import rob_dual_analysis as old
  self.assertEqual(old.analyze(dict(run,mode=old.MODE))['status'],'not-qualified')
 def test_exact_anchor_scaled_noise_gate_and_bad_zero_control(self):
  m=self.model();run=self.run_fixture()
  for r in run['rows']:
   if r['config']['anchor']=='independent':
    for s in r['samples']:s['counts'][0]=200*131072
   if r['config']['anchor']=='none' and r['config']['n']==0:
    for s in r['samples']:s['counts'][0]=131072
    r['samples'][0]['counts'][0]=3*131072
  self.assertTrue(m.analyze(run)['qualified'])
  next(r for r in run['rows'] if r['config']['anchor']=='none' and r['config']['n']==0)['samples'][0]['counts'][0]+=1
  self.assertFalse(m.analyze(run)['qualified'])
class DriverPresence(unittest.TestCase):
 def test_registered_v2_driver_exists(self):self.assertTrue((previous.ROOT/'tools/diagnostic/run_sm8650_rob_dual_v2.py').exists(),'v2 driver missing')
if __name__=='__main__':unittest.main()
