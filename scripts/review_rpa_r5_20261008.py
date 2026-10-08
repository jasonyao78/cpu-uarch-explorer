#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only R5 review: real planner/adapter/engine with a fake executor.

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
    with tempfile.TemporaryDirectory(prefix='r5-fake-runner-') as d:
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
r = {'heads': heads,
     'scope': __doc__,
     'm0b_changed_files_since_round4': git(TREE, 'diff', '--name-only',
                                           'fa663f5..HEAD').splitlines(),
     'source_sha256': {f: hashlib.sha256((TREE/f).read_bytes()).hexdigest()
                      for f in ['analysis/sm8650_tlb_a1.py',
                                'analysis/tests/test_sm8650_tlb_a1.py']}}
platform = json.loads((TREE/'configs/platforms/redmi-k70pro-01.json').read_text())
plans = {}
for layer in ['l1-main', 'l2-repro', 'l3-target']:
    path = TREE/'configs/experiments'/f'ptr-chase-sm8650-x4-tlb-a1-{layer}.json'
    plans[layer] = build_plan(json.loads(path.read_text()), platform)
r['plan_cases'] = {layer: len(plan.cases) for layer, plan in plans.items()}

good = {6: .2, 8: 4., 10: 6.5, 12: 7.}
never = {6: .1, 8: .2, 10: .1, 12: .2}
low_on = {6: .2, 8: 2.5, 10: 2.5, 12: 2.5}
left = {6: 4., 8: 4., 10: 4., 12: 4.}
frozen = a1.freeze_thresholds([0., .2, 0., .4, .2], 0.)
r['frozen'] = frozen
r['left_censor'] = a1.classify_onset(left)
r['left_censor_propagation'] = a1.adjudicate_h(
    {s: left for s in [-1, 0, 1]}, [5, 6, 7, 8], 1)
r['missing_scope'] = attempt(lambda: a1.adjudicate_h(
    {-1: good, 0: good}, [5, 6, 7, 8], 1))
r['l3'] = {
    'empty': attempt(lambda: a1.check_l3_consistency({})),
    'one': attempt(lambda: a1.check_l3_consistency({7: {'verdict': 'supported'}})),
    'wrong_four_targets': attempt(lambda: a1.check_l3_consistency(
        {t: {'verdict': 'supported'} for t in [7, 42, 100, 201]})),
    'correct_four_targets': attempt(lambda: a1.check_l3_consistency(
        {t: {'verdict': 'supported'} for t in [7, 42, 100, 200]})),
}
r['stop_rejected'] = attempt(lambda: a1.run_a1_adjudication(
    [], {'frozen': False, 'stop': 'floor-noisy'}))
r['empty_records'] = attempt(lambda: a1.run_a1_adjudication([], frozen))

fixtures = {}
for layer, plan in plans.items():
    curve = never if layer == 'l2-repro' else good
    fixtures[layer] = [make_record(case, curve, layer) for case in plan.cases]
r['fake_runner_summary'] = {
    'records': sum(len(records) for records in fixtures.values()),
    'process_observations': sum(record['metrics'][0]['repetitions']
        for records in fixtures.values() for record in records),
    'all_status_ok': all(record['status'] == 'ok'
        for records in fixtures.values() for record in records),
    'note': 'L1 is sharp, L2 replication deliberately never on, L3 control is high',
}
r['l1_only_without_l2_l3'] = a1.run_a1_adjudication(fixtures['l1-main'], frozen)
forward = fixtures['l1-main']+fixtures['l2-repro']+fixtures['l3-target']
reordered = fixtures['l2-repro']+fixtures['l1-main']+fixtures['l3-target']
with mock.patch.object(a1, 'check_l3_consistency', wraps=a1.check_l3_consistency) as l3_spy:
    r['full128_forward'] = a1.run_a1_adjudication(forward, frozen)
    r['full128_l3_call_count'] = l3_spy.call_count
r['full128_reordered'] = a1.run_a1_adjudication(reordered, frozen)

h1_cases = [c for c in plans['l1-main'].cases if c.param_value('set_hypothesis') == 1]
threshold_records = [make_record(c, low_on, 'threshold') for c in h1_cases]
with mock.patch.object(a1, 'classify_onset', wraps=a1.classify_onset) as spy:
    r['threshold_pipeline'] = a1.run_a1_adjudication(threshold_records, frozen)
    r['threshold_pipeline_classifier_kwargs'] = [call.kwargs for call in spy.call_args_list]
r['direct_classify_selected_two'] = a1.classify_onset(low_on, on_threshold=2.)
r['direct_classify_three'] = a1.classify_onset(low_on, on_threshold=3.)
one_sample = [make_record(c, good, 'one-sample', repetitions=1) for c in h1_cases]
r['under_sampled_one_process_per_case'] = a1.run_a1_adjudication(one_sample, frozen)

base = fixtures['l1-main'][0]
audit_inputs = {}
rec = copy.deepcopy(base); rec['probe']['realized']['set_target_region_nodes'] = [1]*4
audit_inputs['wrong_sum'] = rec
rec = copy.deepcopy(base); rec['probe']['realized']['set_target_region_nodes'] = [1, 1, 1, 3, 0]
audit_inputs['wrong_dimension'] = rec
rec = copy.deepcopy(base); rec['probe']['realized'].pop('set_region_vpn_hi')
audit_inputs['missing_actual_hi'] = rec
r['audit_gates'] = {name: attempt(lambda rec=rec: a1.gate_record(rec))
                    for name, rec in audit_inputs.items()}
r['task_diff_since_round4'] = git(R2, 'diff', '24a919c..HEAD', '--',
                                'docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md')
r['prior_requirement_lines'] = (R2/'docs/reviews/2026-10-08-rpa-round3-review.md').read_text().splitlines()[75:79]
args.out.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n')


def verdicts(result):
    return {h: x['verdict'] for h, x in result['per_hypothesis'].items()}


print(json.dumps({
    'heads': heads, 'plans': r['plan_cases'], 'fake_runner': r['fake_runner_summary'],
    'left_censor': r['left_censor'], 'left_propagation': r['left_censor_propagation']['verdict'],
    'missing_scope': r['missing_scope'], 'l3': r['l3'],
    'freeze': frozen, 'threshold_pipeline': verdicts(r['threshold_pipeline']),
    'threshold_pipeline_classifier_kwargs': r['threshold_pipeline_classifier_kwargs'],
    'direct_selected_two': r['direct_classify_selected_two'],
    'direct_three': r['direct_classify_three'],
    'l1_only': verdicts(r['l1_only_without_l2_l3']),
    'full128_forward': verdicts(r['full128_forward']),
    'full128_reordered': verdicts(r['full128_reordered']),
    'full128_l3_call_count': r['full128_l3_call_count'],
    'one_process_per_case': verdicts(r['under_sampled_one_process_per_case']),
    'audit_gates': r['audit_gates'],
    'task_changed': bool(r['task_diff_since_round4']),
}, ensure_ascii=False, indent=2))
