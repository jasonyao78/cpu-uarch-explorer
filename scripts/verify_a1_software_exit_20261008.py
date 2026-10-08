#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""A1 软件出口复现：真实 producer + 合成外部 I/O、归档重放、真实图表。

不运行手机/adb/目标探针/perf。合成 H* 只验证软件，不能充当硬件证据。
历史统计比较仅排除新增 identity 元数据；cohort 比较不规范化。
"""
import argparse
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import types


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    root = args.tree.resolve(); sys.path.insert(0, str(root))
    from analysis import sm8650_tlb as current
    from analysis.load import load_run
    from analysis.sm8650_tlb import TlbError
    from analysis.sm8650_tlb_a1 import run_a1_adjudication
    from analysis.tests.test_sm8650_tlb_a1_contract import produce_a1
    from analysis.tests.a1_production_fixture import freeze_fixture
    from analysis.sm8650_tlb_a1_freeze import CODE_PATHS, CONFIG_PATHS
    from analysis import tlb_figures
    result = {'scope': __doc__, 'head': subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=root,text=True).strip()}
    with tempfile.TemporaryDirectory(prefix='a1-software-exit-') as tmp:
        records = produce_a1(Path(tmp)/'formal')
        frozen = freeze_fixture(Path(tmp)/'calibration')
        out = run_a1_adjudication(records, frozen)
        shuffled = copy.deepcopy(records); random.Random(71).shuffle(shuffled)
        serial = lambda x: json.dumps(x,sort_keys=True,separators=(',',':'))
        assert serial(out) == serial(run_a1_adjudication(shuffled,frozen))
        assert out['h_star'] == 1 and out['n_records'] == 128
        assert len(out['case_audit']) == 128 and all(len(c['processes']) == 10 for c in out['case_audit'])
        negatives = {}
        conflict = copy.deepcopy(records); conflict[0]['params']['set_filler_pages'] = 1024
        for name, bad in (('missing',records[1:]),('duplicate',records+[records[0]]),('conflict',conflict)):
            try: run_a1_adjudication(bad,frozen)
            except TlbError as e: negatives[name] = str(e)
            else: raise AssertionError(f'{name} incorrectly accepted')
        result['production_chain'] = {'ok_records':128, 'synthetic_observations':1280,
            'calibration_records':2, 'calibration_observations':20,
            'case_audit_processes':1280, 'canonical_json_permutation_equal':True,
            'negative_rejections':negatives, 'synthetic_h_star':1,
            'frozen_on_threshold':frozen['on_threshold']}
    src = subprocess.check_output(['git','show','3e539c6:analysis/sm8650_tlb.py'],cwd=root,text=True)
    old = types.ModuleType('analysis._a1_exit_old'); old.__package__='analysis'
    old.__file__=str(root/'analysis/sm8650_tlb.py');sys.modules[old.__name__]=old
    exec(compile(src,old.__file__,'exec'),old.__dict__)
    registry=current.load_registry(root/'configs/pmu-event-registry.json')
    replay=[]
    for path in sorted((root/'data/public/runs').glob('*ptr-chase-sm8650-x4-tlb*/records.jsonl')):
        if 'pilot' in path.parent.name: continue
        run=load_run(path.parent);records=run.ok_records+run.failed_records
        a=old.analyze_records(records,path.parent.name,registry)
        b=current.analyze_records(records,path.parent.name,registry)
        normalized=dataclasses.asdict(b)
        for group in normalized['groups']:del group['identity']
        row={'run':path.parent.name,'records':len(records),
            'statistics_equal':dataclasses.asdict(a)==normalized,
            'cohort_equal':old.grade_thp_cohorts(a.groups)==current.grade_thp_cohorts(b.groups),
            'records_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        assert row['statistics_equal'] and row['cohort_equal'],row
        replay.append(row)
    assert len(replay)==51 and sum(r['records'] for r in replay)==295
    result['legacy_replay']={'baseline':'3e539c6','runs':51,'records':295,'rows':replay}
    with tempfile.TemporaryDirectory(prefix='a1-exit-figures-') as tmp:
        assert tlb_figures.main(['--runs-root',str(root/'data/public/runs'),'--out',tmp])==0
        files={}
        for path in sorted(Path(tmp).iterdir()):
            assert path.read_bytes()==(root/'docs/reports/2026-09-30-sm8650-tlb'/path.name).read_bytes()
            files[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        assert len(files)==5
        result['campaign_figures']={'equal_to_main_committed_outputs':True,'sha256':files}
    paths=(*CODE_PATHS,*CONFIG_PATHS,'analysis/sm8650_tlb.py','analysis/tlb_figures.py')
    result['source_sha256']={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
    result['outcome']='PASS: software exit checks only; target qualification/calibration still required'
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(result['outcome'])


if __name__=='__main__': main()
