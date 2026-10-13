"""Producer-native identities, strict coverage and order-invariant packet parsing."""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class Packets(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/rob_admission_window.c'),'-o',str(b)],check=True)
   cls.schedule=[json.loads(l) for l in subprocess.check_output([str(b),'--plan','--chain','16','--gap','0','--filler','sink','--indices','32,3,4,5,6,7']).splitlines()][5:]
 def decoder(self):
  try:return importlib.import_module('tools.diagnostic.owned_roi_packets').decode
  except ModuleNotFoundError:self.fail('packet decoder missing')
 def rows(self):
  return [dict(type=kind,trial=s['trial'],position=s['position'],**({'ordinal':j} if kind=='warm-roi' else {})) for s in self.schedule for j,kind in enumerate(['warm-roi']*4+['round'])]
 def test_real_native_identity_coverage_and_permutation(self):
  f=self.decoder();a=f(self.rows(),self.schedule);self.assertEqual(a,f(list(reversed(self.rows())),self.schedule));self.assertEqual(len(a['valid']),256)
 def test_missing_duplicate_conflict(self):
  f=self.decoder();rr=self.rows()
  for bad in (rr[:-1],rr+[rr[0]],rr+[dict(rr[0],position=9)]):
   with self.assertRaises(ValueError):f(bad,self.schedule)
 def test_invalid_needs_reason_trace_and_budget(self):
  f=self.decoder();rr=self.rows()[5:];s=self.schedule[0];identity=dict(trial=s['trial'],position=s['position']);inv=dict(type='invalid-packet',**identity,metrics={},failure={'reason':'ROI-metadata-changed'},completed_warm=0,stage=0);rej=dict(type='rejected-window',**identity,stage=0,metrics={},hardware_values_usable=False,reason='ROI-metadata-changed')
  a=f([inv,rej,*rr],self.schedule);self.assertEqual(len(a['valid']),255);self.assertEqual(len(a['invalid']),1)
  with self.assertRaises(ValueError):f([inv,*rr],self.schedule)
  with self.assertRaises(ValueError):f([dict(inv,failure={'reason':'metric-low'}),rej,*rr],self.schedule)

 def test_pairing_preserves_trial_labels(self):
  self.decoder();from tools.diagnostic.owned_roi_packets import paired_trials
  cells={(t,'a'):1 for t in range(32)}|{(t,'b'):1 for t in range(32)};cells.pop((7,'b'));self.assertNotIn(7,paired_trials(cells,('a',),('b',)));self.assertEqual(len(paired_trials(cells,('a',),('b',))),31);cells.pop((8,'b'))
  with self.assertRaises(ValueError):paired_trials(cells,('a',),('b',))
