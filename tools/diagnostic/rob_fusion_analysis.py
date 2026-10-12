#!/usr/bin/env python3
"""Independent D0/D1 recurrence qualification and finite NOP gap response; no physical allocation inference.

Frozen purpose/gates (fresh v2 raw only, v1 immutable): docs/design/2026-10-12-rob-fusion-groups.md. Exact
producer words, schedule, raw inventory and provenance are audited before statistics.
"""
import argparse,hashlib,json,statistics as st,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='rob-fusion-groups'
PROTOCOL='docs/design/2026-10-12-rob-fusion-groups.md'
BUILD='docs/reviews/evidence/2026-10-12-rob-fusion-groups/build.json'
PLAN='docs/reviews/evidence/2026-10-12-rob-fusion-groups/plan.json'
DRIVER='tools/diagnostic/run_sm8650_rob_fusion.py'
CONSUMER='tools/diagnostic/rob_fusion_analysis.py'
GRID=(0,64,128,192,256,384);PATTERNS=('nop-pair','add','nop-add')
EVENTS=(17,8,58,33133,35,1);ITERATIONS=131072

def conditions(phase):
 _require(phase in ('qualification','scan'),'fusion phase')
 specs=[(a,'nop-pair',0) for a in ('none','serial','independent')]
 specs+= [('none',p,64) for p in PATTERNS] if phase=='qualification' else [(a,p,g) for g in GRID[1:] for p in PATTERNS for a in ('none','serial','independent')]
 return [dict(name=f'e{e}-{a}-{p}-g{g}',args=['--run','--anchor',a,'--pattern',p,'--g',str(g),*(['--reverse'] if e%2 else [])]) for e in range(3) for a,p,g in (specs if e%2==0 else list(reversed(specs)))]
def identity(c):
 args=c['args'];return args[2],args[4],int(args[6]),'--reverse' in args

def expected(a,p,g,rev):
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
  if a!='none':words.extend([0x1e61c021 if side and a=='independent' else 0x1e61c000]*16)
  for j in range(g):
   if p!='add':words.append(0xd503201f)
   words.append(0xd503201f if p=='nop-pair' else 0x8b000000|(17<<16)|(16<<5)|(4+j%8))
 words.append(0xf1000463);branch=len(words);words.extend([0x54000001|(((16-branch)&0x7ffff)<<5),0xaa0403e0 if p!='nop-pair' and g else 0xd2800000,0xd65f03c0]);loop=branch-16+1
 cfg=dict(type='config',version=1,probe=MODE,pattern=p,anchor=a,groups=g,instructions_per_group=1 if p=='add' else 2,chain=16,iterations=ITERATIONS,warmup_iterations=ITERATIONS,windows=8,reverse=rev,events=list(EVENTS),pmu_type=8,loop_mod64=0)
 program=dict(type='program',loop_offset=64,branch_offset=4*branch,loop_instructions=loop,prologue_instructions=16,code_bytes=4*len(words),words=words)
 return [cfg,program,*[dict(type='schedule',position=i,round=7-i if rev else i) for i in range(8)]]
def plans():return {f'{a}-{p}-{g}-{int(rev)}':expected(a,p,g,rev) for a in ('none','serial','independent') for p in PATTERNS for g in GRID for rev in (False,True)}
def validate_plan(p):_require(_same(p,plans()),'fusion actual registered plan mismatch')

