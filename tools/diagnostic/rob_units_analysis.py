#!/usr/bin/env python3
"""Relative syntactic units and D0/D1 chain-length controls; no physical allocation inference.

Frozen purpose/gates: docs/design/2026-10-12-rob-retirement-units.md. Exact
producer words, schedule, raw inventory and provenance are audited before statistics.
"""
import argparse,hashlib,json,statistics as st,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='rob-retirement-units'
PROTOCOL='docs/design/2026-10-12-rob-retirement-units.md'
BUILD='docs/reviews/evidence/2026-10-12-rob-retirement-units/build.json'
PLAN='docs/reviews/evidence/2026-10-12-rob-retirement-units/plan.json'
DRIVER='tools/diagnostic/run_sm8650_rob_units.py'
CONSUMER='tools/diagnostic/rob_units_analysis.py'
PATTERNS=('nop-pair','nop-add-discard','add-sub-discard');CHAINS=(16,32);GRIDS={p:((0,64,128,144,160,168,176,192) if p=='add-sub-discard' else (0,64,256,288,320,336,352,384)) for p in PATTERNS}
EVENTS=(17,8,58,33133,35,1);ITERATIONS=131072

def conditions(phase):
 _require(phase in ('qualification','scan'),'units phase')
 specs=[('none','nop-pair',0,16)]+[(a,'nop-pair',0,k) for k in CHAINS for a in ('serial','independent')]+[('none',p,64,16) for p in PATTERNS]
 if phase=='scan':
  for p in PATTERNS:
   for g in GRIDS[p][2:]:specs += [('none',p,g,16)]+[(a,p,g,k) for k in CHAINS for a in ('serial','independent')]
 return [dict(name=f'e{e}-{a}-{p}-g{g}-k{k}',args=['--run','--anchor',a,'--pattern',p,'--g',str(g),'--chain',str(k),*(['--reverse'] if e%2 else [])]) for e in range(3) for a,p,g,k in (specs if e%2==0 else list(reversed(specs)))]
def identity(c):
 a=c['args'];return a[2],a[4],int(a[6]),int(a[8]),'--reverse' in a
