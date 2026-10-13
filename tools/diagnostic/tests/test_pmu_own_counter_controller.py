"""Real controller, transaction and native plans; only the external adb mocked."""
import contextlib,importlib.util,io,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.diagnostic import pmu_own_counter_analysis as m
ROOT=Path(__file__).resolve().parents[3]
def windows(p):
 rr=[p,dict(type='policy',actual=1,read_only=True)];counter=[100000]*4
 for ordinal in range(24):
  role=2-ordinal%3 if p['epoch']==1 else ordinal%3;dd=[40000,24800,64+(8192 if role==1 else 0),32+(8192 if role==2 else 0)];kb=list(counter);pre=[v+10 for v in kb];post=[v+d for v,d in zip(pre,dd)];ka=[v+10 for v in post];counter=[v+100 for v in ka]
  def direct(v):return [dict(sequence_before=2,sequence_after=2,index=32 if i==0 else i,width=64,cap=True,offset=0,hardware=x,total=x) for i,x in enumerate(v)]
  rr.append(dict(type='window',round=ordinal//3,role=role,cpu=7,enabled=100000,running=100000,kernel_before=kb,kernel_after=ka,direct_before=direct(pre),direct_after=direct(post)))
 return rr+[dict(type='final',fds_closed=True,global_policy_mutation=False,owned_direct_read=True)]
class Controller(unittest.TestCase):
 def test_absolute_fd_binding(self):
  rr=windows(m.expected(0));self.assertEqual(m.audit_process(rr,rr[0])['status'],'OWN_DIRECT_COUNTER_QUALIFIED');rr[2]['direct_before'][0]['hardware']+=10000000;rr[2]['direct_before'][0]['total']+=10000000;rr[2]['direct_after'][0]['hardware']+=10000000;rr[2]['direct_after'][0]['total']+=10000000
  with self.assertRaisesRegex(ValueError,'absolute'):m.audit_process(rr,rr[0])
 def execute(self,bad=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);spec=importlib.util.spec_from_file_location('own_counter_controller',ROOT/m.DRIVER);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d);d.ROOT=root;files=(d.DRIVER,d.TX,d.PROTOCOL,m.CONSUMER,'configs/platforms/redmi-k70pro-01.json','probes/diagnostic/pmu_own_counter.c','probes/common/perf_user_counter.h','probes/common/perf_group_read.h')
   for rel in files:p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/rel).read_bytes())
   native=root/'native';subprocess.run(['clang','-O2','-std=c11',str(ROOT/'probes/diagnostic/pmu_own_counter.c'),'-o',str(native)],check=True);plans={str(e):json.loads(subprocess.check_output([str(native),'--plan',str(e)])) for e in range(3)};binary=root/'binary';binary.write_bytes(b'External target mocked, not measured evidence');evidence=root/m.EVIDENCE;evidence.mkdir(parents=True);build=dict(source_commit='software-only',binary_sha256=d.sha(binary),source_sha256={rel:d.sha(root/rel) for rel in files});(evidence/'build.json').write_text(json.dumps(build));(evidence/'plan.json').write_text(json.dumps(plans));state={'policy':0,'calls':0,'writes':[]};profile=json.loads((root/'configs/platforms/redmi-k70pro-01.json').read_text());pol=profile['environment_profiles']['charging-thermal']['measurement_environment'];snapshot=dict(power=dict(wakefulness='Dozing',screen_on=False),device_idle=dict(force_idle=False),camera=dict(active=False),services=dict(mi_thermald='running'),airplane_mode=True,thermal=dict(max_cpu_c=40),cpufreq={n:dict(governor='walt',min_khz=672000,max_khz=v) for n,v in pol['preconditions']['cpufreq_max_khz'].items()})
   def response(out='',rc=0):return SimpleNamespace(stdout=out,returncode=rc,stderr='',timed_out=False)
   class Device:
    def execute(self,args):
     if args[0]=='pidof':return response(rc=1)
     if args[0]=='chmod':return response()
     if args[0]=='sha256sum':return response(build['binary_sha256']+' anonymous')
     cmd=args[-1]
     if cmd.startswith('cat /sys'):return response('0x410fd821\n4096\n')
     if cmd.startswith('cat /proc'):return response(str(state['policy'])+'\n')
     if cmd.startswith('printf '):state['policy']=int(cmd.split()[1]);state['writes'].append(state['policy']);return response()
     epoch=int(cmd.split()[-1]);state['calls']+=1;assert state['policy']==1
     rr=windows(plans[str(epoch)])
     if bad:rr[2]['direct_before'][0]['index']=0
     return response('\n'.join(json.dumps(v) for v in rr)+'\n')
   original_check=d.subprocess.check_output;original_run=d.subprocess.run
   def check(cmd,*a,**kw):
    if cmd==['adb','devices']:return 'List of devices attached\nsoftware-only\tdevice\n'
    if cmd[:3]==['git','rev-parse','HEAD']:return 'software-only-head\n'
    if cmd[:3]==['git','branch','--show-current']:return 'software-only-branch\n'
    if cmd[:2]==['git','show']:return (root/cmd[2].split(':',1)[1]).read_bytes()
    return original_check(cmd,*a,**kw)
   def run(cmd,*a,**kw):return subprocess.CompletedProcess(cmd,0,b'',b'') if cmd[:2]==['adb','push'] else original_run(cmd,*a,**kw)
   with patch.object(d,'AdbExecutor',return_value=Device()),patch.object(d,'collect_android_state',return_value=snapshot),patch.object(d,'default_store',return_value=SimpleNamespace(unfinished=lambda:[])),patch.object(d.subprocess,'check_output',side_effect=check),patch.object(d.subprocess,'run',side_effect=run),patch.object(d.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
    if bad:
     with self.assertRaises(ValueError):d.main(['--binary',str(binary)])
    else:self.assertEqual(d.main(['--binary',str(binary)]),0)
   tx=json.loads(next((root/'data/private/perf-user-access-transactions').glob('*.json')).read_text());self.assertEqual(tx['state'],'restored');self.assertEqual(state['policy'],0);self.assertEqual(state['writes'],[1,0]);self.assertEqual(state['calls'],1 if bad else 3)
 def test_three_producer_plans_restored(self):self.execute()
 def test_bad_metadata_restores_on_consumer_exception(self):self.execute(True)
