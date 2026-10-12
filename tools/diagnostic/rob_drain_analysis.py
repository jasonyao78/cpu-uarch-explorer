#!/usr/bin/env python3
"""FPSR/FPCR retirement boundary and next-input reset qualification; no physical allocation inference.

Frozen purpose/gates: docs/design/2026-10-12-rob-retirement-drain-next.md. Exact
producer words, schedule, raw inventory and provenance are audited before statistics.
"""
import argparse,hashlib,json,statistics as st,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='rob-retirement-drain'
PROTOCOL='docs/design/2026-10-12-rob-retirement-drain-next.md'
BUILD='docs/reviews/evidence/2026-10-12-rob-retirement-drain/build.json'
PLAN='docs/reviews/evidence/2026-10-12-rob-retirement-drain/plan.json'
DRIVER='tools/diagnostic/run_sm8650_rob_drain.py'
CONSUMER='tools/diagnostic/rob_drain_analysis.py'
PATTERNS=('fpcr','fpsr');CHAINS=(16,32)
EVENTS=(17,8,58,33133,35,1);ITERATIONS=1048576

def conditions(phase):
 _require(phase=='qualification','drain only frozen qualification; scan forbidden')
 specs=[(a,p,g,k) for p in PATTERNS for k in CHAINS for a,g in [('none',0),('serial',0),('independent',0),('none',64)]]
 return [dict(name=f'e{e}-{a}-{p}-g{g}-k{k}',args=['--run','--anchor',a,'--drain',p,'--g',str(g),'--chain',str(k),*(['--reverse'] if e%2 else [])]) for e in range(3) for a,p,g,k in (specs if e%2==0 else list(reversed(specs)))]
def identity(c):
 a=c['args'];return a[2],a[4],int(a[6]),int(a[8]),'--reverse' in a
