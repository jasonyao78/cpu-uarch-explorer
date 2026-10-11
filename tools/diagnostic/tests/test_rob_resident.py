"""Real resident producer plans; external PMU fixtures are software evidence only."""
import json,subprocess,tempfile,unittest,struct
from pathlib import Path
from tools.diagnostic.rob_dependency_analysis import expected_code
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'probes/diagnostic/rob_resident_control.c'
SPECS=[('none','independent',0),('none','independent',128),('none','dependent',128),('fsqrt','independent',128),('fsqrt','dependent',128)]
class ResidentProducer(unittest.TestCase):
 def test_real_program_and_all_schedules(self):
  self.assertTrue(SOURCE.exists(),'resident control producer missing')
  with tempfile.TemporaryDirectory() as d:
   exe=Path(d)/'resident';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(SOURCE),'-o',str(exe)],check=True)
   for a,link,n in SPECS:
    for rev in (False,True):
     args=['--plan','--anchor',a,'--link',link,'--n',str(n),*(['--reverse'] if rev else [])]
     rr=[json.loads(l) for l in subprocess.check_output([str(exe),*args],text=True).splitlines()];self.assertEqual(len(rr),18);cfg,p,*ss=rr
     self.assertEqual((cfg['probe'],cfg['anchor'],cfg['link'],cfg['n'],cfg['windows']),('rob-resident-control',a,link,n,16))
     code=expected_code({'args':['--anchor-link',link,'-a',a,'--chain','16','-n',str(n)]});self.assertEqual(struct.pack('<'+'I'*len(p['words']),*p['words']),code)
     want=[(b,s,v) for b in range(8) for s,v in enumerate(['resident','reinstall'] if b%2==0 else ['reinstall','resident'])]
     if rev:want.reverse()
     self.assertEqual([(w['block'],w['slot'],w['preparation']) for w in ss],want)
     g=1
     for pos,s in enumerate(ss):
      g+=s['preparation']=='reinstall';self.assertEqual((s['position'],s['installation_generation']),(pos,g))
   for args in ([],['--plan'],['--plan','--anchor','none','--link','dependent','--n','0'],['--plan','--anchor','fsqrt','--link','independent','--n','0']):self.assertNotEqual(subprocess.run([str(exe),*args],capture_output=True).returncode,0)

class ResidentAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.exe=Path(cls.temp.name)/'producer'
  subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(SOURCE),'-o',str(cls.exe)],check=True)
  cls.actual={}
  for a,link,n in SPECS:
   for rev in (False,True):
    args=['--plan','--anchor',a,'--link',link,'--n',str(n),*(['--reverse'] if rev else [])]
    cls.actual[f'{a}-{link}-{n}-{int(rev)}']=[json.loads(l) for l in subprocess.check_output([str(cls.exe),*args],text=True).splitlines()]
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def model(self):
  self.assertTrue((ROOT/'tools/diagnostic/rob_resident_analysis.py').exists(),'resident consumer missing')
  from tools.diagnostic import rob_resident_analysis
  return rob_resident_analysis
 def records(self,c):
  model=self.model();a,link,n,rev=model.identity(c);want=json.loads(json.dumps(self.actual[f'{a}-{link}-{n}-{int(rev)}']));cfg,program,*schedule=want
  records=[cfg,program,dict(type='runtime',cpu=7,fpcr=0,code_base=0x100000,event_ids=list(range(101,107)))]
  for s in schedule:
   cycle=2 if n==0 else (50 if a=='none' else 416)
   if s['preparation']=='reinstall' and a=='none' and n==128 and link=='independent':cycle+=4
   ir=131072*program['loop_instructions']+program['prologue_instructions']+1
   records.append(dict(s,type='round',code_base=0x100000,code_matches_plan=True,ns=10000000,enabled=10000000,running=10000000,counts=[cycle*131072,ir,ir,ir,0,0]))
  return records
 def run_fixture(self):
  model=self.model();rows=[model.audit_process(self.records(c),c,self.actual) for c in model.conditions()]
  return dict(mode=model.MODE,processes=15,rows=rows)
 def test_real_plans_consumer_complete_coverage_and_effect(self):
  m=self.model();m.validate_plan(self.actual);r=m.analyze(self.run_fixture());self.assertEqual((r['windows'],len(r['window_ratios'])),(240,240));self.assertEqual(r['primary']['maintenance_effect'],'maintenance-associated-increase');self.assertFalse(r['physical_entries_certified'])
 def test_rehashed_style_window_identity_counterexamples(self):
  import copy
  m=self.model();c=m.conditions()[0]
  for bad in ('missing','duplicate','order','program','generation','preparation','base','ids','mux','ir','timing','count-type','config-type','copy'):
   rr=copy.deepcopy(self.records(c))
   if bad=='missing':rr.pop()
   elif bad=='duplicate':rr.append(rr[-1])
   elif bad=='order':rr[-2:]=rr[-2:][::-1]
   elif bad=='program':rr[1]['words'][16]^=1
   elif bad=='generation':rr[-1]['installation_generation']+=1
   elif bad=='preparation':rr[-1]['preparation']='reinstall' if rr[-1]['preparation']=='resident' else 'resident'
   elif bad=='base':rr[-1]['code_base']+=4096
   elif bad=='ids':rr[2]['event_ids'][1]=rr[2]['event_ids'][0]
   elif bad=='mux':rr[3]['running']-=1
   elif bad=='ir':rr[3]['counts'][1]=1
   elif bad=='timing':rr[3]['ns']=0
   elif bad=='count-type':rr[3]['counts'][0]=True
   elif bad=='config-type':rr[0]['n']=False
   elif bad=='copy':rr[3]['code_matches_plan']=False
   with self.subTest(bad=bad),self.assertRaises(ValueError):m.audit_process(rr,c,self.actual)
 def test_scientific_gate_does_not_rescue_variability_or_ignore_signs(self):
  m=self.model();run=self.run_fixture();primary=[r for r in run['rows'] if r['config']['anchor']=='none' and r['config']['n']==128 and r['config']['link']=='independent']
  for r in primary:
   r['samples'][0]['counts'][0]=100*131072
  a=m.analyze(run);self.assertEqual(a['primary']['maintenance_effect'],'effect-not-replicated');self.assertEqual(a['primary']['state'],'resident-supply-still-variable')
  with self.assertRaises(ValueError):m.analyze(dict(run,rows=run['rows'][::-1]))
 def test_exact_effect_boundary_is_not_rounded_into_pass(self):
  m=self.model();run=self.run_fixture()
  for r in run['rows']:
   if r['config']['anchor']=='none' and r['config']['n']==128 and r['config']['link']=='independent':
    for s in r['samples']:
     if s['preparation']=='reinstall':s['counts'][0]=52*131072
  self.assertEqual(m.analyze(run)['primary']['maintenance_effect'],'effect-not-replicated')
class ResidentDriverPresence(unittest.TestCase):
 def test_production_driver_exists(self):
  self.assertTrue((ROOT/'tools/diagnostic/run_sm8650_rob_resident.py').exists(),'resident production driver missing')
if __name__=='__main__':unittest.main()
