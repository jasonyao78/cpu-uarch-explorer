#!/usr/bin/env python3
"""Q-A page-set contrasts, independent offset/order and finite refill curves.

Frozen contract: docs/design/2026-10-12-tlb-balanced-reach.md. No HPA/PFN
attribution, refill probability or physical entry naming from these counters.
"""
import argparse,hashlib,json,statistics as st,subprocess,sys
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='tlb-balanced-reach';PROTOCOL='docs/design/2026-10-12-tlb-balanced-reach.md';BUILD='docs/reviews/evidence/2026-10-12-tlb-balanced-reach/build.json';PLAN='docs/reviews/evidence/2026-10-12-tlb-balanced-reach/plan.json';DRIVER='tools/diagnostic/run_sm8650_tlb_reach.py';CONSUMER='tools/diagnostic/tlb_reach_analysis.py'
GRID=(512,1024,1280,1536,1792,2048,2304,2560,3072);SHAPES=('dense','spaced','balanced-random');ORDERS=('random','reverse-random')
@lru_cache(maxsize=20)
def permutation(n,seed):
 out=list(range(n));x=seed;mask=(1<<64)-1
 for i in range(n-1,0,-1):
  x^=(x<<13)&mask;x^=x>>7;x^=(x<<17)&mask;j=x%(i+1);out[i],out[j]=out[j],out[i]
 return out
