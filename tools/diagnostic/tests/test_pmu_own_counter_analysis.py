"""Typed dataflow and prerequisite rejection for own direct counter samples."""
import importlib,unittest
class DirectAnalysis(unittest.TestCase):
 def m(self):
  try:return importlib.import_module('tools.diagnostic.pmu_own_counter_analysis')
  except ModuleNotFoundError:self.fail('direct consumer not implemented')
 def test_actual_index0_width_sequence_and_total(self):
  m=self.m();v=dict(sequence_before=2,sequence_after=2,index=32,width=64,cap=True,offset=(1<<64)-3,hardware=5,total=2);self.assertEqual(m.direct(v),2)
  for k,value in (('index',0),('width',32),('cap',False),('sequence_after',4),('hardware',True),('total',3)):
   b=dict(v);b[k]=value
   with self.assertRaises(ValueError):m.direct(b)
 def test_empty_and_partial_producer_reject(self):
  m=self.m()
  with self.assertRaises(ValueError):m.audit_process([],m.expected(0))
  with self.assertRaises(ValueError):m.audit_process([m.expected(0),dict(type='final',fds_closed=True)],m.expected(0))
