"""实际C++计划/动态布局→driver→写盘→raw审计；PMU/PFN模拟仅属软件证据。"""
import contextlib,copy,hashlib,importlib.util,io,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.diagnostic import tlb_association_analysis as model
from tools.diagnostic.tests import test_tlb_association as fixture
ROOT=Path(__file__).resolve().parents[3]
class AssociationRaw(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.launch=subprocess.check_output(['git','rev-parse','f054ae6585f50835be1dbd573aef25ffede670ea'],cwd=ROOT,text=True).strip();cls.blob=staticmethod(lambda rel:subprocess.check_output(['git','show',cls.launch+':'+rel],cwd=ROOT));cls.build=json.loads(cls.blob(model.BUILD));fixture.AssociationAnalysis.setUpClass();cls.actual=fixture.AssociationAnalysis();model.validate_plan(fixture.AssociationAnalysis.actual)
 @classmethod
 def tearDownClass(cls):fixture.AssociationAnalysis.tearDownClass()
 def execute_fixture(self,root,corrupt=False,active=False):
  for rel in set([model.DRIVER,model.CONSUMER,model.PROTOCOL,model.BUILD,model.PLAN,'configs/platforms/redmi-k70pro-01.json',*self.build['source_sha256']]):
   p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(self.blob(rel))
  spec=importlib.util.spec_from_file_location('repr_registered_driver',root/model.DRIVER);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver);binary=root/'external-stub';binary.write_bytes(b'not target code; mock deployment only');calls=[]
  policy=json.loads(self.blob('configs/platforms/redmi-k70pro-01.json'))['environment_profiles']['charging-thermal']['measurement_environment'];snapshot=dict(power=dict(wakefulness='Dozing',screen_on=False),device_idle=dict(force_idle=False),camera=dict(active=False),services=dict(mi_thermald='running'),airplane_mode=True,thermal=dict(max_cpu_c=40),cpufreq={n:dict(governor='walt',min_khz=672000,max_khz=v) for n,v in policy['preconditions']['cpufreq_max_khz'].items()});owner=self
  def result(stdout='',rc=0):return SimpleNamespace(stdout=stdout,stderr='',returncode=rc,timed_out=False)
  class External:
   def execute(self,args):
    if args[0]=='pidof':return result('999\n') if active and args[1]=='rob_zero_latency_units' else result(rc=1)
    if args[0]=='chmod':return result()
    if args[0]=='sha256sum':return result(owner.build['binaries']['tlb_pfn_association']+' anonymous-target-binary')
    if args[0]=='su' and args[2].startswith('cat '):return result('0x410fd821\n4096\n')
    assert args[:2]==['su','-c'];reverse='--reverse' in args[2];assert reverse==bool(len(calls)%2);calls.append(1);rr=owner.actual.records(reverse)
    if corrupt:next(x for x in rr if x['type']=='graph-certificate' and x['cell']!='floor')['stored_words'][0]^=1
    return result('\n'.join(json.dumps(x) for x in rr)+'\n')
  original_check=subprocess.check_output;original_run=subprocess.run;original_sha=driver.sha
  def check(cmd,*a,**kw):
   if cmd==['adb','devices']:return 'List of devices attached\nsynthetic-target\tdevice\n'
   if cmd[:3]==['git','rev-parse','HEAD']:return self.launch+'\n'
   if cmd[:3]==['git','branch','--show-current']:return 'synthetic-software-test\n'
   if cmd[:2]==['git','show']:return original_check(cmd,cwd=ROOT)
   return original_check(cmd,*a,**kw)
  def run(cmd,*a,**kw):
   if cmd[:2]==['adb','push']:return subprocess.CompletedProcess(cmd,0,b'',b'')
   return original_run(cmd,*a,**kw)
  def sha(p):return self.build['binaries']['tlb_pfn_association'] if Path(p)==binary else original_sha(p)
  with patch.object(driver,'AdbExecutor',return_value=External()),patch.object(driver,'collect_android_state',return_value=snapshot),patch.object(driver,'default_store',return_value=SimpleNamespace(unfinished=lambda:[])),patch.object(driver,'sha',side_effect=sha),patch.object(driver.subprocess,'check_output',side_effect=check),patch.object(driver.subprocess,'run',side_effect=run),patch.object(driver.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
   if corrupt:
    with self.assertRaises(ValueError):driver.main(['--binary',str(binary)])
   else:self.assertEqual(driver.main(['--binary',str(binary)]),0)
  raw=next((root/'data/private').iterdir());manifest=json.loads((raw/'manifest.json').read_text());self.assertEqual((len(calls),manifest['status']),(1,'stopped') if corrupt else (3,'complete'));return raw,manifest
 def test_first_bad_actual_graph_stops_and_is_not_patched(self):
  with tempfile.TemporaryDirectory() as d:self.execute_fixture(Path(d),True)
 def test_audit_bypass_is_detected(self):
  with tempfile.TemporaryDirectory() as d,patch.object(model,'audit_process',return_value=None),self.assertRaises(AssertionError):self.execute_fixture(Path(d),True)
 def test_complete_real_plan_persistence_and_rehashed_counterexamples(self):
  with tempfile.TemporaryDirectory() as d:
   raw,original=self.execute_fixture(Path(d));summary,hashes=model.audit_raw(raw);a=model.analyze(summary);self.assertEqual((len(hashes),len(summary['rows']),a['windows']),(18,99,297));self.assertEqual(a['verdict'],'ASSOCIATION_SENSITIVE')
   for kind in ('missing','extra','duplicate','requested','result-order','plan','binary','midr','mode','v1-mode','status','driver','consumer','stderr','environment','word-before','word-after','head','mask','pfn-before','pfn-after','wire','canonical','huge','ids','uint-id','mux','count','ir','round-order','geometry'):
    mp=raw/'manifest.json';m=copy.deepcopy(original);name=m['results'][0]['name'];f=raw/(name+'.stdout.jsonl');target=mp;saved=mp.read_bytes()
    if kind=='missing':target=raw/'final-environment.json';saved=target.read_bytes();target.unlink()
    elif kind=='extra':target=raw/'unexpected';saved=None;target.write_text('extra')
    elif kind in ('driver','consumer'):target=raw/(kind+'.py');saved=target.read_bytes();target.write_text('drift')
    elif kind=='stderr':target=raw/(name+'.stderr.log');saved=target.read_bytes();target.write_text('warning')
    elif kind=='environment':
     target=raw/'final-environment.json';saved=target.read_bytes();x=json.loads(saved);x['snapshot']['cpufreq']['policy7']['max_khz']-=1;target.write_text(json.dumps(x))
    elif kind in ('word-before','word-after','head','mask','pfn-before','pfn-after','wire','canonical','huge','ids','uint-id','mux','count','ir','round-order','geometry'):
     target=f;saved=f.read_bytes();rr=[json.loads(l) for l in saved.splitlines()];c=next(x for x in rr if x['type']=='cell' and x['n']);graphs=[x for x in rr if x['type']=='graph-certificate' and x['cell']==c['cell']];certs=[x for x in rr if x['type']=='pfn-certificate' and x['cell']==c['cell']];sample=next(x for x in rr if x['type']=='round' and x['cell']==c['cell'])
     if kind.startswith('word-'):graphs[kind.endswith('after')]['stored_words'][0]^=1
     elif kind=='head':graphs[0]['head']+=64
     elif kind=='mask':c['mask']=True
     elif kind.startswith('pfn-'):certs[kind.endswith('after')]['alias_pfns'][0]+=1
     elif kind=='wire':certs[0]['alias_entries'][0]|=1<<62
     elif kind=='canonical':rr[2]['canonical_pfns'][0]=0
     elif kind=='huge':next(x for x in rr if x['type']=='backing')['shmem_pmd_kb']=1
     elif kind=='ids':rr[1]['ids'][1]=rr[1]['ids'][0]
     elif kind=='uint-id':rr[1]['ids'][0]=2**64
     elif kind=='mux':sample['running']=1
     elif kind=='count':sample['counts'][3]=True
     elif kind=='ir':sample['counts'][1]=3*c['loads']
     elif kind=='round-order':rr[-2:]=rr[-2:][::-1]
     elif kind=='geometry':next(x for x in rr if x['type']=='geometry' and x['cell']==c['cell'])['position_nodes'][0]+=1
     f.write_text('\n'.join(json.dumps(x) for x in rr)+'\n');m['results'][0]['stdout_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();mp.write_text(json.dumps(m))
    else:
     if kind=='duplicate':m['results'].append(m['results'][-1])
     elif kind=='requested':m['conditions'][0]['args']=['100']
     elif kind=='result-order':m['results'][:2]=m['results'][:2][::-1]
     elif kind=='plan':m['plan_sha256']='bad'
     elif kind=='binary':m['binary_sha256']='bad'
     elif kind=='midr':m['midr']='0x410fd820'
     elif kind=='mode':m['mode']='tlb-shared-alias'
     elif kind=='v1-mode':m['mode']='tlb-pointer-representation'
     elif kind=='status':m['status']='stopped'
     mp.write_text(json.dumps(m))
    with self.subTest(kind=kind),self.assertRaises((ValueError,FileNotFoundError)):model.audit_raw(raw)
    if saved is None:target.unlink()
    else:target.write_bytes(saved)
    mp.write_text(json.dumps(original))
 def test_existing_rob_probe_blocks_new_work(self):
  with tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(RuntimeError,'active probe'):self.execute_fixture(Path(d),active=True)
 def test_auxiliary_prefetch_background_does_not_erase_walk_contrast(self):
  with tempfile.TemporaryDirectory() as d:
   raw,m=self.execute_fixture(Path(d));result=m['results'][0];f=raw/(result['name']+'.stdout.jsonl');rr=[json.loads(l) for l in f.read_text().splitlines()]
   for x in rr:
    if x['type']=='round' and x['cell']=='floor':x['counts'][4]=100000000
   f.write_text('\n'.join(json.dumps(x) for x in rr)+'\n');result['stdout_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();(raw/'manifest.json').write_text(json.dumps(m));a=model.analyze(model.audit_raw(raw)[0]);self.assertEqual(a['verdict'],'ASSOCIATION_SENSITIVE');self.assertEqual(a['prefetch_status'],'INCOMPUTABLE')
if __name__=='__main__':unittest.main()
