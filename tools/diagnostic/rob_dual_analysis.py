#!/usr/bin/env python3
"""Independent D0/D1 recurrence qualification and finite NOP gap response; no physical allocation inference.

Frozen purpose/gates: docs/design/2026-10-11-rob-dual-anchor.md. Exact
producer words, schedule, raw inventory and provenance are audited before statistics.
"""
import argparse,hashlib,json,statistics as st,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='rob-dual-anchor'
PROTOCOL='docs/design/2026-10-11-rob-dual-anchor.md'
BUILD='docs/reviews/evidence/2026-10-11-rob-dual-anchor/build.json'
PLAN='docs/reviews/evidence/2026-10-11-rob-dual-anchor/plan.json'
DRIVER='tools/diagnostic/run_sm8650_rob_dual.py'
CONSUMER='tools/diagnostic/rob_dual_analysis.py'
GRID=(0,128,256,384,512,640,672,704,768,896)
EVENTS=(17,8,58,59,33133,35);ITERATIONS=131072

def conditions(phase):
 _require(phase in ('qualification','scan'),'dual phase')
 specs=[(a,n) for n in ((0,128) if phase=='qualification' else GRID) for a in ('none','serial','independent')]
 return [dict(name=f'e{e}-{a}-n{n}',args=['--run','--anchor',a,'--n',str(n),*(['--reverse'] if e%2 else [])]) for e in range(3) for a,n in (specs if e%2==0 else list(reversed(specs)))]
def identity(c):
 args=c['args'];return args[2],int(args[4]),'--reverse' in args

