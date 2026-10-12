"""Actual generated A64 plans; only external PMU values are simulated."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SOURCE=ROOT/'probes/diagnostic/rob_destination_control.c'
class DestinationAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not SOURCE.exists():raise AssertionError('destination producer missing')
  cls.temp=tempfile.TemporaryDirectory();cls.exe=Path(cls.temp.name)/'producer';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(SOURCE),'-o',str(cls.exe)],check=True);cls.actual={}
  for a in ('none','serial','independent'):
   for p in ('nop-pair','add-live','nop-add-live','add-discard','nop-add-discard'):
    for g in (0,64):
     for rev in (False,True):cls.actual[f'{a}-{p}-{g}-{int(rev)}']=[json.loads(l) for l in subprocess.check_output([str(cls.exe),'--plan','--anchor',a,'--pattern',p,'--g',str(g),*(['--reverse'] if rev else [])],text=True).splitlines()]
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def model(self):
  from tools.diagnostic import rob_destination_analysis
  return rob_destination_analysis
 def records(self,c):
  m=self.model();a,p,g,rev=m.identity(c);cfg,program,*schedule=copy.deepcopy(self.actual[f'{a}-{p}-{g}-{int(rev)}']);rows=[cfg,program,dict(type='runtime',cpu=7,fpcr=0,code_base=1048576,event_ids=list(range(101,107)))]
  for s in schedule:
   cyc=416 if a=='serial' else 208 if a=='independent' else 1 if not g else 36 if p=='add-live' and s['position']%2 else 21 if p=='add-live' else 20 if p=='add-discard' else 28;ir=m.ITERATIONS*program['loop_instructions']+program['prologue_instructions']+2;rows.append(dict(s,type='round',code_base=1048576,code_matches_plan=True,result_bits=None if a=='none' else [0x3ff0000000000000]*2,gpr_result=0x3333 if p.endswith('live') and g else 0,ns=10000000,enabled=10000000,running=10000000,counts=[cyc*m.ITERATIONS,ir,ir,0,0,0]))
  return rows
 def data(self):
  m=self.model();return dict(mode=m.MODE,processes=24,rows=[m.audit_process(self.records(c),c,self.actual) for c in m.conditions()])
 def test_actual_code_oracle_only_Rd_changes_inside_loop(self):
  m=self.model();m.validate_plan(self.actual);self.assertEqual(len(self.actual),60)
  for a in ('none','serial','independent'):
   for prefix in ('add','nop-add'):
    live=self.actual[f'{a}-{prefix}-live-64-0'][1];dead=self.actual[f'{a}-{prefix}-discard-64-0'][1];stop=live['branch_offset']//4+1;self.assertEqual([w&~31 for w in live['words'][:stop]],[w&~31 for w in dead['words'][:stop]])
    adds=lambda row:[w for w in row['words'] if w&0xff000000==0x8b000000];self.assertEqual(len(adds(live)),128);self.assertTrue(all(w&31==31 for w in adds(dead)));self.assertEqual(adds(live),[0x8b110200|(4+j%8) for j in range(64)]*2)
 def test_complete_destination_contrast_and_qualifications(self):
  a=self.model().analyze(self.data());self.assertEqual((a['windows'],a['status']),(192,'DISCARD_DESTINATION_REMOVES_OBSERVED_VARIABILITY'));self.assertTrue(a['qualified']);self.assertFalse(a['physical_entries_certified']);self.assertEqual(a['comparisons'][1]['status'],'VARIABILITY_NOT_REPLICATED')
 def test_real_window_code_checksum_and_type_reject(self):
  m=self.model();c=next(c for c in m.conditions() if m.identity(c)[1]=='add-discard')
  for bad in ('missing','extra','order','word','typed','mux','ir','result','gpr','ids','base'):
   rr=self.records(c)
   if bad=='missing':rr.pop()
   elif bad=='extra':rr.append(rr[-1])
   elif bad=='order':rr[-2:]=rr[-2:][::-1]
   elif bad=='word':rr[1]['words'][16]^=1
   elif bad=='typed':rr[0]['groups']=True
   elif bad=='mux':rr[-1]['running']=1
   elif bad=='ir':rr[-1]['counts'][1]=1
   elif bad=='result':rr[-1]['result_bits']=[0,0]
   elif bad=='gpr':rr[-1]['gpr_result']=0x3333
   elif bad=='ids':rr[2]['event_ids'][0]=rr[2]['event_ids'][1]
   elif bad=='base':rr[-1]['code_base']+=4096
   with self.subTest(bad=bad),self.assertRaises(ValueError):m.audit_process(rr,c,self.actual)
 def test_variable_live_is_studied_not_discarded(self):
  m=self.model();r=self.data();self.assertTrue(m.analyze(r)['qualified'])
  for row in r['rows']:
   if row['config']['pattern']=='nop-pair' and row['config']['groups']==64:row['samples'][0]['counts'][0]=100*m.ITERATIONS
  self.assertFalse(m.analyze(r)['qualified'])
 def test_not_replicated_and_partial_epoch_variability(self):
  m=self.model();r=self.data()
  for row in r['rows']:
   if row['config']['pattern']=='add-live':
    for s in row['samples']:s['counts'][0]=21*m.ITERATIONS
  self.assertEqual(m.analyze(r)['status'],'VARIABILITY_NOT_REPLICATED')
  row=next(row for row in r['rows'] if row['config']['pattern']=='add-live');row['samples'][0]['counts'][0]=36*m.ITERATIONS;self.assertEqual(m.analyze(r)['status'],'INCONCLUSIVE')
  with self.assertRaises(ValueError):m.analyze(dict(r,rows=r['rows'][::-1]))
 def test_cache_gate_is_explicit(self):
  m=self.model();r=self.data();r['rows'][0]['samples'][0]['counts'][5]=132;self.assertFalse(m.analyze(r)['qualified'])
class DestinationPresence(unittest.TestCase):
 def test_driver_exists(self):self.assertTrue((ROOT/'tools/diagnostic/run_sm8650_rob_destination.py').exists())
if __name__=='__main__':unittest.main()
