#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only RV2-02 round-4 review of production APIs and integer-VA collectors.

Reuses committed v2 planner/adapter/fake-engine and archive/figure checks.
All added curves and records are synthetic software fixtures, never phone data.
Exit 0 means diagnostics ran, not that the reviewed implementation passed.
"""
import argparse
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--tree', type=Path, required=True)
p.add_argument('--main-tree', type=Path, required=True)
p.add_argument('--r2-tree', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
args = p.parse_args()
TREE, MAIN, R2 = (x.resolve() for x in
                  [args.tree, args.main_tree, args.r2_tree])
saved_argv = sys.argv
sys.argv = ['review_rpa_v2_20261007.py', '--tree', str(TREE),
    '--main-tree', str(MAIN), '--r2-tree', str(R2), '--out', str(args.out)]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(str(R2/'scripts/review_rpa_v2_20261007.py'))
sys.argv = saved_argv
r, attempt = ns['r'], ns['attempt']
from analysis import sm8650_tlb_a1 as a1

# v2 checked its then-current registration commit; use the actual review HEAD.
r['golden_ctest_registration'] = {
    'commit': r['heads']['m0b'],
    'committed': 'add_test(NAME tlb_set_collect_golden' in
        ns['git'](TREE, 'show', 'HEAD:tests/CMakeLists.txt'),
    'working_tree': 'add_test(NAME tlb_set_collect_golden' in
        (TREE/'tests/CMakeLists.txt').read_text(),
    'diff': ns['git'](TREE, 'diff', '--', 'tests/CMakeLists.txt'),
}
r['round4_changed_files'] = ns['git'](TREE, 'diff', '--name-only',
                                    '5ccb841..HEAD').splitlines()
r['source_sha256'] = {f: hashlib.sha256((TREE/f).read_bytes()).hexdigest()
    for f in ['analysis/sm8650_tlb_a1.py',
              'analysis/tests/test_sm8650_tlb_a1.py',
              'probes/common/tlb_set_collect.h']}

curves = {
    'stable_sharp': {6: .2, 8: 4., 10: 6.5, 12: 7.},
    'tail_only_37_5pct_of_peak': {6: .2, 8: 8., 10: 3., 12: 3.},
    'tail_below_on_above_floor': {6: .2, 8: 4., 10: 1.5, 12: 1.5},
    'left_censored_all_high': {6: 4., 8: 4., 10: 4., 12: 4.},
    'right_censored_last_point': {6: .1, 8: .2, 10: .5, 12: 4.},
    'only_one_point': {12: 4.},
    'observed_tail_trough_excluded_from_median':
        {6: .2, 8: 8., 10: 1.5, 12: 1.5, 14: 8., 16: 8.},
}
r['a1_onset_counterexamples'] = {name: {'input': c,
    'result': attempt(lambda c=c: a1.classify_onset(c))}
    for name, c in curves.items()}
good = curves['stable_sharp']
r['a1_identical_sharp_all_scopes'] = {str(h): a1.adjudicate_h(
    {-1: good, 0: good, 1: good}, [5, 6, 7, 8], h)
    for h in range(1, 5)}
r['a1_left_censored_h_verdict'] = a1.adjudicate_h(
    {s: curves['left_censored_all_high'] for s in [-1, 0, 1]},
    [5, 6, 7, 8], 1)
r['a1_missing_scope_one'] = a1.adjudicate_h({-1: good, 0: good},
                                                         [5, 6, 7, 8], 1)
r['a1_missing_window_eight'] = a1.adjudicate_h(
    {s: {6: .2, 10: 4., 12: 6.5, 14: 7.} for s in [-1, 0, 1]},
    [5, 6, 7, 8], 1)
r['a1_l3_counterexamples'] = {
    'empty': attempt(lambda: a1.check_l3_consistency({})),
    'one_target': attempt(lambda: a1.check_l3_consistency(
        {7: {'verdict': 'supported'}})),
    'four_targets_different_onsets': attempt(lambda: a1.check_l3_consistency({
        t: {'verdict': 'supported', 'onset': w}
        for t, w in zip([7, 42, 100, 200], [6, 8, 10, 12])})),
}

base = {'status': 'ok', 'params': copy.deepcopy(ns['expected']),
        'probe': {'realized': copy.deepcopy(r['engine_uniform']['value']['realized'])}}
fixtures = {'valid': base}
rec = copy.deepcopy(base); rec['probe']['realized']['set_target_region_nodes'] = [1]*4
fixtures['wrong_node_sum'] = rec
rec = copy.deepcopy(base); rec['probe']['realized']['set_target_region_nodes'] = [2]*4+[0]
fixtures['wrong_node_dimension'] = rec
rec = copy.deepcopy(base); del rec['probe']['realized']['set_region_vpn_hi']
fixtures['missing_actual_high_fields'] = rec
rec = copy.deepcopy(base)
rec['params']['set_region_scope'] = 0
rec['probe']['realized'].update(set_region_scope=0, set_active_regions=1,
    set_target_region_nodes=[8, 0, 0, 0], set_region_vpn_hi_pure=0)
fixtures['isolated_impure'] = rec
rec = copy.deepcopy(base); rec['probe']['realized'] = copy.deepcopy(
    r['engine_mixed']['value']['realized'])
fixtures['mixed_domain'] = rec
r['a1_gate_counterexamples'] = {name: attempt(lambda rec=rec: a1.gate_record(rec))
                               for name, rec in fixtures.items()}

# Use exactly the author's happy-path calibration, then consume a formal curve.
# A temporary in-process constant override is an oracle sensitivity check only.
frozen = a1.freeze_thresholds([0., .2, 0., .4, .2], scatter_mid=0.)
test_curve = {6: .2, 8: 2.5, 10: 2.5, 12: 2.5}
before = a1.ONSET_ON_PER_ROUND
actual = a1.classify_onset(test_curve)
try:
    a1.ONSET_ON_PER_ROUND = frozen['on_threshold']
    with_selected = a1.classify_onset(test_curve)
finally:
    a1.ONSET_ON_PER_ROUND = before
r['a1_threshold_handoff'] = {
    'freeze_result': frozen, 'classifier_constant_after_freeze': before,
    'formal_curve': test_curve, 'actual_result': actual,
    'result_with_selected_threshold_applied_explicitly': with_selected,
}
r['a1_freeze_stop_rules'] = {
    'floor_noisy': a1.freeze_thresholds([0., 5., 0., 8.], 0.),
    'filler_exclusion_broken': a1.freeze_thresholds([0., .1, 0.], 2.),
    'no_grid_value': a1.freeze_thresholds([4., 4.2, 3.8], 0.),
}

# Addresses are integers only; no pointer is dereferenced. The header is production.
harness = r'''
#include "tlb_set_collect.h"
#include <cstdio>
#include <set>
namespace tlc=tlb_set_collect;
void sets(const std::set<unsigned>& ss){
 std::printf("[");bool first=true;for(auto s:ss){std::printf("%s%u",first?"":",",s);first=false;}std::printf("]");}
int main(){
 std::vector<tlc::Region> rs;
 for(int k=0;k<4;k++)rs.push_back({reinterpret_cast<char*>((uintptr_t(5+k)<<28)+uint64_t(k)*8*4096),16384});
 for(int C=1;C<=4;C++){
  std::vector<uintptr_t> vs;std::vector<int> cs(4,0);
  int got=tlc::collect_set_addrs(C,7,12,rs,0,&vs,&cs);
  for(int M=1;M<=4;M++){
   std::set<unsigned> ss;for(auto v:vs)ss.insert(tlc::set_index(M,v));
   std::printf("{\"collector\":%d,\"model\":%d,\"nodes\":%d,\"actual_sets\":",C,M,got);
   sets(ss);std::puts("}");
  }
 }
 uintptr_t b=(uintptr_t(0x5a)<<28)+224ull*1024*1024;
 tlc::Region cross{reinterpret_cast<char*>(b),16384};
 std::vector<uintptr_t> vs;std::vector<int> cs(1,0);
 tlc::collect_set_addrs(1,7,12,{cross},0,&vs,&cs);
 std::set<unsigned> hs,his;
 for(auto v:vs){hs.insert(tlc::set_index(3,v));his.insert((v>>28)&255);}
 std::printf("{\"isolated_crossing\":true,\"actual_hi\":");sets(his);
 std::printf(",\"collector_H1_under_model_H3_sets\":");sets(hs);std::puts("}");
}
'''
with tempfile.TemporaryDirectory(prefix='rpa4-native-') as td:
    t = Path(td); (t/'h.cpp').write_text(harness)
    c = subprocess.run(['clang++', '-std=c++17', '-O2', '-I',
        str(TREE/'probes/common'), str(t/'h.cpp'), '-o', str(t/'h')],
        text=True, capture_output=True)
    r['a1_prediction_compile'] = {'rc': c.returncode, 'stderr': c.stderr}
    if c.returncode:
        raise RuntimeError(c.stderr)
    matrix = [json.loads(line) for line in
              subprocess.check_output([str(t/'h')], text=True).splitlines()]
    rows = []
    for x in matrix:
        if 'collector' not in x:
            continue
        pred = a1.predicted_hw_sets(x['collector'], 7, x['model'], [5, 6, 7, 8])
        rows.append({**x, 'prediction': sorted(pred) if pred is not None else 'multi',
            'matches': set(x['actual_sets']) == pred if pred is not None
                       else len(x['actual_sets']) > 1})
    r['a1_prediction_matrix'] = rows
    r['a1_isolated_crossing'] = matrix[-1]

r['a1_entry_callers'] = []
for root in [TREE/'analysis', TREE/'runner', TREE/'scripts', R2/'scripts']:
    for path in root.rglob('*.py'):
        if 'tests' in path.parts or 'review_' in path.name or path.name == 'sm8650_tlb_a1.py':
            continue
        source = path.read_text()
        if any(token in source for token in ['sm8650_tlb_a1', 'freeze_thresholds',
                'adjudicate_h', 'check_l3_consistency']):
            r['a1_entry_callers'].append(str(path.relative_to(root.parent)))
args.out.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({
    'heads': r['heads'],
    'prediction_pairs_matching': sum(x['matches'] for x in r['a1_prediction_matrix']),
    'prediction_pairs_total': len(r['a1_prediction_matrix']),
    'onset_results': {k: v['result'] for k, v in r['a1_onset_counterexamples'].items()},
    'missing_scope_one': r['a1_missing_scope_one'],
    'l3_results': r['a1_l3_counterexamples'],
    'gate_results': r['a1_gate_counterexamples'],
    'threshold_handoff': r['a1_threshold_handoff'],
    'entry_callers': r['a1_entry_callers'],
    'legacy_runs': len(r['legacy_replay']),
    'legacy_statistics_equal': sum(x['normalized_equal'] for x in r['legacy_replay']),
    'legacy_cohort_equal': sum(x['cohort_equal'] for x in r['legacy_replay']),
    'main_overlay': {k: v for k, v in r['main_overlay'].items() if k != 'log'},
}, ensure_ascii=False, indent=2))
