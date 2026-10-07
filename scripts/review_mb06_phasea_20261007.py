#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reproduce MB-06/Phase A review against explicitly selected source trees.

All fabricated counts and virtual addresses are SYNTHETIC software fixtures.
The native harness compiles unchanged address-selection functions and never
dereferences its addresses. No adb, target probe, perf syscall or device run.
Archived public campaign replay omits pilot records without a latency frame.
Results are diagnostics, including observed defects, not a passing test suite.
"""
import argparse,contextlib,copy,dataclasses,hashlib,io,json,subprocess,sys,tempfile,types,unittest
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tree',type=Path,required=True)
parser.add_argument('--main-tree',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
TREE=args.tree.resolve()
MAIN=args.main_tree.resolve()
sys.path.insert(0,str(TREE))
from analysis import sm8650_tlb as a
from analysis.load import load_run
from analysis.tests.test_sm8650_tlb import _record
from runner.adapters.ptr_chase import PtrChaseAdapter
from runner import plan
from runner.tests.test_plan import SPEC,PLATFORM

def attempt(fn):
    try:
        v=fn()
        return {'ok':True,'value':dataclasses.asdict(v) if dataclasses.is_dataclass(v) else v}
    except Exception as e:
        return {'ok':False,'exception':type(e).__name__,'message':str(e)}

def load_module(name,path,source=None):
    m=types.ModuleType(name);m.__file__=str(path);m.__package__=name.rpartition('.')[0]
    sys.modules[name]=m
    exec(compile(path.read_text() if source is None else source,str(path),'exec'),m.__dict__)
    return m

load_module('analysis.chart',MAIN/'analysis/chart.py')
f=load_module('analysis.tlb_figures',MAIN/'analysis/tlb_figures.py')
r={'tree_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE,text=True).strip(),
   'main_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=MAIN,text=True).strip(),
   'scope':'synthetic software checks and archived public data replay; no board/PMU execution'}
x,y=_record(),_record()
x['params']['set_hypothesis']=1;y['params']['set_hypothesis']=2
for metric in y['metrics']:
    if metric['name']=='pmu.cycles.count':
        for o in metric['observations']:o['value']=100*65536
an=a.analyze_records([x,y],'SYNTHETIC-H')
r['residual_identity']={'groups':len(an.groups),'exported_identity':[g['identity'] for g in an.groups],
  'per_group_cycles':[g['cyc_per_load']['median'] for g in an.groups],
  'chart':attempt(lambda:f.curve_from_groups(an.groups,'cyc_per_load')),
  'cohort':attempt(lambda:[u['valid_samples'] for c in a.grade_thp_cohorts(an.groups)['cohorts'] for u in c['units']])}
x,y=_record(),_record();x['params']['chains']=True;y['params']['chains']=1
r['bool_int_groups']=len(a.analyze_records([x,y],'SYNTHETIC-types').groups)
x,y=_record(),_record();x['params']['nested']={'a':1,'b':2};y['params']['nested']={'b':2,'a':1}
r['same_json_object_different_order_groups']=len(a.analyze_records([x,y],'SYNTHETIC-canonical').groups)
ad=PtrChaseAdapter()
stdout=('mode=tlbset set_hypothesis=1 set_target=7 set_window=8 set_rounds=20 '
        'set_domain=multi-region set_filler=512 set_regions=4 page_kb=4 seed=42 '
        'window_valid_rounds=19 window_invalid_rounds=0 window_mux_rounds=0 '
        'valid_rounds=19 probe_ns=1500 pmu_l1d_tlb_refill_count=8.0 '
        'pmu_l1d_tlb_refill_valid_rounds=19')
expected={'tlb_set_mode':1,'set_hypothesis':1,'set_target':7,'set_window':8,'set_rounds':20,
          'set_regions':4,'set_filler_pages':512,'set_pool_pages':65536,'set_scatter':1,'seed':42,
          'pmu_events':[{'name':'l1d_tlb_refill','type':8,'config':5}, {'name':'l2d_tlb_refill','type':8,'config':45}]}
r['descriptor']={'matching_but_missing_requested_event':attempt(lambda:ad.parse_output(stdout,'',expected)),
  'target_mismatch':attempt(lambda:ad.parse_output(stdout.replace('set_target=7','set_target=99'),'',expected)),
  'wrong_mode_legacy_latency':attempt(lambda:ad.parse_output('latency_ns=1.25','',expected)),
  'wrong_regions_filler_seed_scatter':attempt(lambda:ad.parse_output(stdout.replace('set_regions=4','set_regions=1').replace('set_filler=512','set_filler=0').replace('seed=42','seed=99')+' scatter=0','',expected)),
  'fallback_domain':attempt(lambda:ad.parse_output(stdout.replace('multi-region','single-region-fallback'),'',expected))}
s=copy.deepcopy(SPEC);s['execution']['sweep']['chains']=[1,2]
r['mb03_chains']=attempt(lambda:plan.build_plan(s,PLATFORM))
s=copy.deepcopy(SPEC);s['execution']['sweep']['unknown']=[1,2]
r['mb03_unknown']=attempt(lambda:plan.build_plan(s,PLATFORM))
oldsrc=subprocess.check_output(['git','show','3e539c6:analysis/sm8650_tlb.py'],cwd=TREE,text=True)
old=load_module('analysis._review_old',TREE/'analysis/sm8650_tlb.py',oldsrc)
reg=a.load_registry(TREE/'configs/pmu-event-registry.json')
replay=[]
for p in sorted((TREE/'data/public/runs').glob('*ptr-chase-sm8650-x4-tlb*/records.jsonl')):
    if 'pilot' in p.parent.name:continue
    run=load_run(p.parent);records=run.ok_records+run.failed_records
    o=old.analyze_records(records,p.parent.name,reg);n=a.analyze_records(records,p.parent.name,reg)
    d=dataclasses.asdict(n)
    for g in d['groups']:
        assert not any(v is not None for v in g['identity'].values())
        del g['identity']
    replay.append({'run':p.parent.name,'records':len(records),'raw_analysis_equal':dataclasses.asdict(o)==dataclasses.asdict(n),
                   'analysis_same_after_empty_identity_removal':dataclasses.asdict(o)==d,
                   'cohort_same':attempt(lambda:old.grade_thp_cohorts(o.groups))==attempt(lambda:a.grade_thp_cohorts(n.groups))})
r['legacy_replay']=replay
# Include unchanged production selection functions; numeric VA fixtures are never dereferenced.
source=(TREE/'probes/cache-mem/ptr_chase.cpp').read_text()
r['probe_source_sha256']=hashlib.sha256(source.encode()).hexdigest()
chunk=source[source.index('uint32_t tlb_set_index('):source.index('void build_chain(')]
harness='#include <cstdint>\n#include <cstdio>\n#include <vector>\nconstexpr uint32_t kTlbSets=256;\n'+chunk+'''
int main(){
 std::vector<TlbRegion> regions;
 uintptr_t base=uintptr_t(0x5a)<<28;
 for(int k=0;k<4;k++)regions.push_back({reinterpret_cast<char*>(base+(uint64_t(k)*65536+uint64_t(k)*8)*4096),16384});
 for(int H=1;H<=4;H++)for(uint32_t T:{7u,42u,100u,200u}){
   std::vector<uintptr_t> global,isolated;
   collect_set_addrs(H,T,12,regions,&global);
   collect_set_addrs(H,T,12,{regions[0]},&isolated);
   unsigned mask=0;
   for(auto va:global)for(int k=0;k<4;k++)if(va>=reinterpret_cast<uintptr_t>(regions[k].base)&&va<reinterpret_cast<uintptr_t>(regions[k].base)+regions[k].pages*4096)mask|=1u<<k;
   std::printf("H=%d T=%u selected=%zu active_region_mask=%u same_as_isolated0=%d\\n",H,T,global.size(),mask,global==isolated);
 }
}
'''
with tempfile.TemporaryDirectory(prefix='review-region-') as t:
    t=Path(t);(t/'h.cpp').write_text(harness)
    cp=subprocess.run(['clang++','-std=c++17',str(t/'h.cpp'),'-o',str(t/'h')],capture_output=True,text=True)
    r['selection_compile']={'rc':cp.returncode,'stderr':cp.stderr}
    if cp.returncode==0:r['region_selection_output']=subprocess.check_output([str(t/'h')],text=True)
# Public pilot records: inspect serialized contract fields, not target reruns.
rows=[]
for p in sorted((TREE/'data/public/runs').glob('*pilot*/records.jsonl')):
    for row in map(json.loads,p.read_text().splitlines()):
        rows.append({'run':p.parent.name,'status':row['status'],
                     'params':row.get('params'), 'serialized_realized_domain': 'set_domain' in json.dumps(row),
                     'metrics':[m['name'] for m in row['metrics']]})
r['pilot_record_contract']=rows
# Actual main tests import the reviewed m0b analyzer in this fresh process.
tf=load_module('analysis.tests._review_main_figures',MAIN/'analysis/tests/test_tlb_figures.py')
log=io.StringIO()
with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
    result=unittest.TextTestRunner(stream=log,verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(tf))
r['main_overlay_tests']={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'log':log.getvalue()}
from runner.tests.test_plan import TestPlan
mb03_names=['test_unknown_swept_param_rejected_at_plan_time',
 'test_generic_shape_id_independent_of_chase_geometry',
 'test_generic_shape_id_supports_structured_common_params',
 'test_tlb_set_shape_registered_deriver_end_to_end']
log=io.StringIO()
result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite(TestPlan(name) for name in mb03_names))
r['mb03_targeted_tests']={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'log':log.getvalue()}
with tempfile.TemporaryDirectory(prefix='review-mb07-') as td:
    td=Path(td);root=td/'runs';tf._make_dataset(root)
    for p in root.glob('*/records.jsonl'):
        if p.parent.name not in (f.RUN_COARSE,f.RUN_DENSE):continue
        records=[json.loads(line) for line in p.read_text().splitlines()]
        for row in records:
            if 4096<=row['params']['buffer_kb']<32768:
                row['metrics']=[m for m in row['metrics'] if m['name']!='pmu.dtlb_walk.count']
        p.write_text(''.join(json.dumps(row)+'\n' for row in records))
    rc,out,err=tf._run_cli(root,td/'gaps')
    report=(td/'gaps/report.md').read_text() if rc==0 else ''
    r['mb07_onset_gap']={'rc':rc,'stderr':err,'historical_disclosure':'非本数据集重判' in report,
      'unsupported_interval_marked':'〔当前曲线不支持〕[2560, 3072]' in report,
      'false_readjudication_claim':'按可用点重判' in report}
    # Compare the same current chart renderer with old/new analyzers on complete archived data.
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        f.analyze_records=old.analyze_records;f.grade_thp_cohorts=old.grade_thp_cohorts
        old_rc=f.main(['--runs-root',str(TREE/'data/public/runs'),'--out',str(td/'old')])
        f.analyze_records=a.analyze_records;f.grade_thp_cohorts=a.grade_thp_cohorts
        new_rc=f.main(['--runs-root',str(TREE/'data/public/runs'),'--out',str(td/'new')])
    r['complete_render_replay']={'old_rc':old_rc,'new_rc':new_rc,'files':{
      name:(td/'old'/name).read_bytes()==(td/'new'/name).read_bytes()
      for name in ('refill-density.svg','walk-onset.svg','latency-cycles.svg','thp-cohort.svg','report.md')}
      if old_rc==new_rc==0 else {}}
args.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k not in ('legacy_replay','pilot_record_contract')},ensure_ascii=False,indent=2))
print('legacy replay:',len(replay),'analysis same:',sum(x['analysis_same_after_empty_identity_removal'] for x in replay),'cohort same:',sum(x['cohort_same'] for x in replay))
print('pilot records:',len(rows),'serialized domain:',sum(x['serialized_realized_domain'] for x in rows))
