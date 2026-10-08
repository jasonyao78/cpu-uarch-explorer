# SPDX-License-Identifier: Apache-2.0
"""冻结测试只替换外部传输；标定值从真实 producer 输出写盘再回读。"""
import re
from pathlib import Path
from runner.tests.tlb_set_fixtures import a1_plan, run_synthetic_plan


def freeze_fixture(root, floor=None, scatter=None):
    from analysis.sm8650_tlb_a1_freeze import freeze_a1_from_runs
    floor = [0.0, 0.2, 0.0, 0.4, 0.2] * 2 if floor is None else floor
    scatter = [0.0] * 10 if scatter is None else scatter
    for role, values in (('floor', floor), ('scatter', scatter)):
        def output(case, index, stdout):
            return re.sub(r'pmu_l2d_tlb_refill_count=\S+',
                          f'pmu_l2d_tlb_refill_count={values[index]}', stdout)
        plan, platform = a1_plan('calibration-' + role)
        summary, calls = run_synthetic_plan(plan, platform, Path(root) / role, output)
        if summary['ok'] != 1 or calls != 10 or summary['failed']:
            raise AssertionError(f'calibration producer failed: {summary}')
    return freeze_a1_from_runs(Path(root) / 'floor', Path(root) / 'scatter')
