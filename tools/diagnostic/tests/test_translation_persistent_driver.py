"""Registered actual producer→driver→writer→reader; simulated external kernel only."""
import contextlib,hashlib,importlib.util,io,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.diagnostic import translation_persistent_analysis as model
from tools.diagnostic.tests import test_translation_self as vm
from tools.diagnostic.tests import test_translation_persistent_analysis as fixture
ROOT=vm.ROOT
class PersistentDriver(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  assert (ROOT/'tools/diagnostic/translation_persistent_raw.py').exists(),'registered self-read raw reader missing'
  from tools.diagnostic import translation_persistent_raw
  cls.reader=translation_persistent_raw;cls.launch='a49c2b0';cls.blob=staticmethod(lambda rel:subprocess.check_output(['git','show',cls.launch+':'+rel],cwd=ROOT));cls.build=json.loads(cls.blob(model.BUILD));cls.plan=json.loads(cls.blob(model.PLAN));fixture.PersistentAnalysis.setUpClass();cls.fixture=fixture.PersistentAnalysis()
 @classmethod
 def tearDownClass(cls):fixture.PersistentAnalysis.tearDownClass()
 def execute(self,root,denial=False,corrupt=False,not_excited=False):
  (root/'data/private').mkdir(parents=True,exist_ok=True)
  for rel in [model.DRIVER,model.CONSUMER,model.PROTOCOL,model.BUILD,model.PLAN,'configs/platforms/redmi-k70pro-01.json',*self.build['source_sha256']]:
   p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(self.blob(rel))
  spec=importlib.util.spec_from_file_location('registered_self_driver',root/model.DRIVER);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver);binary=root/'mock-external-binary';binary.write_bytes(b'not target code');calls=[];owner=self
  pol=json.loads(self.blob('configs/platforms/redmi-k70pro-01.json'))['environment_profiles']['charging-thermal']['measurement_environment'];snapshot=dict(power=dict(wakefulness='Dozing',screen_on=False),device_idle=dict(force_idle=False),camera=dict(active=False),services=dict(mi_thermald='running'),airplane_mode=True,thermal=dict(max_cpu_c=40),cpufreq={n:dict(governor='walt',min_khz=672000,max_khz=v) for n,v in pol['preconditions']['cpufreq_max_khz'].items()})
  def response(stdout='',rc=0,stderr=''):return SimpleNamespace(stdout=stdout,stderr=stderr,returncode=rc,timed_out=False)
  class External:
   def execute(self,args):
    if args[0]=='pidof':return response(rc=1)
    if args[0]=='chmod':return response()
    if args[0]=='sha256sum':return response(owner.build['binary_sha256']+' target')
    if args[0]=='su' and args[2].startswith('sha256sum '):return response(model.BTF_SHA+' /sys/kernel/btf/vmlinux\n0x410fd821\n4096\n')
    assert args[:2]==['su','-c'] and args[2].endswith('--run');calls.append(1)
    if denial:return response(json.dumps(dict(type='failure',metrics={},failure=dict(reason='bpf-program-load',errno=13)))+'\n',1,'verifier: simulated policy denial\n')
    rr=owner.fixture.records()
    if not_excited:rr[3]['positive']=rr[3]['initial'].copy();rr=rr[:4]+[dict(type='stop',reason='not-excited',captures=1)]
    if corrupt:rr[3]['negative'][6]=1
    return response('\n'.join(json.dumps(r) for r in rr)+'\n')
  check0=subprocess.check_output;run0=subprocess.run;sha0=driver.sha
  def check(cmd,*a,**kw):
   if cmd==['adb','devices']:return 'List of devices attached\nmock\tdevice\n'
   if cmd[:3]==['git','rev-parse','HEAD']:return check0(['git','rev-parse',owner.launch],cwd=ROOT,text=True)
   if cmd[:3]==['git','branch','--show-current']:return 'software-only-test\n'
   if cmd[:2]==['git','show']:return check0(cmd,cwd=ROOT)
   return check0(cmd,*a,**kw)
  def run(cmd,*a,**kw):return subprocess.CompletedProcess(cmd,0,b'',b'') if cmd[:2]==['adb','push'] else run0(cmd,*a,**kw)
  with patch.object(driver,'AdbExecutor',return_value=External()),patch.object(driver,'collect_android_state',return_value=snapshot),patch.object(driver,'default_store',return_value=SimpleNamespace(unfinished=lambda:[])),patch.object(driver,'sha',side_effect=lambda p:owner.build['binary_sha256'] if Path(p)==binary else sha0(p)),patch.object(driver.subprocess,'check_output',side_effect=check),patch.object(driver.subprocess,'run',side_effect=run),patch.object(driver.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
   if corrupt:
    with self.assertRaises(ValueError):driver.main(['--binary',str(binary)])
   else:self.assertEqual(driver.main(['--binary',str(binary)]),1 if denial or not_excited else 0)
  raw=next((root/'data/private').iterdir());return raw,calls
 def test_real_driver_complete_and_independent_raw_reader(self):
  with tempfile.TemporaryDirectory() as d:
   raw,calls=self.execute(Path(d));result=self.reader.audit_raw(raw);self.assertEqual(result['status'],'OWNED_PERSISTENT_DESCRIPTOR_READ');self.assertEqual(result['processes'],3);self.assertEqual(len(calls),3)
   p=raw/'epoch-1.stdout.jsonl';r=[json.loads(z) for z in p.read_text().splitlines()];r[3]['positive'][6]=True;p.write_text('\n'.join(json.dumps(z) for z in r)+'\n');m=json.loads((raw/'manifest.json').read_text());m['results'][1]['stdout_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();(raw/'manifest.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):self.reader.audit_raw(raw)
 def test_denial_stops_without_retries_and_preserves_verifier(self):
  with tempfile.TemporaryDirectory() as d:
   raw,calls=self.execute(Path(d),denial=True);result=self.reader.audit_raw(raw);self.assertEqual((result['status'],len(calls)),('CAPABILITY_UNAVAILABLE',1));self.assertIn('verifier:',(raw/'epoch-0.stderr.log').read_text())
 def test_first_bad_negative_capture_stops_unpatched(self):
  with tempfile.TemporaryDirectory() as d:
   raw,calls=self.execute(Path(d),corrupt=True);m=json.loads((raw/'manifest.json').read_text());self.assertEqual((m['status'],len(calls)),('stopped',1));self.assertEqual([json.loads(z) for z in (raw/'epoch-0.stdout.jsonl').read_text().splitlines()][3]['negative'][6],1)
   with self.assertRaises(ValueError):self.reader.audit_raw(raw)
 def test_no_excitation_stops_and_is_not_denial(self):
  with tempfile.TemporaryDirectory() as d:
   raw,calls=self.execute(Path(d),not_excited=True);result=self.reader.audit_raw(raw);self.assertEqual((result['status'],len(calls)),('NOT_EXCITED',1))
 def test_rehashed_canonical_drift_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   raw,calls=self.execute(Path(d));p=raw/'epoch-0.stdout.jsonl';row=[json.loads(z) for z in p.read_text().splitlines()];row[-1]['canonical_after'][0]+=1;p.write_text('\n'.join(json.dumps(z) for z in row)+'\n');m=json.loads((raw/'manifest.json').read_text());m['results'][0]['stdout_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();(raw/'manifest.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):self.reader.audit_raw(raw)
 def test_rehashed_parent_relation_and_index_are_rejected(self):
  for field,delta in ((6,4096),(7,8),(8,4096),(11,4096),(12,4096)):
   with self.subTest(field=field),tempfile.TemporaryDirectory() as d:
    raw,calls=self.execute(Path(d));p=raw/'epoch-0.stdout.jsonl';row=[json.loads(z) for z in p.read_text().splitlines()];row[3]['positive'][field]+=delta;p.write_text('\n'.join(json.dumps(z) for z in row)+'\n');m=json.loads((raw/'manifest.json').read_text());m['results'][0]['stdout_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();(raw/'manifest.json').write_text(json.dumps(m))
    with self.assertRaises(ValueError):self.reader.audit_raw(raw)
 def test_audit_bypass_cannot_pass_corrupt_production_fixture(self):
  with tempfile.TemporaryDirectory() as d,patch.object(model,'audit_process',return_value=dict(status='OWNED_PERSISTENT_DESCRIPTOR_READ')),self.assertRaises(AssertionError):self.execute(Path(d),corrupt=True)
 def test_unexpected_raw_inventory_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   raw,calls=self.execute(Path(d));(raw/'extra.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'inventory'):self.reader.audit_raw(raw)
if __name__=='__main__':unittest.main()
