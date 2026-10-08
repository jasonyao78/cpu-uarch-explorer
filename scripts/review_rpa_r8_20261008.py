#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only R8 review: real planner/adapter/engine with a fake executor.

Every metric is synthetic. No binary, adb, phone, or perf is executed. Temporary
raw fixtures are deleted; only diagnostic summaries are saved. Exit 0 denotes
completed diagnostics, never approval of the implementation under review.
"""
import argparse
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import mock


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--tree', type=Path, required=True)
p.add_argument('--r2-tree', type=Path, required=True)
p.add_argument('--main-tree', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
args = p.parse_args()
TREE, R2, MAIN = (x.resolve() for x in
                  [args.tree, args.r2_tree, args.main_tree])
sys.path.insert(0, str(TREE))
from analysis import sm8650_tlb_a1 as a1
from runner.adapters.ptr_chase import PtrChaseAdapter
from runner.executor.local import ExecutionResult
from runner.plan import build_plan
from runner.tests.test_engine_fields import SYSINFO


def git(root, *argv):
    return subprocess.check_output(['git', *argv], cwd=root, text=True).strip()


def attempt(fn):
    try:
        return {'ok': True, 'value': fn()}
    except Exception as error:
        return {'ok': False, 'exception': type(error).__name__,
                'message': str(error)}


import contextlib
import io
import random
from analysis.load import load_run
from runner import engine


def stdout_for(case, curve):
    """Synthetic probe output: keep every actual requested parameter/event."""
    params = {k: v.value for k, v in case.params}
    scope, window, regions = (params[k] for k in
        ['set_region_scope', 'set_window', 'set_regions'])
    if scope < 0:
        nodes = [window // regions] * regions
        nodes[-1] += window - sum(nodes)
    else:
        nodes = [0] * regions
        nodes[scope] = window
    fields = {out: str(params[param])
              for out, param in PtrChaseAdapter._TLB_SET_DESCRIPTOR_MAP
              if param in params}
    fields.update(mode='tlbset', page_kb='4', scatter='0',
        set_domain='multi-region', set_active_regions=str(sum(n > 0 for n in nodes)),
        set_target_region_nodes=','.join(map(str, nodes)),
        set_region_vpn_hi='5,6,7,8', set_region_vpn_hi_pure='1',
        window_valid_rounds='20', window_invalid_rounds='0', window_mux_rounds='0',
        valid_rounds='20', probe_ns='1000')
    for event in params['pmu_events']:
        label = event['name']
        fields[f'pmu_{label}_count'] = str((curve[window] if params['set_hypothesis']==1 else .2) if
            label == 'l2d_tlb_refill' else 1000.0 if label == 'cycles' else window)
        fields[f'pmu_{label}_valid_rounds'] = '20'
    return ' '.join(f'{k}={v}' for k, v in fields.items())


class QueueExecutor:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0
    def execute(self, argv, command_prefix=()):
        self.calls += 1
        return ExecutionResult(0, next(self.outputs), '', 'SYNTHETIC-UNEXECUTED')
    def system_info(self):
        return SYSINFO
    def freq_snapshot(self, cpu_hint):
        return None


def persist_and_load(plan, curve, layer):
    """Actual run_plan/_run_case/adapter/writer/loader; fake external execution.

    Only external transport/system collection, binary registration and Git
    provenance are mocked. Case IDs are shortened solely for temporary paths.
    Manifest and records are neither patched nor enriched here.
    """
    cases = tuple(dataclasses.replace(c, id=f'SYNTHETIC-{layer}-{i}')
                  for i, c in enumerate(plan.cases))
    plan = dataclasses.replace(plan, cases=cases)
    executor = QueueExecutor([stdout_for(c, curve) for c in cases
                             for _ in range(c.repetitions)])
    platform = {'target': {'target_id': 'synthetic-01', 'transport': 'local'}}
    with tempfile.TemporaryDirectory(prefix='r8-fake-runner-') as d, \
         mock.patch.object(engine, 'make_executor', return_value=executor), \
         mock.patch.object(engine, '_register_probe',
            return_value=('/SYNTHETIC-UNEXECUTED', {'sha256': 'f'*64})), \
         mock.patch.object(engine, 'git_provenance',
            return_value={'commit': '0'*40, 'dirty': False}), \
         contextlib.redirect_stdout(io.StringIO()):
        summary = engine.run_plan(plan, platform, Path(d)/'run', TREE)
        loaded = load_run(Path(d)/'run')
        assert summary['ok'] == len(cases), summary
        assert executor.calls == sum(c.repetitions for c in cases)
        assert not loaded.failed_records
        return loaded.manifest, loaded.ok_records, executor.calls


heads = {name: git(root, 'rev-parse', 'HEAD')
         for name, root in [('m0b', TREE), ('r2', R2), ('main', MAIN)]}
files = ['analysis/sm8650_tlb_a1.py', 'analysis/tests/test_sm8650_tlb_a1.py',
         'analysis/load.py', 'runner/engine.py', 'runner/schema/README.md'] + [
         f'configs/experiments/ptr-chase-sm8650-x4-tlb-a1-{layer}.json'
         for layer in ['l1-main', 'l2-repro', 'l3-target']]
r = {'heads':heads, 'scope':__doc__,
     'source_sha256':{f:hashlib.sha256((TREE/f).read_bytes()).hexdigest() for f in files},
     'commit_changed_files':git(TREE,'diff','--name-only','6756d00..0840b6e').splitlines(),
     'r2_changed_files':git(R2,'diff','--name-only','50ddb17..e02cc3d').splitlines()}
platform = json.loads((TREE/'configs/platforms/redmi-k70pro-01.json').read_text())
plans = {layer:build_plan(json.loads((TREE/'configs/experiments'/
    f'ptr-chase-sm8650-x4-tlb-a1-{layer}.json').read_text()),platform)
    for layer in ['l1-main','l2-repro','l3-target']}
r['plan_cases'] = {layer:len(plan.cases) for layer,plan in plans.items()}
r['plan_windows'] = {layer:sorted({c.param_value('set_window') for c in plan.cases})
                     for layer,plan in plans.items()}
frozen = a1.freeze_thresholds([0.,.2,0.,.4,.2],0.)
r['frozen'] = frozen
good={6:.2,8:4.,10:6.5,12:7.}
fixtures,manifests,calls={},{},{}
for layer,plan in plans.items():
    manifests[layer],fixtures[layer],calls[layer]=persist_and_load(plan,good,layer)
full=[rec for records in fixtures.values() for rec in records]
r['real_pipeline_summary']={
    'records':len(full),'process_observations':sum(calls.values()),
    'all_status_ok':all(rec['status']=='ok' for rec in full),
    'manifest_experiment_id':{layer:m['experiment_id'] for layer,m in manifests.items()},
    'record_experiment_id_present_by_layer':{layer:sum('experiment_id' in rec
        for rec in records) for layer,records in fixtures.items()},
    'all_existing_gates_pass':all(a1.gate_record(rec)[0] for rec in full),
    'synthetic_response_model':'H1 sharp on L1/L2; other H flat below floor',
}
r['persisted_loaded_128']=attempt(lambda:a1.run_a1_adjudication(full,frozen))

# Diagnostic ONLY: manually supply manifest provenance to isolate L3 changes.
enriched=[]
for layer,records in fixtures.items():
    for rec in records:
        rec=copy.deepcopy(rec);rec['experiment_id']=manifests[layer]['experiment_id']
        enriched.append(rec)
r['diagnostic_only_manifest_enriched_128']=a1.run_a1_adjudication(enriched,frozen)
shuffled=copy.deepcopy(enriched);random.Random(7).shuffle(shuffled)
shuffled_out=a1.run_a1_adjudication(shuffled,frozen)
r['diagnostic_only_128_permutation_equal']=(shuffled_out==r['diagnostic_only_manifest_enriched_128'])
r['diagnostic_only_128_canonical_json_equal']=(json.dumps(shuffled_out,sort_keys=True)==
    json.dumps(r['diagnostic_only_manifest_enriched_128'],sort_keys=True))
r['two_point_truth_table']={name:a1.classify_l3_two_point(c,2.) for name,c in {
    'below_below':{8:.1,12:.1},'below_above':{8:.1,12:4.},
    'above_above':{8:4.,12:7.},'above_below':{8:4.,12:.1}}.items()}

def change_l3(records, action):
    records=copy.deepcopy(records)
    for rec in records:
        if 'a1-l3' in rec['experiment_id'] and rec['params']['set_hypothesis']==1:
            action(rec)
    return records
def set_l2refill(rec, value):
    metric = next(m for m in rec['metrics'] if m['name']=='pmu.l2d_tlb_refill.count')
    metric['value'] = value

all_low=change_l3(enriched,lambda rec:set_l2refill(rec,.3))
r['diagnostic_only_l3_all_low']=a1.run_a1_adjudication(all_low,frozen)
one_bad=change_l3(enriched,lambda rec:set_l2refill(rec,.3)
                  if rec['params']['set_target']==200 else None)
r['diagnostic_only_l3_one_bad_target']=a1.run_a1_adjudication(one_bad,frozen)
missing=[rec for rec in enriched if not ('a1-l3' in rec['experiment_id']
    and rec['params']['set_hypothesis']==1 and rec['params']['set_target']==200)]
r['diagnostic_only_l3_missing_target']=attempt(lambda:a1.run_a1_adjudication(missing,frozen))
# Previously required exact coverage: produce protocol-valid records from
# neighboring plans, changing parameters BEFORE adapter/runner execution.
def alter_l3_plan(param, remap):
    plan = plans['l3-target']
    cases = []
    for case in plan.cases:
        params = tuple((k, dataclasses.replace(rv, value=remap.get(rv.value,rv.value)))
                       if k==param else (k,rv) for k,rv in case.params)
        cases.append(dataclasses.replace(case,params=params))
    return dataclasses.replace(plan,cases=tuple(cases))

coverage_inputs = {}
for label,param,remap,curve in [
    ('wrong_fourth_target','set_target',{200:201},good),
    ('wrong_two_windows','set_window',{8:100,12:200},{100:4.,200:7.})]:
    manifest, records, count = persist_and_load(alter_l3_plan(param,remap),curve,label)
    assert all(rec['status']=='ok' for rec in records)
    for rec in records:
        rec['experiment_id'] = manifest['experiment_id']  # diagnostic-only bridge
    l1_l2 = [rec for rec in enriched if 'a1-l3' not in rec['experiment_id']]
    r['diagnostic_only_'+label] = a1.run_a1_adjudication(l1_l2+records,frozen)
    coverage_inputs[label] = {'l3_records':len(records),'fake_calls':count,
        'all_status_ok':True,
        'targets':sorted({rec['params']['set_target'] for rec in records}),
        'windows':sorted({rec['params']['set_window'] for rec in records})}
r['neighboring_plan_coverage_inputs'] = coverage_inputs

# Owner's new test: count actual producer calls rather than trusting its name.
from analysis.tests.test_sm8650_tlb_a1 import TestProductionChain,TestFullChain
with tempfile.TemporaryDirectory(prefix='r8-owner-fixture-') as d, \
     mock.patch.object(engine,'run_plan',wraps=engine.run_plan) as run_spy, \
     mock.patch.object(engine,'_run_case',wraps=engine._run_case) as case_spy:
    with contextlib.chdir(TREE):
        owner=TestProductionChain()._build(d)
    r['owner_128_fixture_summary']={
        'records':len(owner),'run_plan_calls':run_spy.call_count,
        '_run_case_calls':case_spy.call_count,
        'experiment_id_present':sum('experiment_id' in rec for rec in owner),
        'region_nodes_sum_differs_from_requested_window':sum(
            sum(rec['probe']['realized']['set_target_region_nodes'])!=rec['params']['set_window']
            for rec in owner),
    }
r['owner_128_positive']=a1.run_a1_adjudication(owner,{'frozen':True,'on_threshold':3.})
owner_shuffled=copy.deepcopy(owner);random.Random(3).shuffle(owner_shuffled)
r['owner_128_full_result_permutation_equal']=(r['owner_128_positive']==
    a1.run_a1_adjudication(owner_shuffled,{'frozen':True,'on_threshold':3.}))
r['old_handmade_fixture_records']=len(TestFullChain()._l1_l2()+TestFullChain()._l3())
r['task_diff_since_r7_review']=git(R2,'diff','50ddb17..e02cc3d','--',
    'docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md')
args.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
summary={k:r[k] for k in ['heads','commit_changed_files','r2_changed_files',
 'plan_cases','plan_windows','real_pipeline_summary','persisted_loaded_128',
 'owner_128_fixture_summary','two_point_truth_table',
 'diagnostic_only_128_permutation_equal','owner_128_full_result_permutation_equal']}
for k in ['diagnostic_only_manifest_enriched_128','diagnostic_only_l3_all_low',
 'diagnostic_only_l3_one_bad_target','diagnostic_only_wrong_fourth_target',
 'diagnostic_only_wrong_two_windows','owner_128_positive']:
    v=r[k];summary[k]={x:v[x] for x in ['n_records','h_star','h_star_status']}
    summary[k]['h1']={x:v['per_hypothesis'][1][x] for x in ['verdict','reproducible','l3_pass']}
summary['diagnostic_only_l3_missing_target']=r['diagnostic_only_l3_missing_target']
print(json.dumps(summary,ensure_ascii=False,indent=2))
