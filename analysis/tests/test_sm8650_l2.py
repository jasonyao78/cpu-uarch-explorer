# SPDX-License-Identifier: Apache-2.0
"""SM8650 X4 L2 校准分析测试。

合成记录刻意把 base/mixed 后备放在同一个 case 内，确保分析层按
sample_index 联结指标、按实际后备拆组，而不是复用 case 聚合中位数。
"""

from __future__ import annotations

import unittest

from analysis.sm8650_l2 import CalibrationError, analyze_records, build_markdown


_PMU = {
    "pmu.cycles.count": (8, 0x11, [1000, 1200]),
    "pmu.l2d_cache_refill.count": (8, 0x17, [100, 240]),
    "pmu.l3d_cache_refill.count": (8, 0x2A, [10, 24]),
    "pmu.dtlb_walk.count": (8, 0x34, [2, 6]),
}


def _record() -> dict:
    observations = [
        {
            "sample_index": 0,
            "value": 2.0,
            "raw_sample_ref": "raw:0",
            "page_policy_requested": "thp-madvise",
            "page_policy_actual": "base",
            "anon_huge_kb": 0,
            "page_kb": 4,
        },
        {
            "sample_index": 1,
            "value": 4.0,
            "raw_sample_ref": "raw:1",
            "page_policy_requested": "thp-madvise",
            "page_policy_actual": "mixed",
            "anon_huge_kb": 2048,
            "page_kb": 4,
        },
    ]
    metrics = [{
        "name": "latency_ns",
        "unit": "ns",
        "repetitions": 2,
        "observations": observations,
    }]
    for name, (pmu_type, config, values) in _PMU.items():
        metrics.append({
            "name": name,
            "unit": "count",
            "repetitions": 2,
            "observations": [
                {
                    "sample_index": i,
                    "value": value,
                    "raw_sample_ref": f"raw:{i}",
                    "pmu_type": pmu_type,
                    "pmu_config": config,
                    "time_enabled_ns": 100,
                    "time_running_ns": 100,
                }
                for i, value in enumerate(values)
            ],
        })
    return {
        "schema_version": "2.0",
        "status": "ok",
        "target": {"target_id": "redmi-k70pro-01"},
        "probe": {"name": "ptr_chase", "protocol_version": "1.2"},
        "params": {"buffer_kb": 2304, "loads": 1000},
        "metrics": metrics,
    }


class TestAnalyzeRecords(unittest.TestCase):
    def test_aligns_samples_and_splits_actual_backing(self):
        groups = analyze_records([_record()], run_label="thp-request")

        self.assertEqual(
            [(g["buffer_kb"], g["page_policy_actual"], g["n"]) for g in groups],
            [(2304, "base", 1), (2304, "mixed", 1)],
        )
        base, mixed = groups
        self.assertEqual(base["latency_ns"]["median"], 2.0)
        self.assertEqual(base["cycles_per_load"]["median"], 1.0)
        self.assertEqual(base["l2_refills_per_1k_loads"]["median"], 100.0)
        self.assertEqual(mixed["l2_refills_per_1k_loads"]["median"], 240.0)
        self.assertEqual(mixed["anon_huge_kb"]["median"], 2048)

    def test_rejects_observation_index_drift(self):
        record = _record()
        record["metrics"][1]["observations"][1]["sample_index"] = 7
        with self.assertRaisesRegex(CalibrationError, "sample_index"):
            analyze_records([record], run_label="thp-request")

    def test_rejects_multiplexed_pmu_sample(self):
        record = _record()
        record["metrics"][1]["observations"][0]["time_running_ns"] = 99
        with self.assertRaisesRegex(CalibrationError, "multiplex"):
            analyze_records([record], run_label="thp-request")

    def test_rejects_missing_metric(self):
        record = _record()
        record["metrics"].pop()
        with self.assertRaisesRegex(CalibrationError, "metric set"):
            analyze_records([record], run_label="thp-request")

    def test_rejects_wrong_target_or_protocol(self):
        record = _record()
        record["probe"]["protocol_version"] = "1.1"
        with self.assertRaisesRegex(CalibrationError, "protocol"):
            analyze_records([record], run_label="thp-request")

    def test_markdown_keeps_backing_visible(self):
        markdown = build_markdown(analyze_records([_record()], run_label="thp-request"))
        self.assertIn("thp-request", markdown)
        self.assertIn("| 2304 | base | 1 |", markdown)
        self.assertIn("| 2304 | mixed | 1 |", markdown)
        self.assertIn("L2 refill/1k loads", markdown)


if __name__ == "__main__":
    unittest.main()
