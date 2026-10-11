#!/usr/bin/env python3
"""Observed competition counts and repeated victim response, never physical ways.

Contract: docs/design/2026-10-10-tlb-competition-observation.md. Source/launch/
binary/environment acceptance belongs to summarize_sm8650_minimal.py; this
module independently expects every cell/pass and retains all signed contrasts.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import statistics as st
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require, _same, _fields
from tools.diagnostic.tlb_history_analysis import _check_geometry
MODE='tlb-competition'
PROTOCOL='docs/design/2026-10-10-tlb-competition-observation.md'
K=(0,7,8,9,10,11)
PASSES=(1,2,4,8)
META=('cell','position','h','k','direction','passes','rounds')


def config(reverse):
    """Typed fixed producer v1 shape; no inferred defaults from records."""
    return dict(type='config',version=1,probe=MODE,target=100,seed=137,max_w=12,
                old_prefix=9,offset_rotate=True,link_slots=5,f=128,history=12,
                k_grid=list(K),pass_grid=list(PASSES),rounds=16,reverse=reverse,cells=96,windows=7296)


def plan(reverse):
    """Independent semantic/order expectation, checked against actual --plan."""
    _require(type(reverse) is bool,'competition reverse type')
    base=list(itertools.product((1,2),K,(0,1),PASSES))
    if reverse:base.reverse()
    return [config(reverse)]+[dict(type='cell',cell=f'lookup-h{h}-k{k}-d{d}-p{p}',
              position=i,h=h,k=k,direction=d,passes=p,rounds=16) for i,(h,k,d,p) in enumerate(base)]


def validate_plan(value):
    """Production plan alone is not authoritative when damaged or mistyped."""
    _require(_same(value,{'forward':plan(False),'reverse':plan(True)}),'competition plan shape/order/type mismatch')


def sample_check(sample,trial,p,passes):
    _fields(sample,dict(round=trial,role='victim' if p==passes else 'competition',pass_index=p),'competition sample role/pass/order mismatch')
    _require(all(type(sample.get(k)) is int and 0<sample[k]<2**64 for k in ('enabled','running')) and sample['enabled']==sample['running'],'competition empty/mux window')
    v=sample.get('counts')
    _require(type(v) is list and len(v)==6 and all(type(x) is int and 0<=x<2**64 for x in v) and v[0]>0,'competition uint64 six-event counts')


def validate_launch(value):
    """New-profile typed target/condition/result contract before generic Git audit."""
    _fields(value,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,tlb_target=100,
                      protocol_path=PROTOCOL,build_evidence_path='docs/reviews/evidence/2026-10-10-tlb-competition/build.json',
                      plan_path='docs/reviews/evidence/2026-10-10-tlb-competition/plan.json'), 'competition launch identity mismatch')
    expected=[dict(name=f'epoch-{e}',args=['100',*(['--reverse'] if e%2 else [])]) for e in range(5)]
    _require(_same(value.get('conditions'),expected),'competition conditions mismatch')
    results=value.get('results');_require(type(results) is list and len(results)==5,'competition result coverage')
    for e,r in enumerate(results):_fields(r,dict(name=f'epoch-{e}',exit_code=0,timed_out=False),'competition result order/status/type mismatch')


def audit_competition(records,reverse,registered):
    """Full real config/geometry/backing/cell/pass stream, exporting anonymous rows."""
    selected=registered['reverse' if reverse else 'forward'] if type(registered) is dict else registered
    _require(_same(selected,plan(reverse)),'competition production plan mismatch')
    _require(type(records) is list and len(records)==7490,'competition raw record coverage')
    _require(_same(records[0],config(reverse)),'competition actual config mismatch')
    _check_geometry(records[1]);cursor=2;public=[]
    for c in selected[1:]:
        for stage in ('before','after'):
            _fields(records[cursor],dict(type='backing',cell=c['cell'],stage=stage,base_page_bytes=4096,anon_huge_kb=0),'competition backing endpoint mismatch');cursor+=1
        samples=[]
        for t in range(16):
            for p in range(c['passes']+1):
                r=records[cursor];cursor+=1
                _fields(r,dict(type='round',**{k:c[k] for k in META if k!='rounds'}),'competition round metadata/order mismatch')
                sample_check(r,t,p,c['passes'])
                samples.append({k:r[k] for k in ('round','role','pass_index','enabled','running','counts')})
        public.append(dict(**c,samples=samples))
    _require(cursor==len(records),'competition unconsumed records')
    return public


def audit_cells(run):
    """Complete 5-mapping anonymous evidence, before any scientific contrasts."""
    _fields(run,dict(mode=MODE,processes=5),'competition mode/processes mismatch')
    rows=run.get('rows');_require(type(rows) is list and len(rows)==480,'competition complete cell coverage')
    result={};cursor=0
    for e in range(5):
        for expected in plan(bool(e%2))[1:]:
            c=rows[cursor];cursor+=1
            _fields(c,dict(epoch=f'epoch-{e}',**expected),'competition cell semantic/order/type mismatch')
            samples=c.get('samples');p=expected['passes']
            _require(type(samples) is list and len(samples)==16*(p+1),'competition complete sample coverage')
            for i,s in enumerate(samples):sample_check(s,i//(p+1),i%(p+1),p)
            result[c['epoch'],c['h'],c['k'],c['direction'],p]=c
    return result


def analyze(run):
    """K0 matched per H/order/pass/traversal; A/C rates paired only inside epoch.

