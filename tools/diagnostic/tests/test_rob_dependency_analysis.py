"""Actual C config/code; externally controlled counters exercise finite decisions."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE='docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'
def conditions():
 base=[(a,k,n,link) for a,k in (('none',16),('fsqrt',8),('fsqrt',16)) for n in (0,64,128,256) for link in ('independent','dependent')];out=[]
 for e in (0,1):
  for a,k,n,link in (base if e==0 else reversed(base)):
   out.append(dict(name=f'e{e}-{link}-{a}-k{k}-a0-n{n}',args=['-i','131072','-r','3','--pin','7','--pmu-type','8','-e','0x3a','-e','0x3b','-e','0x816d','-e','0x23','-t','add','-a',a,'--chain',str(k),'--align','0','-n',str(n),'--anchor-link',link]))
 return out
class DependencyAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name);cls.exe=d/'producer';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/SOURCE),'-o',str(cls.exe)],check=True);cls.actual={}
  for c in conditions():
   f=d/'code';cfg=json.loads(subprocess.check_output([str(cls.exe),*c['args'],'--write-asm',str(f)],text=True));cls.actual[c['name']]=(cfg,f.read_bytes())
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def module(self):
  self.assertTrue((ROOT/'tools/diagnostic/rob_dependency_analysis.py').exists(),'dependency consumer missing');return importlib.import_module('tools.diagnostic.rob_dependency_analysis')
 def records(self,c):
  cfg,b=self.actual[c['name']];cfg=copy.deepcopy(cfg);anch=cfg['anchors_per_iteration'];n=cfg['n'];value=10+.2*n+13*anch+(20 if anch and n and cfg['anchor_link']=='dependent' else 0)
  runtime=dict(type='runtime',cpu=7,fpcr=0,loop_address_mod64=0,ring_nodes=0,distinct_lines_per_call=0,mapping_4k_verified=None,backing_verified=None,backing_page_bytes=0,backing_info=None,event_ids=[1,2,3,4,5,6])
  rr=[dict(type='round',round=r,serial=False,pair_step=0,ns=100000,enabled=100000,running=100000,metrics={'0x11':int(value*131072),'0x8':cfg['loop_instructions']*131072+17,'0x3a':cfg['loop_instructions']*131072,'0x3b':cfg['loop_instructions']*131072,'0x816d':0,'0x23':0},backing_verified=None,backing_before=None,backing_after=None) for r in range(3)]
  return [cfg,runtime,*rr],b
 def test_actual_48_configs_and_bytes_bind_all_new_dimensions(self):
  m=self.module();self.assertEqual(m.registered_plan()['conditions'],conditions());self.assertEqual((m.registered_plan()['processes'],m.registered_plan()['windows']),(48,144))
  from tools.diagnostic.run_sm8650_minimal import conditions as driver
  self.assertEqual(driver(m.MODE),[(c['name'],c['args']) for c in conditions()])
  for c in conditions():self.assertEqual(self.actual[c['name']],(m.expected_config(c),m.expected_code(c)));r,b=self.records(c);m.audit_process(r,c,b)
 def test_typed_link_chain_id_mux_ir_and_code_reject(self):
  m=self.module();c=conditions()[4];rr,b=self.records(c)
  for kind in ('link','chain','bridge','id','mux','ir','bool-count','code','missing','order','zero-cycles'):
   r=copy.deepcopy(rr);bb=b
   if kind=='link':r[0]['anchor_link']='dependent'
   elif kind=='chain':r[0]['chain']=True
   elif kind=='bridge':r[0]['bridges_per_iteration']=False
   elif kind=='id':r[1]['event_ids'][-1]=1
   elif kind=='mux':r[2]['running']=1
   elif kind=='ir':r[2]['metrics']['0x8']=0
   elif kind=='bool-count':r[2]['metrics']['0x3b']=True
   elif kind=='code':bb=bytes([b[0]^1])+b[1:]
   elif kind=='missing':r.pop()
   elif kind=='order':r[-2:]=r[-2:][::-1]
   elif kind=='zero-cycles':r[2]['metrics']['0x11']=0
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(r,c,bb)
 def rows(self):
  m=self.module();out=[]
  for c in conditions():r,b=self.records(c);out.append(m.audit_process(r,c,b))
  return out
 def test_finite_four_contrasts_value_flow_and_full_matrix(self):
  m=self.module();rows=self.rows();out=m.analyze(rows);self.assertEqual(out['dependency_status'],'dependency-associated-hiding-response');self.assertFalse(out['physical_allocation_certified']);self.assertEqual(len(out['points']),48);self.assertEqual(len(out['primary_gates']),4)
  for bad in (rows[:-1],rows[::-1],rows+[rows[0]]):
   with self.assertRaises(ValueError):m.analyze(bad)
  for kind in ('second-epoch-conflict','threshold-boundary','unstable','count-flow'):
   rr=copy.deepcopy(rows)
   for r in rr:
    if r['anchor']=='fsqrt' and r['n']==128 and r['link']=='dependent':
     if kind=='second-epoch-conflict' and r['epoch']==1:r['cycles']=[v-20 for v in r['cycles']]
     if kind=='threshold-boundary':r['cycles']=[v-15 for v in r['cycles']]
     if kind=='unstable':r['cycles'][0]*=1.2
     if kind!='count-flow':r['counts']['0x11']=r['cycles'].copy()
   if kind=='count-flow':rr[0]['counts']['0x11'][0]+=1
   if kind=='count-flow':
    with self.assertRaises(ValueError):m.analyze(rr)
   else:self.assertEqual(m.analyze(rr)['dependency_status'],'not-qualified',kind)
if __name__=='__main__':unittest.main()
