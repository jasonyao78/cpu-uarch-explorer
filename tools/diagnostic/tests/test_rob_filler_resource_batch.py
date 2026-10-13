"""Real batched envelope identity is compulsory before consumption."""
import importlib,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class BatchEnvelope(unittest.TestCase):
 def test_actual_batch_producer(self):
  p=ROOT/'probes/diagnostic/rob_filler_resource_batch.c';self.assertTrue(p.exists(),'batch producer missing')
  s=p.read_text();start=s.index('static const char*measure_frame');end=s.index('static int one_page',start);self.assertNotIn('snapshot(',s[start:end]);self.assertIn('close-batch-envelope',s)
 def test_registered_envelope(self):
  try:m=importlib.import_module('tools.diagnostic.rob_filler_resource_batch_analysis')
  except ModuleNotFoundError:self.fail('batch consumer missing')
  self.assertEqual(m.expected(64,12)[0]['fd_envelope'],'four-warm-plus-one-formal')
  with self.assertRaises(ValueError):m.audit_process([],m.conditions()[0],m.plans())
