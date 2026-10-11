"""Immutable C producer -> real config/export -> synthetic external raw -> CLI.

Environment, runtime and measurement values are external stubs. Git/source/
build/plan and C producer are real; synthetic files never become device data.
"""
import copy,hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
from tools.diagnostic import rob_resource_analysis as model
ROOT=Path(__file__).resolve().parents[3]
class ResourceRawTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name)
  cls.launch=subprocess.check_output(['git','rev-parse','dcb1a2e'],cwd=ROOT,text=True).strip();cls.blob=staticmethod(lambda r,p:subprocess.check_output(['git','show',r+':'+p],cwd=ROOT))
  cls.build=json.loads(cls.blob(cls.launch,model.BUILD));cls.plan=json.loads(cls.blob(cls.launch,model.PLAN));cls.actual={}
  for p in cls.build['source_sha256']:(d/Path(p).name).write_bytes(cls.blob(cls.build['source_commit'],p))
  exe=d/'producer';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(d),str(d/'rob_window_probe.c'),'-o',str(exe)],check=True)
  for c in cls.plan['conditions']:
   f=d/'code';cfg=json.loads(subprocess.check_output([str(exe),*c['args'],'--write-asm',str(f)],text=True));b=f.read_bytes();cls.actual[c['name']]=(cfg,b)
   assert {'config':cfg,'sha256':hashlib.sha256(b).hexdigest()}==cls.plan['exports'][c['name']]
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def fixture(self,path):
  profile=json.loads(self.blob(self.launch,'configs/platforms/redmi-k70pro-01.json'));policy=copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment']);policy['preconditions']['cpufreq_governor']='walt'
  snapshot=dict(power=dict(wakefulness='Dozing',screen_on=False),device_idle=dict(force_idle=False),camera=dict(active=False),services=dict(mi_thermald='running'),airplane_mode=True,thermal=dict(max_cpu_c=40),cpufreq={n:dict(governor='walt',min_khz=672000,max_khz=v) for n,v in policy['preconditions']['cpufreq_max_khz'].items()})
  driver='tools/diagnostic/run_sm8650_minimal.py';sha=lambda b:hashlib.sha256(b).hexdigest()
  manifest=dict(mode=model.MODE,status='complete',target='redmi-k70pro-01',source_branch='synthetic-test-only',source_head=self.launch,binary_source_head=self.build['source_commit'],binary_sha256=self.build['binaries']['rob_window_probe'],build_evidence_path=model.BUILD,build_evidence_sha256=sha(self.blob(self.launch,model.BUILD)),plan_path=model.PLAN,plan_sha256=self.build['plan_sha256'],protocol_path=model.PROTOCOL,protocol_sha256=sha(self.blob(self.launch,model.PROTOCOL)),driver_sha256=sha(self.blob(self.launch,driver)),conditions=self.plan['conditions'],midr='0x410fd821',base_page_bytes=4096,results=[])
  (path/'driver.py').write_bytes(self.blob(self.launch,driver));(path/'environment-policy.json').write_text(json.dumps(policy))
  for side in ('initial','final'):(path/(side+'-environment.json')).write_text(json.dumps(dict(snapshot=snapshot,violations=[],warnings=[])))
  for c in self.plan['conditions']:
   name=c['name'];cfg,b=self.actual[name];value=100+cfg['n']*.05 if cfg['anchor']=='none' else 300+(4 if cfg['n']>=512 else 0)
   runtime=dict(type='runtime',cpu=7,fpcr=0,loop_address_mod64=0,ring_nodes=0,distinct_lines_per_call=0,mapping_4k_verified=None,backing_verified=None,backing_page_bytes=0,backing_info=None,event_ids=[1,2,3,4,5,6])
   rr=[dict(type='round',round=r,serial=False,pair_step=0,ns=100000,enabled=100000,running=100000,metrics={hex(e):int(value*131072) if e==17 else cfg['loop_instructions']*131072+17 if e==8 else 0 for e in cfg['events']},backing_verified=None,backing_before=None,backing_after=None) for r in range(3)]
   f=path/(name+'.stdout.jsonl');f.write_text('\n'.join(json.dumps(r) for r in [cfg,runtime,*rr])+'\n');(path/(name+'.stderr.log')).write_text('');(path/(name+'-single.bin')).write_bytes(b)
   for side in ('pre','post'):(path/(name+'-'+side+'-environment.json')).write_text(json.dumps(dict(snapshot=snapshot,violations=[],warnings=[])))
   manifest['results'].append(dict(name=name,exit_code=0,timed_out=False,wall_seconds=.1,stdout_sha256=sha(f.read_bytes()),generated_code={'single':copy.deepcopy(self.plan['exports'][name])}))
  (path/'manifest.json').write_text(json.dumps(manifest));return manifest
 def test_complete_real_producer_plan_source_and_synthetic_raw_cli(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);self.fixture(path);summary,rows,hashes=model.audit_raw(path);self.assertEqual((len(rows),len(hashes)),(140,705));self.assertEqual(len(summary['rows']),140)
   out=path/'out.json';sp=path/'sum.json';model.main([d,'--output',str(out),'--summary-output',str(sp)]);r=json.loads(out.read_text());self.assertEqual(r['windows'],420);self.assertTrue(all(c['interval']==[384,512] for c in r['classes']));self.assertEqual(r['input_sha256'],hashlib.sha256(sp.read_bytes()).hexdigest())
 def test_rehashed_sources_plan_runtime_raw_code_and_environment_reject(self):
  for kind in ('status','midr','results-order','binary','plan','driver','policy','env-missing','env-drift','stderr','config','id','round-order','mux','ns','count','code','export-config','export-hash','file-extra'):
   with tempfile.TemporaryDirectory() as d:
    path=Path(d);m=self.fixture(path);entry=m['results'][0];name=entry['name'];f=path/(name+'.stdout.jsonl')
    if kind=='status':m['status']='stopped'
    elif kind=='midr':m['midr']='0x410fd820'
    elif kind=='results-order':m['results'][:2]=m['results'][:2][::-1]
    elif kind=='binary':m['binary_sha256']='bad'
    elif kind=='plan':m['plan_sha256']='bad'
    elif kind=='driver':(path/'driver.py').write_text('drift')
    elif kind=='policy':
     p=path/'environment-policy.json';v=json.loads(p.read_text());v['preconditions']['max_cpu_temp_c']=100;p.write_text(json.dumps(v))
    elif kind=='env-missing':(path/'final-environment.json').unlink()
    elif kind=='env-drift':
     p=path/'final-environment.json';v=json.loads(p.read_text());v['snapshot']['cpufreq']['policy7']['max_khz']-=1;p.write_text(json.dumps(v))
    elif kind=='stderr':(path/(name+'.stderr.log')).write_text('warning')
    elif kind=='code':
     p=path/(name+'-single.bin');b=bytearray(p.read_bytes());b[-8]^=1;p.write_bytes(b);entry['generated_code']['single']['sha256']=hashlib.sha256(b).hexdigest()
    elif kind=='export-config':entry['generated_code']['single']['config']['n']=False
    elif kind=='export-hash':entry['generated_code']['single']['sha256']='bad'
    elif kind=='file-extra':(path/'unexpected.json').write_text('{}')
    else:
     rr=[json.loads(l) for l in f.read_text().splitlines()]
     if kind=='config':rr[0]['n']=False
     elif kind=='id':rr[1]['event_ids'][-1]=1
     elif kind=='round-order':rr[-2:]=rr[-2:][::-1]
     elif kind=='mux':rr[2]['running']=1
     elif kind=='ns':rr[2]['ns']=0
     elif kind=='count':rr[2]['metrics']['0x3']=True
     f.write_text('\n'.join(json.dumps(r) for r in rr)+'\n');entry['stdout_sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
    (path/'manifest.json').write_text(json.dumps(m));out=path/'out.json';sp=path/'sum.json'
    with self.subTest(kind=kind),self.assertRaises((ValueError,AssertionError,FileNotFoundError)):model.main([d,'--output',str(out),'--summary-output',str(sp)])
    self.assertFalse(out.exists());self.assertFalse(sp.exists())
if __name__=='__main__':unittest.main()