def audit_process(rr,c,registered):
 """Exact executed program, fixed VA, checksum and all eight typed PMU windows."""
 validate_plan(registered);a,p,g,rev=identity(c);want=expected(a,p,g,rev)
 _require(type(rr) is list and len(rr)==11,'fusion raw window coverage');_require(_same(rr[:2],want[:2]),'fusion config/program mismatch')
 runtime=rr[2];_fields(runtime,dict(type='runtime',cpu=7,fpcr=0),'fusion CPU/FPCR')
 base=runtime.get('code_base');ids=runtime.get('event_ids');_require(type(base) is int and base>0 and base%4096==0,'fusion code base')
 _require(type(ids) is list and len(ids)==6 and all(type(x) is int and 0<x<2**64 for x in ids) and len(set(ids))==6,'fusion kernel IDs')
 ir=ITERATIONS*want[1]['loop_instructions']+want[1]['prologue_instructions']+2
 for r,s in zip(rr[3:],want[2:]):
  _fields(r,dict(s,type='round',code_base=base,code_matches_plan=True,result_bits=None if a=='none' else [0x3ff0000000000000]*2,gpr_result=0x3333 if p!='nop-pair' and g else 0),'fusion sample order/code/results')
  _require(all(type(r.get(k)) is int and 0<r[k]<2**64 for k in ('ns','enabled','running')) and r['enabled']==r['running'],'fusion time/mux')
  counts=r.get('counts');_require(type(counts) is list and len(counts)==6 and all(type(x) is int and 0<=x<2**64 for x in counts) and counts[0]>0,'fusion counts')
  _require(abs(counts[1]-ir)<=max(1000,.01*ir),'fusion retired instruction mismatch')
 return dict(condition=c['name'],args=c['args'],config=rr[0],program=rr[1],runtime=runtime,samples=rr[3:])

