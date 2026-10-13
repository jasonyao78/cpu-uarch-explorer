"""Real metadata producer plans -> registered driver -> immutable raw, kernel mocked."""
import contextlib,copy,hashlib,importlib.util,io,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.diagnostic import pmu_user_metadata_analysis as m
from tools.diagnostic.pmu_user_metadata_raw import audit_raw
from tools.diagnostic.tests import test_pmu_user_metadata_analysis as fixture
ROOT=Path(__file__).resolve().parents[3]
class MetadataRaw(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.head='ccece666cbb8f161e46680611da4b1abc69cf757';cls.blob=staticmethod(lambda p:subprocess.check_output(['git','show',cls.head+':'+p],cwd=ROOT));cls.build=json.loads(cls.blob(m.BUILD));fixture.MetadataAnalysis.setUpClass();cls.fixture=fixture.MetadataAnalysis()
 @classmethod
 def tearDownClass(cls):fixture.MetadataAnalysis.tearDownClass()
 def execute(self,root,denial=False,corrupt=False,active=False):
  for rel in (m.DRIVER,m.CONSUMER,m.PROTOCOL,m.BUILD,m.PLAN,'configs/platforms/redmi-k70pro-01.json',*self.build['source_sha256']):
   p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(self.blob(rel))
  spec=importlib.util.spec_from_file_location('registered_metadata_driver',root/m.DRIVER);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d);binary=root/'external-binary';binary.write_bytes(b'not target code; deployment mocked');owner=self;calls=[];pol=json.loads(self.blob('configs/platforms/redmi-k70pro-01.json'))['environment_profiles']['charging-thermal']['measurement_environment'];state=dict(power=dict(wakefulness='Dozing',screen_on=False),device_idle=dict(force_idle=False),camera=dict(active=False),services=dict(mi_thermald='running'),airplane_mode=True,thermal=dict(max_cpu_c=40),cpufreq={n:dict(governor='walt',min_khz=672000,max_khz=v) for n,v in pol['preconditions']['cpufreq_max_khz'].items()})
  def response(stdout='',rc=0):return SimpleNamespace(stdout=stdout,stderr='',returncode=rc,timed_out=False)
  class External:
   def execute(self,args):
    if args[0]=='pidof':return response('999',0) if active and args[1]=='tlb_descriptor_dose' else response(rc=1)
    if args[0]=='chmod':return response()
    if args[0]=='sha256sum':return response(owner.build['binary_sha256']+' target')
    if args[0]=='su' and args[2].startswith('cat '):return response('0x410fd821\n4096\n')
    assert args[:2]==['su','-c'] and args[2].endswith('--run --config1 2');calls.append(args);rr=owner.fixture.records()
    if denial:rr=rr[:2]+[dict(type='failure',metrics={},failure=dict(reason='perf-open-user-config',errno=13),fds_closed=True,global_policy_mutation=False,counter_register_reads=0)]
    if corrupt:rr[-1]['counter_register_reads']=1
    return response('\n'.join(json.dumps(v) for v in rr)+'\n',1 if denial else 0)
  check0=subprocess.check_output;run0=subprocess.run;sha0=d.sha
  def check(cmd,*a,**kw):
   if cmd==['adb','devices']:return 'List of devices attached\nsoftware-test\tdevice\n'
   if cmd[:3]==['git','rev-parse','HEAD']:return owner.head+'\n'
   if cmd[:3]==['git','branch','--show-current']:return 'software-test-only\n'
   if cmd[:2]==['git','show']:return check0(cmd,cwd=ROOT)
   return check0(cmd,*a,**kw)
  def run(cmd,*a,**kw):return subprocess.CompletedProcess(cmd,0,b'',b'') if cmd[:2]==['adb','push'] else run0(cmd,*a,**kw)
  with patch.object(d,'AdbExecutor',return_value=External()),patch.object(d,'collect_android_state',return_value=state),patch.object(d,'default_store',return_value=SimpleNamespace(unfinished=lambda:[])),patch.object(d,'sha',side_effect=lambda p:owner.build['binary_sha256'] if Path(p)==binary else sha0(p)),patch.object(d.subprocess,'check_output',side_effect=check),patch.object(d.subprocess,'run',side_effect=run),patch.object(d.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
   if active:
    with self.assertRaisesRegex(RuntimeError,'active probe'):d.main(['--binary',str(binary)])
    self.assertEqual(calls,[]);return None
   if corrupt:
    with self.assertRaises(ValueError):d.main(['--binary',str(binary)])
   else:self.assertEqual(d.main(['--binary',str(binary)]),0)
  self.assertEqual(len(calls),1);return next((root/'data/private').glob('*-metadata'))
 def test_actual_plans_driver_disabled_and_first_denial_raw(self):
  for denial,status in ((False,'access-disabled'),(True,'capability-unavailable')):
   with tempfile.TemporaryDirectory() as tmp:
    raw=self.execute(Path(tmp),denial=denial);a,h=audit_raw(raw);self.assertEqual((a['status'],a['processes'],len(h)),(status,1,10));self.assertFalse(a['counter_read_qualified'])
 def test_active_TLB_prevents_metadata_open_and_bad_read_claim_stops(self):
  with tempfile.TemporaryDirectory() as tmp:self.execute(Path(tmp),active=True)
  with tempfile.TemporaryDirectory() as tmp:self.execute(Path(tmp),corrupt=True)
 def test_rehashed_fields_cannot_promote_disabled_metadata(self):
  with tempfile.TemporaryDirectory() as tmp:
   raw=self.execute(Path(tmp));mp=raw/'manifest.json';original=mp.read_bytes();mf=json.loads(original);name=mf['results'][0]['name'];f=raw/(name+'.stdout.jsonl');saved=f.read_bytes()
   for kind in ('policy','read','id','missing','class','binary'):
    v=[json.loads(l) for l in saved.splitlines()];man=json.loads(original)
    if kind=='policy':v[1]['perf_user_access']=True
    elif kind=='read':v[-1]['counter_read_qualified']=True
    elif kind=='id':v[2]['events'][1]['id']=v[2]['events'][0]['id']
    elif kind=='missing':v.pop(2)
    elif kind=='class':man['results'][0]['classification']['counter_read_qualified']=True
    elif kind=='binary':man['binary_sha256']='bad'
    f.write_text('\n'.join(json.dumps(x) for x in v)+'\n');man['results'][0]['stdout_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();mp.write_text(json.dumps(man))
    with self.subTest(kind=kind),self.assertRaises(ValueError):audit_raw(raw)
   f.write_bytes(saved);mp.write_bytes(original)
