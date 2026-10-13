"""Actual C/BPF plans -> registered driver -> writer -> immutable raw; mock PMU/kernel only."""
import contextlib,copy,hashlib,importlib.util,io,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.diagnostic import tlb_observed_reach_analysis as model
from tools.diagnostic import tlb_observed_reach_raw as reader
from tools.diagnostic.tests import test_tlb_observed_reach_analysis as fixture
ROOT=Path(__file__).resolve().parents[3]
class ObservedReachRaw(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.launch='3a4ad87';cls.blob=staticmethod(lambda rel:subprocess.check_output(['git','show',cls.launch+':'+rel],cwd=ROOT));cls.build=json.loads(cls.blob(model.BUILD));fixture.ObservedReachAnalysis.setUpClass();cls.fixture=fixture.ObservedReachAnalysis()
 @classmethod
 def tearDownClass(cls):fixture.ObservedReachAnalysis.tearDownClass()
 def execute(self,root,phase='qualification',denial=False,corrupt=False,prior=None):
  for rel in [model.DRIVER,model.CONSUMER,model.RAW,model.PROTOCOL,model.BUILD,model.PLAN,'configs/platforms/redmi-k70pro-01.json',*self.build['source_sha256']]:
   p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(self.blob(rel))
  spec=importlib.util.spec_from_file_location('observed_registered_driver',root/model.DRIVER);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver);binary=root/'external-binary';binary.write_bytes(b'not device code; deployment mocked');calls=[];owner=self
  pol=json.loads(self.blob('configs/platforms/redmi-k70pro-01.json'))['environment_profiles']['charging-thermal']['measurement_environment'];snapshot=dict(power=dict(wakefulness='Dozing',screen_on=False),device_idle=dict(force_idle=False),camera=dict(active=False),services=dict(mi_thermald='running'),airplane_mode=True,thermal=dict(max_cpu_c=40),cpufreq={n:dict(governor='walt',min_khz=672000,max_khz=v) for n,v in pol['preconditions']['cpufreq_max_khz'].items()})
  def response(stdout='',rc=0,stderr=''):return SimpleNamespace(stdout=stdout,stderr=stderr,returncode=rc,timed_out=False)
  class External:
   def execute(self,args):
    if args[0]=='pidof':return response(rc=1)
    if args[0]=='chmod':return response()
    if args[0]=='sha256sum':return response(owner.build['binary_sha256']+' target')
    if args[0]=='su' and args[2].startswith('sha256sum '):return response(model.BTF_SHA+' /sys/kernel/btf/vmlinux\n0x410fd821\n4096\n')
    c=model.conditions(phase)[len(calls)];assert args[:2]==['su','-c'] and args[2].endswith(' '.join(c['args']));calls.append(c['name'])
    if denial:return response(json.dumps(dict(type='failure',metrics={},failure=dict(reason='bpf-program-load',errno=13)))+'\n',1,'verifier: simulated denial\n')
    rr,_=owner.fixture.record(c,12345+len(calls))
    if corrupt:
     rr[4]['negative'][6]=1
     if corrupt!='transport':rr=rr[:5]+[dict(type='failure',metrics={},failure=dict(reason='observed-capture-not-qualified',errno=0))]
    return response('\n'.join(json.dumps(r) for r in rr)+'\n',1 if corrupt and corrupt!='transport' else 0)
  check0=subprocess.check_output;run0=subprocess.run;sha0=driver.sha
  def check(cmd,*a,**kw):
   if cmd==['adb','devices']:return 'List of devices attached\nsoftware-test\tdevice\n'
   if cmd[:3]==['git','rev-parse','HEAD']:return check0(['git','rev-parse',owner.launch],cwd=ROOT,text=True)
   if cmd[:3]==['git','branch','--show-current']:return 'software-only-test\n'
   if cmd[:2]==['git','show']:return check0(cmd,cwd=ROOT)
   return check0(cmd,*a,**kw)
  def run(cmd,*a,**kw):return subprocess.CompletedProcess(cmd,0,b'',b'') if cmd[:2]==['adb','push'] else run0(cmd,*a,**kw)
  with patch.object(driver,'AdbExecutor',return_value=External()),patch.object(driver,'collect_android_state',return_value=snapshot),patch.object(driver,'default_store',return_value=SimpleNamespace(unfinished=lambda:[])),patch.object(driver,'sha',side_effect=lambda p:owner.build['binary_sha256'] if Path(p)==binary else sha0(p)),patch.object(driver.subprocess,'check_output',side_effect=check),patch.object(driver.subprocess,'run',side_effect=run),patch.object(driver.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
   args=['--binary',str(binary),'--phase',phase]
   if prior is not None:args+=['--qualification',str(prior)]
   if corrupt:
    with self.assertRaises(ValueError):driver.main(args)
   else:self.assertEqual(driver.main(args),1 if denial else 0)
  raw=next((root/'data/private').glob('*-'+phase));return raw,calls
 def test_real_n0_driver_writer_immutable_raw_and_rehashed_attacks(self):
  with tempfile.TemporaryDirectory() as d:
   raw,calls=self.execute(Path(d));s,h=reader.audit_raw(raw);a=model.analyze(s);self.assertEqual((a['status'],len(calls),len(h)),('OBSERVED_GRAPH_QUALIFIED',3,20))
   original=(raw/'manifest.json').read_bytes();mp=raw/'manifest.json'
   for kind in ('program','typed','prior','negative','pfn','counts','order','ids','observer','duplicate','conditions','binary','extra','environment'):
    m=json.loads(original);name=m['results'][0]['name'];f=raw/(name+'.stdout.jsonl');saved=f.read_bytes();env=raw/'final-environment.json';es=env.read_bytes()
    if kind=='extra':(raw/'extra').write_text('unexpected')
    elif kind=='environment':x=json.loads(es);x['snapshot']['cpufreq']['policy7']['max_khz']-=1;env.write_text(json.dumps(x))
    elif kind in ('duplicate','conditions','binary'):
     if kind=='duplicate':m['results'].append(m['results'][-1])
     elif kind=='conditions':m['conditions'][0]['args'][2]='1024'
     else:m['binary_sha256']='bad'
    else:
     rr=[json.loads(l) for l in f.read_text().splitlines()];sample=70
     if kind=='program':rr[1]['entry_instructions'][0]['imm']^=1
     elif kind=='typed':rr[4]['positive'][1]=True
     elif kind=='prior':rr[5]['previous'][0]=99
     elif kind=='negative':rr[4]['negative'][6]=1
     elif kind=='pfn':rr[-1]['canonical_after'][0]+=1
     elif kind=='counts':rr[sample]['counts'][0]=True
     elif kind=='order':rr[sample:sample+2]=rr[sample:sample+2][::-1]
     elif kind=='ids':rr[69]['event_ids'][1]=rr[69]['event_ids'][0]
     elif kind=='observer':rr[68]['fds_closed']=False
     f.write_text('\n'.join(json.dumps(r) for r in rr)+'\n');m['results'][0]['stdout_sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
    mp.write_text(json.dumps(m))
    with self.subTest(kind=kind),self.assertRaises(ValueError):reader.audit_raw(raw)
    if kind=='extra':(raw/'extra').unlink()
    f.write_bytes(saved);env.write_bytes(es);mp.write_bytes(original)
 def test_first_bad_capture_stops_one_process(self):
  with tempfile.TemporaryDirectory() as d:
   raw,calls=self.execute(Path(d),corrupt=True);self.assertEqual(len(calls),1);self.assertEqual(json.loads((raw/'manifest.json').read_text())['status'],'stopped')
 def test_audit_bypass_detected_by_production_bad_frame(self):
  with tempfile.TemporaryDirectory() as d,patch.object(model,'audit_process',return_value=dict(status='complete')),self.assertRaises(AssertionError):self.execute(Path(d),corrupt='transport')
 def test_capability_denial_first_stop_preserves_verifier(self):
  with tempfile.TemporaryDirectory() as d:
   raw,calls=self.execute(Path(d),denial=True);s,h=reader.audit_raw(raw);self.assertEqual((s['status'],len(calls)),('capability-unavailable',1));self.assertIn('verifier:',(raw/(calls[0]+'.stderr.log')).read_text())
 def test_scan_requires_valid_immutable_qualification_before_device(self):
  with tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(RuntimeError,'qualification required'):self.execute(Path(d),phase='scan')
 def test_full_scan_real_plans_and_same_binary_prior_binding(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);q,_=self.execute(root);raw,calls=self.execute(root,phase='scan',prior=q);s,h=reader.audit_raw(raw);a=model.analyze(s);self.assertEqual((a['windows'],len(calls)),(216,18));self.assertEqual(a['status'],'DESCRIPTOR_BOUND_GEOMETRY_DIFFERENCE');self.assertFalse(a['physical_capacity_certified'])
   f=q/'e0-n32-r0.stdout.jsonl';f.write_text(f.read_text()+'{}\n')
   with self.assertRaisesRegex(ValueError,'prior'):reader.audit_raw(raw)
if __name__=='__main__':unittest.main()
