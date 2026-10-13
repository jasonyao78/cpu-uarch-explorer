"""Coverage, actual emitted words and curve censoring adversarial contracts."""
import copy,importlib,unittest
class Analysis(unittest.TestCase):
 def model(self):
  try:return importlib.import_module('tools.diagnostic.l1_tlb_reach_analysis')
  except ModuleNotFoundError:self.fail('L1 typed consumer not implemented')
 def test_left_right_nonmonotone_and_confirmed_curve(self):
  m=self.model();self.assertEqual(m.onset([(32,0),(48,0),(52,.8),(56,1)])['interval'],[48,52]);self.assertEqual(m.onset([(32,.8),(48,.9)])['status'],'left-censored');self.assertEqual(m.onset([(32,0),(48,.8)])['status'],'right-censored');self.assertEqual(m.onset([(32,0),(48,.8),(52,.9),(56,0)])['status'],'nonmonotone');self.assertEqual(m.onset([(32,0),(48,.02),(52,.9),(56,1)])['status'],'ambiguous')
 def test_real_jit_long_branch_and_terminal_words(self):
  m=self.model();base=0x400000000;order=[0,191,3];w=m.words(base,17,3,order);self.assertEqual(w[-1][0],0xf1000400);self.assertEqual(w[-1][1],0x54000040);self.assertEqual(w[-1][3],0xd65f03c0);self.assertNotEqual(w[-1][2],0);self.assertEqual(w[0][1:],[0,0,0])
 def test_boolean_counter_and_empty_coverage_are_rejected(self):
  m=self.model()
  with self.assertRaises(ValueError):m.counters([True,0,0,0,0,0])
  with self.assertRaises(ValueError):m.audit_process([],m.expected('d',0,'qualification'))
 def test_missing_mapping_and_duplicate_window_reject(self):
  m=self.model();p=m.expected('d',0,'qualification')
  with self.assertRaises(ValueError):m.audit_process([p,dict(type='final',fds_closed=True)],p)
