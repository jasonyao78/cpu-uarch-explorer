#!/usr/bin/env python3
"""Q-D explicit K-chain PMU scope and same-window effective ratios.

Frozen contract: docs/design/2026-10-11-tlb-walk-parallel.md. Preserve all
windows, inactive/negative corrections; no hardware queue capacity naming.
"""
import argparse,hashlib,json,statistics as st,subprocess,sys
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='tlb-walk-parallel';PROTOCOL='docs/design/2026-10-11-tlb-walk-parallel.md'
BUILD='docs/reviews/evidence/2026-10-11-tlb-walk-parallel/build.json';PLAN='docs/reviews/evidence/2026-10-11-tlb-walk-parallel/plan.json';DRIVER='tools/diagnostic/run_sm8650_parallel.py'
EVENTS=[17,8,3,23,52,33064]
def config(reverse):return dict(type='config',version=1,probe=MODE,k_grid=[1,2,4,8],seed=137,base_nodes=8192,load_grid=[262144,1048576],warmup_loads=1048576,rounds=3,events=EVENTS,pmu_type=8,reverse=reverse,cells=33,windows=99)
def plan(reverse):
 _require(type(reverse) is bool,'parallel reverse type');rows=[dict(type='cell',cell='floor',scope='floor',layout='empty',k=0,nodes=0,loads=0,iterations=0,pages=0,line_bytes=0,span_bytes=0,rounds=3)]
 for scope in ('total','per-chain'):
  for layout in ('high','low'):
   for k in (1,2,4,8):
    n=8192*(k if scope=='per-chain' else 1);pages=n if layout=='high' else n//64;span=((n-1)*17+1)*4096 if layout=='high' else pages*4096
    for loads in (262144,1048576):rows.append(dict(type='cell',cell=f'{scope}-{layout}-k{k}-l{loads}',scope=scope,layout=layout,k=k,nodes=n,loads=loads,iterations=loads//k,pages=pages,line_bytes=n*64,span_bytes=span,rounds=3))
 if reverse:rows.reverse()
 return [config(reverse)]+[dict(c,position=i) for i,c in enumerate(rows)]
def validate_plan(value):_require(_same(value,dict(forward=plan(False),reverse=plan(True))),'parallel actual plan mismatch')
@lru_cache(maxsize=8)
def chains(n,k):
 order=list(range(n));state=137;mask=(1<<64)-1
 for i in range(n-1,0,-1):
  state^=(state<<13)&mask;state^=state>>7;state^=(state<<17)&mask;j=state%(i+1);order[i],order[j]=order[j],order[i]
 return [order[j*n//k:(j+1)*n//k] for j in range(k)]
def sample_check(s,c,t):
 _fields(s,dict(type='round',cell=c['cell'],position=c['position'],round=t,head_returned=True),'parallel sample identity')
 _require(type(s.get('enabled')) is int and s['enabled']>0 and type(s.get('running')) is int and s['running']==s['enabled'],'parallel mux/time')
 v=s.get('counts');_require(type(v) is list and len(v)==6 and all(type(x) is int and x>=0 for x in v),'parallel counts')
 if c['k']:
  ir=c['loads']+2*c['iterations'];_require(v[0]>0 and .95*ir<=v[1]<=1.05*ir,'parallel IR/core loop scope')
def audit_process(records,reverse,registered):
 """Actual plan, complete graph and GROUP identities before any estimator."""
 validate_plan(registered);_require(type(records) is list and len(records)==233,'parallel raw coverage');_require(_same(records[0],config(reverse)),'parallel config');pmu=records[1];_fields(pmu,dict(type='pmu'),'parallel PMU');ids=pmu.get('ids');_require(type(ids) is list and len(ids)==6 and all(type(i) is int and i>0 for i in ids) and len(set(ids))==6,'parallel kernel ID coverage')
 out=[];cursor=2
 for c in plan(reverse)[1:]:
  _require(_same(records[cursor],c),'parallel cell identity');cursor+=1;g=records[cursor];cursor+=1;_fields(g,dict(type='geometry',cell=c['cell']),'parallel geometry identity');base=g.get('base');_require(type(base) is int and (base>0 and base%4096==0 if c['k'] else base==0),'parallel mapping base');_require(_same(g.get('chains'),chains(c['nodes'],c['k']) if c['k'] else []),'parallel actual chain permutation')
  for stage in ('before','after'):_fields(records[cursor],dict(type='backing',cell=c['cell'],stage=stage,base_page_bytes=4096,anon_huge_kb=0),'parallel backing');cursor+=1
  samples=[]
  for t in range(3):
   s=records[cursor];cursor+=1;sample_check(s,c,t);samples.append(s)
  out.append(dict(c,geometry=g,pmu_ids=ids,samples=samples))
 return out

def ratios(counts,loads):
 """Same observations; negative corrected A/C stays negative, not clipped."""
 c,m,a=counts[0],counts[4],counts[5]
 return dict(occupancy=a/c if c>0 else None,walks_per_cycle=m/c if c>0 else None,residence_cycles=a/m if m>0 else None,loads_per_cycle=loads/c if c>0 else None)
def analyze(run):
 _fields(run,dict(mode=MODE,processes=5),'parallel run');rows=run.get('rows');_require(type(rows) is list and len(rows)==165,'parallel matrix');by={};cursor=0
 for e in range(5):
  for c in plan(bool(e%2))[1:]:
   r=rows[cursor];cursor+=1;_fields(r,dict(c,epoch=f'epoch-{e}'),'parallel output identity/order');_require(type(r.get('samples')) is list and len(r['samples'])==3,'parallel sample coverage')
   for t,s in enumerate(r['samples']):sample_check(s,c,t)
   by[e,c['cell']]=r
 windows=[];qualification=[]
 for e in range(5):
  floor=by[e,'floor'];background=[st.median(s['counts'][j] for s in floor['samples']) for j in range(6)]
  for c in plan(bool(e%2))[1:]:
   if not c['k']:continue
   for s in by[e,c['cell']]['samples']:
    v=s['counts'];corrected=[v[j]-background[j] for j in range(6)];gates=[dict(event=hex(EVENTS[j]),background=background[j],window=v[j],passed=background[j]<=.01*v[j]) for j in (0,4,5)]
    high=c['layout']=='high';low_cell=c['cell'].replace('-high-','-low-');low_A=st.median(x['counts'][5] for x in by[e,low_cell]['samples']) if high else None
    scope_ok=(v[4]/c['loads']>=.1 and v[5]>0 and v[5]>low_A) if high else v[4]/c['loads']<=.001
    q=dict(epoch=e,cell=c['cell'],round=s['round'],scope_ok=scope_ok,matched_low_A=low_A,walks_per_load=v[4]/c['loads'],background_gates=gates,passed=scope_ok and all(g['passed'] for g in gates))
    if c['loads']==1048576:qualification.append(q)
    windows.append(dict(epoch=e,cell=c['cell'],round=s['round'],counts=v,ratios=ratios(v,c['loads']),corrected_counts=corrected,corrected_ratios=ratios(corrected,c['loads']),cycle_state='positive' if corrected[0]>0 else 'nonpositive-corrected-cycles',scope_check=q))
 points=[]
 for c in plan(False)[1:]:
  if not c['k']:continue
  samples=[s for e in range(5) for s in by[e,c['cell']]['samples']];sums=[sum(s['counts'][j] for s in samples) for j in range(6)];ww=[w for w in windows if w['cell']==c['cell']];corrected=[sum(w['corrected_counts'][j] for w in ww) for j in range(6)];loadsum=15*c['loads']
  points.append(dict(c,samples=15,count_sums=sums,ratios=ratios(sums,loadsum),corrected_count_sums=corrected,corrected_ratios=ratios(corrected,loadsum),l1d_refill_per_load=sums[2]/loadsum,l2d_refill_per_load=sums[3]/loadsum,walks_per_load=sums[4]/loadsum,walk_state='walk-active' if sums[4]>0 else 'walk-inactive',epoch_ratios=[dict(epoch=e,ratios=ratios([sum(s['counts'][j] for s in by[e,c['cell']]['samples']) for j in range(6)],3*c['loads'])) for e in range(5)]))
 return dict(mode=MODE,windows=495,points=points,window_ratios=windows,qualification_checks=qualification,qualification='qualified-effective-occupancy' if all(q['passed'] for q in qualification) else 'not-qualified',physical_queue_certified=False,naming_limit='effective in-flight occupancy on these finite K-chain loads; no walker/MSHR/LQ depth; compare measured data-side controls')

def conditions():return [dict(name=f'epoch-{e}',args=['--run',*(['--reverse'] if e%2 else [])]) for e in range(5)]

def audit_raw(path):
 """Exact inventory, committed launch/binary/plan, environment and real records."""
 expected={'manifest.json','driver.py','environment-policy.json','initial-environment.json','final-environment.json'}|{f'epoch-{e}'+s for e in range(5) for s in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')};_require({p.name for p in path.iterdir()}==expected and all(p.is_file() for p in path.iterdir()),'parallel raw inventory')
 m=json.loads((path/'manifest.json').read_text());_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN),'parallel manifest identity');_require(_same(m.get('conditions'),conditions()) and type(m.get('results')) is list and len(m['results'])==5,'parallel requested coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'parallel launch SHA '+file)
 _require(sha((path/'driver.py').read_bytes())==m['driver_sha256'],'parallel saved driver');build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['tlb_walk_parallel']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'parallel binary/source/plan binding')
 for p,digest in build['source_sha256'].items():_require(sha(blob(head,p))==digest and sha(blob(m['binary_source_head'],p))==digest,'parallel dependency SHA '+p)
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt';env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[]
 for e,(r,c) in enumerate(zip(m['results'],conditions())):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'parallel result order/status');f=path/(c['name']+'.stdout.jsonl');_require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','parallel stdout/stderr binding');records=[json.loads(l) for l in f.read_text().splitlines()];rows.extend(dict(row,epoch=c['name']) for row in audit_process(records,bool(e%2),registered))
 result=dict(mode=MODE,processes=5,source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],rows=rows)
 return result,{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv);run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],qualification=result['qualification'],checks_passed=sum(q['passed'] for q in result['qualification_checks']),checks=len(result['qualification_checks']))))
if __name__=='__main__':main()
