#!/usr/bin/env python3
"""Address-free audit and frozen local-working-set/victim response estimands.

Protocol: docs/design/2026-10-09-tlb-local-capacity.md. Production --plan owns
raw identities/order; source, build, environment and manifest binding belongs
to summarize_sm8650_minimal.py. Windows are retained, not independent replicas.
"""
from collections import Counter
import statistics as st
from tools.diagnostic.tlb_history_analysis import (
    CONFIG_FIELDS, SAMPLE_FIELDS, _check_geometry, _equal, _int, _require,
)

PROTOCOL = 'docs/design/2026-10-09-tlb-local-capacity.md'
EVENTS = ['0x11','0x05','0x2d','0x2f','0x34','0x35']
META = ('cell','position','kind','h','w','f','history','direction','k','victim','block','rounds')


def _config(reverse):
    return dict(type='config',version=1,target=100,seed=137,max_w=12,old_prefix=9,
                offset_rotate=True,link_slots=5,reverse=reverse,cells=94,windows=2080)


def _check_config(value,reverse):
    expected = _config(reverse)
    _require(isinstance(value,dict) and set(value)==set(expected) and
             all(_equal(value[k],v) for k,v in expected.items()), 'capacity config mismatch')


def _cell_id(cell):
    if cell['kind']==0: return f"floor-b{cell['block']}-f{cell['f']}"
    prefix = 'trace' if cell['kind']==1 else 'victim'
    name = (f"{prefix}-h{cell['h']}-w{cell['w']}-f{cell['f']}"
            f"-hist{cell['history']}-d{cell['direction']}")
    return name+f"-k{cell['k']}" if cell['kind']==2 else name


def _check_cells(cells):
    """Reject damaged plans/public tables as well as incomplete raw streams."""
    fields = ('kind','h','w','f','history','direction','k','victim','block','rounds')
    expected = {(0,1,0,f,0,0,0,-1,b,16) for f in (0,128,512) for b in (0,1)}
    expected |= {(1,h,w,128,12,d,0,-1,0,32) for h in (1,2) for w in range(6,13) for d in (0,1)}
    expected |= {(1,h,w,512,12,0,0,-1,0,32) for h in (1,2) for w in (7,8,9,10)}
    expected |= {(1,h,w,0,12,0,0,-1,0,16) for h in (1,2) for w in (8,12)}
    expected |= {(2,h,1,128,12,d,k,0,0,16) for h in (1,2) for k in range(12) for d in (0,1)}
    _require(isinstance(cells,list) and len(cells)==94, 'capacity cell count')
    identities,positions,names = [],[],[]
    for cell in cells:
        _require(isinstance(cell,dict) and all(k in cell for k in META), 'incomplete capacity metadata')
        _require(all(_int(cell[k]) for k in META if k!='cell'), 'noninteger capacity metadata')
        _require(cell['cell']==_cell_id(cell), 'capacity cell name/metadata mismatch')
        identities.append(tuple(cell[k] for k in fields)); positions.append(cell['position']); names.append(cell['cell'])
    _require(set(identities)==expected and len(set(identities))==94 and
             set(positions)==set(range(94)) and len(set(names))==94, 'capacity semantic coverage/duplicates')


def _check_sample(sample,cell,index):
    _require(isinstance(sample,dict) and all(k in sample for k in SAMPLE_FIELDS), 'incomplete capacity sample')
    expected = dict(round=index,trial_position=0,victim=0 if cell['kind']==2 else -1)
    _require(all(_equal(sample[k],v) for k,v in expected.items()), 'capacity round/victim/order coverage')
    _require(_int(sample['enabled']) and sample['enabled']>0 and
             _int(sample['running']) and sample['running']==sample['enabled'], 'invalid/multiplexed capacity window')
    _require(isinstance(sample['counts'],list) and len(sample['counts'])==6 and
             all(_int(v) and v>=0 for v in sample['counts']), 'invalid six-event capacity counts')


