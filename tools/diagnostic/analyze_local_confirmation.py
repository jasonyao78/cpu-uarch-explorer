#!/usr/bin/env python3
"""Frozen local-confirmation estimands; input must pass the raw auditor first.

Protocol: docs/design/2026-10-09-local-confirmation.md. Values are cycles or
walks, never inferred physical ROB entries/ways. Synthetic boundary tests live
in tools/diagnostic/tests/test_confirmation_analysis.py.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics as st
from collections import defaultdict
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))


def first_departure(epoch0, epoch1):
    """Two independent process epochs; absolute 1-cycle effect, no pooling.

    Require an earlier observed platform and two adjacent above-threshold
    points in BOTH epochs. Later return/negative departure or epoch conflict
    is ambiguous. The grid endpoints censor rather than invent a capacity.
    """
    if not epoch0 or set(epoch0)!=set(epoch1) or 0 not in epoch0 or len(epoch0)<3:
        raise ValueError('two identical nonempty grids including baseline required')
    if not all(math.isfinite(v) and v>=0 for e in (epoch0,epoch1) for v in e.values()):
        raise ValueError('invalid cycle value')
    grid=sorted(n for n in epoch0 if n)
    deltas=[[e[n]-e[0] for n in grid] for e in (epoch0,epoch1)]
    bands=[[1 if d>1 else -1 if d < -1 else 0 for d in ds] for ds in deltas]
    out={'threshold_cycles':1.0,'status':'ambiguous','interval':None,'grid':grid,'deltas':deltas}
    if any(v<0 for b in bands for v in b):
        out['reason']='negative departure'; return out
    if bands[0]!=bands[1]:
        out['reason']='process epochs disagree'; return out
    band=bands[0]
    if 1 not in band:
        out['status']='no-departure-observed'; return out
    i=band.index(1)
    if any(v==0 for v in band[i:]):
        out['reason']='return below threshold'; return out
    if i==len(grid)-1:
        out['status']='right-edge-unconfirmed'; return out
    if i==0:
        out['status']='left-grid-insufficient'; return out
    out['status']='confirmed-response'; out['interval']=[grid[i-1],grid[i]]
    return out


def tlb_stats(run, target):
    """Five mapping epochs; average two correlated seeds within each epoch."""
    if run['mode'] not in ('tlb','tlb-confirm100') or target!=run.get('tlb_target',200):
        raise ValueError('TLB target/run mismatch')
    rows=run['rows']; main=[r for r in rows if r['w']]
    epochs={f'epoch-{e}' for e in range(5)}
    expected={(e,seed,f,rotate,h,w) for e in epochs for seed in (42,137) for f in (128,512)
              for rotate in (False,True) for h in (1,2) for w in (8,9)}
    actual=[(r['epoch'],r['seed'],r['f'],r['offset_rotate'],r['h'],r['w']) for r in main]
    floors=[(r['epoch'],r['seed'],r['f'],r['block']) for r in rows if r['w']==0]
    expected_floors={(e,seed,f,b) for e in epochs for seed in (42,137) for f in (128,512) for b in (0,3)}
    if len(rows)!=200 or len(actual)!=160 or set(actual)!=expected or len(floors)!=40 or set(floors)!=expected_floors:
        raise ValueError('TLB epoch/cell coverage mismatch')
    paired=[]
    for epoch in sorted({r['epoch'] for r in main}):
        for seed in (42,137):
            for f in (128,512):
                for rotate in (False,True):
                    cell={(r['h'],r['w']):r['counts_mean'][4] for r in main
                          if (r['epoch'],r['seed'],r['f'],r['offset_rotate'])==(epoch,seed,f,rotate)}
                    if set(cell)!={(1,8),(1,9),(2,8),(2,9)}: raise ValueError('incomplete TLB contrast')
                    paired.append({'epoch':epoch,'seed':seed,'f':f,'offset_rotate':rotate,
                                   'did':cell[1,9]-cell[1,8]-cell[2,9]+cell[2,8]})
    summary=[]
    for f in (128,512):
        for rotate in (False,True):
            values=[st.mean(r['did'] for r in paired if r['epoch']==e and r['f']==f and r['offset_rotate']==rotate)
                    for e in sorted({r['epoch'] for r in paired})]
            summary.append({'f':f,'offset_rotate':rotate,'epoch_values':values,
                            'mean':st.mean(values),'median':st.median(values),'range':[min(values),max(values)]})
    observations=[v for r in rows for v in r['observations']]
    overall=[st.mean(r['did'] for r in paired if r['epoch']==e) for e in sorted(epochs)]
    return {'tlb_target':target,'paired':paired,'summary':summary,'overall_epoch_values':overall,
            'did_positive':sum(r['did']>0 for r in paired),'did_count':len(paired),
            'did_range':[min(r['did'] for r in paired),max(r['did'] for r in paired)],
            'retained_floor_datawalk_max':max(v[4] for r in rows if r['w']==0 for v in r['observations'][1:]),
            'retained_iwalk_max':max(v[5] for r in rows for v in r['observations'][1:]),
            'all_windows_l2_equals_data_plus_instruction':all(v[2]==v[4]+v[5] for v in observations),
            'c9_mean_max':max(r['counts_mean'][4] for r in main if (r['h'],r['w'])==(2,9)),
            'a8_mean_range':[min(r['counts_mean'][4] for r in main if (r['h'],r['w'])==(1,8)),
                             max(r['counts_mean'][4] for r in main if (r['h'],r['w'])==(1,8))]}


def rob_stats(run):
    """Keep class, chain, true alignment and process identity separate."""
    from tools.diagnostic.run_sm8650_minimal import conditions
    registered=conditions('rob-fine')
    def field(opts,key): return opts[opts.index(key)+1]
    expected={(int(name[1]),field(opts,'-t'),field(opts,'-a'),int(field(opts,'--chain')),
               int(field(opts,'--align')),int(field(opts,'-n'))) for name,opts in registered}
    actual={(r['epoch'],r['class'],r['anchor'],r['chain'],r['loop_mod64'],r['n']) for r in run['rows']}
    if actual!=expected or len(run['rows'])!=len(registered) or run['processes']!=len(registered):
        raise ValueError('ROB registered matrix mismatch')
    metadata={(r['iterations'],r['chase_seed']) for r in run['rows']}
    if metadata!={(131072,42)}: raise ValueError('ROB iterations/seed mismatch')
    for r in run['rows']:
        if len(r['cycles_per_iteration'])!=3 or not all(math.isfinite(v) and v>=0 for v in r['cycles_per_iteration']):
            raise ValueError('ROB invalid round values')
    groups=defaultdict(dict)
    for r in run['rows']:
        key=(r['class'],r['anchor'],r['chain'],r['loop_mod64'])
        ident=(r['epoch'],r['n'])
        if ident in groups[key]: raise ValueError('duplicate ROB identity')
        groups[key][ident]=r
    curves=[]
    for (cls,anchor,k,align),cells in sorted(groups.items()):
        epochs=[{n:st.median(r['cycles_per_iteration']) for (e,n),r in cells.items() if e==epoch} for epoch in (0,1)]
        if set(epochs[0])!=set(epochs[1]): raise ValueError('ROB epoch grid mismatch')
        curve={'class':cls,'anchor':anchor,'chain':k,'loop_mod64':align,
               'iterations':131072,'chase_seed':42,'points':[]}
        for n in sorted(epochs[0]):
            point={'n':n,'epoch_medians':[e[n] for e in epochs],
                   'range_all_rounds':[min(v for e in (0,1) for v in cells[e,n]['cycles_per_iteration']),
                                       max(v for e in (0,1) for v in cells[e,n]['cycles_per_iteration'])],
                   'delta_from_n0':[e[n]-e[0] for e in epochs]}
            if anchor=='fsqrt':
                none=groups[cls,'none',8,align]
                reference=[max(epochs[e][0],st.median(none[e,n]['cycles_per_iteration'])) for e in (0,1)]
                point['full_overlap_reference']=reference
                point['excess_over_reference']=[epochs[e][n]-reference[e] for e in (0,1)]
            curve['points'].append(point)
        if cls=='nop' and anchor=='fsqrt': curve['response']=first_departure(*epochs)
        curves.append(curve)
    return {'curves':curves,'processes':run['processes'],
            'rounds':sum(len(r['cycles_per_iteration']) for r in run['rows']),
            'max_retired_relative_error':max(v for r in run['rows'] for v in r['retired_relative_error'])}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('summary',type=Path);p.add_argument('--previous',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); new=json.loads(args.summary.read_text()); old=json.loads(args.previous.read_text())
    def unique(runs,mode):
        rr=[r for r in runs if r['mode']==mode]
        if len(rr)!=1: raise ValueError('exactly one '+mode+' run required')
        return rr[0]
    current=unique(new['runs'],'tlb-confirm100')
    if current['tlb_target']!=100: raise ValueError('target identity')
    result={'protocol':'docs/design/2026-10-09-local-confirmation.md',
            'inputs':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (args.summary,args.previous)},
            'tlb':[tlb_stats(unique(old['runs'],'tlb'),200),tlb_stats(current,100)],
            'rob':rob_stats(unique(new['runs'],'rob-fine'))}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'tlb':[{k:t[k] for k in ('tlb_target','did_positive','did_range')} for t in result['tlb']],
                      'rob':[{k:c[k] for k in ('chain','loop_mod64','response')} for c in result['rob']['curves'] if 'response' in c]}))

if __name__=='__main__': main()
