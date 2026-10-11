"""Real C paired plan/programs -> driver/writer -> raw consumer; external PMU is synthetic.

Immutable launch/source/build are real Git evidence. These software fixtures
never stand in for target-device measurements.
"""
import contextlib,copy,hashlib,importlib.util,io,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.diagnostic import rob_pair_analysis as model
from tools.diagnostic.tests import test_rob_pair_analysis as fixture
ROOT=Path(__file__).resolve().parents[3]
class PairRaw(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.launch=subprocess.check_output(['git','rev-parse','11abe3036450c2be8947880dc701773f048dc976'],cwd=ROOT,text=True).strip()
  cls.blob=staticmethod(lambda rel:subprocess.check_output(['git','show',cls.launch+':'+rel],cwd=ROOT))
  cls.build=json.loads(cls.blob(model.BUILD));cls.plan=json.loads(cls.blob(model.PLAN))
  fixture.PairAnalysis.setUpClass();cls.actual=fixture.PairAnalysis()
  model.validate_plan(fixture.PairAnalysis.actual)
 @classmethod
 def tearDownClass(cls):fixture.PairAnalysis.tearDownClass()
 def execute_fixture(self,root,corrupt=False):
  required=[model.DRIVER,model.PROTOCOL,model.BUILD,model.PLAN,'configs/platforms/redmi-k70pro-01.json',*self.build['source_sha256']]
  for rel in required:
   p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(self.blob(rel))
  spec=importlib.util.spec_from_file_location('pair_registered_driver',root/model.DRIVER);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
  binary=root/'external-binary-stub';binary.write_bytes(b'not target code; mocked deployment only');calls=[]
  profile=json.loads(self.blob('configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment']
  snapshot=dict(power=dict(wakefulness='Dozing',screen_on=False),device_idle=dict(force_idle=False),camera=dict(active=False),services=dict(mi_thermald='running'),airplane_mode=True,thermal=dict(max_cpu_c=40),cpufreq={n:dict(governor='walt',min_khz=672000,max_khz=v) for n,v in policy['preconditions']['cpufreq_max_khz'].items()})
  def result(stdout='',rc=0):return SimpleNamespace(stdout=stdout,stderr='',returncode=rc,timed_out=False)
  owner=self
  class External:
   def execute(self,args):
    if args[0]=='pidof':return result(rc=1)
    if args[0]=='chmod':return result()
    if args[0]=='sha256sum':return result(owner.build['binaries']['rob_dependency_pair']+' anonymous-target-binary')
    if args[0]=='su' and args[2].startswith('cat '):return result('0x410fd821\n4096\n')
    assert args[:2]==['su','-c'];reverse='--reverse' in args[2];index=len(calls);assert reverse==bool((index//3)%2);calls.append(index);records=owner.actual.records(model.conditions()[index])
    if corrupt:records[3]['words'][16]^=1
    return result('\n'.join(json.dumps(r) for r in records)+'\n')
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
  def sha(p):return self.build['binaries']['rob_dependency_pair'] if Path(p)==binary else original_sha(p)
  with patch.object(driver,'AdbExecutor',return_value=External()),patch.object(driver,'collect_android_state',return_value=snapshot),patch.object(driver,'default_store',return_value=SimpleNamespace(unfinished=lambda:[])),patch.object(driver,'sha',side_effect=sha),patch.object(driver.subprocess,'check_output',side_effect=check),patch.object(driver.subprocess,'run',side_effect=run),patch.object(driver.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
   if corrupt:
    with self.assertRaises(ValueError):driver.main(['--binary',str(binary)])
   else:self.assertEqual(driver.main(['--binary',str(binary)]),0)
  raw=next((root/'data/private').iterdir());manifest=json.loads((raw/'manifest.json').read_text())
  self.assertEqual((len(calls),manifest['status']),(1,'stopped') if corrupt else (15,'complete'))
  return raw,manifest
 def test_registered_driver_first_bad_program_stops_one_process(self):
  with tempfile.TemporaryDirectory() as d:self.execute_fixture(Path(d),True)
 def test_driver_audit_bypass_is_caught_by_first_bad_fixture(self):
  with tempfile.TemporaryDirectory() as d,patch.object(model,'audit_process',return_value=None):
   with self.assertRaises(AssertionError):self.execute_fixture(Path(d),True)
 def test_real_plan_driver_persistence_raw_and_rehashed_counterexamples(self):
  with tempfile.TemporaryDirectory() as d:
   raw,original=self.execute_fixture(Path(d));summary,hashes=model.audit_raw(raw);a=model.analyze(summary)
   self.assertEqual((len(hashes),len(summary['rows']),a['windows']),(65,15,480));self.assertEqual(a['verdict'],'paired-dependency-associated-response')
   for kind in ('missing','extra','duplicate','requested','result-order','plan','binary','midr','status','driver','stderr','word','typed','window-order','base','ids','mux','count','copy','ns','ir','environment'):
    mp=raw/'manifest.json';m=copy.deepcopy(original);name=m['results'][0]['name'];f=raw/(name+'.stdout.jsonl');target=mp;saved=mp.read_bytes()
    if kind=='missing':target=raw/'final-environment.json';saved=target.read_bytes();target.unlink()
    elif kind=='extra':target=raw/'unexpected';saved=None;target.write_text('extra')
    elif kind=='driver':target=raw/'driver.py';saved=target.read_bytes();target.write_text('drift')
    elif kind=='stderr':target=raw/(name+'.stderr.log');saved=target.read_bytes();target.write_text('warning')
    elif kind=='environment':
     target=raw/'final-environment.json';saved=target.read_bytes();v=json.loads(saved);v['snapshot']['cpufreq']['policy7']['max_khz']-=1;target.write_text(json.dumps(v))
    elif kind in ('word','typed','window-order','base','ids','mux','count','copy','ns','ir'):
     target=f;saved=f.read_bytes();rr=[json.loads(l) for l in saved.splitlines()]
     if kind=='word':rr[3]['words'][16]^=1
     elif kind=='typed':rr[0]['chain']=True
     elif kind=='window-order':rr[-2:]=rr[-2:][::-1]
     elif kind=='base':rr[-1]['code_base']+=4096
     elif kind=='ids':rr[5]['event_ids'][1]=rr[5]['event_ids'][0]
     elif kind=='mux':rr[6]['running']=1
     elif kind=='count':rr[6]['counts'][0]=True
     elif kind=='copy':rr[6]['code_matches_plan']=False
     elif kind=='ns':rr[6]['ns']=0
     elif kind=='ir':rr[6]['counts'][1]=1
     f.write_text('\n'.join(json.dumps(r) for r in rr)+'\n');m['results'][0]['stdout_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();mp.write_text(json.dumps(m))
    else:
     if kind=='duplicate':m['results'].append(m['results'][-1])
     elif kind=='requested':m['conditions'][0]['args']=['100']
     elif kind=='result-order':m['results'][:2]=m['results'][:2][::-1]
     elif kind=='plan':m['plan_sha256']='bad'
     elif kind=='binary':m['binary_sha256']='bad'
     elif kind=='midr':m['midr']='0x410fd820'
     elif kind=='status':m['status']='stopped'
     mp.write_text(json.dumps(m))
    with self.subTest(kind=kind),self.assertRaises((ValueError,FileNotFoundError)):model.audit_raw(raw)
    if saved is None:target.unlink()
    else:target.write_bytes(saved)
    mp.write_text(json.dumps(original))
if __name__=='__main__':unittest.main()