def analyze(run):
 """Finite matched work comparison; no discarded windows or physical unit inference."""
 _fields(run,dict(mode=MODE),'fusion matrix identity');phase=run.get('phase');cc=conditions(phase)
 _require(type(run.get('processes')) is int and run['processes']==len(cc),'fusion processes');rows=run.get('rows');_require(type(rows) is list and len(rows)==len(cc),'fusion matrix coverage')
 points=[];ratios=[];values={};stable={};background={};medians={}
 for r,c in zip(rows,cc):
  _fields(r,dict(condition=c['name'],args=c['args']),'fusion condition order');audit_process([r['config'],r['program'],r['runtime'],*r['samples']],c,plans());a,p,g,rev=identity(c);e=int(c['name'][1]);v=[s['counts'][0]/ITERATIONS for s in r['samples']];spread=(max(v)-min(v))/st.median(v);ic=[s['counts'][5]/ITERATIONS for s in r['samples']]
  points.append(dict(epoch=e,anchor=a,pattern=p,groups=g,cycles=v,median=st.median(v),range_fraction=spread,stable=spread<=.10,icache_per_iter=ic,background_passed=max(ic)<=.001));values.setdefault((a,p,g),[]).extend(v);stable.setdefault((a,p,g),[]).append(spread<=.10);background.setdefault((a,p,g),[]).append(max(ic)<=.001);medians[a,p,g,e]=st.median(v)
  for z in r['samples']:
   counts=z['counts'];ratios.append(dict(condition=c['name'],position=z['position'],round=z['round'],counts=counts,cycles_per_iter=counts[0]/ITERATIONS,ns=z['ns'],cycles_per_ns=counts[0]/z['ns'],**{hex(event):counts[j]/counts[0] for j,event in enumerate(EVENTS) if j>=2}))
 i0=values['independent','nop-pair',0];s0=values['serial','nop-pair',0];zero=values['none','nop-pair',0];low=[('none',p,64) for p in PATTERNS];refs=[(a,'nop-pair',0) for a in ('none','serial','independent')]+low
 gates=dict(anchors_stable=all(stable['independent','nop-pair',0]+stable['serial','nop-pair',0]),overlap_ratio=max(i0)/min(s0),none_stable=all(b for key in low for b in stable[key]),none_zero_noise_ratio=(max(zero)-min(zero))/min(i0),none_max_ratio=max([*zero,*[x for key in low for x in values[key]]])/min(i0),icache_background=all(b for key in refs for b in background[key]))
 qualified=gates['anchors_stable'] and gates['overlap_ratio']<=.70 and gates['none_stable'] and gates['none_zero_noise_ratio']<=.01 and gates['none_max_ratio']<=.80 and gates['icache_background']
 result=dict(mode=MODE,phase=phase,windows=len(rows)*8,qualification=gates,qualified=qualified,status='group-controls-qualified' if qualified else 'not-qualified',points=points,window_ratios=ratios,physical_entries_certified=False,naming_limit='syntactic matched-work response compatible with fusion eligibility; actual MOP and ROB allocation uncalibrated')
 if phase=='qualification' or not qualified:return result
 curve=[];usable={};response={}
 for g in GRID[1:]:
  for p in PATTERNS:
   ok=all(b for a in ('none','serial','independent') for b in stable[a,p,g]+background[a,p,g]) and max(values['none',p,g])<=.90*min(i0);usable[p,g]=ok;v=values['independent',p,g];response[p,g]=ok and min(v)>=1.25*max(i0)
   curve.append(dict(pattern=p,groups=g,usable=ok,state='supply-or-control-unqualified' if not ok else 'response' if response[p,g] else 'below-response-band' if max(v)<=1.10*min(i0) else 'ambiguous',none_max_ratio=max(values['none',p,g])/min(i0),serial_resource_response=max(values['serial',p,g])>1.10*min(s0),independent_range=[min(v),max(v)]))
 comparisons=[];match=[];positive=[];negative=[]
 for g in GRID[1:]:
  di=[medians['independent','nop-add',g,e]-medians['independent','add',g,e] for e in range(3)];ds=[medians['serial','nop-add',g,e]-medians['serial','add',g,e] for e in range(3)];ok=usable['add',g] and usable['nop-add',g];matched=ok and response['add',g] and response['nop-add',g] and all(abs(x)<=.03*min(i0) for x in di) and all(abs(x)<=.03*min(s0) for x in ds)
  gp=[medians['independent',p,g,e]-medians['independent','nop-pair',g,e] for p in ('add','nop-add') for e in range(3)];all_usable=all(usable[p,g] for p in PATTERNS);pos=all_usable and all(x>=.05*min(i0) for x in gp);neg=all_usable and all(x<=-.05*min(i0) for x in gp);match.append(matched);positive.append(pos);negative.append(neg)
  comparisons.append(dict(groups=g,usable=ok,independent_signed_difference=di,serial_signed_difference=ds,matching_response=matched,gpr_signed_difference=gp,all_modes_usable=all_usable))
 adjacent=lambda flags:any(x and y for x,y in zip(flags,flags[1:]));status='fusion-compatible-work-response' if adjacent(match) else 'inconclusive' if any(not c['usable'] for c in comparisons) else 'matching-response-not-replicated';flow='replicated-GPR-flow-associated-response' if adjacent(positive) else 'replicated-opposite-flow-response' if adjacent(negative) else 'not-replicated'
 result.update(status=status,gpr_flow=flow,curve=curve,comparisons=comparisons);return result

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
 _require(build['binaries']['rob_fusion_groups']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'dual binary/source/plan binding')
 for file,digest in build['source_sha256'].items():_require(sha(blob(head,file))==digest and sha(blob(m['binary_source_head'],file))==digest,'dual source dependency '+file)
 qi=m.get('qualification_input')
 if phase=='qualification':_require(qi is None,'dual qualification input must be absent')
 else:
  _require(type(qi) is dict and type(qi.get('raw_directory')) is str and Path(qi['raw_directory']).name==qi['raw_directory'] and qi['raw_directory']!=path.name,'dual qualification path')
  qp=path.parent/qi['raw_directory'];_fields(json.loads((qp/'manifest.json').read_text()),dict(mode=MODE,phase='qualification'),'dual linked phase')
  qr,_=audit_raw(qp);qa=analyze(qr)
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
 run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],status=result['status'],qualification=result['qualification'],gpr_flow=result.get('gpr_flow'))))
if __name__=='__main__':main()