def expected(a,p,g,k,rev):
 """Independent A64 oracle; syntactic grouping is not a hardware MOP assertion."""
 words=[0xaa0203ee]
 def imm(r,v):
  words.append(0xd2800000|((v&65535)<<5)|r)
  for sh in (16,32,48):words.append(0xf2800000|(((v>>sh)&65535)<<5)|((sh//16)<<21)|r)
 imm(16,0x1111);imm(17,0x2222)
 if True:
  imm(15,0x3ff0000000000000);words.extend([0x9e6701e0,0x9e6701e1,0x9e6701f1])
 while len(words)%16:words.append(0xd503201f)
 for side in (0,1):
  if a!='none':words.extend([0x1e61c021 if side and a=='independent' else 0x1e61c000]*k)
  for j in range(g):words.extend([0xd503201f,0xd503201f])
 words.extend([0x9e66000d,0x9e66002e,0xd53b442c if p=='fpsr' else 0xd53b440c,0xaa0c03f0,0xca0f018c,0x9e670180,0x9e670181,0xf1000463]);branch=len(words)
 words.extend([0x54000001|(((16-branch)&0x7ffff)<<5),0xf900004d,0xf900044e,0xf9000850,0xd2800000,0xd65f03c0]);loop=branch-16+1
 cfg=dict(type='config',version=1,probe=MODE,drain=p,anchor=a,groups=g,instructions_per_group=2,chain=k,iterations=ITERATIONS,warmup_iterations=ITERATIONS,windows=8,reverse=rev,events=list(EVENTS),pmu_type=8,loop_mod64=0)
 program=dict(type='program',loop_offset=64,branch_offset=4*branch,loop_instructions=loop,prologue_instructions=16,code_bytes=4*len(words),words=words)
 return [cfg,program,*[dict(type='schedule',position=i,round=7-i if rev else i) for i in range(8)]]
def plan_key(a,p,g,k,rev):return f'{a}-{p}-g{g}-k{k}-r{int(rev)}'
def plans():return {plan_key(a,p,g,k,rev):expected(a,p,g,k,rev) for p in PATTERNS for k in CHAINS for a,g in [('none',0),('serial',0),('independent',0),('none',64)] for rev in (False,True)}
def validate_plan(p):_require(_same(p,plans()),'drain actual registered plan mismatch')

def audit_process(rr,c,registered):
 """Exact executed program, fixed VA, checksum and all eight typed PMU windows."""
 validate_plan(registered)
 return _audit_records(rr,c)

def _audit_records(rr,c):
 """Validate a single executed program; callers validate the registered plan once."""
 a,p,g,k,rev=identity(c);want=expected(a,p,g,k,rev)
 _require(type(rr) is list and len(rr)==11,'drain raw window coverage');_require(_same(rr[:2],want[:2]),'drain config/program mismatch')
 runtime=rr[2];_fields(runtime,dict(type='runtime',cpu=7,fpcr=0),'drain CPU/FPCR')
 base=runtime.get('code_base');ids=runtime.get('event_ids');_require(type(base) is int and base>0 and base%4096==0,'drain code base')
 _require(type(ids) is list and len(ids)==6 and all(type(x) is int and 0<x<2**64 for x in ids) and len(set(ids))==6,'drain kernel IDs')
 ir=ITERATIONS*want[1]['loop_instructions']+want[1]['prologue_instructions']+5
 for r,s in zip(rr[3:],want[2:]):
  _fields(r,dict(s,type='round',code_base=base,code_matches_plan=True,result_bits=[0x3ff0000000000000]*2,status_raw=0,gpr_result=0),'drain sample order/code/results')
  _require(all(type(r.get(k)) is int and 0<r[k]<2**64 for k in ('ns','enabled','running')) and r['enabled']==r['running'],'drain time/mux')
  counts=r.get('counts');_require(type(counts) is list and len(counts)==6 and all(type(x) is int and 0<=x<2**64 for x in counts) and counts[0]>0,'drain counts')
  _require(abs(counts[1]-ir)<=max(1000,.01*ir),'drain retired instruction mismatch')
 return dict(condition=c['name'],args=c['args'],config=rr[0],program=rr[1],runtime=runtime,samples=rr[3:])

def analyze(run):
 """Separate FPSR candidate qualification from FPCR control; no entry estimate."""
 _fields(run,dict(mode=MODE,phase='qualification'),'drain matrix');cc=conditions(run.get('phase'));rows=run.get('rows')
 _require(type(run.get('processes'))is int and run['processes']==len(cc) and type(rows)is list and len(rows)==len(cc),'drain coverage')
 points=[];ratios=[];values={}
 for r,c in zip(rows,cc):
  _fields(r,dict(condition=c['name'],args=c['args']),'drain order');_audit_records([r['config'],r['program'],r['runtime'],*r['samples']],c);a,p,g,k,rev=identity(c);e=int(c['name'][1]);vv=[z['counts'][0]/ITERATIONS for z in r['samples']];spread=(max(vv)-min(vv))/st.median(vv);ic=[z['counts'][5]/ITERATIONS for z in r['samples']]
  points.append(dict(epoch=e,anchor=a,drain=p,groups=g,chain=k,cycles=vv,median=st.median(vv),range_fraction=spread,stable=spread<=.05,icache_per_iter=ic,background_passed=max(ic)<=.001));values[a,p,g,k,e]=vv
  for z in r['samples']:
   counts=z['counts'];ratios.append(dict(condition=c['name'],position=z['position'],round=z['round'],counts=counts,cycles_per_iter=counts[0]/ITERATIONS,ns=z['ns'],cycles_per_ns=counts[0]/z['ns'],**{hex(event):counts[j]/counts[0] for j,event in enumerate(EVENTS) if j>=2}))
 modes={}
 for p in PATTERNS:
  i0={k:[v for e in range(3) for v in values['independent',p,0,k,e]] for k in CHAINS};s0={k:[v for e in range(3) for v in values['serial',p,0,k,e]] for k in CHAINS};pp=[x for x in points if x['drain']==p]
  gates=dict(all_points_stable=all(x['stable'] for x in pp),overlap_ratios={str(k):max(i0[k])/min(s0[k]) for k in CHAINS},none_noise_ratios={str(k):(max(v for e in range(3) for v in values['none',p,0,k,e])-min(v for e in range(3) for v in values['none',p,0,k,e]))/min(i0[k]) for k in CHAINS},none_max_ratios={str(k):max(v for e in range(3) for v in values['none',p,64,k,e])/min(i0[k]) for k in CHAINS},icache_background=all(x['background_passed'] for x in pp))
  good=gates['all_points_stable'] and all(x<=.70 for x in gates['overlap_ratios'].values()) and all(x<=.01 for x in gates['none_noise_ratios'].values()) and all(x<=.80 for x in gates['none_max_ratios'].values()) and gates['icache_background'];modes[p]=dict(qualified=good,gates=gates,status='qualified' if good else 'not-qualified')
 return dict(mode=MODE,phase='qualification',windows=384,status='FPSR_REFERENCE_QUALIFIED' if modes['fpsr']['qualified'] else 'REFERENCE_NOT_QUALIFIED',modes=modes,points=points,window_ratios=ratios,physical_entries_certified=False,allocation_units_certified=False,naming_limit='per-mode original-result/input-reset/retirement-boundary qualification only; not a physical ROB entry or allocation estimate')

def audit_raw(path):
 """Launch/source/build/environment and complete raw inventory, never patched input."""
 phase=json.loads((path/'manifest.json').read_text()).get('phase');cc=conditions(phase)
 inventory={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+suffix for c in conditions(phase) for suffix in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')}
 _require({p.name for p in path.iterdir()}==inventory and all(p.is_file() for p in path.iterdir()),'drain raw inventory')
 m=json.loads((path/'manifest.json').read_text());phase=m.get('phase');cc=conditions(phase);_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'drain manifest identity')
 _require(_same(m.get('conditions'),cc) and type(m.get('results')) is list and len(m['results'])==len(cc),'drain requested/result coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'drain launch SHA '+file)
 for saved,key in (('driver.py','driver_sha256'),('consumer.py','consumer_sha256')):_require(sha((path/saved).read_bytes())==m[key],'drain saved '+saved)
 build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['rob_fp_drain']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'drain binary/source/plan binding')
 for file,digest in build['source_sha256'].items():_require(sha(blob(head,file))==digest and sha(blob(m['binary_source_head'],file))==digest,'drain source dependency '+file)
 _require(m.get('qualification_input') is None,'drain cannot borrow earlier qualification')
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt'
 env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[]
 for r,c in zip(m['results'],conditions(phase)):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'drain result identity/status');f=path/(c['name']+'.stdout.jsonl')
  _require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','drain stdout/stderr')
  rows.append(_audit_records([json.loads(l) for l in f.read_text().splitlines()],c))
 return dict(mode=MODE,phase=phase,processes=len(cc),source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],rows=rows),{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv)
 run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],status=result['status'],modes=result['modes'],gpr_flow=result.get('gpr_flow'))))
if __name__=='__main__':main()