def audit_capacity(rows,reverse,plan):
    """Audit one process against actual producer plan; export all anonymous samples.

    Stream contract is config, geometry, then each planned cell's before/after
    backing and buffered round rows. Victim samples are sixteen rounds of one
    fixed victim, not history's Latin bundle. VA checks reuse the frozen selector.
    """
    try:
        _require(type(reverse) is bool, 'capacity reverse must be boolean')
        selected = plan['reverse' if reverse else 'forward'] if isinstance(plan,dict) else plan
        _require(isinstance(selected,list) and len(selected)==95, 'capacity production plan count')
        _check_config(selected[0],reverse); cells = selected[1:]
        _require(all(c.get('type')=='cell' for c in cells), 'capacity plan record type')
        _check_cells(cells)
        _require([c['position'] for c in cells]==list(range(94)), 'capacity production position order')
        _require(isinstance(rows,list) and len(rows)==2270, 'capacity raw record count')
        _check_config(rows[0],reverse); _check_geometry(rows[1])
        cursor,result = 2,[]
        for cell in cells:
            for stage in ('before','after'):
                endpoint = rows[cursor]; cursor += 1
                _require(isinstance(endpoint,dict) and endpoint.get('type')=='backing' and
                         endpoint.get('cell')==cell['cell'] and endpoint.get('stage')==stage and
                         _equal(endpoint.get('base_page_bytes'),4096) and _equal(endpoint.get('anon_huge_kb'),0),
                         'capacity backing endpoint mismatch')
            samples = []
            for index in range(cell['rounds']):
                row = rows[cursor]; cursor += 1
                _require(isinstance(row,dict) and row.get('type')=='round' and
                         all(_equal(row.get(k),cell[k]) for k in META if k!='rounds'),
                         'capacity round metadata/physical order mismatch')
                _check_sample(row,cell,index)
                sample = {k:row[k] for k in SAMPLE_FIELDS}; sample['counts'] = row['counts'][:]
                samples.append(sample)
            public = {k:cell[k] for k in META}
            public.update({k:rows[0][k] for k in CONFIG_FIELDS})
            public.update(samples=samples,counts_mean=[st.mean(s['counts'][i] for s in samples) for i in range(6)])
            result.append(public)
        _require(cursor==len(rows), 'unconsumed capacity records')
        return result
    except (KeyError,TypeError,IndexError,AttributeError) as error:
        raise ValueError('malformed capacity raw records or production plan') from error


def _tail(values):
    preceding,last = st.mean(values[-16:-8]),st.mean(values[-8:])
    return dict(values=values,first8=st.mean(values[:8]),preceding8=preceding,last8=last,
                drift=last-preceding)


def _response(points,threshold):
    """Operational threshold interval; censored grids never become bounded success.

    Any crossing followed by a value below threshold is a hard response return.
    Numerical decreases which stay above threshold remain diagnostics only.
    """
    values = [p['difference'] for p in points]; grid = [p['x'] for p in points]
    decreases = [{'from':grid[i-1],'to':grid[i],'delta':values[i]-values[i-1]}
                 for i in range(1,len(grid)) if values[i]<values[i-1]]
    result = dict(status='no-response-observed',interval=None,candidate_interval=None,
                  censor_bound=grid[-1],interval_points=[],issues=[],adjacent_decreases=decreases,
                  threshold_returns=[])
    high = [i for i,v in enumerate(values) if v>=threshold]
    if not high: return result
    first = high[0]
    returns = [grid[i] for i in range(first+1,len(grid)) if values[i]<threshold]
    if first==0:
        result.update(status='left-censored',candidate_interval=[None,grid[0]],censor_bound=grid[0],
                      interval_points=grid[:2])
    elif first==len(grid)-1:
        result.update(status='right-end-unconfirmed',candidate_interval=[grid[first-1],grid[first]],
                      censor_bound=grid[-1],interval_points=grid[-2:])
    else:
        result.update(status='confirmed-response',candidate_interval=[grid[first-1],grid[first]],
                      censor_bound=None,interval_points=grid[first-1:first+2])
    result['threshold_returns'] = returns
    if returns:
        result['issues'].append('nonmonotonic-response-return')
        result['status'] = 'nonmonotonic-response-return'
    return result


def _finish_response(curve,issues):
    curve['issues'] = list(dict.fromkeys(curve['issues']+issues))
    if curve['issues']:
        curve['status'] = curve['issues'][0]; curve['interval'] = None
    elif curve['status'] in ('confirmed-response','left-censored'):
        curve['interval'] = curve['candidate_interval'][:]
    curve['bounded_confirmed'] = curve['status']=='confirmed-response'
    return curve