def expected(a,n,rev):
 """Independent A64 instruction oracle; no imported shared-C generator output."""
 words=[0xaa0203ee]
 def imm(r,v):
  words.append(0xd2800000|((v&65535)<<5)|r)
  for sh in (16,32,48):words.append(0xf2800000|(((v>>sh)&65535)<<5)|((sh//16)<<21)|r)
 imm(16,0x1111);imm(17,0x2222)
 if a!='none':
  imm(15,0x3ff0000000000000);words.extend([0x9e6701e0,0x9e6701e1,0x9e6701f1])
 while len(words)%16:words.append(0xd503201f)
 for side in (0,1):
  if a!='none':words.extend([0x1e61c021 if side and a=='independent' else 0x1e61c000]*16)
  words.extend([0xd503201f]*n)
 words.append(0xf1000463);branch=len(words);words.extend([0x54000001|(((16-branch)&0x7ffff)<<5),0xd65f03c0]);loop=branch-16+1
 cfg=dict(type='config',version=1,probe=MODE,**{'class':'nop'},anchor=a,n=n,chain=16,iterations=ITERATIONS,warmup_iterations=ITERATIONS,windows=8,reverse=rev,events=list(EVENTS),pmu_type=8,loop_mod64=0)
 program=dict(type='program',loop_offset=64,branch_offset=4*branch,loop_instructions=loop,prologue_instructions=16,code_bytes=4*len(words),words=words)
 return [cfg,program,*[dict(type='schedule',position=p,round=7-p if rev else p) for p in range(8)]]
def plans():return {f'{a}-{n}-{int(rev)}':expected(a,n,rev) for a in ('none','serial','independent') for n in GRID for rev in (False,True)}
def validate_plan(p):_require(_same(p,plans()),'dual actual registered plan mismatch')

def audit_process(rr,c,registered):
 """One fixed real program/VA, exact eight windows including executed result bits."""
 validate_plan(registered);a,n,rev=identity(c);want=expected(a,n,rev)
 _require(type(rr) is list and len(rr)==11,'dual raw window coverage');_require(_same(rr[:2],want[:2]),'dual config/program mismatch')
 runtime=rr[2];_fields(runtime,dict(type='runtime',cpu=7,fpcr=0),'dual CPU/FPCR')
 base=runtime.get('code_base');ids=runtime.get('event_ids');_require(type(base) is int and base>0 and base%4096==0,'dual code base')
 _require(type(ids) is list and len(ids)==6 and all(type(x) is int and 0<x<2**64 for x in ids) and len(set(ids))==6,'dual kernel IDs')
 ir=ITERATIONS*want[1]['loop_instructions']+want[1]['prologue_instructions']+1
 for r,s in zip(rr[3:],want[2:]):
  _fields(r,dict(s,type='round',code_base=base,code_matches_plan=True,result_bits=None if a=='none' else [0x3ff0000000000000]*2),'dual sample order/code/result')
  _require(all(type(r.get(k)) is int and 0<r[k]<2**64 for k in ('ns','enabled','running')) and r['enabled']==r['running'],'dual time/mux')
  counts=r.get('counts');_require(type(counts) is list and len(counts)==6 and all(type(x) is int and 0<=x<2**64 for x in counts) and counts[0]>0,'dual counts')
  _require(abs(counts[1]-ir)<=max(1000,.01*ir),'dual retired instruction mismatch')
 return dict(condition=c['name'],args=c['args'],config=rr[0],program=rr[1],runtime=runtime,samples=rr[3:])

def analyze(run):
 """Overlap qualification precedes finite response; every raw window contributes."""
 _fields(run,dict(mode=MODE),'dual matrix identity');phase=run.get('phase');cc=conditions(phase)
 _require(type(run.get('processes')) is int and run['processes']==len(cc),'dual processes');rows=run.get('rows');_require(type(rows) is list and len(rows)==len(cc),'dual matrix coverage')
 points=[];ratios=[];values={};stable={}
 for r,c in zip(rows,cc):
  _fields(r,dict(condition=c['name'],args=c['args']),'dual condition order')
  audit_process([r['config'],r['program'],r['runtime'],*r['samples']],c,plans());a,n,rev=identity(c);e=int(c['name'][1]);v=[s['counts'][0]/ITERATIONS for s in r['samples']];spread=(max(v)-min(v))/st.median(v)
  points.append(dict(epoch=e,anchor=a,n=n,cycles=v,median=st.median(v),range_fraction=spread,stable=spread<=.10));values.setdefault((a,n),[]).extend(v);stable.setdefault((a,n),[]).append(spread<=.10)
  for s in r['samples']:
   counts=s['counts'];ratios.append(dict(condition=c['name'],position=s['position'],round=s['round'],counts=counts,cycles_per_iter=counts[0]/ITERATIONS,ns=s['ns'],cycles_per_ns=counts[0]/s['ns'],**{hex(event):counts[j]/counts[0] for j,event in enumerate(EVENTS) if j>=2}))
 i0=values['independent',0];s0=values['serial',0]
 gates=dict(anchors_stable=all(stable['independent',0]+stable['serial',0]),overlap_ratio=max(i0)/min(s0),none_stable=all(stable['none',0]+stable['none',128]),none_max_ratio=max(values['none',0]+values['none',128])/min(i0))
 qualified=gates['anchors_stable'] and gates['overlap_ratio']<=.70 and gates['none_stable'] and gates['none_max_ratio']<=.80
 result=dict(mode=MODE,phase=phase,windows=len(rows)*8,qualification=gates,qualified=qualified,status='dual-anchor-overlap-qualified' if qualified else 'not-qualified',points=points,window_ratios=ratios,physical_entries_certified=False,naming_limit='independent stable-valued FP recurrence overlap and effective NOP separation response; allocation units and bottleneck uncalibrated')
 if phase=='qualification' or not qualified:return result
 curve=[]
 for n in GRID:
  control=all(stable[a,n][e] for a in ('none','serial','independent') for e in range(3)) and max(values['none',n])<=.90*min(i0) and max(values['serial',n])<=1.10*min(s0)
  state='supply-or-control-unqualified' if not control else 'overlap-loss-response' if min(values['independent',n])>=1.25*max(i0) else 'no-overlap-loss' if max(values['independent',n])<=1.10*min(i0) else 'ambiguous'
  curve.append(dict(n=n,state=state,none_max_ratio=max(values['none',n])/min(i0),serial_max_ratio=max(values['serial',n])/min(s0),independent_range=[min(values['independent',n]),max(values['independent',n])]))
 states=[p['state'] for p in curve];high=[j for j,s in enumerate(states) if s=='overlap-loss-response'];status='inconclusive';interval=None
 if high:
  h=high[0];low=[j for j in range(h) if states[j]=='no-overlap-loss'];reverse=any(s=='no-overlap-loss' for s in states[h+1:])
  if reverse:status='nonmonotonic'
  elif not low:status='left-censored'
  elif h==len(curve)-1 or states[h+1]!='overlap-loss-response':status='right-censored' if h==len(curve)-1 else 'inconclusive'
  elif all(states[j]=='no-overlap-loss' for j in range(max(low)+1,h)):
   status='effective-overlap-loss-interval';interval=[curve[max(low)]['n'],curve[h]['n']]
 result.update(status=status,interval=interval,curve=curve);return result

def audit_raw(path):
 """Launch/source/build/environment and complete raw inventory, never patched input."""
 phase=json.loads((path/'manifest.json').read_text()).get('phase');cc=conditions(phase)
 inventory={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+suffix for c in conditions(phase) for suffix in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')}
 _require({p.name for p in path.iterdir()}==inventory and all(p.is_file() for p in path.iterdir()),'dual raw inventory')
 m=json.loads((path/'manifest.json').read_text());phase=m.get('phase');cc=conditions(phase);_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'dual manifest identity')
 _require(_same(m.get('conditions'),cc) and type(m.get('results')) is list and len(m['results'])==len(cc),'dual requested/result coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'dual launch SHA '+file)
 for saved,key in (('driver.py','driver_sha256'),('consumer.py','consumer_sha256')):_require(sha((path/saved).read_bytes())==m[key],'dual saved '+saved)
 build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['rob_dual_anchor']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'dual binary/source/plan binding')
 for file,digest in build['source_sha256'].items():_require(sha(blob(head,file))==digest and sha(blob(m['binary_source_head'],file))==digest,'dual source dependency '+file)
 qi=m.get('qualification_input')
 if phase=='qualification':_require(qi is None,'dual qualification input must be absent')
 else:
  _require(type(qi) is dict and type(qi.get('raw_directory')) is str and Path(qi['raw_directory']).name==qi['raw_directory'] and qi['raw_directory']!=path.name,'dual qualification path')
  qr,_=audit_raw(path.parent/qi['raw_directory']);qa=analyze(qr)
  _require(qr['phase']=='qualification' and qa['qualified'] and _same(qi,dict(raw_directory=qr['raw_directory'],manifest_sha256=qr['manifest_sha256'],binary_sha256=qr['binary_sha256'],qualified=True)) and qr['binary_sha256']==m['binary_sha256'],'dual qualification provenance/gate')
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt'
 env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[]
 for r,c in zip(m['results'],conditions(phase)):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'dual result identity/status');f=path/(c['name']+'.stdout.jsonl')
  _require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','dual stdout/stderr')
  rows.append(audit_process([json.loads(l) for l in f.read_text().splitlines()],c,registered))
 return dict(mode=MODE,phase=phase,processes=len(cc),source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],rows=rows),{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv)
 run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],status=result['status'],qualification=result['qualification'],interval=result.get('interval'))))
if __name__=='__main__':main()
