#!/usr/bin/env python3
"""Bind owned descriptor graph to PMU: N0 first, scan only with exact qualified prior raw.

Purpose and finite contract: docs/design/2026-10-13-tlb-observed-reach.md. Owned
fault/map and private observers only; no global environment mutation or target retries.
"""
import argparse,copy,hashlib,json,shlex,shutil,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.run_sm8650_minimal import sha,write,AdbExecutor,collect_android_state,evaluate_preconditions_full,default_store
from tools.diagnostic import tlb_observed_reach_analysis as model

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--phase',choices=('qualification','scan'),default='qualification');p.add_argument('--qualification',type=Path);a=p.parse_args(argv);phase=a.phase;head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();build=json.loads((ROOT/model.BUILD).read_text());registered=json.loads((ROOT/model.PLAN).read_text())
 for rel in (model.DRIVER,model.CONSUMER,model.RAW,model.PROTOCOL,model.BUILD,model.PLAN):
  if hashlib.sha256(subprocess.check_output(['git','show',head+':'+rel],cwd=ROOT)).hexdigest()!=sha(ROOT/rel):raise RuntimeError('STOP uncommitted registered input '+rel)
 if not model.exact(registered,model.plans()) or sha(a.binary)!=build['binary_sha256'] or sha(ROOT/model.PLAN)!=build['actual_plan_sha256']:raise RuntimeError('STOP binary/registered plan')
 for rel,digest in build['source_sha256'].items():
  if sha(ROOT/rel)!=digest:raise RuntimeError('STOP source drift '+rel)
 prior=None
 if phase=='scan':
  if a.qualification is None:raise RuntimeError('STOP qualification required')
  from tools.diagnostic.tlb_observed_reach_raw import audit_raw
  q,h=audit_raw(a.qualification)
  if q['phase']!='qualification' or model.analyze(q)['status']!='OBSERVED_GRAPH_QUALIFIED' or q['binary_sha256']!=sha(a.binary):raise RuntimeError('STOP prior qualification mismatch')
  prior=dict(raw_directory=str(a.qualification.resolve()),manifest_sha256=sha(a.qualification/'manifest.json'),raw_sha256=h)
 elif a.qualification is not None:raise RuntimeError('STOP prior forbidden for qualification')
 if default_store().unfinished():raise RuntimeError('STOP unfinished environment journal')
 devices=subprocess.check_output(['adb','devices'],text=True).splitlines()[1:]
 if sum(l.endswith('\tdevice') for l in devices)!=1:raise RuntimeError('STOP one owned target required')
 ex=AdbExecutor(timeout_s=600)
 for name in ('tlb_observed_reach','translation_persistent_read','tlb_descriptor_graph','translation_install_read','translation_shared_leaf','translation_self_leaf','translation_self_read','rob_cache_marker','rob_speculative_marker','rob_anchor_order','rob_zero_latency_units','tlb_pfn_association','tlb_shared_alias','ptr_chase','rob_window_probe','rob_fp_drain','rob_dual_anchor','rob_retirement_units'):
  r=ex.execute(['pidof',name])
  if r.returncode!=1 or r.stdout.strip():raise RuntimeError('STOP active probe/ownership')
 r=ex.execute(['su','-c','sha256sum /sys/kernel/btf/vmlinux; cat /sys/devices/system/cpu/cpu7/regs/identification/midr_el1; getconf PAGESIZE'])
 if r.returncode or r.stdout.split()[0]!=model.BTF_SHA or [int(x,0) for x in r.stdout.splitlines()[1:]]!=[0x410fd821,4096]:raise RuntimeError('STOP BTF/target identity')
 profile=json.loads((ROOT/'configs/platforms/redmi-k70pro-01.json').read_text());policy=copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment']);policy['preconditions']['cpufreq_governor']='walt'
 out=ROOT/'data/private'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+model.MODE+'-'+phase);out.mkdir(parents=True,exist_ok=False);shutil.copy2(__file__,out/'driver.py');shutil.copy2(ROOT/model.CONSUMER,out/'consumer.py');write(out/'environment-policy.json',policy)
 m=dict(mode=model.MODE,phase=phase,target='redmi-k70pro-01',source_branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),source_head=head,binary_source_head=build['source_commit'],binary_sha256=sha(a.binary),build_sha256=sha(ROOT/model.BUILD),plan_sha256=sha(ROOT/model.PLAN),protocol_sha256=sha(ROOT/model.PROTOCOL),btf_sha256=model.BTF_SHA,consumer_sha256=sha(ROOT/model.CONSUMER),driver_sha256=sha(__file__),conditions=model.conditions(phase),qualification_input=prior,results=[],status='started');write(out/'manifest.json',m);print('OUT',out,flush=True)
 def inspect(name):
  state=collect_android_state(ex);v,w=evaluate_preconditions_full(state,policy);write(out/(name+'-environment.json'),dict(snapshot=state,violations=v,warnings=w))
  if v or w:raise RuntimeError('STOP environment '+name)
 try:
  inspect('initial');remote='/data/local/tmp/cpu-uarch/tlb_observed_reach';subprocess.run(['adb','push',str(a.binary),remote],check=True,capture_output=True);r=ex.execute(['chmod','755',remote])
  if r.returncode:raise RuntimeError('STOP chmod')
  r=ex.execute(['sha256sum',remote])
  if r.returncode or r.stdout.split()[0]!=m['binary_sha256']:raise RuntimeError('STOP deployed SHA')
  host=out/'host-plan';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'probes/diagnostic/tlb_observed_reach.c'),'-o',str(host)],check=True,capture_output=True)
  for c in model.conditions(phase):
   time.sleep(15);name=c['name'];inspect(name+'-pre');r=ex.execute(['su','-c',shlex.join([remote,*c['args']])]);f=out/(name+'.stdout.jsonl');f.write_text(r.stdout);(out/(name+'.stderr.log')).write_text(r.stderr);entry=dict(name=name,exit_code=r.returncode,timed_out=r.timed_out,stdout_sha256=sha(f));m['results'].append(entry);write(out/'manifest.json',m)
   if r.timed_out:raise RuntimeError('STOP timeout')
   rr=[json.loads(l) for l in r.stdout.splitlines()];program=None
   if len(rr)>1 and rr[0].get('probe')==model.MODE:
    pp=rr[1];program=json.loads(subprocess.check_output([str(host),'--bpf-plan',str(pp['owner_pid']),str(pp['map_fd'])],text=True));write(out/(name+'-actual-plan.json'),program)
   verdict=model.audit_process(rr,program,c,registered);entry['status']=verdict['status'];write(out/'manifest.json',m);inspect(name+'-post')
   if verdict['status']!='complete':m['status']={'CAPABILITY_UNAVAILABLE':'capability-unavailable','NOT_EXCITED':'not-excited'}.get(verdict['status'],'technical-failure');break
   if r.returncode or r.stderr:raise RuntimeError('STOP inconsistent success status/stderr')
   print('OK',name,str(rr[0]['captures'])+' captures / 12 windows',flush=True)
  else:m['status']='complete'
 except Exception as error:m['status']='stopped';m['reason']=str(error);raise
 finally:
  write(out/'manifest.json',m)
  try:inspect('final')
  except Exception as error:m['status']='stopped';m['final_environment_error']=str(error);write(out/'manifest.json',m)
 if 'final_environment_error' in m:raise RuntimeError(m['final_environment_error'])
 return 0 if m['status']=='complete' else 1
if __name__=='__main__':raise SystemExit(main())