Lookup gates concern observable counts, not allocation/admission. Sparse K is
not turned into an interval. Window pollution/drift blocks response naming.
"""
    cells=audit_cells(run);lookup=[];victim=[];replication=[]
    def subset(c,role,index=None):return [s for s in c['samples'] if s['role']==role and (index is None or s['pass_index']==index)]
    for e in range(5):
        epoch=f'epoch-{e}'
        for h,d,p in itertools.product((1,2),(0,1),PASSES):
            zero=cells[epoch,h,0,d,p]
            for k in K[1:]:
                c=cells[epoch,h,k,d,p]
                for i in range(p):
                    rr,zz=subset(c,'competition',i),subset(zero,'competition',i)
                    counts=[[s['counts'][j] for s in rr] for j in range(6)]
                    control=[[s['counts'][j] for s in zz] for j in range(6)]
                    differences=[st.mean(a)-st.mean(b) for a,b in zip(counts,control)]
                    gates=[dict(event=event,value=differences[index],lower=.75*k,upper=1.25*k,passed=.75*k<=differences[index]<=1.25*k) for index,event in ((1,'0x05'),(3,'0x2f'))]
                    lookup.append(dict(epoch=epoch,h=h,k=k,direction=d,passes=p,pass_index=i,
                        counts=counts,control_counts=control,count_mean_differences=differences,gates=gates,observable=all(g['passed'] for g in gates)))
        for d,p in itertools.product((0,1),PASSES):
            baseline={h:subset(cells[epoch,h,0,d,p],'victim') for h in (1,2)}
            baseline_ok=all(st.mean(s['counts'][4]>0 for s in rs)<=.125 for rs in baseline.values())
            for k in K:
                families={};issues=[]
                if not baseline_ok:issues.append('baseline-contaminated')
                for h in (1,2):
                    rs=subset(cells[epoch,h,k,d,p],'victim');walk=[s['counts'][4] for s in rs]
                    rate=st.mean(v>0 for v in walk);drift=st.mean(v>0 for v in walk[8:])-st.mean(v>0 for v in walk[:8])
                    families[str(h)]=dict(counts=[s['counts'] for s in rs],walk=walk,response_rate=rate,walk_mean=st.mean(walk),rate_drift=drift,count_over_one=sum(v>1 for v in walk))
                    if any(v>1 for v in walk):issues.append('single-load-window-residual')
                    if abs(drift)>.25:issues.append('preparation-drift')
                diff=families['1']['response_rate']-families['2']['response_rate']
                victim.append(dict(epoch=epoch,k=k,direction=d,passes=p,families=families,difference=diff,
                    baseline_ok=baseline_ok,issues=list(dict.fromkeys(issues)),response_observed=not issues and diff>=.5))
    for k,p in itertools.product(K[1:],PASSES):
        names=[f'epoch-{e}' for e in range(5) if all(next(v for v in victim if v['epoch']==f'epoch-{e}' and v['k']==k and v['passes']==p and v['direction']==d)['response_observed'] for d in (0,1))]
        related=[v for v in lookup if v['k']==k and v['passes']==p]
        replication.append(dict(k=k,passes=p,epoch_names=names,epochs=len(names),required_epochs=4,passed=len(names)>=4,all_related_lookups_observable=all(v['observable'] for v in related)))
    return dict(mode=MODE,protocol_path=PROTOCOL,processes=5,windows=36480,lookup_points=lookup,
        victim_points=victim,replication=replication,all_lookup_observable=all(v['observable'] for v in lookup),
        physical_ways_certified=False,naming_limit='observed whole-window competition and victim response; no physical capacity or admission proof')


def main(argv=None):
    """Raw acceptance is mandatory; technical failures publish no artifacts."""
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('raw',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--summary-output',type=Path)
    args=parser.parse_args(argv)
    from tools.diagnostic.summarize_sm8650_minimal import summarize
    run=summarize(args.raw);result=analyze(run)
    summary=json.dumps(run,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    result.update(data_origin='device-raw',input_sha256=hashlib.sha256(summary.encode()).hexdigest())
    output=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    if args.summary_output:args.summary_output.write_text(summary)
    args.output.write_text(output)
    print(json.dumps(dict(windows=result['windows'],lookup_observable=sum(p['observable'] for p in result['lookup_points']),lookup_points=len(result['lookup_points']),repeated_response_points=sum(p['passed'] for p in result['replication']),physical_ways_certified=False)))
if __name__=='__main__':main()