def expected(a,p,g,k,rev):
 """Independent A64 oracle; syntactic grouping is not a hardware MOP assertion."""
 words=[0xaa0203ee]
 def imm(r,v):
  words.append(0xd2800000|((v&65535)<<5)|r)
  for sh in (16,32,48):words.append(0xf2800000|(((v>>sh)&65535)<<5)|((sh//16)<<21)|r)
 imm(16,0x1111);imm(17,0x2222)
 if a!='none':
  imm(15,0x3ff0000000000000);words.extend([0x9e6701e0,0x9e6701e1,0x9e6701f1])
 while len(words)%16:words.append(0xd503201f)
 for side in (0,1):
  if a!='none':words.extend([0x1e61c021 if side and a=='independent' else 0x1e61c000]*k)
  for j in range(g):words.extend([0x8b11021f if p=='add-sub-discard' else 0xd503201f,0xd503201f if p=='nop-pair' else 0x8b11021f if p=='nop-add-discard' else 0xcb11021f])
 words.append(0xf1000463);branch=len(words);words.extend([0x54000001|(((16-branch)&0x7ffff)<<5),0xd2800000,0xd65f03c0]);loop=branch-16+1
 cfg=dict(type='config',version=1,probe=MODE,pattern=p,anchor=a,groups=g,instructions_per_group=2,chain=k,iterations=ITERATIONS,warmup_iterations=ITERATIONS,windows=8,reverse=rev,events=list(EVENTS),pmu_type=8,loop_mod64=0)
 program=dict(type='program',loop_offset=64,branch_offset=4*branch,loop_instructions=loop,prologue_instructions=16,code_bytes=4*len(words),words=words)
 return [cfg,program,*[dict(type='schedule',position=i,round=7-i if rev else i) for i in range(8)]]
def plans():return {f'{a}-{p}-g{g}-k{k}-r{int(rev)}':expected(a,p,g,k,rev) for a in ('none','serial','independent') for p in PATTERNS for g in GRIDS[p] for k in CHAINS for rev in (False,True)}
def validate_plan(p):_require(_same(p,plans()),'units actual registered plan mismatch')

def audit_process(rr,c,registered):
 """Exact executed program, fixed VA, checksum and all eight typed PMU windows."""
 validate_plan(registered)
 return _audit_records(rr,c)

def _audit_records(rr,c):
 """Validate a single executed program; callers validate the registered plan once."""
 a,p,g,k,rev=identity(c);want=expected(a,p,g,k,rev)
 _require(type(rr) is list and len(rr)==11,'units raw window coverage');_require(_same(rr[:2],want[:2]),'units config/program mismatch')
 runtime=rr[2];_fields(runtime,dict(type='runtime',cpu=7,fpcr=0),'units CPU/FPCR')
 base=runtime.get('code_base');ids=runtime.get('event_ids');_require(type(base) is int and base>0 and base%4096==0,'units code base')
 _require(type(ids) is list and len(ids)==6 and all(type(x) is int and 0<x<2**64 for x in ids) and len(set(ids))==6,'units kernel IDs')
 ir=ITERATIONS*want[1]['loop_instructions']+want[1]['prologue_instructions']+2
 for r,s in zip(rr[3:],want[2:]):
  _fields(r,dict(s,type='round',code_base=base,code_matches_plan=True,result_bits=None if a=='none' else [0x3ff0000000000000]*2,gpr_result=0),'units sample order/code/results')
  _require(all(type(r.get(k)) is int and 0<r[k]<2**64 for k in ('ns','enabled','running')) and r['enabled']==r['running'],'units time/mux')
  counts=r.get('counts');_require(type(counts) is list and len(counts)==6 and all(type(x) is int and 0<=x<2**64 for x in counts) and counts[0]>0,'units counts')
  _require(abs(counts[1]-ir)<=max(1000,.01*ir),'units retired instruction mismatch')
 return dict(condition=c['name'],args=c['args'],config=rr[0],program=rr[1],runtime=runtime,samples=rr[3:])

def analyze(run):
 """Fused-eligible relative weights are a tested model, never an entry certificate."""
 _fields(run,dict(mode=MODE),'units matrix');phase=run.get('phase');cc=conditions(phase);_require(type(run.get('processes')) is int and run['processes']==len(cc),'units processes');rows=run.get('rows');_require(type(rows) is list and len(rows)==len(cc),'units coverage');points=[];ratios=[];values={};stable={};background={}
 for r,c in zip(rows,cc):
  _fields(r,dict(condition=c['name'],args=c['args']),'units order');_audit_records([r['config'],r['program'],r['runtime'],*r['samples']],c);a,p,g,k,rev=identity(c);e=int(c['name'][1]);vv=[s['counts'][0]/ITERATIONS for s in r['samples']];spread=(max(vv)-min(vv))/st.median(vv);ic=[s['counts'][5]/ITERATIONS for s in r['samples']];point=dict(epoch=e,anchor=a,pattern=p,groups=g,chain=k,cycles=vv,median=st.median(vv),range_fraction=spread,stable=spread<=.10,icache_per_iter=ic,background_passed=max(ic)<=.001);points.append(point);values[a,p,g,k,e]=vv;stable[a,p,g,k,e]=spread<=.10;background[a,p,g,k,e]=max(ic)<=.001
  for z in r['samples']:
   counts=z['counts'];ratios.append(dict(condition=c['name'],position=z['position'],round=z['round'],counts=counts,cycles_per_iter=counts[0]/ITERATIONS,ns=z['ns'],cycles_per_ns=counts[0]/z['ns'],**{hex(event):counts[j]/counts[0] for j,event in enumerate(EVENTS) if j>=2}))
 i0={k:[v for e in range(3) for v in values['independent','nop-pair',0,k,e]] for k in CHAINS};s0={k:[v for e in range(3) for v in values['serial','nop-pair',0,k,e]] for k in CHAINS};zero=[v for e in range(3) for v in values['none','nop-pair',0,16,e]];ref=[p for p in points if p['groups']==0 or p['groups']==64];gates=dict(anchors_stable=all(p['stable'] for p in ref if p['anchor']!='none'),overlap_ratios={str(k):max(i0[k])/min(s0[k]) for k in CHAINS},none_zero_noise_ratio=(max(zero)-min(zero))/min(i0[16]),none_stable=all(p['stable'] for p in ref if p['groups']==64),none_max_ratio=max(v for p in ref if p['anchor']=='none' and p['groups']==64 for v in p['cycles'])/min(i0[16]),icache_background=all(p['background_passed'] for p in ref));qualified=gates['anchors_stable'] and all(v<=.70 for v in gates['overlap_ratios'].values()) and gates['none_zero_noise_ratio']<=.01 and gates['none_stable'] and gates['none_max_ratio']<=.80 and gates['icache_background'];result=dict(mode=MODE,phase=phase,windows=len(rows)*8,qualification=gates,qualified=qualified,status='unit-controls-qualified' if qualified else 'not-qualified',points=points,window_ratios=ratios,physical_entries_certified=False,allocation_units_certified=False,common_proxy_interval=None,naming_limit='relative eligible-group / anchor-length proxy under explicit alpha and lifecycle assumptions; not physical ROB entries')
 if phase=='qualification' or not qualified:return result
 curves=[]
 for p in PATTERNS:
  for k in CHAINS:
   for e in range(3):
    states=[];comparisons=[];grid=GRIDS[p][2:];interval=None
    for g in grid:
     keys=[('none',p,g,16,e),('serial',p,g,k,e),('independent',p,g,k,e)];nv,sv,iv=[values[key] for key in keys];ok=all(stable[key] and background[key] for key in keys) and max(nv)<=.90*min(i0[16]);state='INCOMPUTABLE' if not ok else 'near-serial' if min(iv)>=.95*max(sv) and max(iv)<=1.05*min(sv) else 'overlap-retained' if max(iv)<.90*min(sv) else 'ambiguous';states.append(state);comparisons.append(dict(groups=g,state=state,none_cycles=nv,serial_cycles=sv,independent_cycles=iv))
    status='ambiguous'
    if 'INCOMPUTABLE' in states:status='INCOMPUTABLE'
    elif 'ambiguous' in states:status='ambiguous'
    elif any(states[i]=='near-serial' and 'overlap-retained' in states[i+1:] for i in range(len(states))):status='ambiguous'
    elif 'near-serial' not in states:status='no-saturation-through-grid'
    elif states[0]=='near-serial':status='left-censored'
    else:
     index=states.index('near-serial')
     if index==len(states)-1:status='right-censored'
     else:status='interval';interval=[grid[index-1],grid[index]]
    alpha=2 if p=='add-sub-discard' else 1;curves.append(dict(epoch=e,pattern=p,chain=k,status=status,interval=interval,model_alpha=alpha,proxy_interval=[alpha*v+2*k for v in interval] if interval else None,points=comparisons))
 summaries=[]
 for p in PATTERNS:
  for k in CHAINS:
   vv=[c for c in curves if c['pattern']==p and c['chain']==k];rep=all(c['status']=='interval' and c['interval']==vv[0]['interval'] for c in vv);summaries.append(dict(pattern=p,chain=k,replicated=rep,interval=vv[0]['interval'] if rep else None,proxy_interval=vv[0]['proxy_interval'] if rep else None))
 common=None
 if all(s['replicated'] for s in summaries):
  lo=max(s['proxy_interval'][0] for s in summaries);hi=min(s['proxy_interval'][1] for s in summaries)
  if lo<hi:common=[lo,hi]
 result.update(status='COMMON_RETIREMENT_PROXY_COMPATIBLE' if common else 'INCONCLUSIVE',curves=curves,proxy_summaries=summaries,common_proxy_interval=common);return result

def audit_raw(path):
 """Launch/source/build/environment and complete raw inventory, never patched input."""
 phase=json.loads((path/'manifest.json').read_text()).get('phase');cc=conditions(phase)
 inventory={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+suffix for c in conditions(phase) for suffix in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')}
 _require({p.name for p in path.iterdir()}==inventory and all(p.is_file() for p in path.iterdir()),'units raw inventory')
 m=json.loads((path/'manifest.json').read_text());phase=m.get('phase');cc=conditions(phase);_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'units manifest identity')
 _require(_same(m.get('conditions'),cc) and type(m.get('results')) is list and len(m['results'])==len(cc),'units requested/result coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'units launch SHA '+file)
 for saved,key in (('driver.py','driver_sha256'),('consumer.py','consumer_sha256')):_require(sha((path/saved).read_bytes())==m[key],'units saved '+saved)
 build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['rob_retirement_units']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'units binary/source/plan binding')
 for file,digest in build['source_sha256'].items():_require(sha(blob(head,file))==digest and sha(blob(m['binary_source_head'],file))==digest,'units source dependency '+file)
 qi=m.get('qualification_input')
 if phase=='qualification':_require(qi is None,'units qualification input must be absent')
 else:
  _require(type(qi) is dict and type(qi.get('raw_directory')) is str and Path(qi['raw_directory']).name==qi['raw_directory'] and qi['raw_directory']!=path.name,'units qualification path')
  qp=path.parent/qi['raw_directory'];_fields(json.loads((qp/'manifest.json').read_text()),dict(mode=MODE,phase='qualification'),'units linked phase')
  qr,_=audit_raw(qp);qa=analyze(qr)
  _require(qr['phase']=='qualification' and qa['qualified'] and _same(qi,dict(raw_directory=qr['raw_directory'],manifest_sha256=qr['manifest_sha256'],binary_sha256=qr['binary_sha256'],qualified=True)) and qr['binary_sha256']==m['binary_sha256'],'units qualification provenance/gate')
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt'
 env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[]
 for r,c in zip(m['results'],conditions(phase)):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'units result identity/status');f=path/(c['name']+'.stdout.jsonl')
  _require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','units stdout/stderr')
  rows.append(_audit_records([json.loads(l) for l in f.read_text().splitlines()],c))
 return dict(mode=MODE,phase=phase,processes=len(cc),source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],rows=rows),{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv)
 run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],status=result['status'],qualification=result['qualification'],gpr_flow=result.get('gpr_flow'))))
if __name__=='__main__':main()
