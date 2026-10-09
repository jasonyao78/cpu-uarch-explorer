#!/usr/bin/env python3
"""Audit complete standalone epochs and export anonymous derived evidence."""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import json
import statistics as st
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.diagnostic.run_sm8650_minimal import conditions, validate_realized, OLD_PROTOCOL, binary_name, NEW_EVIDENCE, NEW_PROTOCOL, QUALIFICATION_MODES, THP_QUALIFICATION_MODES


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def require_registered_evidence(manifest):
    """New protocols require their committed build path; legacy optionality stays legacy."""
    mode=manifest['mode']
    if mode in NEW_EVIDENCE:
        expected='docs/reviews/evidence/'+NEW_EVIDENCE[mode]+'/build.json'
        assert manifest.get('build_evidence_path')==expected, 'required registered build path'
        assert manifest.get('protocol_path')==NEW_PROTOCOL[mode], 'required registered protocol path'


def validate_backing(config, runtime, rounds):
    """New binary's actual backing must flow through every initial/pre/post record."""
    requested=config['backing_requested']
    assert requested in ('4k','thp2m')
    huge=requested=='thp2m'; kb=config['memory_bytes']//1024
    assert runtime['backing_verified'] is True and runtime['backing_page_bytes']==(2097152 if huge else 4096)
    assert runtime['mapping_4k_verified'] is (not huge)
    def backing(info):
        assert all(type(info[k]) is int for k in ('rss_kb','swap_kb','anon_huge_kb','kernel_page_kb','mmu_page_kb'))
        assert info['rss_kb']==kb and info['swap_kb']==0
        assert info['anon_huge_kb']==(kb if huge else 0)
        assert info['no_huge'] is (not huge)
        assert info['kernel_page_kb'] in ((4,2048) if huge else (4,))
        assert info['mmu_page_kb'] in ((4,2048) if huge else (4,))
    backing(runtime['backing_info'])
    for row in rounds:
        assert row['backing_verified'] is True
        backing(row['backing_before']);backing(row['backing_after'])


def validate_collapse(config, rows):
    """Require exactly one successful local collapse BEFORE runtime/PMU records.

    Protocol: docs/design/2026-10-09-local-collapse-qualification.md. This
    validates observation flow; actual full backing remains a separate gate.
    """
    records=[r for r in rows if r.get('type')=='backing-collapse']
    requested=config.get('collapse_requested',False)
    assert type(requested) is bool
    if not requested:
        assert not records
        return
    assert config['backing_requested']=='thp2m' and len(records)==1
    assert len(rows)>2 and rows[0]==config and rows[1]==records[0] and rows[2]['type']=='runtime'
    c=records[0]; kb=config['memory_bytes']//1024
    assert type(c['memory_bytes']) is int and c['memory_bytes']==config['memory_bytes']
    assert type(c['pmd_bytes']) is int and c['pmd_bytes']==2097152
    assert type(c['return_code']) is int and c['return_code']==0
    assert type(c['errno']) is int and c['errno']==0
    assert c['before_status'] in ('verified','coverage-mismatch') and c['after_status']=='verified'
    for key in ('before','after'):
        info=c[key]
        assert all(type(info[k]) is int for k in ('rss_kb','swap_kb','anon_huge_kb','kernel_page_kb','mmu_page_kb'))
        assert info['rss_kb']==kb and info['swap_kb']==0 and info['no_huge'] is False
        assert 0<=info['anon_huge_kb']<=kb and info['anon_huge_kb']%2048==0
        assert info['kernel_page_kb'] in (4,2048) and info['mmu_page_kb'] in (4,2048)
    assert (c['before']['anon_huge_kb']==kb)==(c['before_status']=='verified')
    assert c['after']['anon_huge_kb']==kb and c['after']==rows[2]['backing_info']


