#!/usr/bin/env python3
"""Finite L1 qualification/scan with immutable producer plans and whole raw.

Purpose docs/design/2026-10-13-l1-tlb-reach.md; primary sole board operator.
No environment mutation; unfinished perf/runner journals stop every new batch.
"""
import argparse,copy,hashlib,json,shlex,shutil,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.run_sm8650_minimal import AdbExecutor,sha,write,collect_android_state,evaluate_preconditions_full,default_store
from tools.diagnostic.run_sm8650_pmu_enabled_metadata import ownership
from tools.diagnostic import l1_tlb_reach_analysis as model

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--mode',choices=('i','d'),required=True);p.add_argument('--phase',choices=('qualification','scan'),required=True);p.add_argument('--qualification',type=Path);a=p.parse_args(argv)
 ex=AdbExecutor(timeout_s=180);ownership(ex);q=ex.execute(['pidof','l1_tlb_reach'])
 if q.returncode!=1 or q.stdout.strip():raise RuntimeError('STOP active L1 probe')
 if default_store().unfinished():raise RuntimeError('STOP unfinished environment journal')
 for path in (ROOT/'data/private/perf-user-access-transactions').glob('*.json'):
  if json.loads(path.read_text()).get('state')!='restored':raise RuntimeError('STOP unfinished perf policy journal')
 q=ex.execute(['su','-c','cat /proc/sys/kernel/perf_user_access'])
 if q.returncode or q.stdout.strip()!='0':raise RuntimeError('STOP unexpected perf user profile')
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();build=json.loads((ROOT/model.EVIDENCE/'build.json').read_text());plans=json.loads((ROOT/model.EVIDENCE/'plan.json').read_text())
 for rel,h in build['source_sha256'].items():
  if sha(ROOT/rel)!=h or hashlib.sha256(subprocess.check_output(['git','show',head+':'+rel],cwd=ROOT)).hexdigest()!=h:raise RuntimeError('STOP producer/source drift '+rel)
 for rel in (model.EVIDENCE+'/build.json',model.EVIDENCE+'/plan.json'):
  if hashlib.sha256(subprocess.check_output(['git','show',head+':'+rel],cwd=ROOT)).hexdigest()!=sha(ROOT/rel):raise RuntimeError('STOP uncommitted build/plan')
 if sha(a.binary)!=build['binary_sha256']:raise RuntimeError('STOP binary drift')
 expected={f'{m}:{e}:{p}':model.expected(m,e,p) for m in ('i','d') for e in range(3) for p in ('qualification','scan')}
 if not model._same(plans,expected):raise RuntimeError('STOP actual plan drift')
 if a.phase=='scan':
  if a.qualification is None:raise RuntimeError('STOP qualification raw required')
  qm=json.loads((a.qualification/'manifest.json').read_text())
  if qm.get('status')!='L1_QUALIFIED' or qm.get('mode')!=a.mode or qm.get('binary_sha256')!=build['binary_sha256'] or qm.get('phase')!='qualification':raise RuntimeError('STOP qualification provenance')
  if len(qm['results'])!=3:raise RuntimeError('STOP partial qualification')
  for row in qm['results']:
   stdout=a.qualification/(row['name']+'.stdout.jsonl')
   if sha(stdout)!=row['stdout_sha256']:raise RuntimeError('STOP qualification raw drift')
   p0=model.expected(a.mode,row['epoch'],'qualification');v=model.audit_process([json.loads(l) for l in stdout.read_text().splitlines()],p0)
   if v['status']!='L1_QUALIFIED':raise RuntimeError('STOP original qualification gate')
 profile=json.loads((ROOT/'configs/platforms/redmi-k70pro-01.json').read_text());policy=copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment']);policy['preconditions']['cpufreq_governor']='walt';stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=ROOT/'data/private'/(stamp+'-l1-'+a.mode+'-tlb-'+a.phase);out.mkdir(parents=True,exist_ok=False)
 for rel,name in ((model.DRIVER,'driver.py'),(model.CONSUMER,'consumer.py'),(model.PROTOCOL,'protocol.md'),(model.EVIDENCE+'/build.json','build.json'),(model.EVIDENCE+'/plan.json','plan.json')):shutil.copy2(ROOT/rel,out/name)
 write(out/'environment-policy.json',policy)
 manifest=dict(target='redmi-k70pro-01',mode=a.mode,phase=a.phase,source_head=head,source_branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),binary_source_head=build['source_commit'],binary_sha256=sha(a.binary),source_sha256=build['source_sha256'],qualification_manifest_sha256=sha(a.qualification/'manifest.json') if a.qualification else None,results=[],status='created',global_policy_mutation=False);write(out/'manifest.json',manifest);print('OUT',out,flush=True)
 def inspect(name):
  s=collect_android_state(ex);v,w=evaluate_preconditions_full(s,policy);write(out/(name+'-environment.json'),dict(snapshot=s,violations=v,warnings=w))
  if v or w:raise RuntimeError('STOP environment '+name)
 try:
  inspect('initial');remote='/data/local/tmp/cpu-uarch/l1_tlb_reach';subprocess.run(['adb','push',str(a.binary),remote],check=True,capture_output=True);q=ex.execute(['chmod','755',remote])
  if q.returncode:raise RuntimeError('STOP chmod')
  q=ex.execute(['sha256sum',remote])
  if q.returncode or q.stdout.split()[0]!=manifest['binary_sha256']:raise RuntimeError('STOP deployed SHA')
  for epoch in range(3):
   time.sleep(15);name=f'e{epoch}';inspect(name+'-pre');args=['--run',a.mode,str(epoch),a.phase];q=ex.execute(['su','-c',shlex.join([remote,*args])]);stdout=out/(name+'.stdout.jsonl');stdout.write_text(q.stdout);(out/(name+'.stderr.log')).write_text(q.stderr);row=dict(name=name,epoch=epoch,args=args,exit_code=q.returncode,timed_out=q.timed_out,stdout_sha256=sha(stdout));manifest['results'].append(row);write(out/'manifest.json',manifest);inspect(name+'-post')
   if q.returncode or q.timed_out or q.stderr:raise RuntimeError('STOP producer exit '+name)
   v=model.audit_process([json.loads(l) for l in q.stdout.splitlines()],model.expected(a.mode,epoch,a.phase));row['classification']={k:v[k] for k in ('status','curves','physical_capacity_certified')};write(out/(name+'-analysis.json'),v);write(out/'manifest.json',manifest)
   if v['status']=='L1_NOT_QUALIFIED':manifest['status']='L1_NOT_QUALIFIED';return 0
   print('OK',name,len(v['rows']),'windows',v['status'],flush=True)
  manifest['status']='L1_QUALIFIED' if a.phase=='qualification' else 'L1_SCAN_COMPLETE'
 except BaseException as e:manifest['status']='stopped';manifest['error']=repr(e);raise
 finally:
  write(out/'manifest.json',manifest)
  inventory={p.name:sha(p) for p in out.iterdir() if p.is_file()};write(out/'raw-sha256.json',inventory)
 print(manifest['status'],'no physical capacity promotion',flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
