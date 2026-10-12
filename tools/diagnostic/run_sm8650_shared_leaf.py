#!/usr/bin/env python3
"""Bounded self-only shared alias leaf pointer capability check; baseline environment read-only."""
import argparse,copy,hashlib,json,shlex,shutil,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.run_sm8650_minimal import sha,write,AdbExecutor,collect_android_state,evaluate_preconditions_full,default_store
from tools.diagnostic import translation_shared_leaf_analysis as model

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);a=p.parse_args(argv)
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();build=json.loads((ROOT/model.BUILD).read_text())
 for rel in (model.DRIVER,model.CONSUMER,model.PROTOCOL,model.BUILD,model.PLAN):
  if hashlib.sha256(subprocess.check_output(['git','show',head+':'+rel],cwd=ROOT)).hexdigest()!=sha(ROOT/rel):raise RuntimeError('STOP uncommitted registered input')
 for rel,digest in build['source_sha256'].items():
  if sha(ROOT/rel)!=digest:raise RuntimeError('STOP source drift')
 if sha(a.binary)!=build['binary_sha256']:raise RuntimeError('STOP binary')
 if default_store().unfinished():raise RuntimeError('STOP unfinished journal')
 devices=subprocess.check_output(['adb','devices'],text=True).splitlines()[1:]
 if sum(s.endswith('\tdevice') for s in devices)!=1:raise RuntimeError('STOP one owned device required')
 ex=AdbExecutor(timeout_s=30)
 for name in ('translation_shared_leaf','ptr_chase','rob_zero_latency_units','tlb_pfn_association','rob_window_probe'):
  r=ex.execute(['pidof',name])
  if r.returncode!=1 or r.stdout.strip():raise RuntimeError('STOP active probe/ownership')
 r=ex.execute(['su','-c','sha256sum /sys/kernel/btf/vmlinux; cat /sys/devices/system/cpu/cpu7/regs/identification/midr_el1; getconf PAGESIZE'])
 if r.returncode or r.stdout.split()[0]!=model.BTF_SHA or [int(x,0) for x in r.stdout.splitlines()[1:]]!=[0x410fd821,4096]:raise RuntimeError('STOP target BTF/identity')
 profile=json.loads((ROOT/'configs/platforms/redmi-k70pro-01.json').read_text());policy=copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment']);policy['preconditions']['cpufreq_governor']='walt'
 out=ROOT/'data/private'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+model.MODE);out.mkdir(exist_ok=False)
 shutil.copy2(__file__,out/'driver.py');shutil.copy2(ROOT/model.CONSUMER,out/'consumer.py');write(out/'environment-policy.json',policy)
 m=dict(mode=model.MODE,target='redmi-k70pro-01',source_branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),source_head=head,binary_source_head=build['source_commit'],binary_sha256=sha(a.binary),build_sha256=sha(ROOT/model.BUILD),protocol_sha256=sha(ROOT/model.PROTOCOL),btf_sha256=model.BTF_SHA,consumer_sha256=sha(ROOT/model.CONSUMER),driver_sha256=sha(__file__),results=[],status='started');write(out/'manifest.json',m);print('OUT',out,flush=True)
 def inspect(name):
  state=collect_android_state(ex);v,w=evaluate_preconditions_full(state,policy);write(out/(name+'-environment.json'),dict(snapshot=state,violations=v,warnings=w))
  if v or w:raise RuntimeError('STOP environment '+name)
 try:
  inspect('initial');remote='/data/local/tmp/cpu-uarch/translation_shared_leaf';subprocess.run(['adb','push',str(a.binary),remote],check=True,capture_output=True)
  r=ex.execute(['chmod','755',remote])
  if r.returncode:raise RuntimeError('STOP chmod')
  r=ex.execute(['sha256sum',remote])
  if r.returncode or r.stdout.split()[0]!=m['binary_sha256']:raise RuntimeError('STOP deployed SHA')
  host=out/'host-plan';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'probes/diagnostic/translation_shared_leaf.c'),'-o',str(host)],check=True,capture_output=True)
  for epoch in range(3):
   time.sleep(15);name='epoch-'+str(epoch);inspect(name+'-pre');r=ex.execute(['su','-c',shlex.join([remote,'--run'])]);f=out/(name+'.stdout.jsonl');f.write_text(r.stdout);(out/(name+'.stderr.log')).write_text(r.stderr)
   entry=dict(name=name,exit_code=r.returncode,timed_out=r.timed_out,stdout_sha256=sha(f));m['results'].append(entry);write(out/'manifest.json',m)
   if r.timed_out:raise RuntimeError('STOP timeout')
   records=[json.loads(s) for s in r.stdout.splitlines()];plan=None
   if len(records)==1 and records[0].get('type')=='leaf-read':
    pp=records[0]['program'];plan=json.loads(subprocess.check_output([str(host),'--plan',str(pp['owner_pid']),str(pp['selected_va']),str(pp['map_fd'])],text=True));write(out/(name+'-actual-plan.json'),plan)
   verdict=model.audit_process(records,plan);entry['verdict']=verdict;write(out/'manifest.json',m);inspect(name+'-post');print('RESULT',name,verdict['status'],flush=True)
   if verdict['status']!='SHARED_LEAF_DESCRIPTOR_READ':m['status']={'CAPABILITY_UNAVAILABLE':'capability-unavailable','NOT_EXCITED':'not-excited'}.get(verdict['status'],'technical-failure');break
   if r.returncode or r.stderr:raise RuntimeError('STOP inconsistent success status/stderr')
  else:m['status']='complete'
 except Exception as error:m['status']='stopped';m['reason']=str(error);raise
 finally:
  write(out/'manifest.json',m)
  try:inspect('final')
  except Exception as error:m['status']='stopped';m['final_environment_error']=str(error);write(out/'manifest.json',m)
 if 'final_environment_error' in m:raise RuntimeError(m['final_environment_error'])
 return 0 if m['status']=='complete' else 1
if __name__=='__main__':raise SystemExit(main())