def summarize(path):
    m=json.loads((path/'manifest.json').read_text())
    require_registered_evidence(m)
    assert m['status']=='complete' and len(m['results'])==len(m['conditions'])
    registered=[{'name':n,'args':a} for n,a in conditions(m['mode'])]
    assert m['conditions']==registered, 'conditions differ from registered matrix'
    assert sorted(r['name'] for r in m['results'])==sorted(c['name'] for c in registered), 'result coverage'
    assert sha(path/'driver.py')==m['driver_sha256']
    root=Path(__file__).resolve().parents[2]
    driver=subprocess.check_output(['git','show',m['source_head']+':tools/diagnostic/run_sm8650_minimal.py'],cwd=root)
    assert hashlib.sha256(driver).hexdigest()==m['driver_sha256'], 'driver not launch commit'
    protocol=subprocess.check_output(['git','show',m['source_head']+':'+m.get('protocol_path',OLD_PROTOCOL)],cwd=root)
    assert hashlib.sha256(protocol).hexdigest()==m['protocol_sha256']
    if 'build_evidence_path' in m:
        build_blob=subprocess.check_output(['git','show',m['source_head']+':'+m['build_evidence_path']],cwd=root)
        assert hashlib.sha256(build_blob).hexdigest()==m['build_evidence_sha256']
        build=json.loads(build_blob)
        assert build['binaries'][binary_name(m['mode'])]==m['binary_sha256'] and build['source_commit']==m['binary_source_head']
        for rel,digest in build['source_sha256'].items():
            if m['mode'] in NEW_EVIDENCE:
                assert hashlib.sha256(subprocess.check_output(['git','show',m['binary_source_head']+':'+rel],cwd=root)).hexdigest()==digest
            assert hashlib.sha256(subprocess.check_output(['git','show',m['source_head']+':'+rel],cwd=root)).hexdigest()==digest
    if m['mode'].startswith('tlb'):
        assert m.get('tlb_target',int(registered[0]['args'][0]))==int(registered[0]['args'][0]), 'manifest target'
    history_plan=None
    if m['mode'] in ('tlb-history','tlb-capacity'):
        assert m['plan_path']==build['plan_path']
        plan_blob=subprocess.check_output(['git','show',m['source_head']+':'+m['plan_path']],cwd=root)
        assert hashlib.sha256(plan_blob).hexdigest()==m['plan_sha256']==build['plan_sha256']
        history_plan=json.loads(plan_blob)
    expected_envs={'initial-environment.json','final-environment.json'}
    expected_envs|={entry['name']+'-'+suffix+'-environment.json' for entry in m['results'] for suffix in ('pre','post')}
    assert {env.name for env in path.glob('*-environment.json')}==expected_envs
    envs=[]
    for env in path.glob('*-environment.json'):
        e=json.loads(env.read_text()); assert not e['violations'] and not e['warnings']; envs.append(e['snapshot'])
    if m['mode'] in NEW_EVIDENCE:
        from tools.diagnostic.analyze_long_load import audit_environment
        profile=json.loads(subprocess.check_output(['git','show',m['source_head']+':configs/platforms/redmi-k70pro-01.json'],cwd=root))
        policy=profile['environment_profiles']['charging-thermal']['measurement_environment']
        policy['preconditions']['cpufreq_governor']='walt'
        saved=json.loads((path/'environment-policy.json').read_text())
        audit_environment({p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')},saved,policy)
    result={'mode':m['mode'],'source_branch':m['source_branch'],'source_head':m['source_head'],
            'binary_sha256':m['binary_sha256'],'manifest_sha256':sha(path/'manifest.json'),
            'raw_directory':path.name,'processes':len(m['results']),'rows':[],
            'max_cpu_c_range':[min(e['thermal']['max_cpu_c'] for e in envs),max(e['thermal']['max_cpu_c'] for e in envs)],
            'wall_seconds':sum(e['wall_seconds'] for e in m['results'])}
    if m['mode'] in NEW_EVIDENCE or m['mode'] in ('tlb-confirm100','rob-fine','rob-miss-qualify'):
        result.update({k:m[k] for k in ('binary_source_head','build_evidence_sha256','driver_sha256','protocol_path','protocol_sha256')})
        if m['mode'].startswith('tlb'): result['tlb_target']=m['tlb_target']
    for entry in sorted(m['results'],key=lambda e:next(i for i,c in enumerate(registered) if c['name']==e['name'])):
        raw=path/(entry['name']+'.stdout.jsonl')
        assert entry['exit_code']==0 and not entry['timed_out'] and sha(raw)==entry['stdout_sha256']
        rows=[json.loads(line) for line in raw.read_text().splitlines()]
        assert not any(r['type']=='failure' for r in rows)
        opts=next(c['args'] for c in registered if c['name']==entry['name'])
        validate_realized(m['mode'],opts,rows)
        rounds=[r for r in rows if r['type']=='round']
        assert all(r['enabled']>0 and r['enabled']==r['running'] for r in rounds)
        if m['mode'] in ('tlb-history','tlb-capacity'):
            if m['mode']=='tlb-capacity':
                from tools.diagnostic.tlb_capacity_analysis import audit_capacity as cell_audit
            else:
                from tools.diagnostic.tlb_history_analysis import audit_history as cell_audit
            reverse='--reverse' in opts
            cells=cell_audit(rows,reverse,history_plan['reverse' if reverse else 'forward'])
            for cell in cells: result['rows'].append({'epoch':entry['name'],**cell})
        elif m['mode'].startswith('tlb'):
            geometry=next(r for r in rows if r['type']=='geometry')
            ts=geometry['target_pages']; filler=geometry['filler_pages']
            def index(h,va):
                vpn=va>>12
                return (vpn if h==1 else vpn^(vpn>>8))&255
            assert len(filler)==len(set(filler))==512
            for h,pages in enumerate(ts,1):
                assert len(pages)==len(set(pages))==9 and all(v%4096==0 for v in pages)
                assert all(index(h,v)==geometry['target'] for v in pages)
                assert len({index(3-h,v) for v in pages})==9
                for th in (1,2): assert not ({index(th,v) for v in pages}&{index(th,v) for v in filler})
            orders=[r for r in rows if r['type']=='filler_order']
            assert len(orders)==2 and {r['seed'] for r in orders}=={42,137}
            assert all(len(r['addresses'])==512 and set(r['addresses'])==set(filler) for r in orders)
            endpoints=[r for r in rows if r['type']=='backing']
            assert len(endpoints)==80 and all(e['base_page_bytes']==4096 and e['anon_huge_kb']==0 for e in endpoints)
            assert sum(e['stage']=='before' for e in endpoints)==40
            groups=defaultdict(list)
            for r in rounds: groups[(r['seed'],r['f'],r['offset_rotate'],r['h'],r['w'],r['block'])].append(r)
            assert len(rounds)==800 and len(groups)==40
            opts=next(c['args'] for c in m['conditions'] if c['name']==entry['name'])
            reverse='--reverse' in opts
            expected_keys={(seed,f,False,1,0,b) for seed in (42,137) for f in (128,512) for b in (0,3)}
            expected_keys|={(seed,f,(b==1 if reverse else b==2),h,w,b) for seed in (42,137) for f in (128,512) for b in (1,2) for h in (1,2) for w in (8,9)}
            assert set(groups)==expected_keys
            for key,rr in sorted(groups.items()):
                seed,f,rotate,h,w,block=key
                assert sorted(r['round'] for r in rr)==list(range(20))
                assert all(r['retained']==(r['round']>0) for r in rr)
                rr.sort(key=lambda r:r['round'])
                kept=[r for r in rr if r['retained']]
                values=[st.mean(r['counts'][i] for r in kept) for i in range(6)]
                result['rows'].append({'epoch':entry['name'],'seed':seed,'f':f,'offset_rotate':rotate,
                                      'h':h,'w':w,'block':block,'counts_mean':values,
                                      'observations':[r['counts'] for r in rr]})
        else:
            config=next(r for r in rows if r['type']=='config')
            runtime=next(r for r in rows if r['type']=='runtime')
            if m['mode']=='rob-collapse-qualify': validate_collapse(config,rows)
            assert runtime['cpu']==7 and runtime['fpcr']==0 and runtime['loop_address_mod64']==config['loop_mod64']
            if config['anchor']=='miss':
                if m['mode'] in THP_QUALIFICATION_MODES: validate_backing(config,runtime,rounds)
                else: assert runtime['mapping_4k_verified']
            if m['mode'] in QUALIFICATION_MODES:
                assert runtime['distinct_lines_per_call']==runtime['ring_nodes']==config['memory_bytes']//64
            assert len(rounds)==(6 if config['paired'] else 3)
            for generated in entry['generated_code'].values():
                assert generated['sha256'] in [sha(p) for p in path.glob(entry['name']+'-*.bin')]
            for serial in sorted({r['serial'] for r in rounds}):
                rr=sorted((r for r in rounds if r['serial']==serial),key=lambda r:r['round'])
                assert [r['round'] for r in rr]==list(range(3))
                expected=config['iterations']*config['loop_instructions']+config['loop_offset']//4+1
                assert all(abs(r['metrics']['0x8']-expected)<=max(1000,0.01*expected) for r in rr)
                result['rows'].append({'condition':entry['name'],'class':config['class'],'anchor':config['anchor'],
                                      'n':config['n'],'chain':config['chain'],'serial':serial,
                                      'memory_bytes':config['memory_bytes'],'code_bytes':config['code_bytes'],
                                      'cycles_per_iteration':[r['metrics']['0x11']/config['iterations'] for r in rr],
                                      'ns_per_iteration':[r['ns']/config['iterations'] for r in rr],
                                      'counts_per_iteration':{k:[r['metrics'][k]/config['iterations'] for r in rr] for k in rr[0]['metrics']},
                                      'retired_relative_error':[abs(r['metrics']['0x8']-expected)/expected for r in rr],
                                      'generated_code_sha256':{k:v['sha256'] for k,v in entry['generated_code'].items()}})
                if m['mode']=='rob-collapse-qualify':
                    result['rows'][-1]['collapse_requested']=config.get('collapse_requested',False)
                if m['mode']=='rob-fine' or m['mode'] in QUALIFICATION_MODES:
                    result['rows'][-1].update({'loop_mod64':config['loop_mod64'],'iterations':config['iterations'],
                                               'chase_seed':config['chase_seed'],'epoch':int(entry['name'][1])})
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('runs',nargs='+',type=Path); p.add_argument('--output',required=True,type=Path)
    a=p.parse_args(); data={'runs':[summarize(path) for path in a.runs]}
    a.output.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({r['mode']:{'processes':r['processes'],'derived_rows':len(r['rows']),'max_cpu_c':r['max_cpu_c_range']} for r in data['runs']}))

if __name__=='__main__': main()
