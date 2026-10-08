#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only R6 review: real planner/adapter/engine with a fake executor.

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
from runner.artifacts import ArtifactStore
from runner.engine import _run_case
from runner.executor.local import ExecutionResult
from runner.plan import build_plan
from runner.tests.test_engine_fields import PROBE_META, SYSINFO


def git(root, *argv):
    return subprocess.check_output(['git', *argv], cwd=root, text=True).strip()


def attempt(fn):
    try:
        return {'ok': True, 'value': fn()}
    except Exception as error:
        return {'ok': False, 'exception': type(error).__name__,
                'message': str(error)}


class FakeExecutor:
    def __init__(self, stdout):
        self.stdout = stdout
        self.calls = 0

    def execute(self, argv, command_prefix=()):
        self.calls += 1
        return ExecutionResult(0, self.stdout, '', 'SYNTHETIC-UNEXECUTED')

    def freq_snapshot(self, cpu_hint):
        return None


def make_record(case, curve, layer, repetitions=None):
    """Preserve actual plan parameters/control; shorten only the synthetic raw ID.

    A deliberately under-sampled fixture overrides repetitions explicitly and
    is kept separate from the 128-case/1280-process canonical plan fixture.
    """
    params = {k: v.value for k, v in case.params}
    h, scope, window = (params[k] for k in
                        ['set_hypothesis', 'set_region_scope', 'set_window'])
    case = dataclasses.replace(case,
        id=f'SYNTHETIC:{layer}:h{h}:s{scope}:w{window}:t{params["set_target"]}',
        repetitions=case.repetitions if repetitions is None else repetitions)
    regions = params['set_regions']
    if scope < 0:
        nodes = [window//regions]*regions
        nodes[-1] += window-sum(nodes)
    else:
        nodes = [0]*regions
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
        fields[f'pmu_{label}_count'] = str(curve[window] if
            label == 'l2d_tlb_refill' else 1000.0 if label == 'cycles' else window)
        fields[f'pmu_{label}_valid_rounds'] = '20'
    executor = FakeExecutor(' '.join(f'{k}={v}' for k, v in fields.items()))
    with tempfile.TemporaryDirectory(prefix='r6-fake-runner-') as d:
        record = _run_case(case,
            {'target': {'target_id': 'synthetic-01', 'transport': 'local'}},
            PROBE_META, '/SYNTHETIC-UNEXECUTED', executor,
            ArtifactStore(Path(d)/'run'), SYSINFO, PROBE_META['git'])
    if record['status'] != 'ok':
        raise RuntimeError(record.get('failure'))
    assert executor.calls == case.repetitions
    return record



heads = {name: git(root, 'rev-parse', 'HEAD')
         for name, root in [('m0b', TREE), ('r2', R2), ('main', MAIN)]}
r = {'heads': heads, 'scope': __doc__,
     'source_sha256': {f: hashlib.sha256((TREE/f).read_bytes()).hexdigest()
                      for f in ['analysis/sm8650_tlb_a1.py',
                                'analysis/tests/test_sm8650_tlb_a1.py']}}
platform = json.loads((TREE/'configs/platforms/redmi-k70pro-01.json').read_text())
plans = {}
for layer in ['l1-main', 'l2-repro', 'l3-target']:
    path = TREE/'configs/experiments'/f'ptr-chase-sm8650-x4-tlb-a1-{layer}.json'
    plans[layer] = build_plan(json.loads(path.read_text()), platform)
r['plan_cases'] = {layer: len(plan.cases) for layer, plan in plans.items()}
plan_identities = {layer: {json.dumps({k:v.value for k,v in case.params},sort_keys=True)
    for case in plan.cases} for layer,plan in plans.items()}
r['identical_params_overlap_l1_l3'] = len(plan_identities['l1-main'] & plan_identities['l3-target'])
good = {6: .2, 8: 4., 10: 6.5, 12: 7.}
low_on = {6: .2, 8: 2.5, 10: 2.5, 12: 2.5}
frozen = a1.freeze_thresholds([0., .2, 0., .4, .2], 0.)
r['frozen'] = frozen
fixtures = {layer: [make_record(c, good, layer) for c in plan.cases]
            for layer, plan in plans.items()}
full = fixtures['l1-main']+fixtures['l2-repro']+fixtures['l3-target']
r['fake_runner_summary'] = {
    'records': len(full),
    'process_observations': sum(rec['metrics'][0]['repetitions'] for rec in full),
    'all_status_ok': all(rec['status']=='ok' for rec in full),
    'set_target_present_by_layer': {layer: sum('set_target' in rec['params']
        for rec in recs) for layer, recs in fixtures.items()},
}
import random
shuffled = full.copy(); random.Random(7).shuffle(shuffled)
with mock.patch.object(a1, 'classify_onset', wraps=a1.classify_onset) as cls_spy, \
     mock.patch.object(a1, 'check_l3_consistency', wraps=a1.check_l3_consistency) as l3_spy:
    r['actual_128_forward'] = attempt(lambda: a1.run_a1_adjudication(full, frozen))
    r['actual_128_classifier_calls'] = cls_spy.call_count
    r['actual_128_l3_calls'] = l3_spy.call_count
r['actual_128_shuffled'] = attempt(lambda: a1.run_a1_adjudication(shuffled, frozen))

# Component closure: prove that on is now transmitted, independently of routing.
with mock.patch.object(a1, 'classify_onset', wraps=a1.classify_onset) as spy:
    r['threshold_two'] = a1.adjudicate_h(
        {s: low_on for s in [-1,0,1]}, [5,6,7,8], 1, on_threshold=2.)
    r['threshold_three'] = a1.adjudicate_h(
        {s: low_on for s in [-1,0,1]}, [5,6,7,8], 1, on_threshold=3.)
    r['threshold_classifier_kwargs'] = [c.kwargs for c in spy.call_args_list]

# These fixtures are the author's own test shape, not production runner records.
from analysis.tests.test_sm8650_tlb_a1 import TestFullChain
owner = TestFullChain()._l1_l2()
r['owner_fixture_shape'] = {
    'records': len(owner),
    'set_target_present': sum('set_target' in rec['params'] for rec in owner),
    'hypotheses': sorted({rec['params']['set_hypothesis'] for rec in owner}),
    'seeds': sorted({rec['params']['seed'] for rec in owner}),
    'notes': 'handmade author test fixture: not a production record positive oracle',
}
with mock.patch.object(a1, 'classify_onset', wraps=a1.classify_onset) as spy:
    r['owner_no_l3'] = a1.run_a1_adjudication(owner, frozen)
    r['owner_classifier_kwargs'] = [c.kwargs for c in spy.call_args_list]
owner_shuffled = copy.deepcopy(owner); random.Random(7).shuffle(owner_shuffled)
owner_shuffled_result = a1.run_a1_adjudication(owner_shuffled, frozen)
r['owner_24_permutation_equal'] = (owner_shuffled_result == r['owner_no_l3'])
r['owner_24_unsorted_json_byte_equal'] = (json.dumps(owner_shuffled_result) == json.dumps(r['owner_no_l3']))

l3_low = [make_record(c, {8:.1,12:.1}, 'l3-low')
          for c in plans['l3-target'].cases if c.param_value('set_hypothesis')==1]
r['owner_plus_all_negative_l3'] = a1.run_a1_adjudication(owner+l3_low, frozen)
r['l3_two_point_labels'] = {name: a1.classify_onset(curve, on_threshold=2.)
    for name,curve in {'low_high':{8:.1,12:4.},'high_high':{8:4.,12:7.},
                       'low_low':{8:.1,12:.1}}.items()}
r['l3_wrong_four_targets'] = attempt(lambda: a1.check_l3_consistency(
    {t:{'verdict':'supported'} for t in [7,42,100,201]}))

noisy = copy.deepcopy(owner)
for rec in noisy:
    if rec['params']['seed']==1337 and rec['params']['set_window']>=8:
        rec['metrics'][0]['value'] += .1
r['owner_same_onset_different_platform'] = a1.run_a1_adjudication(noisy, frozen)
scoped = {}
for rec in noisy:
    sd=rec['params']['seed']; sc=rec['params']['set_region_scope']; w=rec['params']['set_window']
    scoped.setdefault(sd,{}).setdefault(sc,{})[w]=rec['metrics'][0]['value']
r['l2_same_onset_classes'] = {str(sd): {str(sc): a1.classify_onset(c,on_threshold=2.)
    for sc,c in scopes.items()} for sd,scopes in scoped.items()}

# Coverage/identity negatives in the same author fixture representation.
missing_w = [rec for rec in owner if rec['params']['set_window']!=6]
r['missing_window'] = attempt(lambda: a1.run_a1_adjudication(missing_w,frozen))
duplicate = copy.deepcopy(owner[0]); duplicate['metrics'][0]['value']=4.
r['duplicate_first'] = a1.run_a1_adjudication([duplicate]+owner,frozen)
r['duplicate_last'] = a1.run_a1_adjudication(owner+[duplicate],frozen)
r['empty_records'] = attempt(lambda: a1.run_a1_adjudication([],frozen))
base = fixtures['l1-main'][0]
audit = {}
rec = copy.deepcopy(base); rec['probe']['realized']['set_target_region_nodes']=[1]*4
audit['wrong_sum']=rec
rec = copy.deepcopy(base); rec['probe']['realized']['set_target_region_nodes']=[1,1,1,3,0]
audit['wrong_dimension']=rec
rec = copy.deepcopy(base); rec['probe']['realized'].pop('set_region_vpn_hi')
audit['missing_actual_hi']=rec
r['audit_gates'] = {k: attempt(lambda rec=rec:a1.gate_record(rec)) for k,rec in audit.items()}
r['task_diff_since_r5'] = git(R2,'diff','e11ad84..HEAD','--',
    'docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md')
args.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({
    'heads':heads,'plans':r['plan_cases'],'runner':r['fake_runner_summary'],
    'actual_128':r['actual_128_forward'],'actual_shuffled':r['actual_128_shuffled'],
    'threshold_two':r['threshold_two']['verdict'],
    'threshold_three':r['threshold_three']['verdict'],
    'threshold_classifier_kwargs':r['threshold_classifier_kwargs'],
    'author_fixture':r['owner_fixture_shape'],
    'owner_no_l3':r['owner_no_l3'],
    'owner_plus_all_negative_l3':r['owner_plus_all_negative_l3'],
    'owner_same_onset_different_platform':r['owner_same_onset_different_platform'],
    'duplicate_first_h_star':r['duplicate_first']['h_star'],
    'duplicate_last_h_star':r['duplicate_last']['h_star'],
    'l3_two_point_labels':r['l3_two_point_labels'],
    'l3_wrong_four_targets':r['l3_wrong_four_targets'],
},ensure_ascii=False,indent=2))
