#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only synthetic seam checks and archived replay for M0-4.

Uses existing unit fixtures; these are software inputs, not measurements.
The chart module is loaded from --main with the reviewed analyzer from --tree.
"""
import argparse
import copy
import dataclasses
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types
import tempfile
from unittest.mock import patch


def attempt(fn):
    """Keep a consumer's return or exception as named diagnostic evidence."""
    try:
        value = fn()
        return {'ok': True, 'value': dataclasses.asdict(value) if dataclasses.is_dataclass(value) else value}
    except Exception as e:
        return {'ok': False, 'exception': type(e).__name__, 'message': str(e)}


def main():
    """Exercise seams without target execution; write outcomes to --out."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree', type=Path, required=True)
    p.add_argument('--main', type=Path, required=True)
    p.add_argument('--baseline', default='adaac4d')
    p.add_argument('--out', type=Path, required=True)
    args=p.parse_args()
    sys.path.insert(0,str(args.tree))
    from analysis import sm8650_tlb as analyzer
    from analysis.load import load_run
    from analysis.tests.test_sm8650_tlb import _record
    from runner import plan
    from runner.tests.test_plan import SPEC, PLATFORM
    result={'tree_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.tree,text=True).strip(),
            'main_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.main,text=True).strip()}
    spec=copy.deepcopy(SPEC)
    spec['execution']['sweep']['chains']=[1,2]
    result['chains_sweep']=[{'id':c.id, 'params':{k:rv.value for k,rv in c.params}}
                           for c in plan.build_plan(spec,PLATFORM).cases]
    from runner.adapters.ptr_chase import PtrChaseAdapter
    result['chains_argv']=[{'id':c.id,'chains':dict(c.params)['chains'].value, 'argv':PtrChaseAdapter().build_argv({k:rv.value for k,rv in c.params})} for c in plan.build_plan(spec,PLATFORM).cases]
    spec=copy.deepcopy(SPEC)
    spec['execution']['sweep']['unsupported_dimension']=[1,2]
    unknown=plan.build_plan(spec,PLATFORM)
    result['unsupported_sweep']={'accepted_cases':len(unknown.cases),
        'recorded':any('unsupported_dimension' in dict(c.params) for c in unknown.cases)}
    spec=copy.deepcopy(SPEC)
    spec['parameters']=[{'name':'repetitions','type':'int','default':3}]
    spec['execution']={'probe':'tlb_set','probe_shape':'tlb-set',
                       'sweep':{'ways':[8,9]},'fixed_params':[]}
    platform=copy.deepcopy(PLATFORM)
    platform['probes']['tlb_set']='SYNTHETIC-UNEXECUTED'
    with patch.dict(plan._CASE_DERIVERS,{'tlb-set':lambda params:{'ways':params['ways']}}):
        result['new_shape']=attempt(lambda: plan.build_plan(spec,platform))
    # Supply chase fields only to get past the first generic-shape defect.
    spec=copy.deepcopy(SPEC)
    spec['execution']['probe_shape']='tlb-set'
    spec['execution']['fixed_params'].append('pmu_events')
    spec['execution']['params']={'pmu_events':[{'name':'cycles','type':4,'config':17}]}
    deriver=plan._derive_ptr_chase_case_params
    with patch.dict(plan._CASE_DERIVERS,{'tlb-set':lambda p:{**deriver(p),'ways':plan.ResolvedValue(8,'derived')}}):
        result['generic_shape_pmu']=attempt(lambda: plan.build_plan(spec,PLATFORM))
    for name in ['chart','tlb_figures']:
        sp=importlib.util.spec_from_file_location('analysis.'+name,args.main/'analysis'/f'{name}.py')
        module=importlib.util.module_from_spec(sp)
        sys.modules[sp.name]=module
        sp.loader.exec_module(module)
    figures=sys.modules['analysis.tlb_figures']
    test_spec=importlib.util.spec_from_file_location('analysis.tests._review_figures',args.main/'analysis/tests/test_tlb_figures.py')
    chart_fixtures=importlib.util.module_from_spec(test_spec)
    sys.modules[test_spec.name]=chart_fixtures
    test_spec.loader.exec_module(chart_fixtures)
    with tempfile.TemporaryDirectory(prefix='m0b-chart-gap-') as temporary:
        temp=Path(temporary)
        chart_fixtures._make_dataset(temp/'runs')
        records_path=temp/'runs'/figures.RUN_COARSE/'records.jsonl'
        records=[json.loads(line) for line in records_path.read_text().splitlines()]
        for record in records:
            if record['params']['buffer_kb']==128:
                record['metrics']=[m for m in record['metrics'] if m['name']!='pmu.dtlb_walk.count']
        records_path.write_text(''.join(json.dumps(r)+'\n' for r in records))
        rc,stdout,stderr=chart_fixtures._run_cli(temp/'runs',temp/'out')
        walk=temp/'out/walk-onset.svg'
        result['partial_metric_chart_cli']={'rc':rc,'stderr':stderr,
            'walk_circles':walk.read_text().count('<circle') if walk.exists() else None,
            'expected_complete_walk_circles':20, 'report':(temp/'out/report.md').read_text() if (temp/'out/report.md').exists() else None}
        # Remove the onset region while retaining the maximum endpoint; a partial plot remains.
        for name in (figures.RUN_COARSE,figures.RUN_DENSE):
            rp=temp/'runs'/name/'records.jsonl'
            rs=[json.loads(line) for line in rp.read_text().splitlines()]
            for rec in rs:
                if 4096 <= rec.get('params',{}).get('buffer_kb',0) < 32768:
                    rec['metrics']=[m for m in rec.get('metrics',[]) if m['name']!='pmu.dtlb_walk.count']
            rp.write_text(''.join(json.dumps(r)+'\n' for r in rs))
        rc,stdout,stderr=chart_fixtures._run_cli(temp/'runs',temp/'sparse-out')
        scan,_=figures.load_campaign(temp/'runs')
        audit=[]
        points=figures.curve_from_groups(scan,'dtlb_walk_per_1k',skipped=audit)
        result['removed_walk_onset_region']={'rc':rc,'stderr':stderr,'walk_available_buffers_kb':[p[0] for p in points], 'skipped_points':audit, 'report':(temp/'sparse-out/report.md').read_text() if (temp/'sparse-out/report.md').exists() else None}
    a,b=_record(),_record()
    a['params']['chains']=1
    b['params']['chains']=2
    for metric in b['metrics']:
        if metric['name']=='pmu.cycles.count':
            for observation in metric['observations']:
                observation['value']=100*65536
    analyzed=analyzer.analyze_records([a,b],'SYNTHETIC-identity')
    result['identity_groups']=[{'identity':g['identity'],'cyc_per_load':g['cyc_per_load']['median']}
                               for g in analyzed.groups]
    result['chart_curves']=attempt(lambda:figures.curve_from_groups(analyzed.groups,'cyc_per_load'))
    result['cohort_sample_n']=attempt(lambda:[u['valid_samples'] for c in analyzer.grade_thp_cohorts(analyzed.groups)['cohorts'] for u in c['units']])
    x,y=_record(),_record()
    x['params']['hypothesis']='H1'
    y['params']['hypothesis']='H2'
    result['different_hypotheses_groups']=len(analyzer.analyze_records([x,y],'SYNTHETIC-H').groups)
    x,y=_record(),_record()
    x['params']['chains']=True
    y['params']['chains']=1
    result['bool_integer_chains_groups']=len(analyzer.analyze_records([x,y],'SYNTHETIC-type').groups)
    missing=_record(buffer_kb=128)
    missing['metrics']=[m for m in missing['metrics'] if m['name']!='pmu.l1d_tlb_refill.count']
    r=analyzer.analyze_records([missing],'SYNTHETIC-missing')
    result['inherited_defects']={
        'markdown':attempt(lambda:analyzer.build_markdown([r])),
        'knee_floor':attempt(lambda:analyzer.adjudicate_knee({42:[{
            'pages':32,'cyc_per_load':1,'l1d_tlb_refill_per_1k':None}]})),
        'chart':attempt(lambda:figures.curve_from_groups(r.groups,'l1d_tlb_refill_per_1k')),
    }
    source=subprocess.check_output(['git','show',f'{args.baseline}:analysis/sm8650_tlb.py'],cwd=args.tree,text=True)
    old=types.ModuleType('analysis._review_snapshot')
    old.__file__=str(args.tree/'analysis/sm8650_tlb.py')
    old.__package__='analysis'
    sys.modules[old.__name__]=old
    exec(compile(source,old.__file__,'exec'),old.__dict__)
    registry=analyzer.load_registry(args.tree/'configs/pmu-event-registry.json')
    rows=[]
    for path in sorted((args.tree/'data/public/runs').glob('*ptr-chase-sm8650-x4-tlb*/records.jsonl')):
        run=load_run(path.parent)
        records=run.ok_records+run.failed_records
        old_result=old.analyze_records(records,path.parent.name,registry)
        new_result=analyzer.analyze_records(records,path.parent.name,registry)
        a=dataclasses.asdict(old_result)
        b=dataclasses.asdict(new_result)
        old_cohort=attempt(lambda:old.grade_thp_cohorts(old_result.groups))
        new_cohort=attempt(lambda:analyzer.grade_thp_cohorts(new_result.groups))
        for g in b['groups']:
            if any(v is not None for v in g['identity'].values()):
                raise ValueError('Historical run has nonempty identity; cannot normalize it away')
            del g['identity']
        rows.append({'run':path.parent.name,'records':len(records),'equal_after_removing_empty_identity':a==b, 'cohort_outcome_equal':old_cohort==new_cohort})
    result['replay']=rows
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('chains_sweep','replay','partial_metric_chart_cli','removed_walk_onset_region')},ensure_ascii=False,indent=2))
    print('historical replay:',len(rows),'equal:',sum(x['equal_after_removing_empty_identity'] for x in rows))


if __name__=='__main__':
    main()
