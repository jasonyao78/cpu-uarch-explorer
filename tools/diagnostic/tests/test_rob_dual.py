"""Real generated dual-chain program; PMU fixtures are explicitly synthetic."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'probes/diagnostic/rob_dual_anchor.c'
class DualAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not SOURCE.exists():raise AssertionError('dual anchor producer missing')
  cls.temp=tempfile.TemporaryDirectory();cls.exe=Path(cls.temp.name)/'producer'
  subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(SOURCE),'-o',str(cls.exe)],check=True)
  cls.actual={}
  for a in ('none','serial','independent'):
   for n in (0,128,256,384,512,640,672,704,768,896):
    for rev in (False,True):
     args=['--plan','--anchor',a,'--n',str(n),*(['--reverse'] if rev else [])]
     cls.actual[f'{a}-{n}-{int(rev)}']=[json.loads(l) for l in subprocess.check_output([str(cls.exe),*args],text=True).splitlines()]
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def model(self):
  from tools.diagnostic import rob_dual_analysis
  return rob_dual_analysis
 def records(self,c):
  m=self.model();a,n,rev=m.identity(c);cfg,program,*ss=copy.deepcopy(self.actual[f'{a}-{n}-{int(rev)}'])
  rr=[cfg,program,dict(type='runtime',cpu=7,fpcr=0,code_base=0x100000,event_ids=list(range(101,107)))]
  for s in ss:
   cycle=2+n//8 if a=='none' else 416 if a=='serial' else 208 if n<=512 else 320
   ir=m.ITERATIONS*program['loop_instructions']+program['prologue_instructions']+1
   rr.append(dict(s,type='round',code_base=0x100000,code_matches_plan=True,result_bits=None if a=='none' else [0x3ff0000000000000]*2,ns=10000000,enabled=10000000,running=10000000,counts=[cycle*m.ITERATIONS,ir,ir,ir,0,0]))
  return rr
 def run_fixture(self,phase='qualification'):
  m=self.model();return dict(mode=m.MODE,phase=phase,processes=len(m.conditions(phase)),rows=[m.audit_process(self.records(c),c,self.actual) for c in m.conditions(phase)])
 def test_actual_programs_only_second_chain_operands_change(self):
  m=self.model();m.validate_plan(self.actual)
  for n in m.GRID:
   s=self.actual[f'serial-{n}-0'][1];i=self.actual[f'independent-{n}-0'][1]
   diff=[j for j,(x,y) in enumerate(zip(s['words'],i['words'])) if x!=y]
   self.assertEqual(diff,list(range(32+n,48+n)))
   self.assertTrue(all(s['words'][j]==0x1e61c000 and i['words'][j]==0x1e61c021 for j in diff))
   self.assertEqual(s['words'][14],0x9e6701e1)
 def test_qualification_and_finite_interval_actual_plan(self):
  m=self.model();self.assertEqual(m.analyze(self.run_fixture())['status'],'dual-anchor-overlap-qualified')
  a=m.analyze(self.run_fixture('scan'));self.assertEqual(a['status'],'effective-overlap-loss-interval');self.assertEqual(a['interval'],[512,640]);self.assertFalse(a['physical_entries_certified'])
 def test_typed_real_program_window_counterexamples(self):
  m=self.model();c=m.conditions('qualification')[0]
  for bad in ('missing','duplicate','order','word','config-bool','base','ids','mux','ir','count-bool','result','code-copy','round','zero-time'):
   rr=copy.deepcopy(self.records(c))
   if bad=='missing':rr.pop()
   elif bad=='duplicate':rr.append(rr[-1])
   elif bad=='order':rr[-2:]=rr[-2:][::-1]
   elif bad=='word':rr[1]['words'][16]^=1
   elif bad=='config-bool':rr[0]['n']=False
   elif bad=='base':rr[-1]['code_base']+=4096
   elif bad=='ids':rr[2]['event_ids'][1]=rr[2]['event_ids'][0]
   elif bad=='mux':rr[-1]['running']-=1
   elif bad=='ir':rr[-1]['counts'][1]=1
   elif bad=='count-bool':rr[-1]['counts'][0]=True
   elif bad=='result':rr[-1]['result_bits']=[0,0]
   elif bad=='code-copy':rr[-1]['code_matches_plan']=False
   elif bad=='round':rr[-1]['round']+=1
   elif bad=='zero-time':rr[-1]['ns']=0
   with self.subTest(bad=bad),self.assertRaises(ValueError):m.audit_process(rr,c,self.actual)
 def test_failed_overlap_and_unstable_supply_are_not_rescued(self):
  m=self.model();run=self.run_fixture()
  for r in run['rows']:
   if r['config']['anchor']=='independent':
    for s in r['samples']:s['counts'][0]=416*m.ITERATIONS
  self.assertEqual(m.analyze(run)['status'],'not-qualified')
  run=self.run_fixture()
  for r in run['rows']:
   if r['config']['anchor']=='none' and r['config']['n']==128:r['samples'][0]['counts'][0]=400*m.ITERATIONS
  self.assertEqual(m.analyze(run)['status'],'not-qualified')
 def test_exact_gates_censor_and_nonmonotonic(self):
  m=self.model();run=self.run_fixture('scan')
  for r in run['rows']:
   if r['config']['anchor']=='independent' and r['config']['n']==704:
    for s in r['samples']:s['counts'][0]=208*m.ITERATIONS
  self.assertEqual(m.analyze(run)['status'],'nonmonotonic')
  run=self.run_fixture('scan')
  for r in run['rows']:
   if r['config']['anchor']=='independent' and r['config']['n']<896:
    for s in r['samples']:s['counts'][0]=208*m.ITERATIONS
  self.assertEqual(m.analyze(run)['status'],'right-censored')
  with self.assertRaises(ValueError):m.analyze(dict(run,rows=run['rows'][::-1]))
class DualDriverPresence(unittest.TestCase):
 def test_driver_exists(self):self.assertTrue((ROOT/'tools/diagnostic/run_sm8650_rob_dual.py').exists(),'dual production driver missing')
if __name__=='__main__':unittest.main()
