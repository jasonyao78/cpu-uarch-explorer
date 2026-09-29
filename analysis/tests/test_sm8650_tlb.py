# SPDX-License-Identifier: Apache-2.0
"""SM8650 X4 TLB 层级探测分析器测试（任务书 v4.1 §9.3）。

合成记录仿 `test_sm8650_x4_p0prime` 的 `_record` 模式（G0 事件组 + 逐
样本 seed/vma_base/backing 入档）。覆盖骨架契约：正控点对不被误报为
knee（§6.2.2 三条件不全满足时无候选）、`0x05` density >1000/1k 保留
原值不截断、注册表资格门控（未注册/CANDIDATE → SEMANTICS_UNVERIFIED
但不阻断采集）、multiplex 样本拒绝、全失败 run 进 rejected 不抛错、
契约缺项硬错误、注册表资格值白名单。
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from analysis.sm8650_tlb import (
    TlbError,
    analyze_records,
    build_markdown,
    detect_knee_candidates,
    load_registry,
    main,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REGISTRY = _REPO_ROOT / "configs" / "pmu-event-registry.json"

_PMU = {
    "pmu.cycles.count": (8, 0x11, [2000, 2100]),
    "pmu.mem_access_rd.count": (8, 0x66, [1000, 1000]),
    "pmu.l1d_tlb_refill.count": (8, 0x05, [300, 310]),
    "pmu.dtlb_walk.count": (8, 0x34, [1, 2]),
}

_QUALIFIED_ALL = [
    ("cycles", "0x11", "qualified"),
    ("mem_access_rd", "0x66", "qualified"),
    ("l1d_tlb_refill", "0x05", "qualified"),
    ("dtlb_walk", "0x34", "qualified"),
]


def _record(*, buffer_kb=512, loads=65536, seed=42, backing="base",
            latencies=(2.4, 4.4), cycles=None, refills=(300, 310),
            multiplexed=(), include_seed=True, include_vma=True) -> dict:
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
            **({"vma_base": f"0x7f3a{index:08x}"} if include_vma else {}),
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
        if name == "pmu.cycles.count" and cycles is not None:
            values = cycles
        if name == "pmu.l1d_tlb_refill.count":
            values = refills
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
                **({"vma_base": f"0x7f3a{index:08x}"} if include_vma else {}),
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


def _write_registry(path, entries):
    """entries 为 (name, config, qualification) 列表；写临时注册表并加载。"""
    document = {
        "schema_version": "1.0",
        "events": [
            {"type": 8, "config": config, "name": name,
             "qualification": qualification}
            for name, config, qualification in entries
        ],
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return load_registry(path)


def _rows(groups):
    """分组 → §6.2.2 输入点列（页数 = buffer/4KiB，升序，取组中位数）。"""
    return [
        {
            "pages": group["buffer_kb"] // 4,
            "l1d_tlb_refill_per_1k": group["l1d_tlb_refill_per_1k"]["median"],
            "cyc_per_load": group["cyc_per_load"]["median"],
        }
        for group in sorted(groups, key=lambda group: group["buffer_kb"])
    ]


class TestSamples(unittest.TestCase):
    def test_samples_carry_seed_backing_vma_and_derived_rates(self):
        result = analyze_records([_record()], "run-a")
        self.assertEqual(len(result.groups), 1)
        group = result.groups[0]
        self.assertEqual(group["seed"], 42)
        self.assertEqual(group["page_policy_actual"], "base")
        self.assertEqual(group["buffer_kb"], 512)
        self.assertEqual(group["ring_passes"], 8)  # loads=65536 = 8×8192 slots
        # 无注册表时 fail-closed：全部 PMU 事件资格不足（只降级结论）。
        self.assertEqual(group["unqualified_events"], sorted(_PMU))
        samples = group["samples"]
        self.assertEqual(len(samples), 2)
        first = samples[0]
        self.assertEqual(first["seed"], 42)
        self.assertEqual(first["vma_base"], "0x7f3a00000000")
        self.assertAlmostEqual(first["latency_ns"], 2.4)
        self.assertAlmostEqual(first["cyc_per_load"], 2000 / 65536)
        self.assertAlmostEqual(first["mem_rd_per_1k"], 1000 / 65536 * 1000)
        self.assertAlmostEqual(first["l1d_tlb_refill_per_1k"], 300 / 65536 * 1000)
        self.assertAlmostEqual(first["dtlb_walk_per_1k"], 1 / 65536 * 1000)

    def test_vma_base_optional_for_old_records(self):
        result = analyze_records([_record(include_vma=False)], "run-a")
        first = result.groups[0]["samples"][0]
        self.assertNotIn("vma_base", first)

    def test_refill_density_above_1000_per_1k_is_not_truncated(self):
        # §3.2：`0x05` 在 4096 页可超过 1000/1k（事件总数大于 timed
        # loads 数）——分析器保留原值，不截断、不改写为 miss 概率。
        record = _record(loads=4096, refills=(5000, 5200))
        result = analyze_records([record], "run-a")
        samples = result.groups[0]["samples"]
        self.assertAlmostEqual(
            samples[0]["l1d_tlb_refill_per_1k"], 5000 / 4096 * 1000
        )
        self.assertGreater(samples[0]["l1d_tlb_refill_per_1k"], 1000)
        median = result.groups[0]["l1d_tlb_refill_per_1k"]["median"]
        self.assertGreater(median, 1000)
        self.assertAlmostEqual(median, (5000 + 5200) / 2 / 4096 * 1000)


class TestKneeCandidates(unittest.TestCase):
    def test_positive_control_points_are_not_misreported_as_knee(self):
        """三条件不全满足即否决（§6.2.2 合取语义）。fixture 的页数档与
        refill 密度取正控量级（128/4096 页、≈288→1030/1k，对应 run
        20260927T182613Z 格局），但 cycles 是构造值：cyc/load 比值
        ≈1.05 <1.15，故无候选。注意真实正控点对的 cyc/load median 为
        6.633→16.216（比值 ≈2.44 ≥1.15），三条件**全满足**，按冻结规则
        会被提名——那是真阳性，不是误报；本测试钉的是门逻辑，不是对真
        实数据的复演。"""
        with tempfile.TemporaryDirectory() as tmp:
            registry = _write_registry(
                Path(tmp) / "registry.json", _QUALIFIED_ALL
            )
            result = analyze_records([
                _record(buffer_kb=512, loads=65536, latencies=(2.0, 2.0),
                        cycles=(131072, 131072), refills=(18874, 18874)),
                _record(buffer_kb=16384, loads=2097152, latencies=(2.1, 2.1),
                        cycles=(4404019, 4404019), refills=(2160066, 2160066)),
            ], "run-a", registry)
        self.assertEqual(len(result.groups), 2)
        self.assertEqual(result.groups[0]["unqualified_events"], [])
        rows = _rows(result.groups)
        self.assertEqual([row["pages"] for row in rows], [128, 4096])
        refill = [row["l1d_tlb_refill_per_1k"] for row in rows]
        cyc = [row["cyc_per_load"] for row in rows]
        self.assertGreaterEqual(refill[1] / refill[0], 2.0)   # ≈3.58
        self.assertGreaterEqual(refill[1] - refill[0], 50.0)  # ≈742
        self.assertLess(cyc[1] / cyc[0], 1.15)                # ≈1.05
        self.assertEqual(detect_knee_candidates(rows), [])

    def test_knee_candidate_requires_all_three_conditions(self):
        """三条件全满足才提名——反向锚定检测函数不是恒返回空。"""
        rows = [
            {"pages": 128, "l1d_tlb_refill_per_1k": 300.0, "cyc_per_load": 2.0},
            {"pages": 192, "l1d_tlb_refill_per_1k": 700.0, "cyc_per_load": 2.4},
        ]
        self.assertEqual(detect_knee_candidates(rows), [(128, 192)])

    def test_unqualified_event_gates_candidates_but_not_sampling(self):
        """未注册/CANDIDATE 事件 → SEMANTICS_UNVERIFIED：样本照常入表，
        但该组不得产出 knee 候选（采集不被资格门控阻断）。"""
        rows = [
            {"pages": 128, "l1d_tlb_refill_per_1k": 300.0, "cyc_per_load": 2.0},
            {"pages": 192, "l1d_tlb_refill_per_1k": 700.0, "cyc_per_load": 2.4},
        ]
        entries_by_case = {
            "unregistered": [e for e in _QUALIFIED_ALL if e[1] != "0x05"],
            "candidate": [
                ("cycles", "0x11", "qualified"),
                ("mem_access_rd", "0x66", "qualified"),
                ("l1d_tlb_refill", "0x05", "candidate"),
                ("dtlb_walk", "0x34", "qualified"),
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            for label, entries in entries_by_case.items():
                with self.subTest(label=label):
                    registry = _write_registry(
                        Path(tmp) / f"registry-{label}.json", entries
                    )
                    result = analyze_records([_record()], "run-a", registry)
                    group = result.groups[0]
                    self.assertEqual(len(group["samples"]), 2)
                    self.assertIn("pmu.l1d_tlb_refill.count",
                                  group["unqualified_events"])
                    self.assertNotIn("pmu.dtlb_walk.count",
                                     group["unqualified_events"])
                    self.assertEqual(
                        detect_knee_candidates(
                            rows,
                            unqualified_events=group["unqualified_events"],
                        ),
                        [],
                    )
                    markdown = build_markdown([result])
                    self.assertIn("l1d_tlb_refill", markdown)
        # 对照：资格齐全时同一点列会提名（防门控测试空心化）。
        self.assertEqual(detect_knee_candidates(rows), [(128, 192)])

    def test_multiplexed_sample_is_rejected_and_reported(self):
        result = analyze_records([_record(multiplexed=(1,))], "run-a")
        self.assertEqual(len(result.groups), 1)
        self.assertEqual(len(result.groups[0]["samples"]), 1)
        self.assertEqual(result.groups[0]["samples"][0]["sample_index"], 0)
        self.assertEqual(len(result.rejected), 1)
        self.assertIn("multiplexed", result.rejected[0])


class TestContractErrors(unittest.TestCase):
    def test_missing_seed_is_hard_error(self):
        with self.assertRaises(TlbError):
            analyze_records([_record(include_seed=False)], "run-a")

    def test_incoherent_contract_fields_are_hard_errors(self):
        cases = {}
        record = _record()
        record["metrics"] = record["metrics"][:-1]  # metric 集合缺 dtlb_walk
        cases["metric set mismatch"] = record
        record = _record()
        record["metrics"][1]["observations"][0]["pmu_config"] = 0x12
        cases["pmu encoding mismatch"] = record
        record = _record()
        record["metrics"][1]["observations"][0]["sample_index"] = 9
        cases["sample_index misaligned"] = record
        record = _record()
        record["metrics"][0]["observations"][0]["page_policy_actual"] = "weird"
        cases["unknown backing"] = record
        record = _record()
        record["params"]["stride"] = 0
        cases["zero stride"] = record
        for label, record in cases.items():
            with self.subTest(label=label), self.assertRaises(TlbError):
                analyze_records([record], "run-a")

    def test_vma_base_format_is_validated(self):
        # 与 runner/adapters/ptr_chase.py 同款契约：^0x[0-9a-f]+$。
        for bad in ("xyz", "0xAB12", "0X7f3a00000000"):
            record = _record()
            record["metrics"][0]["observations"][0]["vma_base"] = bad
            with self.subTest(vma_base=bad), self.assertRaises(TlbError):
                analyze_records([record], "run-a")


class TestRegistry(unittest.TestCase):
    def test_real_registry_qualifies_g0_tlb_events(self):
        registry = load_registry(_REGISTRY)
        self.assertEqual(registry.qualification(8, 0x05), "qualified")
        self.assertEqual(registry.qualification(8, 0x34), "qualified")
        self.assertIsNone(registry.qualification(8, 0xFFFF))  # 未注册

    def test_registry_rejects_bad_qualification_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            with self.subTest(qualification="verified"):
                with self.assertRaises(TlbError):
                    _write_registry(path, [("cycles", "0x11", "verified")])
            with self.subTest(config="not hex"):
                path.write_text(json.dumps({"events": [
                    {"type": 8, "config": "zz", "name": "x",
                     "qualification": "qualified"},
                ]}), encoding="utf-8")
                with self.assertRaises(TlbError):
                    load_registry(path)
            with self.subTest(duplicate="(type, config)"):
                path.write_text(json.dumps({"events": [
                    {"type": 8, "config": "0x11", "name": "a",
                     "qualification": "qualified"},
                    {"type": 8, "config": "0x11", "name": "b",
                     "qualification": "candidate"},
                ]}), encoding="utf-8")
                with self.assertRaises(TlbError):
                    load_registry(path)


class TestAllFailedRun(unittest.TestCase):
    def test_cli_reports_all_failed_run_without_raising(self):
        """全失败 run（如被环境门禁 fail-closed 的段）必须进统一报告：
        不得抛 TlbError，失败记录进 rejected 清单并可检索。"""
        record = _record()
        record["status"] = "failed"
        record["metrics"] = []
        record["failure"] = {
            "reason": "environment-precondition-failed",
            "detail": "cpufreq-max-mismatch:policy7",
        }
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = (
                Path(tmp)
                / "20260928T025226Z-ptr-chase-sm8650-x4-tlb-coarse"
            )
            run_dir.mkdir()
            (run_dir / "records.jsonl").write_text(
                json.dumps(record) + "\n", encoding="utf-8"
            )
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                rc = main(["--run", str(run_dir), "--registry", str(_REGISTRY)])
        self.assertEqual(rc, 0)
        output = buf.getvalue()
        self.assertIn("tlb-coarse", output)
        self.assertIn("environment-precondition-failed", output)


if __name__ == "__main__":
    unittest.main()
