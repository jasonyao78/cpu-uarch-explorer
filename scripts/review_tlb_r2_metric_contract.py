#!/usr/bin/env python3
"""Read-only review: synthetic missing metrics, archived replay, main chart overlay.

Synthetic fixtures are software inputs, never board measurements. Output goes
only to --out. Imports select r2's analyzer and main's chart generator without
changing either checkout. --baseline must be a local Git revision.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types
import unittest
import xml.etree.ElementTree as ET


def load_source(name, path, source=None):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = name.rpartition('.')[0]
    sys.modules[name] = module
    exec(compile(source if source is not None else path.read_text(), str(path), 'exec'), module.__dict__)
    return module


def attempt(fn):
    try:
        value = fn()
        return {'ok': True, 'value': value}
    except Exception as exc:
        return {'ok': False, 'exception': type(exc).__name__, 'message': str(exc)}


def normalize(value):
    if dataclasses.is_dataclass(value):
        return normalize(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()
                if k not in ('metric_contract', 'main_metric_contract')}
    if isinstance(value, (list, tuple)):
        return [normalize(v) for v in value]
    return value


def remove_metric(record, name):
    record = copy.deepcopy(record)
    record['metrics'] = [m for m in record['metrics'] if m['name'] != name]
    return record


def anchor_summary(verdict):
    return {'status': verdict.status,
            'main_metric_contract': verdict.evidence.get('main_metric_contract')}


def derived_judgments(module, result):
    """Replay the existing numeric consumers, split by backing and training."""
    by_regime = {}
    for group in result.groups:
        key = (group['page_policy_actual'], group['ring_passes'])
        by_regime.setdefault(key, {}).setdefault(group['seed'], []).append({
            'pages': group['buffer_kb'] // 4,
            'l1d_tlb_refill_per_1k': group['l1d_tlb_refill_per_1k']['median'],
            'cyc_per_load': group['cyc_per_load']['median'],
            'dtlb_walk_per_1k': group['dtlb_walk_per_1k']['median'],
            'walk_samples': [s['dtlb_walk_per_1k'] for s in group['samples']],
        })
    return {'regimes': {str(key): {
        'knee': module.adjudicate_knee(rows), 'walk': module.detect_walk_onset(rows),
        'q3': module.adjudicate_q3(association_points=[r for rs in rows.values() for r in rs]),
    } for key, rows in by_regime.items()}, 'cohorts': module.grade_thp_cohorts(result.groups)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r2', type=Path, required=True)
    parser.add_argument('--main', type=Path, required=True)
    parser.add_argument('--baseline', default='a104dbf')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.r2))
    from analysis import sm8650_tlb as new
    from analysis.load import load_run
    from analysis.tests import test_sm8650_tlb as fixtures

    old_source = subprocess.check_output(
        ['git', 'show', f'{args.baseline}:analysis/sm8650_tlb.py'], cwd=args.r2, text=True)
    old = load_source('analysis._review_baseline_tlb', args.r2 / 'analysis/sm8650_tlb.py', old_source)
    chart = load_source('analysis.chart', args.main / 'analysis/chart.py')
    figures = load_source('analysis.tlb_figures', args.main / 'analysis/tlb_figures.py')
    registry = new.load_registry(args.r2 / 'configs/pmu-event-registry.json')
    report = {'r2_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.r2, text=True).strip(),
              'main_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.main, text=True).strip(),
              'baseline': args.baseline, 'synthetic': {}}

    for name, (_, _, field, _) in new._PMU_EVENTS.items():
        result = new.analyze_records([remove_metric(fixtures._record(), name)], 'SYNTHETIC-missing')
        group = result.groups[0]
        checks = {
            'contract': group['metric_contract'],
            'group_field': group[field],
            'markdown': attempt(lambda: new.build_markdown([result])),
            'markdown_samples': attempt(lambda: new.build_markdown([result], show_samples=True)),
            'cohort': attempt(lambda: new.grade_thp_cohorts(result.groups)),
            'main_chart_curve': attempt(lambda: figures.curve_from_groups(result.groups, field)),
        }
        row = {'pages': 32, 'l1d_tlb_refill_per_1k': None if field == 'l1d_tlb_refill_per_1k' else 1.0,
               'cyc_per_load': None if field == 'cyc_per_load' else 1.0,
               'dtlb_walk_per_1k': None if field == 'dtlb_walk_per_1k' else 1.0,
               'walk_samples': [None if field == 'dtlb_walk_per_1k' else 1.0] * 10}
        checks['detect_knee'] = attempt(lambda: new.detect_knee_candidates([row]))
        checks['adjudicate_knee_at_32_pages'] = attempt(lambda: new.adjudicate_knee({42: [row]}))
        checks['walk_onset'] = attempt(lambda: new.detect_walk_onset({42: [row]}))
        checks['q3'] = attempt(lambda: new.adjudicate_q3(association_points=[row]))
        checks['fixed_overhead_none_count'] = attempt(lambda: new.adjudicate_fixed_overhead([
            {'buffer_kb': 512, 'slots': 8192, 'loads': 65536, 'seed': 42, 'event': name, 'count': None}]))

        before = fixtures._anchor_run('before', fixtures._T0)
        after = fixtures._anchor_run('after', fixtures._T2)
        before.ok_records = [remove_metric(r, name) for r in before.ok_records]
        checks['anchor_missing_event'] = attempt(lambda: anchor_summary(new.validate_anchors(
            fixtures._block(before=before, after=after), registry)))
        main_run = fixtures._main_run('main', fixtures._T1)
        main_run.ok_records = [remove_metric(r, name) for r in main_run.ok_records]
        checks['main_missing_event_anchor_decoupling'] = attempt(lambda: anchor_summary(new.validate_anchors(
            fixtures._block(main=main_run, after=after), registry)))
        report['synthetic'][name] = checks

    full = fixtures._record(latencies=(100, 110), cycles=(6553600, 7208960), refills=(100, 110))
    degraded = remove_metric(fixtures._record(latencies=(1, 2)), 'pmu.cycles.count')
    mixed = new.analyze_records([full, degraded], 'SYNTHETIC-mixed-coverage')
    g = mixed.groups[0]
    report['mixed_coverage'] = {'samples': len(g['samples']), 'missing': g['metric_contract']['missing'],
                              'latency_stats': g['latency_ns'], 'cycles_stats': g['cyc_per_load'],
                              'available_cycles': sum(s['cyc_per_load'] is not None for s in g['samples']),
                              'chart_cycles': attempt(lambda: figures.curve_from_groups(mixed.groups, 'cyc_per_load'))}
    mixed_walk = new.analyze_records([fixtures._record(), remove_metric(fixtures._record(),
                        'pmu.dtlb_walk.count')], 'SYNTHETIC-mixed-walk')
    gw = mixed_walk.groups[0]
    report['mixed_walk_onset'] = attempt(lambda: new.detect_walk_onset({42: [{
        'pages': 128, 'dtlb_walk_per_1k': gw['dtlb_walk_per_1k']['median'],
        'walk_samples': [s['dtlb_walk_per_1k'] for s in gw['samples']]}]}))
    report['bimodal_none_markdown'] = attempt(lambda: new.build_markdown([
        dataclasses.replace(new.analyze_records([fixtures._record()], 'SYNTHETIC-bimodal'),
                            groups=[dict(new.analyze_records([fixtures._record()], 'SYNTHETIC-bimodal').groups[0], bimodal=None)])]))
    extra = fixtures._record()
    extra_metric = fixtures.TestMetricContract()._extra_metric()
    extra['metrics'].append(extra_metric)
    result = new.analyze_records([extra], 'SYNTHETIC-extra')
    report['extras_retention'] = {'contract': result.groups[0]['metric_contract'],
                                'sample_keys': sorted(result.groups[0]['samples'][0]),
                                'extra_value_retained': '8144' in repr(result)}

    runs_root = args.r2 / 'data/public/runs'
    paths = sorted(p.parent for p in runs_root.glob('*ptr-chase-sm8650-x4-tlb*/records.jsonl'))
    replay = []
    for path in paths:
        data = load_run(path)
        records = data.ok_records + data.failed_records
        a = attempt(lambda: normalize(old.analyze_records(records, path.name, registry)))
        b = attempt(lambda: normalize(new.analyze_records(records, path.name, registry)))
        identical = a == b
        markdown_equal = None
        if a['ok'] and b['ok']:
            markdown_equal = old.build_markdown([old.analyze_records(records, path.name, registry)], True) == new.build_markdown([
                new.analyze_records(records, path.name, registry)], True)
        judgments_equal = None
        judgments_ok = None
        if a['ok'] and b['ok']:
            ja = attempt(lambda: derived_judgments(old, old.analyze_records(records, path.name, registry)))
            jb = attempt(lambda: derived_judgments(new, new.analyze_records(records, path.name, registry)))
            judgments_ok = ja['ok'] and jb['ok']
            judgments_equal = judgments_ok and ja['value'] == jb['value']
        replay.append({'run': path.name, 'records': len(records), 'old_ok': a['ok'], 'new_ok': b['ok'],
                       'normalized_equal': identical, 'markdown_equal': markdown_equal, 'derived_judgments_equal': judgments_equal,
                       'derived_judgments_ok': judgments_ok,
                       **({'old_outcome': {k: v for k, v in a.items() if k != 'value'},
                           'new_outcome': {k: v for k, v in b.items() if k != 'value'}}
                          if not a['ok'] or not b['ok'] else {})})
    report['replay'] = replay
    report['replay_counts'] = {'runs': len(replay), 'equal': sum(r['normalized_equal'] for r in replay),
                               'changed': sum(not r['normalized_equal'] for r in replay),
                               'both_accept': sum(r['old_ok'] and r['new_ok'] for r in replay),
                               'both_reject': sum(not r['old_ok'] and not r['new_ok'] for r in replay),
                               'old_reject_new_accept': sum(not r['old_ok'] and r['new_ok'] for r in replay)}
    blocks = []
    data_runs = [load_run(path) for path in paths]
    for before, body, after in zip(data_runs, data_runs[1:], data_runs[2:]):
        if 'tlb-anchor' not in before.run_dir.name or 'tlb-anchor' in body.run_dir.name or 'tlb-anchor' not in after.run_dir.name:
            continue
        a = attempt(lambda: normalize(old.validate_anchors(old.group_block([before, body, after]), registry)))
        b = attempt(lambda: normalize(new.validate_anchors(new.group_block([before, body, after]), registry)))
        blocks.append({'main': body.run_dir.name, 'old_ok': a['ok'], 'new_ok': b['ok'],
                       'old_status': a.get('value', {}).get('status'), 'new_status': b.get('value', {}).get('status'),
                       'normalized_equal': a == b})
    report['block_replay'] = blocks

    scan, thp = figures.load_campaign(runs_root)
    graded = new.grade_thp_cohorts(thp)
    generated = figures.build_figures(scan, graded)
    generated['report.md'] = figures.build_report(graded)
    comparisons = {}
    figures.analyze_records = old.analyze_records
    old_scan, old_thp = figures.load_campaign(runs_root)
    old_graded = old.grade_thp_cohorts(old_thp)
    old_generated = figures.build_figures(old_scan, old_graded)
    old_generated['report.md'] = figures.build_report(old_graded)
    for name, content in generated.items():
        (args.out / name).write_text(content)
        comparisons[name] = {'bytes': len(content.encode()), 'sha256': hashlib.sha256(content.encode()).hexdigest(),
                              'equal_to_old_analyzer': content == old_generated[name]}
        if name.endswith('.svg'):
            ET.fromstring(content)
            comparisons[name]['circles'] = content.count('<circle')
    report['main_figures_real_data'] = comparisons
    figures.analyze_records = new.analyze_records
    chart_tests = load_source('analysis.tests.test_tlb_figures', args.main / 'analysis/tests/test_tlb_figures.py')
    with (args.out / 'overlay-chart-tests.log').open('w') as log:
        test_result = unittest.TextTestRunner(stream=log, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromModule(chart_tests))
    report['overlay_chart_tests'] = {'run': test_result.testsRun, 'failures': len(test_result.failures),
                                    'errors': len(test_result.errors)}
    (args.out / 'results.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({key: report[key] for key in ('r2_head', 'main_head', 'replay_counts',
                                                   'main_figures_real_data', 'overlay_chart_tests')}, indent=2))
    for name, checks in report['synthetic'].items():
        print(name, json.dumps({key: value for key, value in checks.items() if isinstance(value, dict) and value.get('ok') is False}))
    print('mixed_coverage', json.dumps(report['mixed_coverage']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
