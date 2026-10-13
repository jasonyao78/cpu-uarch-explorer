"""Write-ahead restore proof; fake only the external device, never metadata evidence."""
import json,tempfile,unittest,importlib
from pathlib import Path
from types import SimpleNamespace
class TransactionTests(unittest.TestCase):
 def scenario(self,kind):
  module=importlib.import_module('tools.diagnostic.perf_user_access_transaction');state={'value':0,'writes':[]}
  class Device:
   def execute(self,args):
    text=args[-1]
    if text.startswith('cat '):return SimpleNamespace(returncode=0,stdout=str(state['value'])+'\n',stderr='',timed_out=False)
    value=int(text.split()[1]);state['writes'].append(value)
    if (kind=='apply-fail' and value==1) or (kind=='restore-fail' and value==0):return SimpleNamespace(returncode=1,stdout='',stderr='fake denial',timed_out=False)
    state['value']=value;return SimpleNamespace(returncode=0,stdout='',stderr='',timed_out=False)
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'own-tx.json';tx=module.PerfUserAccessTransaction(Device(),p)
   def work():
    self.assertEqual((state['value'],json.loads(p.read_text())['state']),(1,'applied'))
    if kind=='work-fail':raise ValueError('actual-work-failed')
    return 'own-metadata'
   if kind=='ok':self.assertEqual(tx.run(work),'own-metadata')
   elif kind=='work-fail':
    with self.assertRaisesRegex(ValueError,'actual-work-failed'):tx.run(work)
   elif kind=='apply-fail':
    with self.assertRaisesRegex(RuntimeError,'write failed'):tx.run(work)
   else:
    with self.assertRaisesRegex(RuntimeError,'restore failed'):tx.run(work)
   j=json.loads(p.read_text());self.assertEqual(j['baseline'],0)
   if kind=='restore-fail':self.assertEqual((state['value'],j['state']),(1,'restore-failed'));self.assertIn('restore_error',j)
   else:self.assertEqual((state['value'],j['state']),(0,'restored'))
   if kind=='work-fail':self.assertIn('work_error',j)
   return state,j
 def test_success_restores(self):self.assertEqual(self.scenario('ok')[0]['writes'],[1,0])
 def test_work_failure_still_restores(self):self.scenario('work-fail')
 def test_apply_failure_does_not_leave_profile_or_mask_cause(self):self.scenario('apply-fail')
 def test_restore_failure_is_persisted_before_propagation(self):self.scenario('restore-fail')