def _joint(curves):
    """Intersect both orders inside each epoch BEFORE counting matching intervals."""
    records,matched,censored = [],[],[]
    lookup = {(c['epoch'],c['direction']):c for c in curves}
    for epoch in (f'epoch-{i}' for i in range(5)):
        a,b = lookup[epoch,0],lookup[epoch,1]
        valid = a['bounded_confirmed'] and b['bounded_confirmed'] and a['interval']==b['interval']
        records.append(dict(epoch=epoch,statuses=[a['status'],b['status']],
                            intervals=[a['interval'],b['interval']],same_bounded_interval=valid,
                            interval=a['interval'][:] if valid else None))
        if valid: matched.append((epoch,tuple(a['interval'])))
        if a['status']==b['status'] and a['status'] in ('left-censored','right-end-unconfirmed','no-response-observed') and a['censor_bound']==b['censor_bound']:
            censored.append((epoch,a['status'],a['censor_bound']))
    counts = [dict(interval=list(interval),epochs=sum(v==interval for _,v in matched),
                   epoch_names=[e for e,v in matched if v==interval]) for interval in sorted({v for _,v in matched})]
    winners = [c for c in counts if c['epochs']>=4]
    return dict(passed=bool(winners),interval=winners[0]['interval'] if winners else None,required_epochs=4,
                epoch_results=records,interval_counts=counts,
                consistent_censoring=[dict(status=status,bound=bound,epochs=sum(s==status and b==bound for _,s,b in censored))
                                      for status,bound in sorted({(s,b) for _,s,b in censored})],
                status_counts=dict(sorted(Counter(c['status'] for c in curves).items())))


