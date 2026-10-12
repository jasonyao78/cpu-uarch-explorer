"""Actual group producer plans; only external PMU numbers are synthetic."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SOURCE=ROOT/'probes/diagnostic/rob_fusion_groups.c'
class FusionAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not SOURCE.exists():raise AssertionError('fusion group producer missing')
  cls.temp=tempfile.TemporaryDirectory();cls.exe=Path(cls.temp.name)/'producer'
  subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(SOURCE),'-o',str(cls.exe)],check=True);cls.actual={}
  for a in ('none','serial','independent'):
   for pattern in ('nop-pair','add','nop-add'):
    for g in (0,64,128,192,256,384):
     for rev in (False,True):
      args=['--plan','--anchor',a,'--pattern',pattern,'--g',str(g),*(['--reverse'] if rev else [])]
      cls.actual[f'{a}-{pattern}-{g}-{int(rev)}']=[json.loads(l) for l in subprocess.check_output([str(cls.exe),*args],text=True).splitlines()]
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def model(self):
  from tools.diagnostic import rob_fusion_analysis
  return rob_fusion_analysis
 def records(self,c):
  m=self.model();a,p,g,rev=m.identity(c);cfg,program,*ss=copy.deepcopy(self.actual[f'{a}-{p}-{g}-{int(rev)}']);rr=[cfg,program,dict(type='runtime',cpu=7,fpcr=0,code_base=0x100000,event_ids=list(range(101,107)))]
  for s in ss:
   cycle=2+g*(2 if p!='add' else 1)//4 if a=='none' else 416 if a=='serial' else 350 if g>=128 and p!='nop-pair' else 320 if g>=256 else 208
   ir=m.ITERATIONS*program['loop_instructions']+program['prologue_instructions']+2
   rr.append(dict(s,type='round',code_base=0x100000,code_matches_plan=True,result_bits=None if a=='none' else [0x3ff0000000000000]*2,gpr_result=0x3333 if p!='nop-pair' and g else 0,ns=10000000,enabled=10000000,running=10000000,counts=[cycle*m.ITERATIONS,ir,ir,0,0,0]))
  return rr
 def run_fixture(self,phase='qualification'):
  m=self.model();return dict(mode=m.MODE,phase=phase,processes=len(m.conditions(phase)),rows=[m.audit_process(self.records(c),c,self.actual) for c in m.conditions(phase)])
 def test_real_byte_oracle_shared_zero_and_equal_ALU_sequence(self):
  m=self.model();m.validate_plan(self.actual)
  for a in ('none','serial','independent'):
   self.assertEqual(self.actual[f'{a}-add-0-0'][1],self.actual[f'{a}-nop-pair-0-0'][1]);self.assertEqual(self.actual[f'{a}-nop-add-0-0'][1],self.actual[f'{a}-nop-pair-0-0'][1])
   for g in m.GRID[1:]:
    aa=self.actual[f'{a}-add-{g}-0'][1]['words'];na=self.actual[f'{a}-nop-add-{g}-0'][1]['words'];adds=lambda words:[x for x in words if x&0xff000000==0x8b000000]
    self.assertEqual(adds(aa),adds(na));self.assertEqual(len(adds(aa)),2*g);self.assertEqual(len(na)-len(aa),2*g)
 def test_finite_complete_qualified_matching_work_and_GPR_flow(self):
  m=self.model();self.assertEqual(m.analyze(self.run_fixture())['status'],'group-controls-qualified');a=m.analyze(self.run_fixture('scan'));self.assertEqual(a['status'],'fusion-compatible-work-response');self.assertEqual(a['gpr_flow'],'replicated-GPR-flow-associated-response');self.assertEqual(a['windows'],1152);self.assertFalse(a['physical_entries_certified'])
 def test_typed_window_and_checksum_counterexamples(self):
  m=self.model();c=m.conditions('qualification')[0]
  for bad in ('missing','duplicate','order','word','bool','base','ids','mux','ir','count','result','gpr','copy','round','zero'):
   rr=copy.deepcopy(self.records(c))
   if bad=='missing':rr.pop()
   elif bad=='duplicate':rr.append(rr[-1])
   elif bad=='order':rr[-2:]=rr[-2:][::-1]
   elif bad=='word':rr[1]['words'][16]^=1
   elif bad=='bool':rr[0]['groups']=False
   elif bad=='base':rr[-1]['code_base']+=4096
   elif bad=='ids':rr[2]['event_ids'][1]=rr[2]['event_ids'][0]
   elif bad=='mux':rr[-1]['running']-=1
   elif bad=='ir':rr[-1]['counts'][1]=1
   elif bad=='count':rr[-1]['counts'][0]=True
   elif bad=='result':rr[-1]['result_bits']=[0,0]
   elif bad=='gpr':rr[-1]['gpr_result']=1
   elif bad=='copy':rr[-1]['code_matches_plan']=False
   elif bad=='round':rr[-1]['round']+=1
   elif bad=='zero':rr[-1]['ns']=0
   with self.subTest(bad=bad),self.assertRaises(ValueError):m.audit_process(rr,c,self.actual)
 def test_supply_and_Icache_noise_reach_scientific_exit(self):
  m=self.model();run=self.run_fixture()
  for r in run['rows']:
   if r['config']['pattern']=='nop-add':r['samples'][0]['counts'][0]=400*m.ITERATIONS
  self.assertFalse(m.analyze(run)['qualified'])
  run=self.run_fixture();run['rows'][0]['samples'][0]['counts'][5]=132
  self.assertFalse(m.analyze(run)['qualified'])
 def test_matching_requires_two_adjacent_groups_and_full_value_flow(self):
  m=self.model();run=self.run_fixture('scan')
  for r in run['rows']:
   if r['config']['pattern']=='nop-add' and r['config']['anchor']=='independent' and r['config']['groups']>=192:
    for s in r['samples']:s['counts'][0]=390*m.ITERATIONS
  self.assertNotEqual(m.analyze(run)['status'],'fusion-compatible-work-response')
  with self.assertRaises(ValueError):m.analyze(dict(run,rows=run['rows'][::-1]))
class FusionPresence(unittest.TestCase):
 def test_driver_exists(self):self.assertTrue((ROOT/'tools/diagnostic/run_sm8650_rob_fusion.py').exists(),'fusion driver missing')
if __name__=='__main__':unittest.main()
