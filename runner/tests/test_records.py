# SPDX-License-Identifier: Apache-2.0
"""统计与落盘契约：分位数正确性、JSONL 持久追加、原子写、record 条件字段。"""

import json
import tempfile
import unittest
from pathlib import Path

from runner.records import JsonlWriter, build_run_record, write_json_atomic
from runner.statistics import summarize


class TestStatistics(unittest.TestCase):
    def test_median_and_percentiles(self):
        stats = summarize([5.0, 1.0, 3.0, 2.0, 4.0])
        self.assertEqual(stats["median"], 3.0)
        self.assertEqual(stats["min"], 1.0)
        self.assertEqual(stats["max"], 5.0)
        self.assertAlmostEqual(stats["p25"], 2.0)
        self.assertAlmostEqual(stats["p75"], 4.0)

    def test_single_sample(self):
        stats = summarize([1.5])
        self.assertEqual(stats["median"], 1.5)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            summarize([])


class TestRecordShape(unittest.TestCase):
    BASE = dict(target={"os": "darwin"}, probe={"name": "p"}, environment={},
                params={}, params_provenance={}, raw_command="true")

    def test_ok_record_has_metrics(self):
        r = build_run_record(status="ok", metrics=[{"name": "m", "value": 1.0, "unit": "ns"}], **self.BASE)
        self.assertEqual(r["schema_version"], "2.0")
        self.assertNotIn("failure", r)

    def test_failed_record_has_failure_and_empty_metrics(self):
        r = build_run_record(status="failed", metrics=[],
                             failure={"reason": "probe-exit-1"}, **self.BASE)
        self.assertEqual(r["metrics"], [])
        self.assertEqual(r["failure"]["reason"], "probe-exit-1")


class TestPersistence(unittest.TestCase):
    def test_jsonl_append_durable(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "records.jsonl"
            w = JsonlWriter(p)
            w.append({"a": 1})
            w.append({"a": 2})
            w.close()
            lines = p.read_text().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[1])["a"], 2)

    def test_atomic_write_no_partial_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.json"
            write_json_atomic(p, {"x": 1})
            self.assertEqual(json.loads(p.read_text())["x"], 1)
            self.assertFalse((Path(d) / "m.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
