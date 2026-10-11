#!/usr/bin/env python3
"""Fixed page membership victim/history response; no physical ways estimate.

Contract: docs/design/2026-10-11-tlb-victim-history.md. Actual production plan,
full geometry/backing/source/raw acceptance precede counter observations.
"""
import argparse,hashlib,itertools,json,statistics as st,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic.tlb_history_analysis import _check_geometry
from tools.diagnostic.tlb_competition_analysis import sample_check
MODE='tlb-victim-history';PROTOCOL='docs/design/2026-10-11-tlb-victim-history.md'
BUILD='docs/reviews/evidence/2026-10-11-tlb-victim-history/build.json';PLAN='docs/reviews/evidence/2026-10-11-tlb-victim-history/plan.json'
META=('cell','position','h','w','victim','history_direction','direction','passes','rounds')

def config(reverse):
 return dict(type='config',version=1,probe=MODE,target=100,seed=137,max_w=12,old_prefix=9,offset_rotate=True,link_slots=5,f=128,history=12,w_grid=[1,8,9],victim_ranks=['first','middle','last'],history_directions=[0,1],passes=8,rounds=16,reverse=reverse,cells=56,windows=8064)

def plan(reverse):
 """Independent frozen semantics, not inferred from raw fields or a row count."""
 _require(type(reverse) is bool,'victim history reverse type');base=[]
 for hd in (0,1):
  for w in (1,8,9):
   for v in ([0] if w==1 else [0,w//2,w-1]):
    for d in (0,1):
     for h in (1,2):base.append((h,w,v,hd,d))
 if reverse:base.reverse()
 return [config(reverse)]+[dict(type='cell',cell=f'victim-h{h}-w{w}-v{v}-hist{hd}-d{d}',position=i,h=h,w=w,victim=v,history_direction=hd,direction=d,passes=8,rounds=16) for i,(h,w,v,hd,d) in enumerate(base)]

def validate_plan(value):
 _require(_same(value,dict(forward=plan(False),reverse=plan(True))),'victim history real plan shape/type/order mismatch')

def validate_launch(value):
 _fields(value,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,tlb_target=100,protocol_path=PROTOCOL,build_evidence_path=BUILD,plan_path=PLAN),'victim history launch identity mismatch')
 expected=[dict(name=f'epoch-{e}',args=['100',*(['--reverse'] if e%2 else [])]) for e in range(5)]
 _require(_same(value.get('conditions'),expected),'victim history conditions mismatch');results=value.get('results');_require(type(results) is list and len(results)==5,'victim history result coverage')
 for e,r in enumerate(results):_fields(r,dict(name=f'epoch-{e}',exit_code=0,timed_out=False),'victim history result order/status/type mismatch')

def audit_victim_history(records,reverse,registered):
 """Anonymous cells only after exact config/plan/VA/backing and all roles pass."""
 selected=registered['reverse' if reverse else 'forward'] if type(registered) is dict else registered
 _require(_same(selected,plan(reverse)),'victim history production plan mismatch')
 _require(type(records) is list and len(records)==8178,'victim history raw record coverage');_require(_same(records[0],config(reverse)),'victim history config mismatch');_check_geometry(records[1]);cursor=2;out=[]
 for c in selected[1:]:
  for stage in ('before','after'):
   _fields(records[cursor],dict(type='backing',cell=c['cell'],stage=stage,base_page_bytes=4096,anon_huge_kb=0),'victim history backing endpoint mismatch');cursor+=1
  samples=[]
  for t in range(16):
   for p in range(9):
    r=records[cursor];cursor+=1;_fields(r,dict(type='round',**{k:c[k] for k in META if k!='rounds'}),'victim history metadata/order/type mismatch');sample_check(r,t,p,8);samples.append({k:r[k] for k in ('round','role','pass_index','enabled','running','counts')})
  out.append(dict(**c,samples=samples))
 _require(cursor==len(records),'victim history unconsumed records');return out

def audit_cells(run):
 _fields(run,dict(mode=MODE,processes=5),'victim history mode/processes mismatch');rows=run.get('rows');_require(type(rows) is list and len(rows)==280,'victim history whole cell coverage');out={};i=0
 for e in range(5):
  for c in plan(bool(e%2))[1:]:
   r=rows[i];i+=1;_fields(r,dict(epoch=f'epoch-{e}',**c),'victim history cell identity/order/type mismatch');samples=r.get('samples');_require(type(samples) is list and len(samples)==144,'victim history sample coverage')
   for j,s in enumerate(samples):sample_check(s,j//9,j%9,8)
   out[f'epoch-{e}',c['h'],c['w'],c['victim'],c['history_direction'],c['direction']]=r
 return out

def analyze(run):
 """Paired A/C observations retain page-role and history; no keys may collapse."""
 cells=audit_cells(run);lookup=[];victim=[];replication=[]
 def subset(c,role,index=None):return [s for s in c['samples'] if s['role']==role and (index is None or s['pass_index']==index)]
 observable={}
 for e in range(5):
  epoch=f'epoch-{e}'
  for h,hd,d in itertools.product((1,2),(0,1),(0,1)):
   zero=cells[epoch,h,1,0,hd,d]
   for w in (8,9):
    for v in (0,w//2,w-1):
     c=cells[epoch,h,w,v,hd,d];okay=[]
     for p in range(8):
      rr,zz=subset(c,'competition',p),subset(zero,'competition',p);counts=[[s['counts'][j] for s in rr] for j in range(6)];control=[[s['counts'][j] for s in zz] for j in range(6)];diff=[st.mean(x)-st.mean(y) for x,y in zip(counts,control)]
      gates=[dict(event=event,value=diff[index],lower=.75*(w-1),upper=1.25*(w-1),passed=.75*(w-1)<=diff[index]<=1.25*(w-1)) for index,event in ((1,'0x05'),(3,'0x2f'))];passed=all(g['passed'] for g in gates);okay.append(passed)
      lookup.append(dict(epoch=epoch,h=h,w=w,victim=v,history_direction=hd,direction=d,pass_index=p,counts=counts,control_counts=control,count_mean_differences=diff,gates=gates,observable=passed))
     observable[epoch,h,w,v,hd,d]=all(okay)
  for hd,d in itertools.product((0,1),(0,1)):
   baselines={h:subset(cells[epoch,h,1,0,hd,d],'victim') for h in (1,2)};base_ok=all(st.mean(s['counts'][4]>0 for s in rr)<=.125 for rr in baselines.values())
   for w in (8,9):
    for v in (0,w//2,w-1):
     families={};issues=[]
     if not base_ok:issues.append('baseline-contaminated')
     if not all(observable[epoch,h,w,v,hd,d] for h in (1,2)):issues.append('lookup-not-observable')
     for h in (1,2):
      rr=subset(cells[epoch,h,w,v,hd,d],'victim');walk=[s['counts'][4] for s in rr];rate=st.mean(x>0 for x in walk);drift=st.mean(x>0 for x in walk[8:])-st.mean(x>0 for x in walk[:8]);families[str(h)]=dict(counts=[s['counts'] for s in rr],walk=walk,response_rate=rate,walk_mean=st.mean(walk),rate_drift=drift,count_over_one=sum(x>1 for x in walk))
      if any(x>1 for x in walk):issues.append('single-load-window-residual')
      if abs(drift)>.25:issues.append('preparation-drift')
     diff=families['1']['response_rate']-families['2']['response_rate'];victim.append(dict(epoch=epoch,w=w,victim=v,history_direction=hd,direction=d,families=families,difference=diff,baseline_ok=base_ok,issues=list(dict.fromkeys(issues)),response_observed=not issues and diff>=.5))
 for w in (8,9):
  for v in (0,w//2,w-1):
   for hd in (0,1):
    names=[f'epoch-{e}' for e in range(5) if all(next(p for p in victim if p['epoch']==f'epoch-{e}' and p['w']==w and p['victim']==v and p['history_direction']==hd and p['direction']==d)['response_observed'] for d in (0,1))];related=[p for p in lookup if p['w']==w and p['victim']==v and p['history_direction']==hd];replication.append(dict(w=w,victim=v,history_direction=hd,epoch_names=names,epochs=len(names),required_epochs=4,passed=len(names)>=4,all_related_lookups_observable=all(p['observable'] for p in related)))
 return dict(mode=MODE,protocol_path=PROTOCOL,processes=5,windows=40320,lookup_points=lookup,victim_points=victim,replication=replication,all_lookup_observable=all(p['observable'] for p in lookup),physical_ways_certified=False,naming_limit='fixed page membership, sampled victim/history response; no admission or physical ways proof')

def audit_raw(path):
 """Exact 25-file raw inventory plus Git/source/plan/environment acceptance."""
 m=json.loads((path/'manifest.json').read_text());validate_launch(m)
 expected={'manifest.json','driver.py','environment-policy.json','initial-environment.json','final-environment.json'}|{f'epoch-{e}'+suffix for e in range(5) for suffix in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')}
 _require({p.name for p in path.iterdir()}==expected and all(p.is_file() for p in path.iterdir()),'victim history complete raw inventory mismatch')
 from tools.diagnostic.summarize_sm8650_minimal import summarize
 return summarize(path),{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.iterdir())}

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path);a=p.parse_args(argv)
 run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,ensure_ascii=False,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes)
 if a.summary_output:a.summary_output.write_text(s)
 a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n');print(json.dumps(dict(windows=40320,lookup_observable=sum(p['observable'] for p in result['lookup_points']),lookup_points=len(result['lookup_points']),repeated_response_points=sum(p['passed'] for p in result['replication']),physical_ways_certified=False)))
if __name__=='__main__':main()
