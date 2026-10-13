"""Actual metadata-only producer; policy mutation and unsafe MRS are forbidden."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class UserMetadata(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.src=ROOT/'probes/diagnostic/pmu_user_reader.c';cls.tmp=tempfile.TemporaryDirectory();cls.bin=Path(cls.tmp.name)/'metadata'
  if cls.src.exists():subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(cls.src),'-o',str(cls.bin)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_actual_user_flags_and_no_register_reads(self):
  self.assertTrue(self.src.exists(),'safe PMU metadata producer missing')
  for flag in (2,3):
   p=json.loads(subprocess.check_output([str(self.bin),'--plan','--config1',str(flag)],text=True));self.assertEqual(p['events'],[17,8,112,113]);self.assertEqual(p['config1'],flag);self.assertTrue(p['metadata_only']);self.assertEqual(p['counter_register_reads'],0);self.assertFalse(p['global_policy_mutation']);self.assertTrue(p['own_thread_only'])
 def test_unregistered_flag_and_host_run_fail_closed(self):
  self.assertTrue(self.src.exists(),'safe PMU metadata producer missing')
  for argv in (['--plan','--config1','0'],['--run','--config1','2']):
   q=subprocess.run([str(self.bin),*argv],text=True,capture_output=True);self.assertNotEqual(q.returncode,0);self.assertEqual(json.loads(q.stdout.splitlines()[-1])['metrics'],{})
