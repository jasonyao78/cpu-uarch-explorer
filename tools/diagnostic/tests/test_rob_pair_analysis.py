"""Real paired producer programs/schedules; external counters are software fixtures."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from tools.diagnostic import rob_pair_analysis as model
ROOT=Path(__file__).resolve().parents[3]
class PairAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.exe=Path(cls.temp.name)/'producer';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/rob_dependency_pair.c'),'-o',str(cls.exe)],check=True);cls.actual={}
  for a,k in [('none',16),('fsqrt',8),('fsqrt',16)]:
   for rev in (False,True):cls.actual[f'{a}-{k}-{int(rev)}']=[json.loads(l) for l in subprocess.check_output([str(cls.exe),'--plan','--anchor',a,'--chain',str(k),*(['--reverse'] if rev else [])],text=True).splitlines()]
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def records(self,c):
  a,k,rev=model.identity(c);pp=copy.deepcopy(self.actual[f'{a}-{k}-{int(rev)}']);config=pp[0];programs=pp[1:5];by={p['variant']:p for p in programs};rr=pp[:5]+[dict(type='runtime',cpu=7,fpcr=0,code_base=0x10000000,event_ids=[101,102,103,104,105,106])]
  for s in pp[5:]:
   variant=s['variant'];base=30 if a=='none' else 200 if k==8 else 400;cycle=base+(0 if variant.endswith('0') else 30 if a=='none' else 10 if variant=='i128' else 30);p=by[variant];ir=131072*p['loop_instructions']+p['prologue_instructions']+1
   rr.append(dict(s,type='round',code_base=0x10000000,code_matches_plan=True,ns=1000000,enabled=1000000,running=1000000,counts=[cycle*131072,ir,ir,ir,0,0]))
  return rr
 def run_fixture(self):return dict(mode=model.MODE,processes=15,rows=[model.audit_process(self.records(c),c,self.actual) for c in model.conditions()])
 def test_actual_plan_to_main_positive_and_absolute_drift_retained(self):
  model.validate_plan(self.actual);run=self.run_fixture();a=model.analyze(run);self.assertEqual((a['windows'],a['verdict'],len(a['contrasts'])),(480,'paired-dependency-associated-response',80));self.assertFalse(a['physical_entries_certified'])
  # Whole-block offsets preserve paired signs while absolute supply varies.
  for row in run['rows']:
   for s in row['samples']:s['counts'][0]+=s['block']*8*131072
  a=model.analyze(run);self.assertEqual(a['verdict'],'paired-dependency-associated-response');self.assertTrue(any(p['cycle_range_fraction']>.1 for p in a['points']))
 def test_real_record_boundary_rejections(self):
  c=model.conditions()[0];rr=self.records(c)
  for kind in ('config','typed','word','order','base','id','mux','ir','count','shape','copy','ns'):
   r=copy.deepcopy(rr)
   if kind=='config':r[0]['iterations']=1
   elif kind=='typed':r[0]['chain']=True
   elif kind=='word':r[3]['words'][16]^=1
   elif kind=='order':r[-2:]=r[-2:][::-1]
   elif kind=='base':r[-1]['code_base']+=4096
   elif kind=='id':r[5]['event_ids'][1]=101
   elif kind=='mux':r[-1]['running']=1
   elif kind=='ir':r[-1]['counts'][1]=1
   elif kind=='count':r[-1]['counts'][0]=True
   elif kind=='shape':r.pop()
   elif kind=='copy':r[-1]['code_matches_plan']=False
   elif kind=='ns':r[-1]['ns']=0
   with self.subTest(kind=kind),self.assertRaises(ValueError):model.audit_process(r,c,self.actual)
 def test_main_sentinel_none_or_signed_fail_never_promotes(self):
  for kind in ('sentinel','none','signal','semantics'):
   run=self.run_fixture()
   for row in run['rows']:
    a,k,rev=model.identity({'args':row['args']})
    for s in row['samples']:
     if kind=='sentinel' and s['variant']=='d0':s['counts'][0]+=3*131072
     if kind=='none' and a=='none' and s['variant']=='d128':s['counts'][0]+=6*131072
     if kind=='signal' and a=='fsqrt' and s['variant']=='d128':s['counts'][0]-=20*131072
     if kind=='semantics':s['counts'][4]=2*s['counts'][0]
   out=model.analyze(run)
   if kind=='semantics':self.assertEqual(out['cycle_semantics']['0x816d'],'cycle-semantics-incompatible')
   else:self.assertEqual(out['verdict'],'not-qualified',kind)
 def test_coverage_duplicate_typed_and_value_flow(self):
  for kind in ('missing','duplicate','order','sample'):
   run=self.run_fixture()
   if kind=='missing':run['rows'].pop()
   elif kind=='duplicate':run['rows'][-1]=run['rows'][0]
   elif kind=='order':run['rows'][:2]=run['rows'][:2][::-1]
   else:run['rows'][0]['samples'][0]['variant']='d128'
   with self.subTest(kind=kind),self.assertRaises(ValueError):model.analyze(run)
if __name__=='__main__':unittest.main()