@lru_cache(maxsize=36)
def pages(shape,n):return list(range(n)) if shape=='dense' else [257*i for i in range(n)] if shape=='spaced' else [256*permutation(4096,271)[i]+i%256 for i in range(n)]
def config(reverse):return dict(type='config',version=1,probe=MODE,pool_pages=1048576,page_set_seed=271,order_seed=137,n_grid=list(GRID),load_budget=1048576,rounds=3,events=[17,8,5,45,47,52],pmu_type=8,reverse=reverse,cells=55,windows=165)
def plan(reverse):
 _require(type(reverse) is bool,'reach reverse type');rows=[dict(type='cell',cell='floor',shape='floor',offset='empty',order='empty',n=0,loads=0,span_bytes=0,line_bytes=0,rounds=3)]
 for shape in SHAPES:
  for order in ORDERS:
   for n in GRID:
    pp=pages(shape,n);rows.append(dict(type='cell',cell=f'{shape}-rotated-{order}-n{n}',shape=shape,offset='rotated',order=order,n=n,loads=(1048576//n)*n,span_bytes=(max(pp)-min(pp)+1)*4096,line_bytes=n*64,rounds=3))
 if reverse:rows.reverse()
 return [config(reverse)]+[dict(c,position=i) for i,c in enumerate(rows)]
def validate_plan(value):_require(_same(value,dict(forward=plan(False),reverse=plan(True))),'reach actual plan mismatch')
def mapping(base):
 _require(type(base) is int and base>0 and base%4096==0 and base<=2**64-1048576*4096,'reach base range')
 return dict(type='mapping',base=base,pool_pages=1048576,hpa_state='UNKNOWN',pte_cont_state='UNKNOWN',pfn_state='UNKNOWN',data_cache_state='UNKNOWN',prefaulted_page_ids=sorted({p for shape in SHAPES for p in pages(shape,3072)}))
def geometry(c,base):
 pp=pages(c['shape'],c['n']) if c['n'] else [];oo=list(permutation(c['n'],137)) if c['n'] else []
 if c['order']=='reverse-random':oo.reverse()
 offsets=[64*(p%64) for p in pp];parents=sorted({(base//4096+p)>>9 for p in pp});hist=[0]*256
 for p in pp:hist[(base//4096+p)%256]+=1
 return dict(type='geometry',cell=c['cell'],page_ids=pp,order_indices=oo,offsets=offsets,vpn_low8_hist=hist,l3_parent_count=len(parents),l3_parent_ids=parents)
def sample_check(s,c,t):
 _fields(s,dict(type='round',cell=c['cell'],position=c['position'],round=t,head_returned=True),'reach sample identity');_require(type(s.get('enabled')) is int and s['enabled']>0 and type(s.get('running')) is int and s['running']==s['enabled'],'reach mux/time');v=s.get('counts');_require(type(v) is list and len(v)==6 and all(type(x) is int and x>=0 for x in v),'reach counts')
 if c['n']:_require(v[0]>0 and .95*3*c['loads']<=v[1]<=1.05*3*c['loads'],'reach IR/core loop')
def audit_process(records,reverse,registered):
 """Production geometry is audited against an independent typed oracle."""
 validate_plan(registered);_require(type(records) is list and len(records)==388,'reach raw coverage');_require(_same(records[0],config(reverse)),'reach config');pmu=records[1];_fields(pmu,dict(type='pmu'),'reach PMU');ids=pmu.get('ids');_require(type(ids) is list and len(ids)==6 and all(type(i) is int and i>0 for i in ids) and len(set(ids))==6,'reach kernel ID coverage')
 base=records[2].get('base');_require(_same(records[2],mapping(base)),'reach mapping/prefault/unknown physical state');out=[];cursor=3
 for c in plan(reverse)[1:]:
  _require(_same(records[cursor],c),'reach cell identity');cursor+=1;g=records[cursor];cursor+=1;_require(_same(g,geometry(c,base)),'reach page/order/offset/VA proxy')
  for stage in ('before','after'):_fields(records[cursor],dict(type='backing',cell=c['cell'],stage=stage,base_page_bytes=4096,anon_huge_kb=0),'reach backing');cursor+=1
  samples=[]
  for t in range(3):s=records[cursor];cursor+=1;sample_check(s,c,t);samples.append(s)
  out.append(dict(c,geometry=g,pmu_ids=ids,samples=samples))
 return out

def ratio(v,loads):return dict(cycles_per_load=v[0]/loads,l1_refills_per_load=v[2]/loads,l2_refills_per_load=v[3]/loads,l2_accesses_per_load=v[4]/loads,walks_per_load=v[5]/loads)
def analyze(run):
 """Finite per-mapping curves; failed pressure or floor cannot be averaged away."""
 _fields(run,dict(mode=MODE,processes=5),'reach run');rows=run.get('rows');_require(type(rows) is list and len(rows)==275,'reach matrix');by={};cursor=0
 for e in range(5):
  for c in plan(bool(e%2))[1:]:
   r=rows[cursor];cursor+=1;_fields(r,dict(c,epoch=f'epoch-{e}'),'reach output identity/order');_require(type(r.get('samples')) is list and len(r['samples'])==3,'reach sample coverage')
   for t,s in enumerate(r['samples']):sample_check(s,c,t)
   by[e,c['cell']]=r
 windows=[];checks=[];epoch_points=[];lookup={};valid={}
 for e in range(5):
  background=[st.median(s['counts'][j] for s in by[e,'floor']['samples']) for j in range(6)]
  for c in plan(bool(e%2))[1:]:
   if not c['n']:continue
   rr=by[e,c['cell']]['samples'];sums=[sum(s['counts'][j] for s in rr) for j in range(6)];p=dict(epoch=e,**c,**ratio(sums,3*c['loads']),walk_round_rates=[s['counts'][5]/c['loads'] for s in rr]);epoch_points.append(p);lookup[e,c['shape'],c['order'],c['n']]=p;valid[e,c['cell']]=True
   for s in rr:
    v=s['counts'];corrected=[v[j]-background[j] for j in range(6)];gates=dict(cycle_background=background[0]<=.01*v[0],translation_background=all(background[j]<=.001*c['loads'] for j in range(2,6)),l1_translation_pressure=.75*c['loads']<=v[2]<=1.25*c['loads']);passed=all(gates.values());valid[e,c['cell']] &= passed;checks.append(dict(epoch=e,cell=c['cell'],round=s['round'],gates=gates,passed=passed));windows.append(dict(epoch=e,cell=c['cell'],round=s['round'],counts=v,ratios=ratio(v,c['loads']),corrected_counts=corrected,corrected_ratios=ratio(corrected,c['loads'])))
 points=[]
 for c in plan(False)[1:]:
  if not c['n']:continue
  samples=[s for e in range(5) for s in by[e,c['cell']]['samples']];sums=[sum(s['counts'][j] for s in samples) for j in range(6)];points.append(dict(c,samples=15,count_sums=sums,**ratio(sums,15*c['loads'])))
 background_ok=all(q['passed'] for q in checks);comparisons=[]
 for shape in ('spaced','balanced-random'):
  for n in GRID:
   deltas=[dict(epoch=e,order=o,delta=lookup[e,shape,o,n]['walks_per_load']-lookup[e,'dense',o,n]['walks_per_load']) for e in range(5) for o in ORDERS];vv=[d['delta'] for d in deltas];positive=all(v>=.10 for v in vv);negative=all(v<=-.10 for v in vv);comparisons.append(dict(shape=shape,n=n,deltas=deltas,range=[min(vv),max(vv)],replicated=background_ok and (positive or negative),numeric_replicated=positive or negative,admissible=background_ok,direction='positive' if positive else 'negative' if negative else 'not-replicated'))
 sensitive=any(p['replicated'] for p in comparisons);allsmall=all(abs(d['delta'])<.10 for p in comparisons for d in p['deltas']);verdict='INCONCLUSIVE' if not background_ok else 'GEOMETRY_SENSITIVE' if sensitive else 'NO_DIFFERENCE_DETECTED' if allsmall else 'INCONCLUSIVE';curves=[]
 for e in range(5):
  for shape in SHAPES:
   for order in ORDERS:
    ps=[lookup[e,shape,order,n] for n in GRID];above=[all(v>=.10 for v in p['walk_round_rates']) for p in ps];below=[all(v<.10 for v in p['walk_round_rates']) for p in ps];status='ambiguous';interval=None
    if not all(valid[e,p['cell']] for p in ps):status='INCOMPUTABLE'
    elif not all(a or b for a,b in zip(above,below)):status='ambiguous'
    elif any(above[i] and below[j] for i in range(len(GRID)) for j in range(i+1,len(GRID))):status='ambiguous'
    elif not any(above):status='no-crossing-through3072'
    elif above[0]:status='left-censored'
    else:
     i=above.index(True)
     if len(above)-i<2:status='right-censored'
     else:status='interval';interval=[GRID[i-1],GRID[i]]
    curves.append(dict(epoch=e,shape=shape,order=order,status=status,interval=interval,points=[dict(n=p['n'],walk_round_rates=p['walk_round_rates'],**{k:p[k] for k in ratio([0]*6,1)}) for p in ps]))
 reach=[]
 for shape in SHAPES:
  cc=[c for c in curves if c['shape']==shape];replicated=all(c['status']=='interval' and c['interval']==cc[0]['interval'] for c in cc);reach.append(dict(shape=shape,curves=10,status='replicated' if replicated else 'heterogeneous',interval=cc[0]['interval'] if replicated else None,curve_states=[dict(epoch=c['epoch'],order=c['order'],status=c['status'],interval=c['interval']) for c in cc]))
 return dict(mode=MODE,windows=825,verdict=verdict,background_passed=background_ok,points=points,epoch_points=epoch_points,window_ratios=windows,background_checks=checks,comparisons=comparisons,curves=curves,reach=reach,hpa_state='UNKNOWN',pte_cont_state='UNKNOWN',pfn_state='UNKNOWN',data_cache_state='UNKNOWN',physical_entries_certified=False,attribution_certified=False,naming_limit='finite balanced-VA walk sensitivity and operational translation reach; unknown hardware hash/PFN/PTE_CONT/cache/walk attribution')

def conditions():return [dict(name=f'epoch-{e}',args=['--run',*(['--reverse'] if e%2 else [])]) for e in range(5)]

def audit_raw(path):
 """Exact inventory, committed launch/binary/plan, environment and real records."""
 expected={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{f'epoch-{e}'+s for e in range(5) for s in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')};_require({p.name for p in path.iterdir()}==expected and all(p.is_file() for p in path.iterdir()),'reach raw inventory')
 m=json.loads((path/'manifest.json').read_text());_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'reach manifest identity');_require(_same(m.get('conditions'),conditions()) and type(m.get('results')) is list and len(m['results'])==5,'reach requested coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'reach launch SHA '+file)
 _require(sha((path/'driver.py').read_bytes())==m['driver_sha256'],'reach saved driver');_require(sha((path/'consumer.py').read_bytes())==m['consumer_sha256'],'reach saved consumer');build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['tlb_balanced_reach']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'reach binary/source/plan binding')
 for p,digest in build['source_sha256'].items():_require(sha(blob(head,p))==digest and sha(blob(m['binary_source_head'],p))==digest,'reach dependency SHA '+p)
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt';env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[];mapping=[]
 for e,(r,c) in enumerate(zip(m['results'],conditions())):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'reach result order/status');f=path/(c['name']+'.stdout.jsonl');_require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','reach stdout/stderr binding');records=[json.loads(l) for l in f.read_text().splitlines()];rows.extend(dict(row,epoch=c['name']) for row in audit_process(records,bool(e%2),registered));mapping.append(dict(epoch=e,**records[2]))
 result=dict(mode=MODE,processes=5,source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],mapping=mapping,rows=rows)
 return result,{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv);run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],verdict=result['verdict'],background=result['background_passed'],replicated_differences=sum(p['replicated'] for p in result['comparisons']))))
if __name__=='__main__':main()
