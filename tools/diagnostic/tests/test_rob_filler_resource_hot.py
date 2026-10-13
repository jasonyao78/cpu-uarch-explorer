"""Actual final-RX warm call registration and count isolation."""
import importlib,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class FinalRXWarm(unittest.TestCase):
 def test_actual_warm_producer_registered(self):
  p=ROOT/'probes/diagnostic/rob_filler_resource_hot.c';self.assertTrue(p.exists(),'hot producer missing')
  s=p.read_text();self.assertIn('warm-roi',s);self.assertIn('post-RX-owned-ROI',s)
 def test_warm_coverage_not_silently_ignored(self):
  try:m=importlib.import_module('tools.diagnostic.rob_filler_resource_hot_analysis')
  except ModuleNotFoundError:self.fail('warm consumer missing')
  self.assertEqual(m.expected(64,12)[0]['final_RX_owned_warm_calls'],4)
  with self.assertRaises(ValueError):m.audit_process(m.expected(64,12)[:5]+[{}],m.conditions()[0],m.plans())
