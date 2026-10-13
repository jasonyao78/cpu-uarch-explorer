#!/usr/bin/env python3
"""Own long64 metadata under a declared, restored 0->1->0 policy; never MRS.

Purpose: docs/design/2026-10-13-pmu-enabled-metadata.md. Source, readiness,
write-ahead and restore state are explicit; no frequency or other setting writes.
"""
import argparse,copy,hashlib,json,shlex,shutil,subprocess,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.run_sm8650_minimal import AdbExecutor,sha,write,collect_android_state,evaluate_preconditions_full,default_store
from tools.diagnostic.perf_user_access_transaction import PerfUserAccessTransaction,durable_write
from tools.diagnostic import pmu_user_metadata_analysis as model
PROTOCOL='docs/design/2026-10-13-pmu-enabled-metadata.md';DRIVER='tools/diagnostic/run_sm8650_pmu_enabled_metadata.py';TX='tools/diagnostic/perf_user_access_transaction.py'
def ownership(ex):
 devices=subprocess.check_output(['adb','devices'],text=True).splitlines()[1:]
 if sum(l.endswith('\tdevice') for l in devices)!=1:raise RuntimeError('STOP one online target required')
 for name in ('pmu_user_reader','tlb_descriptor_dose','tlb_observed_reach','ptr_chase','rob_window_probe','rob_issue_marker','rob_fenced_issue_marker','rob_cache_marker','rob_speculative_marker','translation_persistent_read','rob_fp_drain','rob_dual_anchor','rob_anchor_order','rob_zero_latency_units'):
  r=ex.execute(['pidof',name])
  if r.returncode!=1 or r.stdout.strip():raise RuntimeError('STOP active probe/ownership')
 r=ex.execute(['su','-c','cat /sys/devices/system/cpu/cpu7/regs/identification/midr_el1; getconf PAGESIZE'])
 if r.returncode or [int(v,0) for v in r.stdout.split()]!=[0x410fd821,4096]:raise RuntimeError('STOP target identity')
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path);p.add_argument('--restore',type=Path);a=p.parse_args(argv);ex=AdbExecutor(timeout_s=120);ownership(ex);journals=ROOT/'data/private/perf-user-access-transactions'
 if a.restore:
  path=a.restore.resolve()
  if path.parent!=journals.resolve() or path.suffix!='.json':raise RuntimeError('STOP unowned transaction path')
  tx=PerfUserAccessTransaction(ex,path);tx.restore();print('RESTORED',path,flush=True);return 0
 if a.binary is None:raise RuntimeError('STOP binary required')
 if default_store().unfinished():raise RuntimeError('STOP unfinished runner environment transaction')
 for path in journals.glob('*.json'):
  if json.loads(path.read_text()).get('state')!='restored':raise RuntimeError('STOP unfinished perf policy transaction '+str(path))
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();registered=(DRIVER,TX,PROTOCOL,model.CONSUMER,model.BUILD,model.PLAN)
 for rel in registered:
  if hashlib.sha256(subprocess.check_output(['git','show',head+':'+rel],cwd=ROOT)).hexdigest()!=sha(ROOT/rel):raise RuntimeError('STOP uncommitted input '+rel)
 build=json.loads((ROOT/model.BUILD).read_text());plan=json.loads((ROOT/model.PLAN).read_text())
 if not model._same(plan,{str(f):model.expected(f) for f in (2,3)}) or sha(a.binary)!=build['binary_sha256']:raise RuntimeError('STOP binary/plans')
 for rel,h in build['source_sha256'].items():
  if sha(ROOT/rel)!=h:raise RuntimeError('STOP producer source drift')
 profile=json.loads((ROOT/'configs/platforms/redmi-k70pro-01.json').read_text());policy=copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment']);policy['preconditions']['cpufreq_governor']='walt';stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=ROOT/'data/private'/(stamp+'-pmu-enabled-metadata');out.mkdir(parents=True,exist_ok=False);shutil.copy2(__file__,out/'driver.py');shutil.copy2(ROOT/TX,out/'transaction-helper.py');shutil.copy2(ROOT/model.CONSUMER,out/'consumer.py');write(out/'environment-policy.json',policy)
 tx_path=journals/(stamp+'-'+uuid.uuid4().hex[:12]+'.json');tx=PerfUserAccessTransaction(ex,tx_path);manifest=dict(mode='pmu-enabled-metadata',target='redmi-k70pro-01',midr='0x410fd821',source_head=head,source_branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),binary_source_head=build['source_commit'],binary_sha256=sha(a.binary),source_sha256={p:sha(ROOT/p) for p in registered},transaction_path=str(tx_path),registered_conditions=[dict(name=f'e{e}-f3',args=['--run','--config1','3']) for e in range(3)],results=[],status='created',parent_global_policy_mutation=True,producer_register_reads=0,counter_read_qualified=False);write(out/'manifest.json',manifest);print('OUT',out,flush=True)
 def inspect(name):
  s=collect_android_state(ex);v,w=evaluate_preconditions_full(s,policy);write(out/(name+'-environment.json'),dict(snapshot=s,violations=v,warnings=w))
  if v or w:raise RuntimeError('STOP environment '+name)
 inspect('initial');remote='/data/local/tmp/cpu-uarch/pmu_user_reader';subprocess.run(['adb','push',str(a.binary),remote],check=True,capture_output=True);q=ex.execute(['chmod','755',remote])
 if q.returncode:raise RuntimeError('STOP chmod')
 q=ex.execute(['sha256sum',remote])
 if q.returncode or q.stdout.split()[0]!=manifest['binary_sha256']:raise RuntimeError('STOP deployed binarySHA')
 def work():
  for c in manifest['registered_conditions']:
   time.sleep(15);name=c['name'];inspect(name+'-pre');q=ex.execute(['su','-c',shlex.join([remote,*c['args']])]);stdout=out/(name+'.stdout.jsonl');stdout.write_text(q.stdout);(out/(name+'.stderr.log')).write_text(q.stderr);result=dict(name=name,args=c['args'],exit_code=q.returncode,timed_out=q.timed_out,stdout_sha256=sha(stdout));manifest['results'].append(result);write(out/'manifest.json',manifest)
   if q.timed_out:raise RuntimeError('STOP metadata timeout')
   value=model.audit_process([json.loads(l) for l in q.stdout.splitlines()],c,plan);result['classification']=value;inspect(name+'-post')
   if value['status']=='CAPABILITY_UNAVAILABLE':manifest['status']='capability-unavailable';write(out/'manifest.json',manifest);return
   if q.returncode or q.stderr or value['status']!='METADATA_INTAKE_COMPLETE' or value['policy']!=1:raise RuntimeError('STOP unexpected metadata/profile')
   ev=value['events'];eligible=all(e['cap_user_rdpmc'] and 1<=e['index']<=32 and e['pmc_width']==64 and e['sequence_before']==e['sequence_after'] and not(e['sequence_before']%2) for e in ev) and len({e['index'] for e in ev})==4;result['metadata_prerequisites_observed']=eligible;write(out/'manifest.json',manifest)
   if not eligible:manifest['status']='metadata-not-exposed';write(out/'manifest.json',manifest);return
   print('OK',name,'own index/width64 prerequisites',flush=True)
  manifest['status']='metadata-prerequisites-observed';write(out/'manifest.json',manifest)
 try:tx.run(work,dict(source_head=head,protocol=PROTOCOL,protocol_sha256=sha(ROOT/PROTOCOL),raw_directory=str(out),binary_sha256=manifest['binary_sha256']))
 except BaseException as e:manifest['status']='stopped';manifest['error']=repr(e);raise
 finally:
  manifest['transaction_state']=json.loads(tx_path.read_text()).get('state') if tx_path.exists() else 'not-created';write(out/'manifest.json',manifest)
  try:inspect('final')
  except BaseException as e:manifest['final_environment_error']=repr(e);write(out/'manifest.json',manifest);raise
 if tx.read()!=0 or manifest['transaction_state']!='restored':raise RuntimeError('STOP unclosed perf profile')
 print('RESTORED baseline0; MRS reads0; status',manifest['status'],flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
