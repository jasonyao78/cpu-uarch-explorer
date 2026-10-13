"""Actual controller/transaction/producer plan with only external adb mocked."""
import contextlib,importlib.util,io,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tools.diagnostic import pmu_user_metadata_analysis as model
ROOT=Path(__file__).resolve().parents[3]
class EnabledMetadata(unittest.TestCase):
 def execute(self,kind='ok'):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);spec=importlib.util.spec_from_file_location('enabled_metadata_driver',ROOT/'tools/diagnostic/run_sm8650_pmu_enabled_metadata.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d);d.ROOT=root;files=(d.DRIVER,d.TX,d.PROTOCOL,model.CONSUMER,model.BUILD,model.PLAN,'configs/platforms/redmi-k70pro-01.json','probes/diagnostic/pmu_user_reader.c','probes/common/perf_group_read.h')
   for file in files:
    p=root/file;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/file).read_bytes())
   binary=root/'binary';binary.write_bytes(b'not target code; external deployment mocked');build=json.loads((root/model.BUILD).read_text());build['binary_sha256']=d.sha(binary);(root/model.BUILD).write_text(json.dumps(build));state={'policy':0,'writes':[],'calls':0};profile=json.loads((root/'configs/platforms/redmi-k70pro-01.json').read_text());pol=profile['environment_profiles']['charging-thermal']['measurement_environment'];snap=dict(power=dict(wakefulness='Dozing',screen_on=False),device_idle=dict(force_idle=False),camera=dict(active=False),services=dict(mi_thermald='running'),airplane_mode=True,thermal=dict(max_cpu_c=40),cpufreq={n:dict(governor='walt',min_khz=672000,max_khz=v) for n,v in pol['preconditions']['cpufreq_max_khz'].items()})
   def response(out='',rc=0,err=''):return SimpleNamespace(stdout=out,returncode=rc,stderr=err,timed_out=False)
   class Device:
    def execute(self,args):
     if args[0]=='pidof':return response(rc=1)
     if args[0]=='chmod':return response()
     if args[0]=='sha256sum':return response(build['binary_sha256']+' anonymous-target')
     cmd=args[-1]
     if cmd.startswith('cat /sys/'):return response('0x410fd821\n4096\n')
     if cmd.startswith('cat /proc/sys/'):return response(str(state['policy'])+'\n')
     if cmd.startswith('printf '):
      value=int(cmd.split()[1]);state['writes'].append(value)
      if kind=='restore-fail' and value==0:return response(rc=1,err='fake restore denial')
      state['policy']=value;return response()
     assert cmd.endswith('--run --config1 3');state['calls']+=1;assert state['policy']==1
     p=json.loads((root/model.PLAN).read_text())['3'];events=[dict(event=e,id=100+i,index=32 if i==0 else i,pmc_width=64,cap_user_rdpmc=True,offset=0,sequence_before=2,sequence_after=2) for i,e in enumerate(model.EVENTS)]
     if kind=='not-exposed':events[0]['index']=0
     rr=[p,dict(type='policy',perf_user_access=1,read_only=True),dict(type='metadata',cpu=7,events=events),dict(type='final',fds_closed=True,global_policy_mutation=False,counter_register_reads=0,counter_read_qualified=False)]
     if kind=='bad-read':rr[-1]['counter_register_reads']=1
     return response('\n'.join(json.dumps(r) for r in rr)+'\n')
   check0=d.subprocess.check_output;run0=d.subprocess.run
   def check(cmd,*a,**kw):
    if cmd==['adb','devices']:return 'List of devices attached\nsoftware-test\tdevice\n'
    if cmd[:3]==['git','rev-parse','HEAD']:return 'software-only-head\n'
    if cmd[:3]==['git','branch','--show-current']:return 'software-test-only\n'
    if cmd[:2]==['git','show']:
     file=cmd[2].split(':',1)[1];return (root/file).read_bytes()
    return check0(cmd,*a,**kw)
   def run(cmd,*a,**kw):return subprocess.CompletedProcess(cmd,0,b'',b'') if cmd[:2]==['adb','push'] else run0(cmd,*a,**kw)
   with patch.object(d,'AdbExecutor',return_value=Device()),patch.object(d,'collect_android_state',return_value=snap),patch.object(d,'default_store',return_value=SimpleNamespace(unfinished=lambda:[])),patch.object(d.subprocess,'check_output',side_effect=check),patch.object(d.subprocess,'run',side_effect=run),patch.object(d.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
    if kind=='bad-read':
     with self.assertRaises(ValueError):d.main(['--binary',str(binary)])
    elif kind=='restore-fail':
     with self.assertRaisesRegex(RuntimeError,'restore failed'):d.main(['--binary',str(binary)])
    else:self.assertEqual(d.main(['--binary',str(binary)]),0)
   tx=json.loads(next((root/'data/private/perf-user-access-transactions').glob('*.json')).read_text());m=json.loads(next((root/'data/private').glob('*-pmu-enabled-metadata/manifest.json')).read_text());self.assertFalse(m['counter_read_qualified'])
   self.assertEqual((tx['state'],state['policy']),('restore-failed',1) if kind=='restore-fail' else ('restored',0));return state,m
 def test_actual_driver_three_profile_samples_restored(self):
  s,m=self.execute();self.assertEqual((s['calls'],s['writes'],m['status']),(3,[1,0],'metadata-prerequisites-observed'))
 def test_first_no_index_stops_without_MRS_and_restores(self):
  s,m=self.execute('not-exposed');self.assertEqual((s['calls'],m['status']),(1,'metadata-not-exposed'))
 def test_bad_sample_and_restore_failure_both_persist_and_stop(self):self.execute('bad-read');self.execute('restore-fail')
