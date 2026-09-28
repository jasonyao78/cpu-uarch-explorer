# SPDX-License-Identifier: Apache-2.0
"""P0″（demand/prefetch 复测）分析器测试。

合成记录覆盖本 retest 的证据契约：逐样本 seed/backing/ring passes 入档、
demand 与 prefetch 计数分离、multiplex 样本拒绝（保留其余样本）、
组内双峰标记。任何字段缺失都是硬错误——本复测不接受"大概齐全"。
"""

from __future__ import annotations

import unittest

from analysis.sm8650_x4_p0prime import (
    P0PrimeError,
    analyze_records,
    build_markdown,
)

_PMU = {
    "pmu.cycles.count": (8, 0x11, [2000, 2100]),
    "pmu.mem_access_rd.count": (8, 0x66, [1000, 1000]),
    "pmu.l1d_cache_miss.count": (8, 0x8144, [330, 961]),
    "pmu.l1d_cache_hwprf.count": (8, 0x8154, [670, 39]),
    "pmu.l2d_cache_miss.count": (8, 0x814C, [4, 22]),
    "pmu.l2d_cache_hwprf.count": (8, 0x8155, [100, 900]),
}


def _record(*, buffer_kb=512, loads=65536, seed=42, backing="base",
            latencies=(2.4, 4.4), l2_misses=(4, 22), multiplexed=(),
            include_seed=True) -> dict:
    slots = buffer_kb * 1024 // 64
    observations = []
    for index in range(len(latencies)):
        observations.append({
            "sample_index": index,
            "value": latencies[index],
            "raw_sample_ref": f"raw:{index}",
            "page_policy_requested": "base-madvise",
            "page_policy_actual": backing,
            "anon_huge_kb": 0,
            "page_kb": 4,
            **({"seed": seed} if include_seed else {}),
        })
    metrics = [{
        "name": "latency_ns",
        "value": 1.0,
        "unit": "ns",
        "repetitions": len(latencies),
        "observations": observations,
    }]
    n = len(latencies)
    for name, (typ, config, values) in _PMU.items():
        if name == "pmu.l2d_cache_miss.count":
            values = l2_misses
        obs = []
        for index in range(n):
            running = 0 if index in multiplexed else 1000
            obs.append({
                "sample_index": index,
                "value": values[index % len(values)],
                "raw_sample_ref": f"raw:{index}",
                "pmu_type": typ,
                "pmu_config": config,
                "time_enabled_ns": 1000,
                "time_running_ns": running,
                "page_policy_requested": "base-madvise",
                "page_policy_actual": backing,
                "anon_huge_kb": 0,
                **({"seed": seed} if include_seed else {}),
            })
        metrics.append({
            "name": name,
            "value": 0,
            "unit": "events",
            "repetitions": n,
            "observations": obs,
        })
    return {
        "schema_version": "2.0",
        "status": "ok",
        "target": {"target_id": "redmi-k70pro-01"},
        "probe": {"name": "ptr_chase", "protocol_version": "1.2"},
        "params": {
            "buffer_kb": buffer_kb,
            "loads": loads,
            "stride": 64,
            "warmup_passes": 2,
            "base_pages": 1,
            "seed": seed,
        },
        "metrics": metrics,
    }


class TestSamples(unittest.TestCase):
    def test_samples_carry_seed_backing_passes_and_derived_rates(self):
        result = analyze_records([_record()], "run-a")
        self.assertEqual(len(result.groups), 1)
        group = result.groups[0]
        self.assertEqual(group["seed"], 42)
        self.assertEqual(group["page_policy_actual"], "base")
        self.assertEqual(group["buffer_kb"], 512)
        self.assertEqual(group["ring_passes"], 8)  # loads=65536 = 8×8192 slots
        samples = group["samples"]
        self.assertEqual(len(samples), 2)
        first = samples[0]
        self.assertEqual(first["seed"], 42)
        self.assertAlmostEqual(first["latency_ns"], 2.4)
        self.assertAlmostEqual(first["cyc_per_load"], 2000 / 65536)
        self.assertAlmostEqual(first["mem_rd_per_1k"], 1000 / 65536 * 1000)
        self.assertAlmostEqual(first["l1d_miss_per_1k"], 330 / 65536 * 1000)
        self.assertAlmostEqual(first["l1d_hwprf_per_1k"], 670 / 65536 * 1000)
        self.assertAlmostEqual(first["l2d_miss_per_1k"], 4 / 65536 * 1000)
        self.assertAlmostEqual(first["l2d_hwprf_per_1k"], 100 / 65536 * 1000)

    def test_multiplexed_sample_is_rejected_and_reported(self):
        record = _record(multiplexed=(1,))
        result = analyze_records([record], "run-a")
        self.assertEqual(len(result.groups), 1)
        self.assertEqual(len(result.groups[0]["samples"]), 1)
        self.assertEqual(result.groups[0]["samples"][0]["sample_index"], 0)
        self.assertEqual(len(result.rejected), 1)
        self.assertIn("multiplexed", result.rejected[0])

    def test_grouping_splits_by_seed_and_backing(self):
        records = [
            _record(seed=42),
            _record(seed=7),
            _record(seed=42, backing="mixed"),
        ]
        result = analyze_records(records, "run-a")
        keys = {(g["seed"], g["page_policy_actual"]) for g in result.groups}
        self.assertEqual(keys, {(42, "base"), (7, "base"), (42, "mixed")})

    def test_bimodality_flag_on_split_samples(self):
        split = _record(
            seed=7,
            latencies=(2.0, 2.1, 5.0, 5.1),
            l2_misses=(30, 30, 860, 864),
            loads=65536,
        )
        clean = _record()
        result = analyze_records([split, clean], "run-a")
        by_n = {len(g["samples"]): g for g in result.groups}
        self.assertTrue(by_n[4]["bimodal"])
        self.assertFalse(by_n[2]["bimodal"])

    def test_missing_seed_is_hard_error(self):
        with self.assertRaises(P0PrimeError):
            analyze_records([_record(include_seed=False)], "run-a")

    def test_long_training_ring_passes(self):
        record = _record(loads=512 * 8192)
        result = analyze_records([record], "run-a")
        self.assertEqual(result.groups[0]["ring_passes"], 512)

    def test_markdown_contains_group_keys(self):
        result = analyze_records([_record(), _record(seed=7)], "run-a")
        markdown = build_markdown([result])
        self.assertIn("512", markdown)
        self.assertIn("seed=42", markdown)
        self.assertIn("seed=7", markdown)
        self.assertIn("run-a", markdown)


if __name__ == "__main__":
    unittest.main()
