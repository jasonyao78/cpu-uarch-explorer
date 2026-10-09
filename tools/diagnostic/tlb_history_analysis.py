#!/usr/bin/env python3
"""Strict, address-free audit and preregistered TLB-history estimands.

Contract: docs/design/2026-10-09-tlb-history-discrimination.md. Raw acceptance
uses the saved production ``tlb_history --plan`` output, not a row-count-only
matrix. The caller separately binds that plan, binary, source and environment
evidence. Synthetic tests are software evidence, never device observations.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics as st

PROTOCOL = 'docs/design/2026-10-09-tlb-history-discrimination.md'
EVENTS = ['0x11', '0x05', '0x2d', '0x2f', '0x34', '0x35']
META = ('cell', 'position', 'kind', 'h', 'w', 'f', 'history', 'direction',
        'victim', 'block', 'rounds')
CONFIG_FIELDS = ('version', 'target', 'seed', 'max_w', 'old_prefix',
                 'offset_rotate', 'link_slots', 'reverse')
SAMPLE_FIELDS = ('round', 'trial_position', 'victim', 'enabled', 'running', 'counts')


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _int(value):
    return type(value) is int


def _equal(actual, expected):
    return type(actual) is type(expected) and actual == expected


def _config(reverse):
    return dict(type='config', version=1, target=100, seed=137, max_w=12,
                old_prefix=9, offset_rotate=True, link_slots=4, reverse=reverse,
                cells=38, windows=800)


def _check_config(config, reverse):
    expected = _config(reverse)
    _require(isinstance(config, dict) and set(config)==set(expected) and
             all(_equal(config[k], v) for k, v in expected.items()),
             'history config differs from the frozen protocol')


def _cell_id(cell):
    if cell['kind']==0:
        return f"floor-b{cell['block']}-f{cell['f']}"
    prefix = 'trace' if cell['kind']==1 else 'victim'
    return (f"{prefix}-h{cell['h']}-w{cell['w']}-f{cell['f']}"
            f"-hist{cell['history']}-d{cell['direction']}")


def _check_cells(cells):
    """Validate semantic coverage too, so a damaged plan is not authoritative."""
    expected = {(0,1,0,f,0,0,b,16) for f in (0,128,512) for b in (0,1)}
    expected |= {(1,h,w,128,hist,d,0,16) for h in (1,2) for w in (8,9)
                 for hist in (6,12) for d in (0,1)}
    expected |= {(1,h,w,512,12,d,0,16) for h in (1,2) for w in (8,9) for d in (0,1)}
    expected |= {(1,h,w,0,12,0,0,16) for h in (1,2) for w in (8,12)}
    expected |= {(2,h,8,128,hist,0,0,64) for h in (1,2) for hist in (6,12)}
    _require(isinstance(cells, list) and len(cells)==38, 'history cell count')
    identities, positions, names = [], [], []
    for cell in cells:
        _require(isinstance(cell, dict) and all(k in cell for k in META), 'incomplete cell metadata')
        _require(all(_int(cell[k]) for k in META if k!='cell'), 'noninteger cell metadata')
        _require(cell['victim']==-1 and cell['cell']==_cell_id(cell), 'cell name/metadata mismatch')
        identities.append(tuple(cell[k] for k in ('kind','h','w','f','history','direction','block','rounds')))
        positions.append(cell['position']); names.append(cell['cell'])
    _require(set(identities)==expected and len(set(identities))==38 and
             set(positions)==set(range(38)) and len(set(names))==38,
             'history semantic cell coverage or duplicates')


def _index(h, address):
    vpn = address >> 12
    return (vpn if h==1 else vpn ^ (vpn >> 8)) & 255


def _collect(base, pages, h, need):
    """Independent replay of the one-region production collector contract.

    Source: probes/common/tlb_set_collect.h::collect_set_addrs. Replaying need=9
    and need=12 distinguishes preserved old prefixes from a changed collector.
    No address from this check is returned to public evidence or exceptions.
    """
    result = []
    bucket = max(1, pages//need)
    for page in range(1, pages):
        if page < len(result)*bucket:
            continue
        address = base + 4096*page
        if _index(h, address)==100:
            result.append(address)
            if len(result)==need:
                break
    _require(len(result)==need, 'target collector cannot realize frozen geometry')
    return result


def _check_geometry(geometry):
    _require(isinstance(geometry, dict) and geometry.get('type')=='geometry', 'missing geometry')
    _require(_equal(geometry.get('target'),100) and _equal(geometry.get('pool_pages'),65536),
             'geometry target/pool mismatch')
    base = geometry.get('pool_base')
    _require(_int(base) and base>0 and base%4096==0, 'invalid pool base')
    targets, filler = geometry.get('target_pages'), geometry.get('filler_pages')
    _require(isinstance(targets,list) and len(targets)==2, 'target family count')
    for h, pages in enumerate(targets, 1):
        _require(isinstance(pages,list) and len(pages)==12 and
                 all(_int(v) and v%4096==0 and base<=v<base+65536*4096 for v in pages) and
                 len(set(pages))==12, 'target page shape/range')
        _require(all(_index(h,v)==100 for v in pages) and
                 len({_index(3-h,v) for v in pages})==12, 'target candidate signatures')
        old = _collect(base,65536,h,9)
        expected = old[:]
        used = {_index(3-h,v) for v in old}
        for v in _collect(base,65536,h,12):
            other = _index(3-h,v)
            if len(expected)<12 and other not in used:
                expected.append(v); used.add(other)
        _require(pages==expected, 'old prefix or appended target geometry differs from production')
    _require(isinstance(filler,list) and len(filler)==512 and
             all(_int(v) and v>0 and v%4096==0 for v in filler) and
             len(set(filler))==512, 'filler page shape')
    _require(all(not base<=v<base+65536*4096 for v in filler) and
             max(filler)-min(filler)<2048*4096, 'filler mapping range')
    for h in (1,2):
        occupied = {_index(h,v) for family in targets for v in family}
        _require(not occupied & {_index(h,v) for v in filler}, 'filler overlaps a target candidate leaf')


def _check_sample(sample, cell, index):
    _require(isinstance(sample,dict) and all(k in sample for k in SAMPLE_FIELDS), 'incomplete sample')
    victim = cell['kind']==2
    expected = dict(round=index//8 if victim else index,
                    trial_position=index%8 if victim else 0,
                    victim=(index//8+index%8)%8 if victim else -1)
    _require(all(_equal(sample[k],v) for k,v in expected.items()), 'round/trial/victim coverage or order')
    _require(_int(sample['enabled']) and sample['enabled']>0 and
             _int(sample['running']) and sample['running']==sample['enabled'],
             'invalid or multiplexed PMU window')
    counts = sample['counts']
    _require(isinstance(counts,list) and len(counts)==6 and
             all(_int(v) and v>=0 for v in counts), 'invalid six-event counts')


def audit_history(rows, reverse, plan):
    """Audit one raw process epoch; return public cells with every window.

    ``plan`` is either the selected JSONL list or {'forward': [...], 'reverse':
    [...]} saved from the production host exporter. The exact raw stream order
    is config, geometry, then each planned cell's before/after backing records
    and buffered round records. No virtual address is copied to the result.
    """
    try:
        _require(type(reverse) is bool, 'reverse must be boolean')
        selected = plan['reverse' if reverse else 'forward'] if isinstance(plan,dict) else plan
        _require(isinstance(selected,list) and len(selected)==39, 'production plan record count')
        _check_config(selected[0],reverse)
        cells = selected[1:]
        _require(all(c.get('type')=='cell' for c in cells), 'plan has a non-cell record')
        _check_cells(cells)
        _require([c['position'] for c in cells]==list(range(38)), 'production plan position order')
        _require(isinstance(rows,list) and len(rows)==878, 'raw record count/coverage')
        _check_config(rows[0],reverse)
        _check_geometry(rows[1])
        cursor, result = 2, []
        for cell in cells:
            for stage in ('before','after'):
                endpoint = rows[cursor]; cursor += 1
                _require(isinstance(endpoint,dict) and endpoint.get('type')=='backing' and
                         endpoint.get('cell')==cell['cell'] and endpoint.get('stage')==stage and
                         _equal(endpoint.get('base_page_bytes'),4096) and
                         _equal(endpoint.get('anon_huge_kb'),0), 'cell backing endpoint mismatch')
            samples = []
            for index in range(cell['rounds']):
                row = rows[cursor]; cursor += 1
                _require(isinstance(row,dict) and row.get('type')=='round', 'missing ordered round')
                _require(all(_equal(row.get(k),cell[k]) for k in META if k not in ('rounds','victim')),
                         'round metadata differs from production cell')
                _check_sample(row,cell,index)
                sample = {k:row[k] for k in SAMPLE_FIELDS}
                sample['counts'] = row['counts'][:]
                samples.append(sample)
            public = {k:cell[k] for k in META}
            public.update({k:rows[0][k] for k in CONFIG_FIELDS})
            public['samples'] = samples
            public['counts_mean'] = [st.mean(s['counts'][i] for s in samples) for i in range(6)]
            result.append(public)
        _require(cursor==len(rows), 'unconsumed raw records')
        return result
    except (KeyError,TypeError,IndexError,AttributeError) as error:
        raise ValueError('malformed history records or production plan') from error


def _points(values):
    return {'values':values, 'step1':values[0], 'step8':values[7],
            'step16':values[15], 'last4':st.mean(values[-4:])}


def _gate(values):
    """The same sign AND per-epoch magnitude must jointly pass in four epochs."""
    positive = sum(v>=1 for v in values)
    negative = sum(v<=-1 for v in values)
    return {'passed':max(positive,negative)>=4,
            'sign':1 if positive>=4 else -1 if negative>=4 else 0,
            'positive_epochs':positive, 'negative_epochs':negative,
            'threshold_abs':1, 'required_epochs':4}


def _contrast(label, epoch_series):
    result = dict(label, epochs=epoch_series)
    result['step_gates'] = {key:_gate([e[key] for e in epoch_series]) for key in ('step1','step8','step16','last4')}
    result['persistent'] = dict(result['step_gates']['last4'])
    fading = [e for e in epoch_series if abs(e['step1'])>=1 and abs(e['last4'])<0.5]
    result['fading'] = {'passed':len(fading)>=4, 'qualifying_epochs':[e['epoch'] for e in fading],
                        'positive_initial_epochs':sum(e['step1']>=1 for e in fading),
                        'negative_initial_epochs':sum(e['step1']<=-1 for e in fading),
                        'initial_abs_at_least':1, 'last4_abs_below':0.5, 'required_epochs':4}
    return result


def analyze(summary):
    """Analyze five audited process epochs without treating windows as replicates.

    Input is the public single-run {'mode':'tlb-history','tlb_target':100,'rows':
    [audited cell + epoch, ...]}. All 4000 windows remain in trajectory/victim
    diagnostics. Count>1 single-load windows are disclosed, not silently clipped.
    """
    try:
        _require(isinstance(summary,dict) and summary.get('mode')=='tlb-history' and
                 _equal(summary.get('tlb_target'),100), 'history run/target identity')
        rows = summary.get('rows')
        _require(isinstance(rows,list) and len(rows)==190, 'five complete history epochs required')
        epochs = [f'epoch-{i}' for i in range(5)]
        _require({c.get('epoch') for c in rows}==set(epochs), 'history epoch coverage')
        lookup, trajectory, floors = {}, [], []
        for number, epoch in enumerate(epochs):
            cells = [c for c in rows if c['epoch']==epoch]
            _check_cells(cells)
            for cell in cells:
                _require(all(_equal(cell.get(k),_config(bool(number%2))[k]) for k in CONFIG_FIELDS),
                         'public cell config/epoch mismatch')
                samples = cell.get('samples')
                _require(isinstance(samples,list) and len(samples)==cell['rounds'], 'public sample coverage')
                for index,sample in enumerate(samples):
                    _check_sample(sample,cell,index)
                if cell['kind']==1:
                    key = (epoch,cell['h'],cell['w'],cell['f'],cell['history'],cell['direction'])
                    _require(key not in lookup, 'duplicate trajectory identity')
                    counts = [s['counts'][:] for s in samples]
                    lookup[key] = [c[4] for c in counts]
                    trajectory.append(dict(epoch=epoch, **{k:cell[k] for k in META},
                                           counts=counts, datawalk=_points(lookup[key]),
                                           l2_access=_points([c[3] for c in counts])))
                elif cell['kind']==0:
                    floors.append(dict(epoch=epoch, f=cell['f'], block=cell['block'], position=cell['position'],
                                       phase='start' if cell['position']<3 else 'end',
                                       counts=[s['counts'][:] for s in samples]))
        trajectory.sort(key=lambda c:(c['epoch'],c['h'],c['w'],c['f'],c['history'],c['direction']))
        floors.sort(key=lambda c:(c['epoch'],c['position']))
        history_did = []
        for w in (8,9):
            for direction in (0,1):
                series = []
                for epoch in epochs:
                    a = [x-y for x,y in zip(lookup[epoch,1,w,128,12,direction],lookup[epoch,1,w,128,6,direction])]
                    c = [x-y for x,y in zip(lookup[epoch,2,w,128,12,direction],lookup[epoch,2,w,128,6,direction])]
                    values = [x-y for x,y in zip(a,c)]
                    series.append(dict(epoch=epoch, **_points(values), family_deltas={'a':a,'c':c}))
                history_did.append(_contrast({'f':128,'w':w,'direction':direction},series))
        direction_did = []
        for f,histories in ((128,(6,12)),(512,(12,))):
            for w in (8,9):
                for history in histories:
                    series = []
                    for epoch in epochs:
                        a = [x-y for x,y in zip(lookup[epoch,1,w,f,history,0],lookup[epoch,1,w,f,history,1])]
                        c = [x-y for x,y in zip(lookup[epoch,2,w,f,history,0],lookup[epoch,2,w,f,history,1])]
                        series.append(dict(epoch=epoch, **_points([x-y for x,y in zip(a,c)]), family_deltas={'a':a,'c':c}))
                    direction_did.append(_contrast({'f':f,'w':w,'history':history},series))
        victim = []
        for cell in sorted((c for c in rows if c['kind']==2),key=lambda c:(c['epoch'],c['h'],c['history'])):
            samples = cell['samples']
            victims = []
            for index in range(8):
                selected = [s for s in samples if s['victim']==index]
                values = [s['counts'][4] for s in selected]
                public = [dict(trial=s['round'], trial_position=s['trial_position'], counts=s['counts'][:],
                               datawalk=s['counts'][4]) for s in selected]
                victims.append({'victim':index, 'samples':public, 'mean_datawalk':st.mean(values),
                                'window_walk_rate':sum(v>0 for v in values)/8,
                                'count_gt1':sum(v>1 for v in values)})
            trial_means = [st.mean(s['counts'][4] for s in samples if s['round']==trial) for trial in range(8)]
            position_means = [st.mean(s['counts'][4] for s in samples if s['trial_position']==position) for position in range(8)]
            mean_sum = sum(v['mean_datawalk'] for v in victims)
            rate_sum = sum(v['window_walk_rate'] for v in victims)
            first = lookup[cell['epoch'],cell['h'],8,128,cell['history'],0][0]
            victim.append(dict(epoch=cell['epoch'], h=cell['h'], history=cell['history'], f=128, w=8,
                               victims=victims, mean_datawalk_sum=mean_sum, walk_rate_sum=rate_sum,
                               trajectory_step1_datawalk=first,
                               whole_circle_minus_mean_sum=first-mean_sum,
                               whole_circle_minus_rate_sum=first-rate_sum,
                               count_gt1=sum(v['count_gt1'] for v in victims),
                               trial_means=trial_means, position_means=position_means,
                               trial_last4_minus_first4=st.mean(trial_means[-4:])-st.mean(trial_means[:4]),
                               datawalk_histogram=dict(sorted(Counter(s['counts'][4] for s in samples).items()))))
        observations = [s['counts'] for c in rows for s in c['samples']]
        return {'protocol':PROTOCOL, 'events':EVENTS, 'epoch_unit':'mapping process', 'epochs':epochs,
                'windows':len(observations), 'history_did':history_did, 'direction_did':direction_did,
                'trajectory':trajectory, 'victim':victim, 'floor':floors,
                'victim_interpretation':'single-load window walk rates; repeated preparation, not independent resets or certified residency probabilities',
                'diagnostics':{'floor_datawalk_max':max(c[4] for floor in floors for c in floor['counts']),
                               'iwalk_max':max(c[5] for c in observations),
                               'single_load_count_gt1':sum(c['count_gt1'] for c in victim),
                               'all_windows_l2_equals_data_plus_instruction':all(c[2]==c[4]+c[5] for c in observations)}}
    except (KeyError,TypeError,IndexError,AttributeError) as error:
        raise ValueError('malformed public history summary') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    source = args.summary.read_bytes()
    summary = json.loads(source)
    if 'runs' in summary:
        runs = [run for run in summary['runs'] if run.get('mode')=='tlb-history']
        _require(len(runs)==1, 'exactly one history run required')
        summary = runs[0]
    result = analyze(summary)
    result['input_sha256'] = hashlib.sha256(source).hexdigest()
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'epochs':len(result['epochs']), 'windows':result['windows'],
                      'diagnostics':result['diagnostics']}))


if __name__=='__main__':
    main()
