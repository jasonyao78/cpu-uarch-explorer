# SPDX-License-Identifier: Apache-2.0
"""SM8650 X4 TLB 层级探测分析器测试（任务书 v4.1 §9.3）。

合成记录仿 `test_sm8650_x4_p0prime` 的 `_record` 模式（G0 事件组 + 逐
样本 seed/vma_base/backing 入档）。覆盖骨架契约：正控点对不被误报为
knee（§6.2.2 三条件不全满足时无候选）、`0x05` density >1000/1k 保留
原值不截断、注册表资格门控（未注册/CANDIDATE → SEMANTICS_UNVERIFIED
但不阻断采集）、multiplex 样本拒绝、全失败 run 进 rejected 不抛错、
契约缺项硬错误、注册表资格值白名单；以及终态机：§6.2.2 候选 + §6.2.8-1
左删失优先 + §6.2.6 稳定条件（adjudicate_knee）、§6.2.3 walk-onset
（detect_walk_onset）、双峰标记（§9.2 复用 p0prime 预注册规则）；
以及块机制：§6.4 三块归组（group_block，experiment_id 定角色 +
probe SHA-256/target/时序关联证据）与 §6.2.5 锚点判据
（validate_anchors：环境门禁、latency/cyc 对照 short-base 参照 ≤3%、
512 KiB R 值落正控 [p25,p75]、3072 KiB 首块自校准、前后锚点互判）。
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
    adjudicate_knee,
    analyze_records,
    build_markdown,
    detect_knee_candidates,
    detect_walk_onset,
    group_block,
    load_registry,
    main,
    validate_anchors,
)
from analysis import sm8650_tlb
from analysis.load import RunData
from runner.statistics import summarize

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


_COARSE_PAGES = (32, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 2048,
                 4096, 8192)  # §6.2.1 粗扫页序


def _knee_rows(refills, cycs):
    """§6.2.1 页序上的 (R_0x05 /1k, cyc/load) 中位数曲线 → adjudicate_knee 行。"""
    assert len(refills) == len(cycs) == len(_COARSE_PAGES)
    return [
        {"pages": pages, "l1d_tlb_refill_per_1k": refill, "cyc_per_load": cyc}
        for pages, refill, cyc in zip(_COARSE_PAGES, refills, cycs)
    ]


def _walk_rows(points):
    """(pages, R_0x34 median /1k, 逐样本 R_0x34 列) → detect_walk_onset 行。

    注意 median 与 walk_samples 是两个独立输入字段（前者为调用方给的
    页数点中位数统计，后者为逐进程值），不是派生关系——fixture 里两
    者独立构造，与真实调用方（分别取组 median 与逐样本列）一致。
    """
    return [
        {"pages": pages, "dtlb_walk_per_1k": median, "walk_samples": list(samples)}
        for pages, median, samples in points
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


_SINGLE_KNEE_REFILLS = [10, 11, 12, 14, 100, 105, 110, 115, 120, 125,
                        130, 135, 140]
_SINGLE_KNEE_CYCS = [2.0] * 4 + [2.4] * 9


class TestAdjudicateKnee(unittest.TestCase):
    """§6.2.2 候选 + §6.2.8-1 左删失优先 + §6.2.6 稳定条件的终态机。"""

    def test_single_knee_interval_identified(self):
        # ①单膝点：§6.2.1 页序下仅 128→192 三条件全满足。
        rows = _knee_rows(_SINGLE_KNEE_REFILLS, _SINGLE_KNEE_CYCS)
        verdict = adjudicate_knee({42: rows}, seed_coverage=3,
                                  training_coverage=2)
        self.assertEqual(verdict["status"], "INTERVAL_IDENTIFIED")
        self.assertEqual(verdict["intervals"], [(128, 192)])
        self.assertEqual(verdict["evidence"]["per_seed"][42]["candidates"],
                         [(128, 192)])

    def test_double_knee_intervals_listed_separately(self):
        # ②双膝点：128→192 与 1024→2048 分别列出（§6.2.2 多候选）。
        rows = _knee_rows(
            [10, 11, 12, 14, 100, 105, 110, 115, 120, 125, 300, 305, 310],
            [2.0] * 4 + [2.4] * 6 + [2.9] * 3,
        )
        verdict = adjudicate_knee({42: rows}, seed_coverage=4,
                                  training_coverage=2)
        self.assertEqual(verdict["status"], "INTERVAL_IDENTIFIED")
        self.assertEqual(verdict["intervals"], [(128, 192), (1024, 2048)])

    def test_continuous_rise_is_right_censored(self):
        # ③无膝点：连续上升但任一点对三条件都不全满足 → RIGHT_CENSORED。
        rows = _knee_rows(
            [10, 12, 15, 19, 24, 30, 38, 48, 60, 75, 95, 120, 150],
            [2.0 + 0.1 * k for k in range(13)],
        )
        verdict = adjudicate_knee({42: rows}, seed_coverage=4,
                                  training_coverage=2)
        self.assertEqual(verdict["status"], "RIGHT_CENSORED")
        self.assertEqual(verdict["intervals"], [])

    def test_left_censor_precedes_knee_detection(self):
        # ④R_0x05(32 页)=120/1k ≥100 → LEFT_CENSORED，先于 knee 检测执行
        # （§6.2.8-1）：即使 128→192 满足三条件也不提名。
        rows = _knee_rows(
            [120, 122, 125, 130, 300, 305, 310, 315, 320, 325, 330, 335, 340],
            [2.0] * 4 + [2.5] * 9,
        )
        # 防空心化：同一曲线若走到 §6.2.2 本会提名 (128, 192)。
        self.assertEqual(detect_knee_candidates(rows), [(128, 192)])
        verdict = adjudicate_knee({42: rows}, seed_coverage=4,
                                  training_coverage=2)
        self.assertEqual(verdict["status"], "LEFT_CENSORED")
        self.assertEqual(verdict["intervals"], [])
        per_seed = verdict["evidence"]["per_seed"][42]
        self.assertTrue(per_seed["left_censored"])
        self.assertEqual(per_seed["floor_refill_per_1k"], 120)

    def test_phase_a_coverage_naturally_yields_sensitive_terminals(self):
        # §6.2.6：seed/训练覆盖参数缺省时按输入曲线计 seed 覆盖、训练覆
        # 盖=1——Phase A 粗扫（2 seed × 短训练）进来自然落在敏感终态。
        rows = _knee_rows(_SINGLE_KNEE_REFILLS, _SINGLE_KNEE_CYCS)
        one_seed = adjudicate_knee({42: rows})
        self.assertEqual(one_seed["status"], "ORDER_SENSITIVE")
        self.assertEqual(one_seed["evidence"]["seed_coverage"], 1)
        two_seeds = adjudicate_knee({42: rows, 7: rows})
        self.assertEqual(two_seeds["status"], "ORDER_SENSITIVE")
        self.assertEqual(two_seeds["evidence"]["seed_coverage"], 2)
        three_seeds = adjudicate_knee({42: rows, 7: rows, 1337: rows})
        self.assertEqual(three_seeds["status"], "TRAINING_SENSITIVE")
        self.assertEqual(three_seeds["evidence"]["training_coverage"], 1)
        stable = adjudicate_knee({42: rows, 7: rows, 1337: rows},
                                 training_coverage=2)
        self.assertEqual(stable["status"], "INTERVAL_IDENTIFIED")
        self.assertEqual(stable["intervals"], [(128, 192)])

    def test_disjoint_seed_candidates_are_order_sensitive(self):
        # 3 个 seed 但候选区间互不重叠（重叠计数最大 2，不足 ≥3/4）→ 仍
        # ORDER_SENSITIVE（§6.2.6 要求致密区间相互重叠）。
        knee_low = _knee_rows(_SINGLE_KNEE_REFILLS, _SINGLE_KNEE_CYCS)
        knee_high = _knee_rows(
            [10, 11, 12, 14, 16, 17, 18, 19, 20, 21, 100, 105, 110],
            [2.0] * 10 + [2.4] * 3,
        )
        verdict = adjudicate_knee({42: knee_low, 7: knee_high, 1337: knee_low},
                                  training_coverage=2)
        self.assertEqual(verdict["status"], "ORDER_SENSITIVE")
        self.assertEqual(verdict["evidence"]["seed_coverage"], 2)
        self.assertEqual(verdict["intervals"], [(128, 192), (1024, 2048)])

    def test_unqualified_events_gate_to_semantics_unverified(self):
        rows = _knee_rows(_SINGLE_KNEE_REFILLS, _SINGLE_KNEE_CYCS)
        verdict = adjudicate_knee(
            {42: rows}, seed_coverage=4, training_coverage=2,
            unqualified_events=["pmu.l1d_tlb_refill.count"],
        )
        self.assertEqual(verdict["status"], "SEMANTICS_UNVERIFIED")
        self.assertEqual(verdict["intervals"], [])

    def test_empty_input_is_open(self):
        verdict = adjudicate_knee({})
        self.assertEqual(verdict["status"], "OPEN")
        self.assertEqual(verdict["intervals"], [])

    def test_empty_seed_rows_are_treated_as_missing(self):
        # {seed: []}（seed 在、数据空）按缺失 seed 处理：不计入覆盖数、
        # 不进 per_seed（登记 empty_seeds）；全部 seed 空 → OPEN。
        rows = _knee_rows(_SINGLE_KNEE_REFILLS, _SINGLE_KNEE_CYCS)
        verdict = adjudicate_knee({42: [], 7: []})
        self.assertEqual(verdict["status"], "OPEN")
        self.assertEqual(verdict["intervals"], [])
        mixed = adjudicate_knee({42: rows, 7: []})
        self.assertEqual(mixed["status"], "ORDER_SENSITIVE")  # 只算 seed 42
        self.assertEqual(mixed["evidence"]["seed_coverage"], 1)
        self.assertNotIn(7, mixed["evidence"]["per_seed"])
        self.assertEqual(mixed["evidence"]["empty_seeds"], [7])

    def test_knee_evidence_reports_scan_max_pages(self):
        # RIGHT_CENSORED 的扫描上界须可审计（per_seed 带 scan_max_pages，
        # 与 walk evidence 对齐）。
        rows = _knee_rows(
            [10, 12, 15, 19, 24, 30, 38, 48, 60, 75, 95, 120, 150],
            [2.0 + 0.1 * k for k in range(13)],
        )
        verdict = adjudicate_knee({42: rows}, seed_coverage=4,
                                  training_coverage=2)
        self.assertEqual(verdict["status"], "RIGHT_CENSORED")
        per_seed = verdict["evidence"]["per_seed"][42]
        self.assertEqual(per_seed["scan_max_pages"], 8192)


class TestWalkOnset(unittest.TestCase):
    """§6.2.3 walk-onset 三条件 + §6.2.8-5 逐 seed 地板判定。"""

    def test_walk_onset_detected_with_persistence(self):
        # ⑤三条件全满足且有持续性：2048 起 R_0x34 ≥1.0、≥8/10 样本
        # >0.5/1k，下一页数点同样满足 → onset 区间 (2048, 4096)；
        # 两个 order_seed 各自判定（§6.2.8-5）且一致。
        rows = _walk_rows([
            (1024, 0.4, [0.4] * 10),
            (2048, 1.2, [0.6] * 9 + [0.4]),
            (4096, 1.5, [0.8] * 10),
            (8192, 2.0, [1.0] * 10),
        ])
        verdict = detect_walk_onset({42: rows, 7: rows})
        self.assertEqual(verdict["status"], "INTERVAL_IDENTIFIED")
        self.assertEqual(verdict["intervals"], [(2048, 4096)])
        self.assertEqual(verdict["evidence"]["per_seed"][42]["onset"],
                         (2048, 4096))

    def test_single_seed_onset_is_order_sensitive(self):
        # 单 seed 输入即使三条件全满足也不晋升 INTERVAL_IDENTIFIED——
        # 晋升需 ≥2 个 seed 的曲线都满足且一致（有意取舍：顺序敏感是
        # 本任务核心风险，冻结规则纪律下宁可保守降级）。
        rows = _walk_rows([
            (1024, 0.4, [0.4] * 10),
            (2048, 1.2, [0.6] * 9 + [0.4]),
            (4096, 1.5, [0.8] * 10),
            (8192, 2.0, [1.0] * 10),
        ])
        verdict = detect_walk_onset({42: rows})
        self.assertEqual(verdict["status"], "ORDER_SENSITIVE")
        self.assertEqual(verdict["intervals"], [(2048, 4096)])
        self.assertEqual(verdict["evidence"]["per_seed"][42]["onset"],
                         (2048, 4096))

    def test_empty_seed_rows_are_treated_as_missing(self):
        # {seed: []}（seed 在、数据空）按缺失 seed 处理：不进一致性判
        # 定与 per_seed（登记 empty_seeds）；全部 seed 空 → OPEN。混合
        # 时只余一个有效 seed → 同单 seed 护栏，不晋升。
        rows = _walk_rows([
            (2048, 1.2, [0.6] * 9 + [0.4]),
            (4096, 1.5, [0.8] * 10),
        ])
        verdict = detect_walk_onset({42: [], 7: []})
        self.assertEqual(verdict["status"], "OPEN")
        self.assertEqual(verdict["intervals"], [])
        mixed = detect_walk_onset({42: rows, 7: []})
        self.assertEqual(mixed["status"], "ORDER_SENSITIVE")
        self.assertNotIn(7, mixed["evidence"]["per_seed"])
        self.assertEqual(mixed["evidence"]["empty_seeds"], [7])

    def test_single_point_without_persistence_is_not_onset(self):
        # ⑥仅单点满足、下一页数点回落 → 不报 onset；8192 单点满足也
        # 无"下一页数点"可证持续 → 同样不报，终态 RIGHT_CENSORED。
        rows = _walk_rows([
            (1024, 0.4, [0.4] * 10),
            (2048, 1.2, [0.6] * 9 + [0.4]),
            (4096, 0.3, [0.3] * 10),
            (8192, 2.0, [1.0] * 10),
        ])
        verdict = detect_walk_onset({42: rows})
        self.assertEqual(verdict["status"], "RIGHT_CENSORED")
        self.assertEqual(verdict["intervals"], [])
        self.assertIsNone(verdict["evidence"]["per_seed"][42]["onset"])

    def test_floor_rule_requires_8_of_10_samples_per_seed(self):
        # §6.2.8-5：median ≥1.0 不够——同一 order_seed 自己的 10 进程里
        # ≥8 个 >0.5/1k 才算地板分离（此处 7/10 → 该点不合格）。
        rows = _walk_rows([
            (2048, 5.0, [5.0] * 7 + [0.1] * 3),
            (4096, 1.5, [0.8] * 10),
            (8192, 0.2, [0.2] * 10),
        ])
        verdict = detect_walk_onset({42: rows})
        self.assertEqual(verdict["status"], "RIGHT_CENSORED")
        point = verdict["evidence"]["per_seed"][42]["points"][0]
        self.assertEqual(point["pages"], 2048)
        self.assertEqual(point["floor_samples"], 7)
        self.assertFalse(point["qualified"])

    def test_boundary_point_unsatisfied_is_right_censored(self):
        # ⑦边界点：8192 仍未满足（median 0.95 <1.0）→ RIGHT_CENSORED。
        rows = _walk_rows([
            (1024, 0.4, [0.4] * 10),
            (4096, 0.9, [0.9] * 10),
            (8192, 0.95, [0.95] * 10),
        ])
        verdict = detect_walk_onset({42: rows})
        self.assertEqual(verdict["status"], "RIGHT_CENSORED")
        self.assertEqual(verdict["intervals"], [])

    def test_disagreeing_seeds_are_order_sensitive(self):
        # 两 seed onset 区间不一致 → ORDER_SENSITIVE（逐 seed 判定后区间
        # 一致才可报告，同 §6.2.6 的跨 seed 稳定精神）。
        low = _walk_rows([
            (2048, 1.2, [0.6] * 9 + [0.4]),
            (4096, 1.5, [0.8] * 10),
            (8192, 2.0, [1.0] * 10),
        ])
        high = _walk_rows([
            (2048, 0.3, [0.3] * 10),
            (4096, 1.5, [0.8] * 10),
            (8192, 2.0, [1.0] * 10),
        ])
        verdict = detect_walk_onset({42: low, 7: high})
        self.assertEqual(verdict["status"], "ORDER_SENSITIVE")
        self.assertEqual(verdict["intervals"], [(2048, 4096), (4096, 8192)])

    def test_unqualified_events_gate_to_semantics_unverified(self):
        rows = _walk_rows([
            (2048, 1.2, [0.6] * 9 + [0.4]),
            (4096, 1.5, [0.8] * 10),
        ])
        verdict = detect_walk_onset({42: rows},
                                    unqualified_events=["pmu.dtlb_walk.count"])
        self.assertEqual(verdict["status"], "SEMANTICS_UNVERIFIED")
        self.assertEqual(verdict["intervals"], [])

    def test_empty_input_is_open(self):
        verdict = detect_walk_onset({})
        self.assertEqual(verdict["status"], "OPEN")
        self.assertEqual(verdict["intervals"], [])


class TestBimodalFlag(unittest.TestCase):
    """双峰标记（§9.2 复用契约）：移植 p0prime 预注册规则，目标字段钉为
    l1d_tlb_refill_per_1k（knee 判据消费字段）。"""

    def test_clear_bimodal_group_is_flagged(self):
        # 低簇 3 样本、高簇 3 样本，排序相邻比 9 ≥4 且两侧各 ≥2 → bimodal。
        record = _record(latencies=(2.0,) * 6,
                         refills=(100, 100, 100, 900, 900, 900))
        result = analyze_records([record], "run-a")
        self.assertTrue(result.groups[0]["bimodal"])
        markdown = build_markdown([result])
        header = next(line for line in markdown.splitlines()
                      if line.startswith("| run |"))
        self.assertIn("bimodal", header)
        self.assertIn("| YES |", markdown)

    def test_clean_group_is_not_flagged(self):
        record = _record(latencies=(2.0,) * 4, refills=(295, 300, 305, 310))
        result = analyze_records([record], "run-a")
        self.assertFalse(result.groups[0]["bimodal"])
        self.assertIn("| no |", build_markdown([result]))

    def test_zero_values_do_not_trigger_bimodal(self):
        # 排序 [0, 0, x, x]：唯一满足两侧各 ≥2 的分割低侧为 0，比值未定
        # 义 → 跳过（移植规则：零值不参与标记）。
        record = _record(latencies=(2.0,) * 4, refills=(0, 0, 900, 900))
        result = analyze_records([record], "run-a")
        self.assertFalse(result.groups[0]["bimodal"])


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


# ---------------------------------------------------------------------------
# §6.4/§6.2.5 块归组与锚点判定 fixture
#
# 参照期望值现场从真实 evidence run 独立重算（本文件自己的 JSON 解析路
# 径 + runner.statistics.summarize 口径），不写死数字——冻结规则要求参
# 照现读现算（仓内数据修正走 revision history，硬编码会静默过期）。测
# 试钉的是模块计算的正确性（两路独立计算逐位一致），不是常量值；参照
# run 修正后期望值自动跟踪。
# ---------------------------------------------------------------------------

_SHORT_BASE_RUN = "20260928T024022Z-ptr-chase-sm8650-x4-p0prime-short-base"
_CTRL_RUN = "20260927T182613Z-ptr-chase-sm8650-x4-pmu-ctrl-tlb"


def _evidence_group_stats(run_label, buffer_kb, metric, per_loads_scale):
    """参照 run 同 buffer 组逐样本统计（独立重算，不经过被测模块）。"""
    path = (_REPO_ROOT / "data" / "public" / "runs" / run_label
            / "records.jsonl")
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("status") != "ok":
            continue
        params = record.get("params", {})
        if params.get("buffer_kb") != buffer_kb:
            continue
        by_name = {entry["name"]: entry for entry in record["metrics"]}
        for observation in by_name[metric]["observations"]:
            value = observation["value"]
            if per_loads_scale is not None:
                value = value / params["loads"] * per_loads_scale
            values.append(value)
    return summarize(values)


def _reference_expectations():
    """§6.2.5 参照期望值：short-base 512/3072 KiB 组 median（latency 与
    cyc/load）+ 正控 512 KiB 组 R 值 [p25, p75] 与 median。"""
    expectations = {"medians": {}, "r512_p25_p75": {}, "r512_median": {}}
    for buffer_kb in (512, 3072):
        expectations["medians"][buffer_kb] = {
            "latency_ns": _evidence_group_stats(
                _SHORT_BASE_RUN, buffer_kb, "latency_ns", None)["median"],
            "cyc_per_load": _evidence_group_stats(
                _SHORT_BASE_RUN, buffer_kb, "pmu.cycles.count", 1.0)["median"],
        }
    for metric, field in (
        ("pmu.l1d_tlb_refill.count", "l1d_tlb_refill_per_1k"),
        ("pmu.dtlb_walk.count", "dtlb_walk_per_1k"),
    ):
        stats = _evidence_group_stats(_CTRL_RUN, 512, metric, 1000.0)
        expectations["r512_p25_p75"][field] = (stats["p25"], stats["p75"])
        expectations["r512_median"][field] = stats["median"]
    return expectations


_REF = _reference_expectations()  # import 时现读现算一次

_ANCHOR_ID = "ptr-chase-sm8650-x4-tlb-anchor"  # §6.4：锚点 experiment_id
_MAIN_ID = "ptr-chase-sm8650-x4-tlb-coarse"
_PROBE_SHA = "a1b2c3d4" * 8  # 64 hex，块内三 run 必须一致（§6.4 证据①）
_T0 = "2026-09-29T01:00:00+00:00"  # anchor-before
_T1 = "2026-09-29T02:00:00+00:00"  # 主体
_T2 = "2026-09-29T03:00:00+00:00"  # anchor-after


def _case_record(*, buffer_kb, latency_ns, cyc_per_load, refill_per_1k,
                 walk_per_1k, timestamp, sha=_PROBE_SHA, seed=42):
    """锚点/主体 case 记录：10 进程恒定逐样本值（median=p25=p75=给定值，
    便于把判据偏差钉在阈值两侧）。"""
    slots = buffer_kb * 1024 // 64
    loads = slots * 8  # 短训练（loads_per_slot=8），同锚点配置展开
    pmu_values = {
        "pmu.cycles.count": cyc_per_load * loads,
        "pmu.mem_access_rd.count": 1000.0,
        "pmu.l1d_tlb_refill.count": refill_per_1k * loads / 1000.0,
        "pmu.dtlb_walk.count": walk_per_1k * loads / 1000.0,
    }
    observations = [{
        "sample_index": index,
        "value": latency_ns,
        "raw_sample_ref": f"raw:{index}",
        "page_policy_requested": "base-madvise",
        "page_policy_actual": "base",
        "anon_huge_kb": 0,
        "page_kb": 4,
        "seed": seed,
        "vma_base": f"0x7f3a{index:08x}",
    } for index in range(10)]
    metrics = [{
        "name": "latency_ns",
        "value": latency_ns,
        "unit": "ns",
        "repetitions": 10,
        "observations": observations,
    }]
    for name, (typ, config, _) in _PMU.items():
        metrics.append({
            "name": name,
            "value": pmu_values[name],
            "unit": "events",
            "repetitions": 10,
            "observations": [{
                "sample_index": index,
                "value": pmu_values[name],
                "raw_sample_ref": f"raw:{index}",
                "pmu_type": typ,
                "pmu_config": config,
                "time_enabled_ns": 1000,
                "time_running_ns": 1000,
                "page_policy_requested": "base-madvise",
                "page_policy_actual": "base",
                "anon_huge_kb": 0,
                "seed": seed,
                "vma_base": f"0x7f3a{index:08x}",
            } for index in range(10)],
        })
    return {
        "schema_version": "2.0",
        "run_id": f"00000000-0000-0000-0000-{buffer_kb:012d}",
        "timestamp": timestamp,
        "status": "ok",
        "target": {"target_id": "redmi-k70pro-01"},
        "probe": {
            "name": "ptr_chase",
            "protocol_version": "1.2",
            "implementation_id": "portable",
            "artifact": {"sha256": sha},
        },
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


def _loaded_run(label, experiment_id, ok_records, *, failed_records=(),
                summary_failed=None, target_id="redmi-k70pro-01"):
    """直接构造 RunData（group_block 消费已加载 run，不走文件系统）。"""
    manifest = {
        "schema_version": "1.0",
        "experiment_id": experiment_id,
        "protocol_version": "1.2",
        "target": {"target_id": target_id},
        "records": f"/runs/{label}/records.jsonl",
        "summary": {
            "total": len(ok_records) + len(failed_records),
            "ok": len(ok_records),
            "failed": (
                len(failed_records) if summary_failed is None else summary_failed
            ),
            "skipped": 0,
            "unsupported": 0,
        },
    }
    return RunData(run_dir=Path(label), manifest=manifest,
                   ok_records=list(ok_records),
                   failed_records=list(failed_records))


def _anchor_run(label, timestamp, *, lat_512=None, cyc_512=None,
                r05_512=None, r34_512=None,
                lat_3072=None, cyc_3072=None, r05_3072=500.0, r34_3072=0.02,
                sha=_PROBE_SHA, failed_records=(), summary_failed=None):
    """锚点 run：固定 512/3072 KiB 两个 base case（§6.2.5），缺省值 =
    现场重算的参照中位（偏差 0、落在正控区间内）。3072 KiB R 值无历
    史参照，fixture 任取恒定值。"""
    records = [
        _case_record(
            buffer_kb=512,
            latency_ns=(_REF["medians"][512]["latency_ns"]
                        if lat_512 is None else lat_512),
            cyc_per_load=(_REF["medians"][512]["cyc_per_load"]
                          if cyc_512 is None else cyc_512),
            refill_per_1k=(_REF["r512_median"]["l1d_tlb_refill_per_1k"]
                           if r05_512 is None else r05_512),
            walk_per_1k=(_REF["r512_median"]["dtlb_walk_per_1k"]
                         if r34_512 is None else r34_512),
            timestamp=timestamp, sha=sha,
        ),
        _case_record(
            buffer_kb=3072,
            latency_ns=(_REF["medians"][3072]["latency_ns"]
                        if lat_3072 is None else lat_3072),
            cyc_per_load=(_REF["medians"][3072]["cyc_per_load"]
                          if cyc_3072 is None else cyc_3072),
            refill_per_1k=r05_3072, walk_per_1k=r34_3072,
            timestamp=timestamp, sha=sha,
        ),
    ]
    return _loaded_run(label, _ANCHOR_ID, records,
                       failed_records=failed_records,
                       summary_failed=summary_failed)


def _main_run(label, timestamp, sha=_PROBE_SHA):
    """主体 run（粗扫段）：两个非锚点 buffer，值不在判据消费面上。"""
    records = [
        _case_record(buffer_kb=128, latency_ns=2.0, cyc_per_load=2.0,
                     refill_per_1k=10.0, walk_per_1k=0.0,
                     timestamp=timestamp, sha=sha),
        _case_record(buffer_kb=256, latency_ns=2.1, cyc_per_load=2.1,
                     refill_per_1k=12.0, walk_per_1k=0.0,
                     timestamp=timestamp, sha=sha),
    ]
    return _loaded_run(label, _MAIN_ID, records)


def _block(*, before=None, after=None, main=None):
    """按 §6.4 时序组块：anchor-before + 主体 [+ anchor-after]。"""
    runs = [
        before if before is not None else _anchor_run("before", _T0),
        main if main is not None else _main_run("main", _T1),
    ]
    if after is not None:
        runs.append(after)
    return group_block(runs)


def _failed_env_record(timestamp, *, buffer_kb=512, sha=_PROBE_SHA):
    record = _case_record(buffer_kb=buffer_kb, latency_ns=0.0,
                          cyc_per_load=0.0, refill_per_1k=0.0,
                          walk_per_1k=0.0, timestamp=timestamp, sha=sha)
    record["status"] = "failed"
    record["metrics"] = []
    record["failure"] = {
        "reason": "environment-precondition-failed",
        "detail": "cpufreq-max-mismatch:policy7",
    }
    return record


class TestGroupBlock(unittest.TestCase):
    """§6.4 三块归组：角色由 experiment_id 决定；关联证据（probe
    SHA-256 / target / manifest 时序）不满足即硬错误，不降级推断。"""

    def test_grouped_block_carries_roles_and_evidence(self):
        block = _block(after=_anchor_run("after", _T2))
        self.assertEqual(block.status, "BLOCK_GROUPED")
        self.assertEqual(block.anchor_before.manifest["experiment_id"],
                         _ANCHOR_ID)
        self.assertEqual(block.main.manifest["experiment_id"], _MAIN_ID)
        self.assertEqual(block.anchor_after.manifest["experiment_id"],
                         _ANCHOR_ID)
        self.assertEqual(block.evidence["probe_sha256"], _PROBE_SHA)
        self.assertEqual(block.evidence["target_id"], "redmi-k70pro-01")

    def test_missing_anchor_after_is_block_incomplete(self):
        # ⑤缺 anchor-after → BLOCK_INCOMPLETE；validate_anchors 原样结案，
        # 不判锚点、不产出主体（fail-closed）。
        block = _block()
        self.assertEqual(block.status, "BLOCK_INCOMPLETE")
        self.assertIsNone(block.anchor_after)
        verdict = validate_anchors(block)
        self.assertEqual(verdict.status, "BLOCK_INCOMPLETE")
        self.assertIsNone(verdict.main_result)

    def test_association_violations_are_hard_errors(self):
        before = _anchor_run("before", _T0)
        main = _main_run("main", _T1)
        after = _anchor_run("after", _T2)
        with self.subTest(violation="probe sha mismatch"):
            bad_main = _main_run("main-bad", _T1, sha="ff" * 32)
            with self.assertRaises(TlbError):
                group_block([before, bad_main, after])
        with self.subTest(violation="target mismatch"):
            other_target = _loaded_run(
                "main-other", _MAIN_ID, _main_run("m", _T1).ok_records,
                target_id="some-other-device",
            )
            with self.assertRaises(TlbError):
                group_block([before, other_target, after])
        with self.subTest(violation="role order not inferred from position"):
            with self.assertRaises(TlbError):
                group_block([main, before, after])
        with self.subTest(violation="two anchors without main"):
            with self.assertRaises(TlbError):
                group_block([_anchor_run("b1", _T0), _anchor_run("b2", _T1)])
        with self.subTest(violation="four runs"):
            with self.assertRaises(TlbError):
                group_block([before, main, after,
                             _anchor_run("extra", "2026-09-29T04:00:00+00:00")])
        with self.subTest(violation="timing inversion"):
            early_after = _anchor_run("after-early", "2026-09-29T00:30:00+00:00")
            with self.assertRaises(TlbError):
                group_block([before, main, early_after])


class TestValidateAnchors(unittest.TestCase):
    """§6.2.5 锚点判据：ANCHORS_OK / BLOCK_FAILED / BLOCK_INCOMPLETE
    是块级终态（与 §10.2 的 Q 级终态不同层）。"""

    def test_latency_deviation_within_threshold_passes(self):
        # ①latency 偏差 2%（≤3%）通过；主体 case 进入判定（main_result
        # 产出主体分组）；首块 3072 KiB 自校准建立基线。
        block = _block(
            before=_anchor_run("before", _T0,
                               lat_512=_REF["medians"][512]["latency_ns"] * 1.02),
            after=_anchor_run("after", _T2,
                              lat_512=_REF["medians"][512]["latency_ns"] * 1.02),
        )
        self.assertEqual(block.status, "BLOCK_GROUPED")
        verdict = validate_anchors(block)
        self.assertEqual(verdict.status, "ANCHORS_OK")
        self.assertIsNotNone(verdict.main_result)
        self.assertEqual(
            sorted(group["buffer_kb"] for group in verdict.main_result.groups),
            [128, 256],
        )
        self.assertIsNotNone(verdict.baseline_3072)

    def test_latency_deviation_beyond_threshold_fails_block(self):
        # ②latency 偏差 5%（>3%）→ BLOCK_FAILED；主体 case 不入判定
        # （fail-closed：main_result 不产出，无对象可消费）。
        block = _block(
            before=_anchor_run("before", _T0,
                               lat_512=_REF["medians"][512]["latency_ns"] * 1.05),
            after=_anchor_run("after", _T2,
                              lat_512=_REF["medians"][512]["latency_ns"] * 1.05),
        )
        verdict = validate_anchors(block)
        self.assertEqual(verdict.status, "BLOCK_FAILED")
        self.assertIsNone(verdict.main_result)
        self.assertIsNone(verdict.baseline_3072)  # 失败块分布不晋升基线
        failures = verdict.evidence["failures"]
        self.assertTrue(any(
            failure["check"] == "latency_ns_vs_short_base"
            and failure["run"] == "anchor_before"
            and failure["buffer_kb"] == 512
            for failure in failures
        ))

    def test_512_r_values_outside_positive_control_interval_fail(self):
        # ③512 KiB R_0x05/R_0x34 median 落在正控 [p25, p75] 外 → 失败
        # （缺省 fixture 取正控 median，在区间内——①即反向对照）。
        r05_p25, r05_p75 = _REF["r512_p25_p75"]["l1d_tlb_refill_per_1k"]
        r34_p25, _ = _REF["r512_p25_p75"]["dtlb_walk_per_1k"]
        with self.subTest(metric="R_0x05 above p75"):
            block = _block(
                before=_anchor_run("before", _T0, r05_512=r05_p75 + 1.0),
                after=_anchor_run("after", _T2, r05_512=r05_p75 + 1.0),
            )
            verdict = validate_anchors(block)
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertIsNone(verdict.main_result)
        with self.subTest(metric="R_0x34 below p25"):
            block = _block(
                before=_anchor_run("before", _T0, r34_512=r34_p25 / 2),
                after=_anchor_run("after", _T2, r34_512=r34_p25 / 2),
            )
            verdict = validate_anchors(block)
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertTrue(any(
                "dtlb_walk_per_1k" in failure["check"]
                for failure in verdict.evidence["failures"]
            ))

    def test_3072_first_block_self_calibrates_later_blocks_compare(self):
        # ④3072 KiB 无 G0 历史数据：首块只记录不判失，以 anchor-before
        # 的 3072 分布建基线；后续块与之比较（同一规则）。
        first = validate_anchors(_block(after=_anchor_run("after", _T2)))
        self.assertEqual(first.status, "ANCHORS_OK")
        baseline = first.baseline_3072
        self.assertEqual(baseline["l1d_tlb_refill_per_1k"]["median"], 500.0)
        self.assertEqual(baseline["l1d_tlb_refill_per_1k"]["p25"], 500.0)
        # 逐样本值经 ×loads/1000 → /loads×1000 往返，浮点末位有漂移。
        self.assertAlmostEqual(baseline["dtlb_walk_per_1k"]["p75"], 0.02)
        # 第二块与基线一致 → 通过且回显同一基线。
        same = validate_anchors(
            _block(after=_anchor_run("after2", _T2)),
            prior_3072_baseline=baseline,
        )
        self.assertEqual(same.status, "ANCHORS_OK")
        self.assertIs(same.baseline_3072, baseline)
        # 第二块 3072 KiB median 落在基线 [p25, p75] 外 → 失败。
        drifted = validate_anchors(
            _block(
                before=_anchor_run("before2", _T0, r05_3072=600.0),
                after=_anchor_run("after2", _T2, r05_3072=600.0),
            ),
            prior_3072_baseline=baseline,
        )
        self.assertEqual(drifted.status, "BLOCK_FAILED")
        self.assertIsNone(drifted.main_result)
        self.assertTrue(any(
            failure["check"] == "l1d_tlb_refill_per_1k_within_3072_baseline"
            for failure in drifted.evidence["failures"]
        ))

    def test_environment_gate_failure_distorts_anchor(self):
        # §6.2.5：任一锚点 run 环境门禁失败（summary failed>0 或记录带
        # environment-precondition-failed）→ 等同锚点失真，块 fail-closed。
        with self.subTest(mode="failed record with env reason"):
            after = _anchor_run(
                "after", _T2,
                failed_records=[_failed_env_record(_T2)],
            )
            verdict = validate_anchors(_block(after=after))
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertIsNone(verdict.main_result)
            self.assertTrue(any(
                failure["check"] == "environment_gate"
                and failure["run"] == "anchor_after"
                for failure in verdict.evidence["failures"]
            ))
        with self.subTest(mode="manifest summary failed>0"):
            after = _anchor_run("after", _T2, summary_failed=1)
            verdict = validate_anchors(_block(after=after))
            self.assertEqual(verdict.status, "BLOCK_FAILED")

    def test_before_after_mutual_judgment(self):
        # 前后两次锚点 run 同指标互判（同一规则）：各自对照参照都合格、
        # 但彼此之间漂移超阈也判失。
        with self.subTest(mode="latency drift"):
            # ×0.99 与 ×1.02 各自偏差 ≤3%，互判偏差 3.03% >3%。
            block = _block(
                before=_anchor_run(
                    "before", _T0,
                    lat_512=_REF["medians"][512]["latency_ns"] * 0.99),
                after=_anchor_run(
                    "after", _T2,
                    lat_512=_REF["medians"][512]["latency_ns"] * 1.02),
            )
            verdict = validate_anchors(block)
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertTrue(any(
                failure["check"] == "latency_ns_before_after_mutual"
                for failure in verdict.evidence["failures"]
            ))
        with self.subTest(mode="R value drift"):
            # 两者各自落在正控 [p25, p75] 内（取 p25/p75 与 median 的中
            # 点，严格在区间内），但 median 互不落对方 [p25, p75]（恒定
            # 分布区间退化）→ 互判失败。
            r05_p25, r05_p75 = _REF["r512_p25_p75"]["l1d_tlb_refill_per_1k"]
            r05_median = _REF["r512_median"]["l1d_tlb_refill_per_1k"]
            low, high = (r05_p25 + r05_median) / 2, (r05_p75 + r05_median) / 2
            block = _block(
                before=_anchor_run("before", _T0, r05_512=low),
                after=_anchor_run("after", _T2, r05_512=high),
            )
            verdict = validate_anchors(block)
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertTrue(any(
                failure["check"] == "l1d_tlb_refill_per_1k_before_after_mutual"
                for failure in verdict.evidence["failures"]
            ))

    def test_anchor_group_shape_is_validated(self):
        # 锚点 run 组形契约：恰为 {512: 一组, 3072: 一组}——缺 buffer
        # case 是契约缺项，硬错误而非判失（锚点配置的 case 集合本身由
        # §9.3 plan 展开契约测试钉死，此处只验组形）。
        broken = _loaded_run(
            "before", _ANCHOR_ID,
            [_case_record(buffer_kb=512, latency_ns=2.6, cyc_per_load=7.5,
                          refill_per_1k=288.0, walk_per_1k=0.012,
                          timestamp=_T0)],
        )
        block = _block(before=broken, after=_anchor_run("after", _T2))
        with self.assertRaises(TlbError):
            validate_anchors(block)


class TestAnchorReferences(unittest.TestCase):
    """§6.2.5 参照分布的运行时现读现算（冻结规则：不写死数字——仓内
    数据修正走 revision history，参照系自动跟踪修正）。"""

    def test_references_match_independent_recomputation(self):
        # 模块参照（经 validate_anchors 判定证据暴露）与本测试独立重算
        # 的期望值逐位一致；_anchor_references() 进程内只算一次（lazy
        # 缓存，重复调用返回同一对象）。
        verdict = validate_anchors(_block(after=_anchor_run("after", _T2)))
        self.assertEqual(verdict.status, "ANCHORS_OK")
        seen = set()
        for check in verdict.evidence["checks"]:
            if check["check"].endswith("_vs_short_base"):
                field = check["check"].removesuffix("_vs_short_base")
                self.assertEqual(
                    check["reference"],
                    _REF["medians"][check["buffer_kb"]][field],
                )
                seen.add(("median", check["buffer_kb"], field))
            elif check["check"].endswith("_within_positive_control_512"):
                field = check["check"].removesuffix("_within_positive_control_512")
                self.assertEqual(
                    tuple(check["interval"]), _REF["r512_p25_p75"][field]
                )
                seen.add(("r512", field))
        # 防空心化：四类参照（2 buffer × 2 median 字段 + 2 个 R 区间）
        # 都被证据覆盖。
        self.assertEqual(
            seen,
            {("median", buffer, field)
             for buffer in (512, 3072)
             for field in ("latency_ns", "cyc_per_load")}
            | {("r512", field)
               for field in ("l1d_tlb_refill_per_1k", "dtlb_walk_per_1k")},
        )
        self.assertIs(sm8650_tlb._anchor_references(),
                      sm8650_tlb._anchor_references())

    def test_missing_or_incomplete_reference_runs_are_hard_errors(self):
        # fail-closed：参照 run 缺失、带失败记录或 buffer 组不全 →
        # TlbError，不静默降级为跳过判定。
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "runs"
            with self.subTest(case="runs root missing"):
                with self.assertRaises(TlbError):
                    sm8650_tlb._compute_anchor_references(root)
            run_dir = root / sm8650_tlb._ANCHOR_REF_SHORT_BASE_RUN
            run_dir.mkdir(parents=True)
            record = {
                "schema_version": "2.0",
                "status": "ok",
                "params": {"buffer_kb": 512, "loads": 65536},
                "metrics": [
                    {"name": "latency_ns",
                     "observations": [{"sample_index": 0, "value": 2.6}]},
                    {"name": "pmu.cycles.count",
                     "observations": [{"sample_index": 0, "value": 490000}]},
                ],
            }
            (run_dir / "records.jsonl").write_text(
                json.dumps(record) + "\n", encoding="utf-8"
            )
            with self.subTest(case="buffer group missing"):
                with self.assertRaises(TlbError):
                    sm8650_tlb._compute_anchor_references(root)
            with self.subTest(case="reference run with failed records"):
                record["status"] = "failed"
                (run_dir / "records.jsonl").write_text(
                    json.dumps(record) + "\n", encoding="utf-8"
                )
                with self.assertRaises(TlbError):
                    sm8650_tlb._compute_anchor_references(root)


if __name__ == "__main__":
    unittest.main()
