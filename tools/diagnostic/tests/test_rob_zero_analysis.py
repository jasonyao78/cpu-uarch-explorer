"""Immutable C exporter to request/code consumer; only runtime counters are synthetic."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE='docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'
CLASSES=('nop','movi','mov0','movr');GRID=(0,128,256,704);EVENTS=(17,8,58,59,33133,35)
def conditions():
 base=[(c,a,n) for a in ('none','fsqrt') for n in GRID for c in CLASSES];out=[]
 for e in (0,1):
  for c,a,n in (base if e==0 else reversed(base)):
   out.append(dict(name=f'e{e}-{c}-{a}-k16-a0-n{n}',args=['-i','131072','-r','3','--pin','7','--pmu-type','8','-e','0x3a','-e','0x3b','-e','0x816d','-e','0x23','-t',c,'-a',a,'--chain','16','--align','0','-n',str(n)]))
 return out
class ZeroAnalysisTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name)
  for p in (SOURCE,'probes/common/perf_group_read.h','probes/common/rob_backing.h'):(d/Path(p).name).write_bytes((ROOT/p).read_bytes())
  exe=d/'producer';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(d),str(d/'rob_window_probe.c'),'-o',str(exe)],check=True);cls.actual={}
  for c in conditions():
   f=d/'code';cfg=json.loads(subprocess.check_output([str(exe),*c['args'],'--write-asm',str(f)],text=True));cls.actual[c['name']]=(cfg,f.read_bytes())
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def module(self):
  self.assertTrue((ROOT/'tools/diagnostic/rob_zero_analysis.py').exists(),'new consumer missing')
  return importlib.import_module('tools.diagnostic.rob_zero_analysis')
 def records(self,c):
  cfg,code=self.actual[c['name']];cfg=copy.deepcopy(cfg);n=cfg['n'];a=32 if cfg['anchor']=='fsqrt' else 0;ops=1+a+n*(1 if cfg['class']=='nop' else 2)
  runtime=dict(type='runtime',cpu=7,fpcr=0,loop_address_mod64=0,ring_nodes=0,distinct_lines_per_call=0,mapping_4k_verified=None,backing_verified=None,backing_page_bytes=0,backing_info=None,event_ids=[1,2,3,4,5,6])
  rr=[dict(type='round',round=r,serial=False,pair_step=0,ns=100000,enabled=100000,running=100000,metrics={'0x11':(416 if a else 2+n)*131072,'0x8':cfg['loop_instructions']*131072+17,'0x3a':ops*131072,'0x3b':(ops+1)*131072,'0x816d':int(.8*(416 if a else 2+n)*131072) if a and n==128 and cfg['class']=='movi' else 0,'0x23':0},backing_verified=None,backing_before=None,backing_after=None) for r in range(3)]
  return [cfg,runtime,*rr],code
 def test_real_c_all_64_configs_code_and_driver(self):
  m=self.module();p=m.registered_plan();self.assertEqual(p['conditions'],conditions());self.assertEqual((p['processes'],p['windows']),(64,192))
  from tools.diagnostic.run_sm8650_minimal import conditions as driver
  self.assertEqual(driver(m.MODE),[(c['name'],c['args']) for c in conditions()])
  for c in conditions():
   cfg,b=self.actual[c['name']];self.assertEqual(cfg,m.expected_config(c));self.assertEqual(b,m.expected_code(c));self.assertEqual(tuple(cfg['events']),EVENTS)
 def test_actual_config_runtime_and_code_corruption_rejected(self):
  m=self.module();c=conditions()[9];r,b=self.records(c);m.audit_process(r,c,b)
  for kind in ('config-type','runtime-none','runtime-type','round-none','id','order','mux','zero-cycles','negative-count','boolean-count','events','ns','code'):
   rr=copy.deepcopy(r);blob=b
   if kind=='config-type':rr[0]['n']=float(rr[0]['n'])
   elif kind=='runtime-none':rr[1]=None
   elif kind=='runtime-type':rr[1]['cpu']=True
   elif kind=='round-none':rr[2]=None
   elif kind=='id':rr[1]['event_ids'][-1]=1
   elif kind=='order':rr[-2:]=rr[-2:][::-1]
   elif kind=='mux':rr[2]['running']=1
   elif kind=='zero-cycles':rr[2]['metrics']['0x11']=0
   elif kind=='negative-count':rr[2]['metrics']['0x3b']=-1
   elif kind=='boolean-count':rr[2]['metrics']['0x816d']=True
   elif kind=='events':rr[2]['metrics']['0x3a0']=rr[2]['metrics'].pop('0x3a')
   elif kind=='ns':rr[2]['ns']=0
   elif kind=='code':blob=bytes([b[0]^1])+b[1:]
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(rr,c,blob)
 def rows(self):
  m=self.module();return [m.audit_process(*self.records(c)[:1],c,self.records(c)[1]) for c in conditions()]
 def test_frozen_primary_gate_and_all_samples_without_capacity_claim(self):
  m=self.module();rows=self.rows();out=m.analyze(rows);self.assertEqual(out['zero_value_status'],'qualified-limited-response');self.assertFalse(out['physical_allocation_certified']);self.assertEqual(len(out['points']),64)
  for bad in (rows[:-1],rows[::-1],rows+[rows[0]]):
   with self.assertRaises(ValueError):m.analyze(bad)
  for kind in ('zero-also-stalls','nonzero-does-not-stall','unstable-rename','unstable-cycles','second-epoch-conflict','cycle-semantics'):
   rr=copy.deepcopy(rows)
   for r in rr:
    if r['anchor']=='fsqrt' and r['n']==128:
     if kind=='zero-also-stalls' and r['class_name']=='mov0':r['counts']['0x816d']=[.8*x for x in r['cycles']]
     if kind=='nonzero-does-not-stall' and r['class_name']=='movi':r['counts']['0x816d']=[0]*3
     if kind=='unstable-rename' and r['class_name']=='movi':r['counts']['0x816d'][0]*=.5
     if kind=='unstable-cycles' and r['class_name']=='mov0':r['cycles'][0]*=1.2;r['counts']['0x11']=r['cycles'].copy()
     if kind=='second-epoch-conflict' and r['class_name']=='mov0' and r['epoch']==1:r['counts']['0x816d']=[.8*x for x in r['cycles']]
    if kind=='cycle-semantics':r['counts']['0x816d']=[2*x for x in r['cycles']]
   result=m.analyze(rr)
   self.assertEqual(result['zero_value_status'],'not-qualified',kind)
   if kind=='cycle-semantics':self.assertEqual(result['rename_status'],'cycle-semantics-incompatible')
  rr=copy.deepcopy(rows);rr[0]['counts']['0x11'][0]=0
  with self.assertRaises(ValueError):m.analyze(rr)
if __name__=='__main__':unittest.main()
