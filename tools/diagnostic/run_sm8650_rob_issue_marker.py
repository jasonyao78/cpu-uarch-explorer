#!/usr/bin/env python3
"""Test one-shot retirement-blocked marker N0 on one owned SM8650; no environment mutation.

Purpose/finite protocol: docs/design/2026-10-13-rob-issue-marker.md. Reuses
validated environment and deployment primitives; the raw program/schedule consumer is
mandatory before advancing. Partial attempts are retained, never patched.
"""
import argparse,copy,hashlib,json,shlex,shutil,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.run_sm8650_minimal import sha,write,AdbExecutor,collect_android_state,evaluate_preconditions_full,default_store
from tools.diagnostic import rob_issue_marker_analysis as model

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--phase',choices=('qualification',),default='qualification');p.add_argument('--qualification',type=Path);a=p.parse_args(argv);phase=a.phase;head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 for rel in (model.DRIVER,model.CONSUMER,model.PROTOCOL,model.BUILD,model.PLAN):
  b=subprocess.check_output(['git','show',head+':'+rel],cwd=ROOT)
  if hashlib.sha256(b).hexdigest()!=sha(ROOT/rel):raise RuntimeError('STOP uncommitted registered input '+rel)
 build=json.loads((ROOT/model.BUILD).read_text());plan=json.loads((ROOT/model.PLAN).read_text());model.validate_plan(plan)
 if sha(a.binary)!=build['binaries']['rob_issue_marker'] or sha(ROOT/model.PLAN)!=build['plan_sha256']:raise RuntimeError('STOP unregistered binary/plan')
 for rel,digest in build['source_sha256'].items():
  if sha(ROOT/rel)!=digest:raise RuntimeError('STOP source drift '+rel)
 qualification=None
 if a.qualification is not None:raise RuntimeError('STOP previous qualification input forbidden')
 if default_store().unfinished():raise RuntimeError('STOP unfinished environment journal')
 devices=subprocess.check_output(['adb','devices'],text=True).splitlines()[1:]
 if sum(l.endswith('\tdevice') for l in devices)!=1:raise RuntimeError('STOP one online target required')
 ex=AdbExecutor(timeout_s=120)
 for name in ('rob_speculative_marker','rob_cache_marker','tlb_observed_reach','translation_persistent_read','tlb_descriptor_graph','translation_install_read','translation_self_read','translation_self_leaf','translation_shared_leaf','ptr_chase','rob_window_probe','rob_dependency_pair','rob_issue_marker','rob_anchor_order','rob_fp_drain','rob_retirement_units','rob_fusion_groups','rob_destination_control','rob_dual_anchor','rob_resident_control','tlb_cross_region','tlb_page_distribution','tlb_full_repr','tlb_pointer_repr','tlb_balanced_reach','tlb_shared_alias','pagemap_visibility','tlb_address_geometry','tlb_walk_parallel','tlb_local_turn','tlb_victim_history','tlb_competition','tlb_capacity','tlb_history','tlb_local_pair','rob_cold_pair'):
  active=ex.execute(['pidof',name])
  if active.returncode!=1 or active.stdout.strip():raise RuntimeError('STOP active probe or failed ownership check')
 profile=json.loads((ROOT/'configs/platforms/redmi-k70pro-01.json').read_text());policy=copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment']);policy['preconditions']['cpufreq_governor']='walt'
 out=ROOT/'data/private'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+model.MODE+'-'+phase);out.mkdir(parents=True,exist_ok=False);shutil.copy2(__file__,out/'driver.py');shutil.copy2(ROOT/model.CONSUMER,out/'consumer.py');write(out/'environment-policy.json',policy)
 m=dict(mode=model.MODE,phase=phase,purpose=__doc__,target='redmi-k70pro-01',source_branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),source_head=head,binary_source_head=build['source_commit'],binary_sha256=sha(a.binary),build_evidence_path=model.BUILD,build_evidence_sha256=sha(ROOT/model.BUILD),plan_path=model.PLAN,plan_sha256=sha(ROOT/model.PLAN),consumer_path=model.CONSUMER,consumer_sha256=sha(ROOT/model.CONSUMER),protocol_path=model.PROTOCOL,protocol_sha256=sha(ROOT/model.PROTOCOL),driver_sha256=sha(__file__),conditions=model.conditions(phase),results=[],status='started');write(out/'manifest.json',m);print('OUT',out,flush=True)
 def inspect(name):
  state=collect_android_state(ex);violations,warnings=evaluate_preconditions_full(state,policy);write(out/(name+'-environment.json'),dict(snapshot=state,violations=violations,warnings=warnings))
  if violations or warnings:raise RuntimeError('STOP environment '+name+': '+str(violations)+str(warnings))
 try:
  inspect('initial');remote='/data/local/tmp/cpu-uarch/rob_issue_marker';subprocess.run(['adb','push',str(a.binary),remote],check=True,capture_output=True)
  r=ex.execute(['chmod','755',remote])
  if r.returncode:raise RuntimeError('STOP chmod')
  r=ex.execute(['sha256sum',remote])
  if r.returncode or r.stdout.split()[0]!=m['binary_sha256']:raise RuntimeError('STOP deployed binary SHA')
  r=ex.execute(['su','-c','cat /sys/devices/system/cpu/cpu7/regs/identification/midr_el1; getconf PAGESIZE'])
  if r.returncode or [int(x,0) for x in r.stdout.split()]!=[0x410fd821,4096]:raise RuntimeError('STOP target identity')
  m.update(midr='0x410fd821',base_page_bytes=4096,qualification_input=qualification)
  for c in model.conditions(phase):
   time.sleep(15);name=c['name'];inspect(name+'-pre');start=time.monotonic();r=ex.execute(['su','-c',shlex.join([remote,*c['args']])]);stdout=out/(name+'.stdout.jsonl');stdout.write_text(r.stdout);(out/(name+'.stderr.log')).write_text(r.stderr);m['results'].append(dict(name=name,exit_code=r.returncode,timed_out=r.timed_out,wall_seconds=time.monotonic()-start,stdout_sha256=sha(stdout)));write(out/'manifest.json',m)
   if r.timed_out:raise RuntimeError('STOP probe timeout '+name)
   records=[json.loads(l) for l in r.stdout.splitlines()];v=model.audit_process(records,c,plan);inspect(name+'-post')
   if v['status']=='CAPABILITY_UNAVAILABLE':m['status']='capability-unavailable';m['failure']=v['failure'];break
   if r.returncode or r.stderr or v['status']!='complete':raise RuntimeError('STOP probe status/stderr '+name)
   print('OK',name,'144 windows',flush=True)
  else:m['status']='complete'
 except Exception as error:m['status']='stopped';m['reason']=str(error);raise
 finally:
  write(out/'manifest.json',m)
  try:inspect('final')
  except Exception as error:m['status']='stopped';m['final_environment_error']=str(error);write(out/'manifest.json',m)
 if 'final_environment_error' in m:raise RuntimeError(m['final_environment_error'])
 return 0 if m['status']=='complete' else 1
if __name__=='__main__':raise SystemExit(main())