def analyze_capacity(run):
    """Return all windows, local intervals and the frozen joint replication gates.

    Input must be the public single-run auditor table with exactly five process
    epochs. Ratios are single-load-window walk rates, never certified miss
    probabilities; all drift, residual, nonmonotonic and censored cases survive.
    """
    try:
        _require(isinstance(run,dict) and run.get('mode')=='tlb-capacity' and
                 _equal(run.get('tlb_target'),100) and _equal(run.get('processes'),5), 'capacity run identity')
        rows = run.get('rows'); epochs = [f'epoch-{i}' for i in range(5)]
        _require(isinstance(rows,list) and len(rows)==470 and {r.get('epoch') for r in rows}==set(epochs),
                 'five complete capacity epochs required')
        trajectory,victim_cells,floors,lookup = [],[],[],{}
        for number,epoch in enumerate(epochs):
            cells = [c for c in rows if c['epoch']==epoch]; _check_cells(cells)
            for cell in cells:
                _require(all(_equal(cell.get(k),_config(bool(number%2))[k]) for k in CONFIG_FIELDS), 'capacity public config')
                samples = cell.get('samples')
                _require(isinstance(samples,list) and len(samples)==cell['rounds'], 'capacity public sample count')
                for i,sample in enumerate(samples): _check_sample(sample,cell,i)
                counts = [s['counts'][:] for s in samples]
                values = [c[4] for c in counts]
                public = dict(epoch=epoch,**{k:cell[k] for k in META},counts=counts)
                if cell['kind']==1:
                    public.update(datawalk=_tail(values),l1_refill=[c[1] for c in counts],l2_access=[c[3] for c in counts])
                    trajectory.append(public); lookup[epoch,1,cell['h'],cell['f'],cell['direction'],cell['w']] = public
                elif cell['kind']==2:
                    rates = [int(v>0) for v in values]
                    public.update(datawalk=values,mean_datawalk=st.mean(values),window_walk_rate=st.mean(rates),
                                  first8_rate=st.mean(rates[:8]),last8_rate=st.mean(rates[8:]),
                                  rate_drift=st.mean(rates[8:])-st.mean(rates[:8]),count_gt1=sum(v>1 for v in values),
                                  l1_refill=[c[1] for c in counts],l2_access=[c[3] for c in counts])
                    victim_cells.append(public); lookup[epoch,2,cell['h'],128,cell['direction'],cell['k']] = public
                else: floors.append(public)
        trajectory.sort(key=lambda c:(c['epoch'],c['f'],c['direction'],c['w'],c['h']))
        victim_cells.sort(key=lambda c:(c['epoch'],c['direction'],c['k'],c['h']))
        floors.sort(key=lambda c:(c['epoch'],c['position']))
        working,victim_response = [],[]
        for epoch in epochs:
            for f,direction,grid in ((128,0,range(6,13)),(128,1,range(6,13)),(512,0,range(7,11))):
                points = []
                for w in grid:
                    a,c = (lookup[epoch,1,h,f,direction,w]['datawalk'] for h in (1,2))
                    points.append(dict(x=w,a_last8=a['last8'],c_last8=c['last8'],difference=a['last8']-c['last8'],
                                       a_preceding8=a['preceding8'],c_preceding8=c['preceding8'],a_drift=a['drift'],c_drift=c['drift'],
                                       stable=abs(a['drift'])<=.5 and abs(c['drift'])<=.5))
                curve = _response(points,1); used = set(curve['interval_points'])
                stable = all(p['stable'] for p in points if p['x'] in used) if used else None
                curve.update(epoch=epoch,f=f,direction=direction,points=points,threshold=1,
                             all_points_stable=all(p['stable'] for p in points),interval_points_stable=stable)
                working.append(_finish_response(curve,['preparation-drift'] if stable is False else []))
            for direction in (0,1):
                points = []
                for k in range(12):
                    a,c = (lookup[epoch,2,h,128,direction,k] for h in (1,2))
                    points.append(dict(x=k,a_rate=a['window_walk_rate'],c_rate=c['window_walk_rate'],
                                       difference=a['window_walk_rate']-c['window_walk_rate'],
                                       a_mean=a['mean_datawalk'],c_mean=c['mean_datawalk'],
                                       a_drift=a['rate_drift'],c_drift=c['rate_drift'],
                                       a_count_gt1=a['count_gt1'],c_count_gt1=c['count_gt1']))
                issues = []
                if points[0]['a_rate']>.125 or points[0]['c_rate']>.125: issues.append('baseline-contamination')
                if any(abs(p['a_drift'])>.25 or abs(p['c_drift'])>.25 for p in points): issues.append('preparation-drift')
                if any(p['a_count_gt1'] or p['c_count_gt1'] for p in points): issues.append('single-load-window-residual')
                curve = _response(points,.5); curve.update(epoch=epoch,f=128,direction=direction,points=points,threshold=.5)
                victim_response.append(_finish_response(curve,issues))
        all_counts = [s['counts'] for c in rows for s in c['samples']]
        def nonzero(event,kind=None):
            return [dict(epoch=c['epoch'],cell=c['cell'],round=s['round'],counts=s['counts'][:])
                    for c in sorted(rows,key=lambda c:(c['epoch'],c['position'])) if kind is None or c['kind']==kind
                    for s in c['samples'] if s['counts'][event]>0]
        return dict(protocol=PROTOCOL,events=EVENTS,epochs=epochs,epoch_unit='mapping process',windows=len(all_counts),
                    trajectory=trajectory,victim_cells=victim_cells,floor=floors,working_set=working,victim_response=victim_response,
                    working_set_joint=_joint([c for c in working if c['f']==128]),victim_joint=_joint(victim_response),
                    thresholds=dict(working_set_difference=1,working_set_drift_max=.5,victim_difference=.5,
                                    victim_baseline_rate_max=.125,victim_drift_max=.25,required_epochs=4),
                    naming_limit='protocol-specific local working-set and victim-response intervals; no physical ways or certified residency probabilities',
                    diagnostics=dict(floor_datawalk_max=max(c[4] for f in floors for c in f['counts']),
                                     floor_nonzero=nonzero(4,0),iwalk_max=max(c[5] for c in all_counts),iwalk_nonzero=nonzero(5),
                                     single_load_count_gt1=sum(c['count_gt1'] for c in victim_cells),
                                     all_windows_l2_equals_data_plus_instruction=all(c[2]==c[4]+c[5] for c in all_counts)))
    except (KeyError,TypeError,IndexError,AttributeError) as error:
        raise ValueError('malformed public capacity summary') from error
