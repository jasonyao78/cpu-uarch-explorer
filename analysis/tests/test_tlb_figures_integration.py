# SPDX-License-Identifier: Apache-2.0
"""M0-2 / main 图表集成：真实 loader/analyzer/CLI 消费缺指标记录。

复用图表合成数据集；只修改输入副本，不修改仓内测量档案。
"""
import json
from pathlib import Path
import tempfile
import unittest

from analysis import tlb_figures
from analysis.tests.test_tlb_figures import _make_dataset, _run_cli


class TestIntegratedMetricDegradation(unittest.TestCase):
    def _drop_walk(self, root, buffers):
        for name in (tlb_figures.RUN_COARSE, tlb_figures.RUN_DENSE):
            path = root / name / 'records.jsonl'
            records = [json.loads(line) for line in path.read_text().splitlines()]
            for record in records:
                if record['params']['buffer_kb'] in buffers:
                    record['metrics'] = [m for m in record['metrics']
                                         if m['name'] != 'pmu.dtlb_walk.count']
            path.write_text(''.join(json.dumps(r)+'\n' for r in records))

    def test_partial_missing_walk_renders_with_named_disclosure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, out = Path(tmp)/'runs', Path(tmp)/'out'
            _make_dataset(root)
            self._drop_walk(root, {128})
            rc, _, err = _run_cli(root, out)
            self.assertEqual(rc, 0, err)
            self.assertIn('degraded', err)
            self.assertIn('128', err)
            report = (out/'report.md').read_text()
            self.assertIn('数据局限', report)
            self.assertEqual((out/'walk-onset.svg').read_text().count('<circle'), 19)

    def test_missing_entire_onset_region_disclaims_historical_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, out = Path(tmp)/'runs', Path(tmp)/'out'
            _make_dataset(root)
            self._drop_walk(root, {10240, 12288})
            rc, _, err = _run_cli(root, out)
            self.assertEqual(rc, 0, err)
            report = (out/'report.md').read_text()
            self.assertIn('非本数据集重判', report)
            self.assertIn('数据局限', report)
