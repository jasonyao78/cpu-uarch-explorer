"""Real C dual plan/program -> driver/writer -> raw consumer; external PMU is synthetic.

Immutable launch/source/build are real Git evidence. These software fixtures
never stand in for target-device measurements.
"""
import contextlib,copy,hashlib,importlib.util,io,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.diagnostic import rob_fusion_analysis as model
from tools.diagnostic.tests import test_rob_fusion as fixture
ROOT=Path(__file__).resolve().parents[3]
class FusionRaw(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.launch=subprocess.check_output(['git','rev-parse','8182b4321924605a34af0582409cad876558d748'],cwd=ROOT,text=True).strip()
  cls.blob=staticmethod(lambda rel:subprocess.check_output(['git','show',cls.launch+':'+rel],cwd=ROOT))
  cls.build=json.loads(cls.blob(model.BUILD));cls.plan=json.loads(cls.blob(model.PLAN))
  fixture.FusionAnalysis.setUpClass();cls.actual=fixture.FusionAnalysis()
  model.validate_plan(fixture.FusionAnalysis.actual)
 @classmethod
 def tearDownClass(cls):fixture.FusionAnalysis.tearDownClass()
 def execute_fixture(self,root,corrupt=False,phase="qualification",active=False):
  required=[model.DRIVER,model.CONSUMER,model.PROTOCOL,model.BUILD,model.PLAN,'configs/platforms/redmi-k70pro-01.json',*self.build['source_sha256']]
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
    if args[0]=='pidof':return result('999\n') if active and args[1]=='rob_dual_anchor' else result(rc=1)
    if args[0]=='chmod':return result()
    if args[0]=='sha256sum':return result(owner.build['binaries']['rob_fusion_groups']+' anonymous-target-binary')
    if args[0]=='su' and args[2].startswith('cat '):return result('0x410fd821\n4096\n')
    assert args[:2]==['su','-c'];reverse='--reverse' in args[2];index=len(calls);assert reverse==('--reverse' in model.conditions(phase)[index]['args']);calls.append(index);records=owner.actual.records(model.conditions(phase)[index])
    if corrupt:records[1]['words'][16]^=1
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
  def sha(p):return self.build['binaries']['rob_fusion_groups'] if Path(p)==binary else original_sha(p)
  with patch.object(driver,'AdbExecutor',return_value=External()),patch.object(driver,'collect_android_state',return_value=snapshot),patch.object(driver,'default_store',return_value=SimpleNamespace(unfinished=lambda:[])),patch.object(driver,'sha',side_effect=sha),patch.object(driver.subprocess,'check_output',side_effect=check),patch.object(driver.subprocess,'run',side_effect=run),patch.object(driver.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
   args=['--binary',str(binary),'--phase',phase]
   if phase=='scan':args+=['--qualification',str(next((root/'data/private').glob('*-qualification')))]
   if corrupt:
    with self.assertRaises(ValueError):driver.main(args)
   else:self.assertEqual(driver.main(args),0)
  raw=next((root/'data/private').glob('*-'+phase));manifest=json.loads((raw/'manifest.json').read_text())
  self.assertEqual((len(calls),manifest['status']),(1,'stopped') if corrupt else (len(model.conditions(phase)),'complete'))
  return raw,manifest
 def test_registered_driver_first_bad_program_stops_one_process(self):
  with tempfile.TemporaryDirectory() as d:self.execute_fixture(Path(d),True)
 def test_driver_audit_bypass_is_caught_by_first_bad_fixture(self):
  with tempfile.TemporaryDirectory() as d,patch.object(model,'audit_process',return_value=None):
   with self.assertRaises(AssertionError):self.execute_fixture(Path(d),True)
 def test_real_plan_driver_persistence_raw_and_rehashed_counterexamples(self):
  with tempfile.TemporaryDirectory() as d:
   raw,original=self.execute_fixture(Path(d));summary,hashes=model.audit_raw(raw);a=model.analyze(summary)
   self.assertEqual((len(hashes),len(summary['rows']),a['windows']),(78,18,144));self.assertEqual(a['status'],'group-controls-qualified')
   for kind in ('missing','extra','duplicate','requested','result-order','plan','binary','midr','status','driver','stderr','word','typed','window-order','base','ids','mux','count','copy','ns','ir','result','gpr','environment'):
    mp=raw/'manifest.json';m=copy.deepcopy(original);name=m['results'][0]['name'];f=raw/(name+'.stdout.jsonl');target=mp;saved=mp.read_bytes()
    if kind=='missing':target=raw/'final-environment.json';saved=target.read_bytes();target.unlink()
    elif kind=='extra':target=raw/'unexpected';saved=None;target.write_text('extra')
    elif kind=='driver':target=raw/'driver.py';saved=target.read_bytes();target.write_text('drift')
    elif kind=='stderr':target=raw/(name+'.stderr.log');saved=target.read_bytes();target.write_text('warning')
    elif kind=='environment':
     target=raw/'final-environment.json';saved=target.read_bytes();v=json.loads(saved);v['snapshot']['cpufreq']['policy7']['max_khz']-=1;target.write_text(json.dumps(v))
    elif kind in ('word','typed','window-order','base','ids','mux','count','copy','ns','ir','result','gpr'):
     target=f;saved=f.read_bytes();rr=[json.loads(l) for l in saved.splitlines()]
     if kind=='word':rr[1]['words'][16]^=1
     elif kind=='typed':rr[0]['chain']=True
     elif kind=='window-order':rr[-2:]=rr[-2:][::-1]
     elif kind=='base':rr[-1]['code_base']+=4096
     elif kind=='ids':rr[2]['event_ids'][1]=rr[2]['event_ids'][0]
     elif kind=='mux':rr[3]['running']=1
     elif kind=='count':rr[3]['counts'][0]=True
     elif kind=='copy':rr[3]['code_matches_plan']=False
     elif kind=='ns':rr[3]['ns']=0
     elif kind=='ir':rr[3]['counts'][1]=1
     elif kind=='result':rr[3]['result_bits']=[0,0]
     elif kind=='gpr':rr[3]['gpr_result']=1
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
 def test_actual_qualification_to_scan_gate_provenance_and_full_pipeline(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);q,qm=self.execute_fixture(root);raw,sm=self.execute_fixture(root,phase='scan');summary,hashes=model.audit_raw(raw);a=model.analyze(summary)
   self.assertEqual((len(hashes),a['windows'],a['status']),(582,1152,'fusion-compatible-work-response'))
   mp=raw/'manifest.json';original=mp.read_bytes()
   for bad in ('missing','sha','binary','bool','path','scan-link'):
    m=json.loads(original)
    if bad=='missing':m['qualification_input']=None
    elif bad=='sha':m['qualification_input']['manifest_sha256']='wrong'
    elif bad=='binary':m['qualification_input']['binary_sha256']='wrong'
    elif bad=='bool':m['qualification_input']['qualified']=1
    elif bad=='path':m['qualification_input']['raw_directory']='../unsafe-path'
    elif bad=='scan-link':m['qualification_input']['raw_directory']=raw.name
    mp.write_text(json.dumps(m))
    with self.subTest(bad=bad),self.assertRaises((ValueError,FileNotFoundError)):model.audit_raw(raw)
    mp.write_bytes(original)
 def test_unqualified_raw_cannot_launch_scan(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);q,qm=self.execute_fixture(root)
   for result in qm['results']:
    if 'independent-nop-pair-g0' not in result['name']:continue
    f=q/(result['name']+'.stdout.jsonl');rr=[json.loads(l) for l in f.read_text().splitlines()]
    for z in rr[3:]:z['counts'][0]=416*131072
    f.write_text('\n'.join(json.dumps(z) for z in rr)+'\n');result['stdout_sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
   (q/'manifest.json').write_text(json.dumps(qm))
   self.assertFalse(model.analyze(model.audit_raw(q)[0])['qualified'])
   with self.assertRaisesRegex(RuntimeError,'unqualified'):self.execute_fixture(root,phase='scan')
 def test_v1_mode_cannot_be_promoted_to_v2_raw(self):
  with tempfile.TemporaryDirectory() as d:
   raw,manifest=self.execute_fixture(Path(d));manifest['mode']='rob-dual-anchor';(raw/'manifest.json').write_text(json.dumps(manifest))
   with self.assertRaisesRegex(ValueError,'manifest identity'):model.audit_raw(raw)
 def test_anchor_scaled_zero_noise_flows_through_qualification_and_scan(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);q,qm=self.execute_fixture(root)
   for result in qm['results']:
    if 'none-nop-pair-g0' not in result['name']:continue
    f=q/(result['name']+'.stdout.jsonl');rr=[json.loads(l) for l in f.read_text().splitlines()]
    for z in rr[3:]:z['counts'][0]=131072
    rr[3]['counts'][0]=147456;f.write_text('\n'.join(json.dumps(z) for z in rr)+'\n');result['stdout_sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
   (q/'manifest.json').write_text(json.dumps(qm));a=model.analyze(model.audit_raw(q)[0]);self.assertTrue(a['qualified']);self.assertTrue(any(not p['stable'] for p in a['points'] if p['anchor']=='none' and p['groups']==0))
   raw,_=self.execute_fixture(root,phase='scan');self.assertEqual(model.analyze(model.audit_raw(raw)[0])['status'],'fusion-compatible-work-response')
 def test_prior_live_anchor_blocks_new_driver_before_probe(self):
  with tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(RuntimeError,'active probe'):self.execute_fixture(Path(d),active=True)
 def test_Icache_noise_in_actual_raw_prevents_scan_authorization(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);q,qm=self.execute_fixture(root);result=qm['results'][0];f=q/(result['name']+'.stdout.jsonl');rr=[json.loads(l) for l in f.read_text().splitlines()];rr[3]['counts'][5]=132;f.write_text('\n'.join(json.dumps(z) for z in rr)+'\n');result['stdout_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();(q/'manifest.json').write_text(json.dumps(qm));self.assertFalse(model.analyze(model.audit_raw(q)[0])['qualified'])
   with self.assertRaisesRegex(RuntimeError,'unqualified'):self.execute_fixture(root,phase='scan')
if __name__=='__main__':unittest.main()
