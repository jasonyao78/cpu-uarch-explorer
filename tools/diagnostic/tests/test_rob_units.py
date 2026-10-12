"""Real A64 unit candidate code, simulated external PMU; no physical entry certificate."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SOURCE=ROOT/'probes/diagnostic/rob_retirement_units.c'
GRIDS={'nop-pair':(0,64,256,288,320,336,352,384),'nop-add-discard':(0,64,256,288,320,336,352,384),'add-sub-discard':(0,64,128,144,160,168,176,192)}
class UnitsAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not SOURCE.exists():raise AssertionError('units producer missing')
  cls.temp=tempfile.TemporaryDirectory();cls.exe=Path(cls.temp.name)/'producer';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(SOURCE),'-o',str(cls.exe)],check=True);cls.actual={}
  for a in ('none','serial','independent'):
   for p,grid in GRIDS.items():
    for g in grid:
     for k in (16,32):
      for rev in (False,True):cls.actual[f'{a}-{p}-g{g}-k{k}-r{int(rev)}']=[json.loads(l) for l in subprocess.check_output([str(cls.exe),'--plan','--anchor',a,'--pattern',p,'--g',str(g),'--chain',str(k),*(['--reverse'] if rev else [])],text=True).splitlines()]
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def model(self):
  from tools.diagnostic import rob_units_analysis
  return rob_units_analysis
 def records(self,c):
  m=self.model();a,p,g,k,rev=m.identity(c);cfg,program,*sched=copy.deepcopy(self.actual[f'{a}-{p}-g{g}-k{k}-r{int(rev)}']);rr=[cfg,program,dict(type='runtime',cpu=7,fpcr=0,code_base=1048576,event_ids=list(range(101,107)))];alpha=2 if p=='add-sub-discard' else 1
  for s in sched:
   cyc=(1 if not g else 4*g/6 if alpha==2 else 4*g/9) if a=='none' else 26*k if a=='serial' or alpha*g+2*k>=384 else 13*k;ir=m.ITERATIONS*program['loop_instructions']+program['prologue_instructions']+2;rr.append(dict(s,type='round',code_base=1048576,code_matches_plan=True,result_bits=None if a=='none' else [0x3ff0000000000000]*2,gpr_result=0,ns=10000000,enabled=10000000,running=10000000,counts=[round(cyc*m.ITERATIONS),ir,ir,0,0,0]))
  return rr
 def data(self,phase='qualification'):
  m=self.model();return dict(mode=m.MODE,phase=phase,processes=len(m.conditions(phase)),rows=[m.audit_process(self.records(c),c,self.actual) for c in m.conditions(phase)])
 def test_actual_oracle_SUB_does_not_set_flags_and_none_shared(self):
  m=self.model();m.validate_plan(self.actual);self.assertEqual(len(self.actual),288)
  for a in ('none','serial','independent'):
   words=self.actual[f'{a}-add-sub-discard-g64-k16-r0'][1]['words'];subs=[w for w in words if w&0xff000000==0xcb000000];self.assertEqual(subs,[0xcb11021f]*128)
  for p,grid in GRIDS.items():
   for g in grid:self.assertEqual(self.actual[f'none-{p}-g{g}-k16-r0'][1],self.actual[f'none-{p}-g{g}-k32-r0'][1])
 def test_qualification_complete_and_finite_proxy_model(self):
  m=self.model();q=m.analyze(self.data());self.assertEqual((q['windows'],q['qualified']),(192,True));a=m.analyze(self.data('scan'));self.assertEqual(a['windows'],2352);self.assertEqual(a['status'],'COMMON_RETIREMENT_PROXY_COMPATIBLE');self.assertEqual(a['common_proxy_interval'],[368,384]);self.assertFalse(a['physical_entries_certified']);self.assertFalse(a['allocation_units_certified'])
 def test_mixed_supply_variability_prevents_scan_qualification(self):
  m=self.model();r=self.data()
  for row in r['rows']:
   if row['config']['pattern']=='add-sub-discard':row['samples'][0]['counts'][0]=100*m.ITERATIONS
  self.assertFalse(m.analyze(r)['qualified'])
 def test_actual_program_record_and_type_reject(self):
  m=self.model();c=m.conditions('qualification')[0]
  for bad in ('missing','duplicate','order','word','chain','gpr','ids','mux','result','ir'):
   rr=self.records(c)
   if bad=='missing':rr.pop()
   elif bad=='duplicate':rr.append(rr[-1])
   elif bad=='order':rr[-2:]=rr[-2:][::-1]
   elif bad=='word':rr[1]['words'][16]^=1
   elif bad=='chain':rr[0]['chain']=True
   elif bad=='gpr':rr[3]['gpr_result']=1
   elif bad=='ids':rr[2]['event_ids'][0]=rr[2]['event_ids'][1]
   elif bad=='mux':rr[3]['running']=1
   elif bad=='result':rr[3]['result_bits']=[0,0]
   elif bad=='ir':rr[3]['counts'][1]=1
   with self.subTest(bad=bad),self.assertRaises(ValueError):m.audit_process(rr,c,self.actual)
 def test_scan_missing_order_background_and_partial_curves_never_support_model(self):
  m=self.model();r=self.data('scan')
  with self.assertRaises(ValueError):m.analyze(dict(r,rows=r['rows'][::-1]))
  for row in r['rows']:
   if row['config']['pattern']=='nop-add-discard' and row['config']['anchor']=='none' and row['config']['groups']==320:row['samples'][0]['counts'][0]=1000*m.ITERATIONS
  a=m.analyze(r);self.assertNotEqual(a['status'],'COMMON_RETIREMENT_PROXY_COMPATIBLE');self.assertIsNone(a['common_proxy_interval'])
 def test_secondary_curve_nonmonotone_and_censoring(self):
  m=self.model()
  for kind in ('left','left-nonmonotone','right'):
   r=self.data('scan')
   for row in r['rows']:
    c=row['config']
    if c['pattern']=='nop-pair' and c['groups']>=256 and c['anchor']=='independent' and c['chain']==16:
     high=kind=='left' or (kind=='left-nonmonotone' and c['groups']!=320) or (kind=='right' and c['groups']==384)
     for s in row['samples']:s['counts'][0]=(416 if high else 208)*m.ITERATIONS
   a=m.analyze(r);curves=[c for c in a['curves'] if c['pattern']=='nop-pair' and c['chain']==16];self.assertTrue(all(c['status']=={'left':'left-censored','left-nonmonotone':'ambiguous','right':'right-censored'}[kind] for c in curves))
class UnitsPresence(unittest.TestCase):
 def test_driver_exists(self):self.assertTrue((ROOT/'tools/diagnostic/run_sm8650_rob_units.py').exists())
if __name__=='__main__':unittest.main()
