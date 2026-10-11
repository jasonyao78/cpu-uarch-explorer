"""Real immutable C generator, with external runtime/PMU observations stubbed.

No hand-authored producer configuration or generated code. Synthetic curves
verify naming boundaries only; they are not target measurements.
"""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE='docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'
CLASSES=('nop','add','movi','movr','fadd');GRID=(0,128,256,384,512,704,768)
def expected_conditions():
 base=[(c,a,n) for c in CLASSES for a in ('none','fsqrt') for n in GRID];out=[]
 for e in (0,1):
  for c,a,n in (base if e==0 else reversed(base)):
   args=['-i','131072','-r','3','--pin','7','--pmu-type','8','-e','0x03','-e','0x17','-e','0x34','-e','0x02','-t',c,'-a',a,'--chain','16','--align','0','-n',str(n)]
   out.append(dict(name=f'e{e}-{c}-{a}-k16-a0-n{n}',args=args))
 return out
class ResourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name)
  for rel in (SOURCE,'probes/common/perf_group_read.h','probes/common/rob_backing.h'):(d/Path(rel).name).write_bytes(subprocess.check_output(['git','show','1ef4baa:'+rel],cwd=ROOT))
  exe=d/'producer';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(d),str(d/'rob_window_probe.c'),'-o',str(exe)],check=True)
  cls.actual={}
  for p in expected_conditions():
   f=d/'code';config=json.loads(subprocess.check_output([str(exe),*p['args'],'--write-asm',str(f)],text=True));cls.actual[p['name']]=(config,f.read_bytes())
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def module(self):
  self.assertTrue((ROOT/'tools/diagnostic/rob_resource_analysis.py').exists(),'new resource consumer not implemented')
  return importlib.import_module('tools.diagnostic.rob_resource_analysis')
 def test_independent_conditions_and_all_actual_c_config_code(self):
  m=self.module();p=m.registered_plan();self.assertEqual(p['conditions'],expected_conditions());self.assertEqual((p['processes'],p['windows']),(140,420))
  driver=importlib.import_module('tools.diagnostic.run_sm8650_minimal');self.assertEqual(driver.conditions('rob-resource'),[(r['name'],r['args']) for r in p['conditions']])
  for c in p['conditions']:
   config,code=self.actual[c['name']];self.assertEqual(config,m.expected_config(c));self.assertEqual(m.expected_code(c),code);m.audit_code(config,code)
 def records(self,name):
  c,code=self.actual[name];c=copy.deepcopy(c);expected=c['iterations']*c['loop_instructions']+17
  runtime=dict(type='runtime',fpcr=0,cpu=7,loop_address_mod64=0,ring_nodes=0,distinct_lines_per_call=0,mapping_4k_verified=None,backing_verified=None,backing_page_bytes=0,backing_info=None,event_ids=[1,2,3,4,5,6])
  rows=[dict(type='round',round=r,serial=False,pair_step=0,ns=100,enabled=100,running=100,metrics={'0x11':100000,'0x8':expected,'0x3':0,'0x17':0,'0x34':0,'0x2':0},backing_verified=None,backing_before=None,backing_after=None) for r in range(3)]
  return [c,runtime,*rows],code
 def test_real_config_to_synthetic_runtime_rejects_boundary_corruption(self):
  m=self.module();case=expected_conditions()[30];r,code=self.records(case['name']);m.audit_process(r,case,code)
  for kind in ('config-type','runtime-type','runtime-none','round-none','id-duplicate','id-bool','missing','duplicate','order','mux','cycles','count','ns','serial','branch','register'):
   bad=copy.deepcopy(r);blob=code
   if kind=='config-type':bad[0]['n']=float(bad[0]['n'])
   elif kind=='runtime-type':bad[1]['cpu']=True
   elif kind=='runtime-none':bad[1]=None
   elif kind=='round-none':bad[2]=None
   elif kind=='id-duplicate':bad[1]['event_ids'][-1]=1
   elif kind=='id-bool':bad[1]['event_ids'][0]=True
   elif kind=='missing':bad.pop()
   elif kind=='duplicate':bad[-1]=copy.deepcopy(bad[-2])
   elif kind=='order':bad[-2:]=bad[-2:][::-1]
   elif kind=='mux':bad[2]['running']=99
   elif kind=='cycles':bad[2]['metrics']['0x11']=0
   elif kind=='count':bad[2]['metrics']['0x3']=True
   elif kind=='ns':bad[2]['ns']=0
   elif kind=='serial':bad[2]['serial']=0
   else:
    b=bytearray(blob);offset=bad[0]['branch_offset'] if kind=='branch' else bad[0]['loop_offset']+16*4;b[offset]^=1;blob=bytes(b)
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(bad,case,blob)
 def curves(self):
  rows=[]
  for p in expected_conditions():
   c,_=self.actual[p['name']];v=2 if c['anchor']=='none' else 300+(4 if c['n']>=512 else 0)
   rows.append(dict(condition=p['name'],class_name=c['class'],anchor=c['anchor'],n=c['n'],epoch=int(p['name'][1]),cycles=[v,v,v],counts={hex(e):[v,v,v] if e==17 else [0,0,0] for e in c['events']}))
  return rows
 def test_pure_complete_curves_censoring_conflict_and_coverage(self):
  m=self.module();rows=self.curves();result=m.analyze(rows);self.assertTrue(all(c['status']=='interval' and c['interval']==[384,512] for c in result['classes']))
  for bad in (rows[:-1],rows+[rows[0]],rows[::-1]):
   with self.assertRaises(ValueError):m.analyze(bad)
  bad=copy.deepcopy(rows);bad[0]['counts']['0x11']=[0,0,0]
  with self.assertRaises(ValueError):m.analyze(bad)
  for kind,status in [('left','left-censored'),('right','right-censored'),('below','no-onset-through768'),('conflict','ambiguous'),('negative','ambiguous'),('nonmonotonic','ambiguous'),('unstable','ambiguous')]:
   rr=copy.deepcopy(rows)
   for r in rr:
    if r['anchor']!='fsqrt':continue
    n=r['n'];v=300
    if kind=='left':v+=4 if n>=128 else 0
    elif kind=='right':v+=4 if n==768 else 0
    elif kind=='conflict':v+=4 if n>=512 and r['epoch']==0 else 0
    elif kind=='negative':v-=4 if n==128 else 0
    elif kind=='nonmonotonic':v+=4 if n==512 else 0
    elif kind=='unstable':v+=4 if n>=512 else 0
    r['cycles']=[v,v,v*1.2 if kind=='unstable' else v];r['counts']['0x11']=r['cycles'][:]
   self.assertTrue(all(c['status']==status for c in m.analyze(rr)['classes']),kind)
if __name__=='__main__':unittest.main()
