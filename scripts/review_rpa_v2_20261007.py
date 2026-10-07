#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only RPA v2 review: production header, real plans, synthetic consumers.

No adb or target-device execution. Synthetic metric values are fixtures, never
hardware evidence. Exit zero means diagnostics ran, not review approval.
"""
import argparse
import contextlib
import copy
import dataclasses
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
import unittest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tree', type=Path, required=True)
parser.add_argument('--main-tree', type=Path, required=True)
parser.add_argument('--r2-tree', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
TREE, MAIN, R2 = (p.resolve() for p in
                  (args.tree, args.main_tree, args.r2_tree))
sys.path.insert(0, str(TREE))
from analysis import sm8650_tlb as a
from analysis.load import load_run
from analysis.tests.test_sm8650_tlb import _record
from runner.adapters.ptr_chase import PtrChaseAdapter
from runner.engine import _run_case
from runner.executor.local import ExecutionResult
from runner.artifacts import ArtifactStore
from runner.plan import Case, Control, build_plan
from runner.resolve import ResolvedValue
from runner.tests.test_engine_fields import PROBE_META, SYSINFO
from runner.tests.test_plan import PASS_SPEC, PLATFORM

def attempt(fn):
    try:
        return {'ok': True, 'value': fn()}
    except Exception as error:
        return {'ok': False, 'exception': type(error).__name__,
                'message': str(error)}

def module(name, path, source=None):
    m = types.ModuleType(name)
    m.__file__, m.__package__ = str(path), name.rpartition('.')[0]
    sys.modules[name] = m
    exec(compile(path.read_text() if source is None else source,
                 str(path), 'exec'), m.__dict__)
    return m

def git(root, *argv):
    return subprocess.check_output(['git', *argv], cwd=root, text=True)

module('analysis.chart', MAIN/'analysis/chart.py')
fig = module('analysis.tlb_figures', MAIN/'analysis/tlb_figures.py')
r = {'scope': __doc__, 'heads': {name: git(root, 'rev-parse', 'HEAD').strip()
     for name, root in [('m0b', TREE), ('main', MAIN), ('r2', R2)]},
     'm0b_dirty': git(TREE, 'status', '--short')}
source = (TREE/'probes/cache-mem/ptr_chase.cpp').read_text()
header = (TREE/'probes/common/tlb_set_collect.h').read_text()
r['collector_authority'] = {
    'included': '#include "tlb_set_collect.h"' in source,
    'namespace_alias': 'namespace tlc = tlb_set_collect;' in source,
    'cpp_duplicate_definition': bool(re.search(
        r'\b(?:tlb_set_index|set_index|collect_set_addrs|collect_scatter_addrs)'
        r'\s*\([^;{}]*\)\s*\{', source)),
    'header_functions': [name for name in
        ['set_index', 'collect_set_addrs', 'collect_scatter_addrs']
        if re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{', header)],
}

ad = PtrChaseAdapter()
spec = copy.deepcopy(PASS_SPEC)
spec['protocol_version'] = '1.2'
spec['execution']['sweep'] = {'buffer': ['512KiB'], 'warmup_passes': [2, 4]}
spec['execution']['fixed_params'] = ['stride']
cases = [c for c in build_plan(spec, PLATFORM).cases if c.control.id == 'c0']
records = []
r['real_plan_warmup'] = []
for c in cases:
    params = {k: v.value for k, v in c.params}
    r['real_plan_warmup'].append({'case_id': c.id, 'params': params,
                                'argv': ad.build_argv(params)})
    rec = _record(loads=params['loads'])
    rec['params'].update(params)
    # Give every synthetic observation the matching, actually requested warmup.
    for metric in rec['metrics']:
        for obs in metric['observations']:
            obs.update(warmup_loads=params['warmup'],
                       warmup_passes_effective=params['warmup_passes'],
                       warmup_state='warm')
    records.append(rec)
result = a.analyze_records(records, 'SYNTHETIC-real-plan-warmup')
r['real_plan_warmup_consumers'] = {
    'input_records': len(records), 'groups': len(result.groups),
    'group_samples': [len(g['samples']) for g in result.groups],
    'identities': [g['identity'] for g in result.groups],
    'cohort': attempt(lambda: [
        {'seeds': u['seeds'], 'valid_samples': u['valid_samples']}
        for c in a.grade_thp_cohorts(result.groups)['cohorts'] for u in c['units']]),
    'chart': attempt(lambda: fig.curve_from_groups(result.groups, 'cyc_per_load')),
}
for key, values in [('set_hypothesis', (1, 2)), ('loads_per_slot', (8, 16))]:
    x, y = _record(), _record()
    x['params'][key], y['params'][key] = values
    result = a.analyze_records([x, y], 'SYNTHETIC-'+key)
    r['identity_'+key] = {'groups': len(result.groups),
        'identity': [g['identity'] for g in result.groups],
        'chart': attempt(lambda: fig.curve_from_groups(result.groups, 'cyc_per_load')),
        'cohort': attempt(lambda: a.grade_thp_cohorts(result.groups))}

r['a1_plans'] = {}
platform = json.loads((TREE/'configs/platforms/redmi-k70pro-01.json').read_text())
for name in ('l1-main', 'l2-repro', 'l3-target'):
    p = TREE/'configs/experiments'/('ptr-chase-sm8650-x4-tlb-a1-'+name+'.json')
    plan = build_plan(json.loads(p.read_text()), platform)
    r['a1_plans'][name] = {'cases': len(plan.cases),
        'seeds': sorted({c.param_value('seed') for c in plan.cases}),
        'targets': sorted({c.param_value('set_target') for c in plan.cases}),
        'scopes': sorted({c.param_value('set_region_scope') for c in plan.cases}),
        'windows': sorted({c.param_value('set_window') for c in plan.cases}),
        'repetitions': sorted({c.repetitions for c in plan.cases})}

expected = {'tlb_set_mode': 1, 'set_hypothesis': 1, 'set_target': 7,
    'set_window': 8, 'set_rounds': 20, 'set_pool_pages': 65536,
    'set_filler_pages': 512, 'set_regions': 4, 'set_scatter': 0,
    'set_region_scope': -1, 'set_nsets': 0, 'seed': 42,
    'pmu_events': [{'name': 'l1d_tlb_refill', 'type': 8, 'config': 5},
                   {'name': 'l2d_tlb_refill', 'type': 8, 'config': 45}]}
stdout = ('mode=tlbset set_hypothesis=1 set_target=7 set_window=8 set_rounds=20 '
    'set_pool_pages=65536 set_filler_pages=512 set_regions=4 scatter=0 '
    'set_region_scope=-1 set_nsets=0 seed=42 page_kb=4 set_domain=multi-region '
    'set_active_regions=4 set_target_region_nodes=2,2,2,2 '
    'set_region_vpn_hi=90,91,92,93 set_region_vpn_hi_pure=1 '
    'window_valid_rounds=19 window_invalid_rounds=0 window_mux_rounds=0 '
    'valid_rounds=19 probe_ns=1000 '
    'pmu_l1d_tlb_refill_count=8.0 pmu_l1d_tlb_refill_valid_rounds=19 '
    'pmu_l2d_tlb_refill_count=5.0 pmu_l2d_tlb_refill_valid_rounds=19')
class Fake:
    def __init__(self, outputs): self.outputs = iter(outputs)
    def execute(self, argv, command_prefix=()):
        return ExecutionResult(0, next(self.outputs), '', 'SYNTHETIC-UNEXECUTED')
    def freq_snapshot(self, cpu_hint): return None

def engine_run(outputs):
    case = Case(id='SYNTHETIC-realized', probe='ptr_chase',
        control=Control(id='ctl', mechanism='taskset', value='0'),
        params=tuple((k, ResolvedValue(v, 'synthetic')) for k, v in expected.items()),
        repetitions=len(outputs))
    with tempfile.TemporaryDirectory(prefix='review-rpa-realized-') as d:
        rec = _run_case(case,
            {'target': {'target_id': 'synthetic-01', 'transport': 'local'}},
            PROBE_META, '/SYNTHETIC-UNEXECUTED', Fake(outputs),
            ArtifactStore(Path(d)/'run'), SYSINFO, PROBE_META['git'])
    return {'status': rec['status'], 'realized': rec['probe'].get('realized'),
            'failure': rec.get('failure'), 'metrics_empty': not rec['metrics']}

fallback = stdout.replace('set_domain=multi-region', 'set_domain=single-region-fallback').replace(
    'set_active_regions=4', 'set_active_regions=1').replace(
    'set_target_region_nodes=2,2,2,2', 'set_target_region_nodes=8,0,0,0')
r['engine_uniform'] = attempt(lambda: engine_run([stdout]*3))
r['engine_mixed'] = attempt(lambda: engine_run([stdout, fallback, fallback]))
r['engine_bad_integer'] = attempt(lambda: engine_run([
    stdout.replace('set_active_regions=4', 'set_active_regions=oops')]))
r['engine_bad_token'] = attempt(lambda: engine_run([
    stdout.replace('set_target_region_nodes=2,2,2,2',
                   'set_target_region_nodes=2,bad,2,2')]))
r['realized_checks'] = {
    'matching': attempt(lambda: ad.parse_realized(stdout, expected)),
    'bad_sum': attempt(lambda: ad.parse_realized(stdout.replace(
        'set_target_region_nodes=2,2,2,2', 'set_target_region_nodes=2,2,2,3'), expected)),
    'bad_active': attempt(lambda: ad.parse_realized(stdout.replace(
        'set_active_regions=4', 'set_active_regions=3'), expected)),
    'legacy_for_tlb_request': attempt(lambda: ad.parse_output('latency_ns=1.25', '', expected)),
    'seed_drift': attempt(lambda: ad.parse_output(stdout.replace('seed=42', 'seed=99'), '', expected)),
}

harness = r'''
#include "tlb_set_collect.h"
#include <cstdio>
namespace tlc=tlb_set_collect;
int main(){
 std::vector<tlc::Region> rs; uintptr_t b=uintptr_t(0x5a)<<28;
 for(int k=0;k<4;k++)rs.push_back({reinterpret_cast<char*>(b+(uint64_t(k)*65536+uint64_t(k)*8)*4096),16384});
 auto print=[](const char* kind,int x,const std::vector<uintptr_t>& vs,const std::vector<int>& cs){
  int sum=0,active=0;for(int c:cs){sum+=c;if(c>0)active++;}
  std::printf("%s x=%d nodes=%zu slots=%zu sum=%d active=%d counts=",kind,x,vs.size(),cs.size(),sum,active);
  for(int c:cs)std::printf("%d,",c);std::puts("");};
 for(int H=1;H<=4;H++)for(uint32_t T:{7u,42u,100u,200u}){
  std::vector<uintptr_t> vs,iso;std::vector<int> cs(4,0),ics(4,0);
  tlc::collect_set_addrs(H,T,12,rs,0,&vs,&cs);
  tlc::collect_set_addrs(H,T,12,{rs[0]},0,&iso,&ics);
  print("quota",H*1000+T,vs,cs);std::printf("same_as_iso0=%d\n",vs==iso);
 }
 for(int N:{4,96,256}){
  std::vector<uintptr_t> vs;std::vector<int> cs(4,0);
  for(int s=0;s<N;s++)tlc::collect_set_addrs(1,s,12,rs,0,&vs,&cs);
  print("nsets",N,vs,cs);
 }
 for(int k=0;k<4;k++){
  std::vector<uintptr_t> vs;std::vector<int> cs(4,0);
  tlc::collect_set_addrs(4,200,12,{rs[k]},k,&vs,&cs);print("isolation",k,vs,cs);
 }
 std::vector<uintptr_t> t,t2,sc;std::vector<int> tc(4,0),t2c(4,0),scc(4,0);
 tlc::collect_set_addrs(4,7,12,rs,0,&t,&tc);
 tlc::collect_set_addrs(4,42,12,rs,0,&t2,&t2c);
 print("T",7,t,tc);print("T2",42,t2,t2c);
 tlc::collect_scatter_addrs(1,8,rs,0,&sc,&scc);print("scatter",8,sc,scc);
 tlc::Region cross{reinterpret_cast<char*>(b+224ull*1024*1024),16384};
 std::vector<uintptr_t> vs;std::vector<int> cs(1,0);
 tlc::collect_set_addrs(1,7,12,{cross},0,&vs,&cs);
 uintptr_t start=reinterpret_cast<uintptr_t>(cross.base),end=start+(cross.pages-1)*4096;
 bool selected_cross=false;for(auto v:vs)if((v>>28)!=(vs[0]>>28))selected_cross=true;
 std::printf("cross region_pure=%d selected_cross=%d\n",(start>>28)==(end>>28),selected_cross);
}
'''
with tempfile.TemporaryDirectory(prefix='review-rpa-native-') as d:
    p = Path(d); (p/'h.cpp').write_text(harness)
    c = subprocess.run(['clang++', '-std=c++17', '-O2',
        '-I', str(TREE/'probes/common'), str(p/'h.cpp'), '-o', str(p/'h')],
        capture_output=True, text=True)
    r['native_compile'] = {'rc': c.returncode, 'stderr': c.stderr}
    if c.returncode == 0:
        r['native_header_selection'] = subprocess.check_output([str(p/'h')], text=True)

old = module('analysis._rpa_old', TREE/'analysis/sm8650_tlb.py',
             git(TREE, 'show', '3e539c6:analysis/sm8650_tlb.py'))
registry = a.load_registry(TREE/'configs/pmu-event-registry.json')
rows, warmups = [], {}
for p in sorted((TREE/'data/public/runs').glob('*ptr-chase-sm8650-x4-tlb*/records.jsonl')):
    if 'pilot' in p.parent.name: continue
    run = load_run(p.parent); records = run.ok_records+run.failed_records
    for rec in records:
        k = str(rec.get('params', {}).get('warmup_passes', 'MISSING'))
        warmups[k] = warmups.get(k, 0)+1
    x = old.analyze_records(records, p.parent.name, registry)
    y = a.analyze_records(records, p.parent.name, registry)
    d = dataclasses.asdict(y)
    digest_none = all(g['identity']['residual_digest'] is None for g in d['groups'])
    for g in d['groups']: del g['identity']
    rows.append({'run': p.parent.name, 'records': len(records),
        'legacy_digest_none': digest_none,
        'normalized_equal': dataclasses.asdict(x) == d,
        'cohort_equal': old.grade_thp_cohorts(x.groups) == a.grade_thp_cohorts(y.groups)})
r['legacy_replay'], r['legacy_warmup_values'] = rows, warmups
tf = module('analysis.tests._rpa_main_figures', MAIN/'analysis/tests/test_tlb_figures.py')
log = io.StringIO()
with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
    t = unittest.TextTestRunner(stream=log).run(unittest.defaultTestLoader.loadTestsFromModule(tf))
r['main_overlay'] = {'tests': t.testsRun, 'failures': len(t.failures),
                     'errors': len(t.errors), 'log': log.getvalue()}
cm = git(TREE, 'show', '95fa2a9:tests/CMakeLists.txt')
r['golden_ctest_registration'] = {
    'committed': 'add_test(NAME tlb_set_collect_golden' in cm,
    'working_tree': 'add_test(NAME tlb_set_collect_golden' in (TREE/'tests/CMakeLists.txt').read_text(),
    'diff': git(TREE, 'diff', '--', 'tests/CMakeLists.txt')}
r['a3_tracking'] = {name: bool(re.search(r'全链遍历|translation reach',
    (root/'docs/open-items.md').read_text())) for name, root in [('r2', R2), ('m0b', TREE)]}
r['a1_consumer_source_hits'] = []
for root in [TREE/'analysis', TREE/'scripts', R2/'scripts']:
    for p in root.rglob('*.py'):
        if 'review_' in p.name or 'tests' in p.parts: continue
        if any(k in p.read_text() for k in ['domain_consistent', 'set_region_vpn_hi_pure']):
            r['a1_consumer_source_hits'].append(str(p.relative_to(root.parent)))
args.out.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k: v for k, v in r.items() if k not in ('legacy_replay', 'main_overlay')},
                 ensure_ascii=False, indent=2))
print('legacy_runs', len(rows), 'records', sum(x['records'] for x in rows),
      'normalized_equal', sum(x['normalized_equal'] for x in rows),
      'cohort_equal', sum(x['cohort_equal'] for x in rows),
      'all_digest_none', all(x['legacy_digest_none'] for x in rows))
print('main_overlay', {k: v for k, v in r['main_overlay'].items() if k != 'log'})
