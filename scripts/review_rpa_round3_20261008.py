#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only round-3 review, using real production collectors and synthetic curves.

Reuses the committed v2 diagnostics for plans/engine/archive/figure overlay.
No adb or phone execution; synthetic values are not microarchitecture evidence.
Exit 0 means diagnostics completed, not review approval.
"""
import argparse
import contextlib
import copy
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
r, attempt, module = ns['r'], ns['attempt'], ns['module']
from analysis import sm8650_tlb_a1 as a1
r['golden_ctest_registration'] = {
    'commit': '5ccb841',
    'committed': 'add_test(NAME tlb_set_collect_golden' in
        ns['git'](TREE, 'show', '5ccb841:tests/CMakeLists.txt'),
    'working_tree': 'add_test(NAME tlb_set_collect_golden' in
        (TREE/'tests/CMakeLists.txt').read_text(),
    'diff': ns['git'](TREE, 'diff', '--', 'tests/CMakeLists.txt'),
}

curves = {
    'stable_sharp': {6: .2, 8: 4., 10: 6.5, 12: 7.},
    'tail_only_37_5pct_of_peak': {6: .2, 8: 8., 10: 3., 12: 3.},
    'tail_below_on_above_floor': {6: .2, 8: 4., 10: 1.5, 12: 1.5},
    'left_censored_all_high': {6: 4., 8: 4., 10: 4., 12: 4.},
    'right_censored_last_point': {6: .1, 8: .2, 10: .5, 12: 4.},
    'only_one_point': {12: 4.},
}
r['a1_onset_counterexamples'] = {name: {'input': c,
    'result': attempt(lambda c=c: a1.classify_onset(c))}
    for name, c in curves.items()}
good = curves['stable_sharp']
r['a1_identical_sharp_all_scopes'] = {str(h): a1.adjudicate_h(
    {-1: good, 0: good, 1: good}, [5, 6, 7, 8], h)
    for h in range(1, 5)}
r['a1_missing_scope_one'] = a1.adjudicate_h({-1: good, 0: good},
                                                         [5, 6, 7, 8], 1)
r['a1_l3_counterexamples'] = {
    'empty': a1.check_l3_consistency({}),
    'one_target': a1.check_l3_consistency({7: {'verdict': 'supported'}}),
    'four_targets_different_onsets': a1.check_l3_consistency({
        t: {'verdict': 'supported', 'onset': w}
        for t, w in zip([7, 42, 100, 200], [6, 8, 10, 12])}),
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

# Addresses are integers only. The header is the exact code used by the probe.
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
  for(int H=1;H<=4;H++){
   std::set<unsigned> ss;for(auto v:vs)ss.insert(tlc::set_index(H,v));
   std::printf("{\"collector\":%d,\"hardware_model\":%d,\"nodes\":%d,\"hw_sets\":",C,H,got);
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
 std::printf(",\"collector_H1_under_hardware_H3_sets\":");sets(hs);std::puts("}");
}
'''
with tempfile.TemporaryDirectory(prefix='rpa3-native-') as td:
    t = Path(td); (t/'h.cpp').write_text(harness)
    c = subprocess.run(['clang++', '-std=c++17', '-O2', '-I',
        str(TREE/'probes/common'), str(t/'h.cpp'), '-o', str(t/'h')],
        text=True, capture_output=True)
    r['a1_prediction_compile'] = {'rc': c.returncode, 'stderr': c.stderr}
    if c.returncode == 0:
        lines = subprocess.check_output([str(t/'h')], text=True).splitlines()
        matrix = [json.loads(line) for line in lines]
        r['a1_production_collector_truth'] = matrix
        r['a1_self_consistency'] = [
            {'collector': x['collector'], 'actual_same_model_sets': x['hw_sets'],
             'consumer_prediction': sorted(a1.predicted_hw_sets(x['collector'],7,[5,6,7,8]))}
            for x in matrix if x.get('collector') == x.get('hardware_model')
            and 'collector' in x]

# Exercise the real archived roster, including combined B/T grading and SVGs.
fig = ns['fig']
oldfig = module('analysis._rpa3_oldfig', MAIN/'analysis/tlb_figures.py',
    ns['git'](MAIN, 'show', '9093f4a:analysis/tlb_figures.py'))
oldfig.analyze_records = ns['old'].analyze_records
oldfig.grade_thp_cohorts = ns['old'].grade_thp_cohorts
artifacts = []
for label, mod in [('old', oldfig), ('new', fig)]:
    scans, thp = mod.load_campaign(TREE/'data/public/runs')
    graded = mod.grade_thp_cohorts(thp)
    audit = {}
    svgs = mod.build_figures(scans, graded, audit=audit)
    report = mod.build_report(graded, skipped_points=audit.get('skipped_points'),
                              claim_support=audit.get('claim_support'))
    artifacts.append((label, {'figures': svgs, 'report': report, 'cohort': graded}))
r['archived_real_render'] = {
    'figure_equal': {name: artifacts[0][1]['figures'][name] == text
                     for name, text in artifacts[1][1]['figures'].items()},
    'report_equal': artifacts[0][1]['report'] == artifacts[1][1]['report'],
    'combined_BT_cohort_equal': artifacts[0][1]['cohort'] == artifacts[1][1]['cohort'],
}
r['a1_entry_callers'] = []
for root in [TREE/'analysis', TREE/'scripts', R2/'scripts']:
    for path in root.rglob('*.py'):
        if 'tests' in path.parts or 'review_' in path.name or path.name == 'sm8650_tlb_a1.py':
            continue
        if 'sm8650_tlb_a1' in path.read_text():
            r['a1_entry_callers'].append(str(path.relative_to(root.parent)))
args.out.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k: v for k, v in r.items() if k.startswith('a1_') or k in
    ['real_plan_warmup_consumers', 'archived_real_render', 'heads']},
    ensure_ascii=False, indent=2))
print('legacy_runs',len(r['legacy_replay']),
      'statistics_equal',sum(x['normalized_equal'] for x in r['legacy_replay']),
      'cohort_equal',sum(x['cohort_equal'] for x in r['legacy_replay']))
