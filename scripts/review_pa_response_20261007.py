#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only PA response diagnostics: synthetic fixtures and archived public data.

The C++ harness uses production address selection without dereferencing VAs.
The executor is a Python fake; no adb, device binary or perf syscall is invoked.
Exit 0 means diagnostics completed, not that the reviewed package passed.
"""
import argparse
import contextlib
import copy
import dataclasses
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tree', type=Path, required=True)
parser.add_argument('--main-tree', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
TREE, MAIN = args.tree.resolve(), args.main_tree.resolve()
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
from runner.tests.test_plan import SPEC, PLATFORM

def attempt(fn):
    try:
        value = fn()
        return {'ok': True, 'value': value}
    except Exception as error:
        return {'ok': False, 'exception': type(error).__name__, 'message': str(error)}

def module(name, path, source=None):
    m = types.ModuleType(name)
    m.__file__, m.__package__ = str(path), name.rpartition('.')[0]
    sys.modules[name] = m
    exec(compile(path.read_text() if source is None else source, str(path), 'exec'), m.__dict__)
    return m

module('analysis.chart', MAIN/'analysis/chart.py')
fig = module('analysis.tlb_figures', MAIN/'analysis/tlb_figures.py')
head = lambda root: subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
r = {'tree_head': head(TREE), 'main_head': head(MAIN), 'scope': __doc__}
for key, values in [('set_hypothesis', (1, 2)), ('loads_per_slot', (8, 16)), ('warmup_passes', (2, 4))]:
    x, y = _record(), _record()
    x['params'][key], y['params'][key] = values
    result = a.analyze_records([x, y], 'SYNTHETIC-'+key)
    r['identity_'+key] = {'groups': len(result.groups), 'identity': [g['identity'] for g in result.groups],
        'chart': attempt(lambda: fig.curve_from_groups(result.groups, 'cyc_per_load')),
        'cohort': attempt(lambda: [u['valid_samples'] for c in a.grade_thp_cohorts(result.groups)['cohorts'] for u in c['units']])}
x, y = _record(), _record()
x['params']['nested'], y['params']['nested'] = {'a': 1, 'b': 2}, {'b': 2, 'a': 1}
r['same_json_object_groups'] = len(a.analyze_records([x, y], 'SYNTHETIC-dict').groups)

def nset_plan(n):
    spec = copy.deepcopy(SPEC)
    spec['parameters'] = [{'name': 'repetitions', 'type': 'int', 'default': 10}]
    spec['execution'] = {'probe': 'ptr_chase', 'probe_shape': 'tlb_set',
        'sweep': {'set_nsets': [n]}, 'fixed_params': ['set_hypothesis', 'set_window'],
        'params': {'set_hypothesis': 1, 'set_window': 8}}
    built = build_plan(spec, {**PLATFORM, 'controls': []})
    return [{key: value.value for key, value in c.params} for c in built.cases]
r['a3_plan'] = {str(n): attempt(lambda n=n: nset_plan(n)) for n in (96, 256, 258, 260, 264, 272, 288, 320)}

ad = PtrChaseAdapter()
expected = {'tlb_set_mode': 1, 'set_hypothesis': 1, 'set_target': 7, 'set_window': 8,
    'set_rounds': 20, 'set_pool_pages': 65536, 'set_filler_pages': 512,
    'set_regions': 4, 'set_scatter': 0, 'set_region_scope': -1, 'set_nsets': 0, 'seed': 42,
    'pmu_events': [{'name': 'l1d_tlb_refill', 'type': 8, 'config': 5},
                   {'name': 'l2d_tlb_refill', 'type': 8, 'config': 45}]}
stdout = ('mode=tlbset set_hypothesis=1 set_target=7 set_window=8 set_rounds=20 '
    'set_pool_pages=65536 set_filler_pages=512 set_regions=4 scatter=0 '
    'set_region_scope=-1 set_nsets=0 seed=42 page_kb=4 set_domain=multi-region '
    'set_active_regions=4 set_region_nodes=2,2,2,2 window_valid_rounds=19 '
    'window_invalid_rounds=0 window_mux_rounds=0 valid_rounds=19 probe_ns=1000 '
    'pmu_l1d_tlb_refill_count=8.0 pmu_l1d_tlb_refill_valid_rounds=19 '
    'pmu_l2d_tlb_refill_count=5.0 pmu_l2d_tlb_refill_valid_rounds=19')
r['descriptor_shape_rejects_legacy'] = attempt(lambda: ad.parse_output('latency_ns=1.25', '', expected))
r['descriptor_matching'] = attempt(lambda: ad.parse_output(stdout, '', expected))
r['descriptor_parameter_drift'] = attempt(lambda: ad.parse_output(stdout.replace('seed=42', 'seed=99'), '', expected))
r['descriptor_event_missing'] = attempt(lambda: ad.parse_output(stdout.replace('pmu_l2d_tlb_refill_count=5.0', ''), '', expected))

class Fake:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
    def execute(self, argv, command_prefix=()):
        return ExecutionResult(0, next(self.outputs), '', 'SYNTHETIC-UNEXECUTED')
    def freq_snapshot(self, cpu_hint):
        return None

def engine_run(outputs):
    case = Case(id='SYNTHETIC-realized', probe='ptr_chase',
        control=Control(id='ctl', mechanism='taskset', value='0'),
        params=tuple((k, ResolvedValue(v, 'synthetic')) for k, v in expected.items()),
        repetitions=len(outputs))
    with tempfile.TemporaryDirectory(prefix='review-realized-') as d:
        record = _run_case(case, {'target': {'target_id': 'synthetic-01', 'transport': 'local'}},
            PROBE_META, '/SYNTHETIC-UNEXECUTED', Fake(outputs), ArtifactStore(Path(d)/'run'),
            SYSINFO, PROBE_META['git'])
    return {'status': record['status'], 'probe': record['probe'],
        'metrics': record['metrics'], 'failure': record.get('failure')}

fallback = stdout.replace('set_domain=multi-region', 'set_domain=single-region-fallback').replace(
    'set_active_regions=4', 'set_active_regions=1').replace('set_region_nodes=2,2,2,2', 'set_region_nodes=8').replace(
    'pmu_l2d_tlb_refill_count=5.0', 'pmu_l2d_tlb_refill_count=20.0')
r['engine_uniform_realized'] = attempt(lambda: engine_run([stdout, stdout, stdout]))
r['engine_mixed_realized'] = attempt(lambda: engine_run([stdout, fallback, fallback]))
r['engine_bad_active_regions'] = attempt(lambda: engine_run([stdout.replace('set_active_regions=4', 'set_active_regions=oops')]))
r['engine_bad_region_nodes'] = attempt(lambda: engine_run([stdout.replace('set_region_nodes=2,2,2,2', 'set_region_nodes=2,bad,2,2')]))

source = (TREE/'probes/cache-mem/ptr_chase.cpp').read_text()
chunk = source[source.index('uint32_t tlb_set_index('):source.index('void build_chain(')]
harness = '#include <cstdint>\n#include <cstdio>\n#include <vector>\nconstexpr uint32_t kTlbSets=256;\n'+chunk+r'''
int main(){
 std::vector<TlbRegion> regions; uintptr_t base=uintptr_t(0x5a)<<28;
 for(int k=0;k<4;k++)regions.push_back({reinterpret_cast<char*>(base+(uint64_t(k)*65536+uint64_t(k)*8)*4096),16384});
 for(int H=1;H<=4;H++)for(uint32_t T:{7u,42u,100u,200u}){
   std::vector<uintptr_t> global,isolated;std::vector<int> gc,ic;
   collect_set_addrs(H,T,12,regions,&global,&gc);collect_set_addrs(H,T,12,{regions[0]},&isolated,&ic);
   std::printf("quota H=%d T=%u nodes=%zu counts=",H,T,global.size());
   for(int n:gc)std::printf("%d,",n);
   std::printf(" same_as_iso0=%d\n",global==isolated);
 }
 for(int N:{4,32,96,256}){
   std::vector<uintptr_t> vas;std::vector<int> counts;
   for(int s=0;s<N;s++)collect_set_addrs(1,s,8,regions,&vas,&counts);
   int active=0;for(int n:counts)if(n>0)++active;
   unsigned mask=0;for(auto v:vas)for(int k=0;k<4;k++)if(v>=reinterpret_cast<uintptr_t>(regions[k].base)&&v<reinterpret_cast<uintptr_t>(regions[k].base)+regions[k].pages*4096)mask|=1u<<k;
   unsigned long long hash=1469598103934665603ull;
   for(int r=0;r<20;r++)for(int i=0;i<8;i++){hash^=vas[(r*8+i)%vas.size()];hash*=1099511628211ull;}
   int retained=0;for(uint64_t i=1;i<768;i++)if(tlb_set_index(1,base+i*4096)>=unsigned(N))++retained;
   std::printf("nsets N=%d nodes=%zu audit_length=%zu reported_active=%d actual_region_mask=%u traversed_unique=%zu trace_hash=%llu filler_candidates=%d required_filler=512\n",N,vas.size(),counts.size(),active,mask,vas.size()<160?vas.size():size_t(160),hash,retained);
 }
 // A legal numeric region with no imposed 256MiB alignment; no dereferences.
 std::vector<TlbRegion> cross{{reinterpret_cast<char*>(base+224ull*1024*1024),16384}};
 std::vector<uintptr_t> cvs;std::vector<int> cc;
 collect_set_addrs(1,7,12,cross,&cvs,&cc);
 uint64_t first=(cvs[0]>>28)&255;bool changed=false;
 for(auto v:cvs)if(((v>>28)&255)!=first)changed=true;
 std::printf("isolated_scope cross_high_field=%d nodes=%zu active_regions=1\n",changed,cvs.size());
}
'''
with tempfile.TemporaryDirectory(prefix='review-pa-native-') as d:
    p=Path(d);(p/'h.cpp').write_text(harness)
    c=subprocess.run(['clang++','-std=c++17','-O2',str(p/'h.cpp'),'-o',str(p/'h')],capture_output=True,text=True)
    r['native_compile']={'rc':c.returncode,'stderr':c.stderr}
    if c.returncode==0:r['native_selection']=subprocess.check_output([str(p/'h')],text=True)
r['native_probe_loop_uses_window_not_chain_length'] = 'for (long long i = 0; i < opt.window; ++i)' in source

oldsrc=subprocess.check_output(['git','show','3e539c6:analysis/sm8650_tlb.py'],cwd=TREE,text=True)
old=module('analysis._pa_response_old',TREE/'analysis/sm8650_tlb.py',oldsrc)
registry=a.load_registry(TREE/'configs/pmu-event-registry.json')
rows=[]
for p in sorted((TREE/'data/public/runs').glob('*ptr-chase-sm8650-x4-tlb*/records.jsonl')):
    if 'pilot' in p.parent.name:continue
    run=load_run(p.parent);records=run.ok_records+run.failed_records
    x=old.analyze_records(records,p.parent.name,registry);y=a.analyze_records(records,p.parent.name,registry)
    d=dataclasses.asdict(y)
    for g in d['groups']:
        assert not any(v is not None for v in g['identity'].values())
        del g['identity']
    rows.append({'run':p.parent.name,'records':len(records),'normalized_equal':dataclasses.asdict(x)==d,
        'cohort_equal':old.grade_thp_cohorts(x.groups)==a.grade_thp_cohorts(y.groups)})
r['legacy_replay']=rows
tf=module('analysis.tests._pa_main_figures',MAIN/'analysis/tests/test_tlb_figures.py')
log=io.StringIO()
with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
    t=unittest.TextTestRunner(stream=log).run(unittest.defaultTestLoader.loadTestsFromModule(tf))
r['main_overlay']={'tests':t.testsRun,'failures':len(t.failures),'errors':len(t.errors),'log':log.getvalue()}
args.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k not in ('legacy_replay','engine_uniform_realized','engine_mixed_realized','engine_bad_region_nodes')},ensure_ascii=False,indent=2))
print('legacy_runs',len(rows),'records',sum(x['records'] for x in rows),'normalized_equal',sum(x['normalized_equal'] for x in rows),'cohort_equal',sum(x['cohort_equal'] for x in rows))
for key in ('engine_uniform_realized','engine_mixed_realized','engine_bad_active_regions','engine_bad_region_nodes'):
    outcome=r[key]
    print(key,json.dumps({'ok':outcome['ok'],'probe':outcome.get('value',{}).get('probe'),'failure':outcome.get('message')},ensure_ascii=False))
