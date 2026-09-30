# SPDX-License-Identifier: Apache-2.0
"""SM8650 X4 TLB 层级探测分析器测试（任务书 v4.4 §9.3）。

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
（validate_anchors：环境门禁；判据 2 池带 C±1.5W（v4.4 方差表征池
现算，latency/cyc/R 密度两 buffer）+ 互判 |before−after| ≤ 1.5W；
判据 3 512 KiB R_0x34 计数容差（v4.3 形式沿用、v4.4 参照改自池）；
判据 4 3072 KiB 首块自校准、后续块落基线 median ± 1.5W）；
以及 §7 Phase D THP cohort（分级：比较级 ≥5 有效样本出 median / 描述级
3–4 只报原始观测 / <3 与未达比较级终态 INSUFFICIENT_COHORT；跨 seed
同制度合并、异制度分列；mixed 不并入 thp；40 进程次/(buffer×policy)
停止预算含失败计额；转化表）与 §7 Phase C Q3 默认终态（G3 缺失 →
MODEL_UNIDENTIFIABLE 且绝无成本值）；以及 §5.3 固定开销拟合判定
（adjudicate_fixed_overhead：三点最小二乘回收 a/b、|a|/C(N) ≤5%
边界语义、协议偏离 fail-closed、跨 seed 斜率离散度只报告不设阈值、
floor 近零计数 ratio=inf、乱序输入确定性排序输出）。
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
    adjudicate_fixed_overhead,
    adjudicate_knee,
    adjudicate_q3,
    analyze_records,
    audit_thp_budget,
    build_markdown,
    build_thp_conversion,
    detect_knee_candidates,
    detect_walk_onset,
    grade_thp_cohorts,
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
# §6.4/§6.2.5 块归组与锚点判定 fixture（任务书 v4.4 池化参照）
#
# 参照期望值现场从方差表征池（6 个 anchor run）独立重算（本文件自己的
# JSON 解析路径 + runner.statistics.summarize 口径），不写死数字——冻
# 结规则要求参照现读现算（仓内数据修正走 revision history，硬编码会
# 静默过期）。测试钉的是模块计算的正确性（两路独立计算逐位一致），不
# 是常量值；池数据修正后期望值自动跟踪。池成员名单独立写死（防单向
# 漂移），并与模块 _ANCHOR_REF_POOL_RUNS 互钉。
# ---------------------------------------------------------------------------

# 方差表征池（任务书 v4.4 §6.2.5；6 个 ptr-chase-sm8650-x4-tlb-anchor
# run 当夜连跑，入库 beb63ef）。
_POOL_RUNS = [
    "20260929T235909Z-ptr-chase-sm8650-x4-tlb-anchor",
    "20260929T235918Z-ptr-chase-sm8650-x4-tlb-anchor",
    "20260929T235927Z-ptr-chase-sm8650-x4-tlb-anchor",
    "20260929T235938Z-ptr-chase-sm8650-x4-tlb-anchor",
    "20260929T235948Z-ptr-chase-sm8650-x4-tlb-anchor",
    "20260929T235957Z-ptr-chase-sm8650-x4-tlb-anchor",
]

# (派生字段, 记录 metric 名, per-loads 归一系数)——与判据 2 的消费面对齐。
_POOL_METRICS = (
    ("latency_ns", "latency_ns", None),
    ("cyc_per_load", "pmu.cycles.count", 1.0),
    ("l1d_tlb_refill_per_1k", "pmu.l1d_tlb_refill.count", 1000.0),
    ("dtlb_walk_per_1k", "pmu.dtlb_walk.count", 1000.0),
)
_ANCHOR_BUFFERS = (512, 3072)


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
    """§6.2.5 v4.4 池化参照期望值：per (metric, buffer) 的 C（逐 run
    median 的 median）/ W（逐 run median 的 max−min）/ band（C±1.5W）
    + 512 KiB walk 池参照计数 median（同一 C 聚合于逐样本原始计数）。"""
    bands = {}
    for buffer_kb in _ANCHOR_BUFFERS:
        for field, metric, scale in _POOL_METRICS:
            medians = [
                _evidence_group_stats(run, buffer_kb, metric, scale)["median"]
                for run in _POOL_RUNS
            ]
            center = summarize(medians)["median"]
            spread = max(medians) - min(medians)
            bands[(field, buffer_kb)] = {
                "center": center,
                "spread": spread,
                "band": (center - 1.5 * spread, center + 1.5 * spread),
            }
    walk_medians = [
        _evidence_group_stats(run, 512, "pmu.dtlb_walk.count", None)["median"]
        for run in _POOL_RUNS
    ]
    return {
        "bands": bands,
        "walk512_median_count": summarize(walk_medians)["median"],
    }


_REF = _reference_expectations()  # import 时现读现算一次

_ANCHOR_ID = "ptr-chase-sm8650-x4-tlb-anchor"  # §6.4：锚点 experiment_id
_MAIN_ID = "ptr-chase-sm8650-x4-tlb-coarse"
_PROBE_SHA = "a1b2c3d4" * 8  # 64 hex，块内三 run 必须一致（§6.4 证据①）
_T0 = "2026-09-29T01:00:00+00:00"  # anchor-before
_T1 = "2026-09-29T02:00:00+00:00"  # 主体
_T2 = "2026-09-29T03:00:00+00:00"  # anchor-after


def _case_record(*, buffer_kb, latency_ns, cyc_per_load, refill_per_1k,
                 walk_per_1k, timestamp, sha=_PROBE_SHA, seed=42,
                 walk_count=None):
    """锚点/主体 case 记录：10 进程恒定逐样本值（median=p25=p75=给定值，
    便于把判据偏差钉在阈值两侧）。walk_count 给定时每样本 dtlb_walk
    原始计数取该值（walks/窗，v4.3 计数容差判据的消费面），派生 /1k
    密度由分析器换算——512 KiB（loads=65536=2^16）下半整数计数往返
    精确，可把边界钉在 double 精确值上。"""
    slots = buffer_kb * 1024 // 64
    loads = slots * 8  # 短训练（loads_per_slot=8），同锚点配置展开
    pmu_values = {
        "pmu.cycles.count": cyc_per_load * loads,
        "pmu.mem_access_rd.count": 1000.0,
        "pmu.l1d_tlb_refill.count": refill_per_1k * loads / 1000.0,
        "pmu.dtlb_walk.count": (
            walk_per_1k * loads / 1000.0 if walk_count is None else walk_count
        ),
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
                r05_512=None, r34_512=None, walks_512=None,
                lat_3072=None, cyc_3072=None, r05_3072=None, r34_3072=None,
                sha=_PROBE_SHA, failed_records=(), summary_failed=None):
    """锚点 run：固定 512/3072 KiB 两个 base case（§6.2.5），缺省值 =
    现场重算的池参照中心 C（落带中央，全部判据偏差 0）。walks_512 以
    walks/窗计数直接钉 512 KiB R_0x34（v4.3 计数容差判据，v4.4 参照
    改自池），优先于 r34_512 的密度指定。"""
    bands = _REF["bands"]

    def _center(field, buffer_kb, override):
        return bands[(field, buffer_kb)]["center"] if override is None else override

    records = [
        _case_record(
            buffer_kb=512,
            latency_ns=_center("latency_ns", 512, lat_512),
            cyc_per_load=_center("cyc_per_load", 512, cyc_512),
            refill_per_1k=_center("l1d_tlb_refill_per_1k", 512, r05_512),
            walk_per_1k=_center("dtlb_walk_per_1k", 512, r34_512),
            walk_count=(
                _REF["walk512_median_count"]
                if walks_512 is None and r34_512 is None else walks_512
            ),
            timestamp=timestamp, sha=sha,
        ),
        _case_record(
            buffer_kb=3072,
            latency_ns=_center("latency_ns", 3072, lat_3072),
            cyc_per_load=_center("cyc_per_load", 3072, cyc_3072),
            refill_per_1k=_center("l1d_tlb_refill_per_1k", 3072, r05_3072),
            walk_per_1k=_center("dtlb_walk_per_1k", 3072, r34_3072),
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


@contextlib.contextmanager
def _references_root(path):
    """临时替换参照 runs 根并清缓存（模拟参照 run 缺失/损坏）；退出时
    恢复原根与原缓存，与测试执行顺序无关。"""
    old_root = sm8650_tlb._ANCHOR_REF_RUNS_ROOT
    old_cache = sm8650_tlb._ANCHOR_REFERENCES
    sm8650_tlb._ANCHOR_REF_RUNS_ROOT = path
    sm8650_tlb._ANCHOR_REFERENCES = None
    try:
        yield
    finally:
        sm8650_tlb._ANCHOR_REF_RUNS_ROOT = old_root
        sm8650_tlb._ANCHOR_REFERENCES = old_cache


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

    def test_latency_within_pool_band_passes(self):
        # ①判据 2（v4.4）：前/后锚点 latency median 落池带 C±1.5W 内
        # （含带边，inclusive——latency 无 loads 换算，带边 double 精确）
        # → 通过；主体 case 进入判定；首块 3072 KiB 自校准建立基线。
        band = _REF["bands"][("latency_ns", 512)]["band"]
        with self.subTest(edge="centers"):
            block = _block(after=_anchor_run("after", _T2))
            self.assertEqual(block.status, "BLOCK_GROUPED")
            verdict = validate_anchors(block)
            self.assertEqual(verdict.status, "ANCHORS_OK")
            self.assertIsNotNone(verdict.main_result)
            self.assertEqual(
                sorted(g["buffer_kb"] for g in verdict.main_result.groups),
                [128, 256],
            )
            self.assertIsNotNone(verdict.baseline_3072)
        with self.subTest(edge="both at lower band edge"):
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, lat_512=band[0]),
                after=_anchor_run("after", _T2, lat_512=band[0]),
            ))
            self.assertEqual(verdict.status, "ANCHORS_OK")
        with self.subTest(edge="both at upper band edge"):
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, lat_512=band[1]),
                after=_anchor_run("after", _T2, lat_512=band[1]),
            ))
            self.assertEqual(verdict.status, "ANCHORS_OK")

    def test_latency_outside_pool_band_fails_block(self):
        # ②判据 2（v4.4）：latency median 出池带 → BLOCK_FAILED；主体
        # case 不入判定（fail-closed：main_result 不产出）。
        band = _REF["bands"][("latency_ns", 512)]["band"]
        block = _block(
            before=_anchor_run("before", _T0, lat_512=band[1] + 0.01),
            after=_anchor_run("after", _T2, lat_512=band[1] + 0.01),
        )
        verdict = validate_anchors(block)
        self.assertEqual(verdict.status, "BLOCK_FAILED")
        self.assertIsNone(verdict.main_result)
        self.assertIsNone(verdict.baseline_3072)  # 失败块分布不晋升基线
        failures = verdict.evidence["failures"]
        self.assertTrue(any(
            failure["check"] == "latency_ns_band_512"
            and failure["run"] == "anchor_before"
            and failure["buffer_kb"] == 512
            for failure in failures
        ))

    def test_r05_outside_pool_band_fails(self):
        # ③判据 2（v4.4）：R_0x05 密度两 buffer 都走池带（R 值经 loads
        # 往返有浮点末位噪声，带外用 ≥1.0 余量钉，不夹 ulps 边界；带内
        # 由①的缺省 fixture 反向对照）。
        band_512 = _REF["bands"][("l1d_tlb_refill_per_1k", 512)]["band"]
        band_3072 = _REF["bands"][("l1d_tlb_refill_per_1k", 3072)]["band"]
        with self.subTest(case="512 R_0x05 above band"):
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, r05_512=band_512[1] + 1.0),
                after=_anchor_run("after", _T2, r05_512=band_512[1] + 1.0),
            ))
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertIsNone(verdict.main_result)
            self.assertTrue(any(
                failure["check"] == "l1d_tlb_refill_per_1k_band_512"
                for failure in verdict.evidence["failures"]
            ))
        with self.subTest(case="512 R_0x05 below band"):
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, r05_512=band_512[0] - 1.0),
                after=_anchor_run("after", _T2, r05_512=band_512[0] - 1.0),
            ))
            self.assertEqual(verdict.status, "BLOCK_FAILED")
        with self.subTest(case="3072 R_0x05 above band (首块同样适用)"):
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, r05_3072=band_3072[1] + 1.0),
                after=_anchor_run("after", _T2, r05_3072=band_3072[1] + 1.0),
            ))
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertTrue(any(
                failure["check"] == "l1d_tlb_refill_per_1k_band_3072"
                for failure in verdict.evidence["failures"]
            ))

    def test_512_walk_count_tolerance_boundaries(self):
        # ③′判据 3（v4.3 形式沿用，v4.4 参照改自池）：|median − 池参照
        # median| ≤ max(3, 0.5×池参照 median) walks/窗。池参照 median
        # 现算 = 7.75 walks/窗 → 容差 3.875 → 容差带 [3.875, 11.625]
        # （任务书括号备查值经 v4.4 勘误与本现算值一致，d1243a3；
        # 边界值 3.875/11.625 为 dyadic 分数，loads=65536=2^16 下计数
        # 往返 double 精确，可钉恰在带边通过、带外失败。
        with self.subTest(edge="lower bound 3.875 passes"):
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, walks_512=3.875),
                after=_anchor_run("after", _T2, walks_512=3.875),
            ))
            self.assertEqual(verdict.status, "ANCHORS_OK")
        with self.subTest(edge="upper bound 11.625 passes"):
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, walks_512=11.625),
                after=_anchor_run("after", _T2, walks_512=11.625),
            ))
            self.assertEqual(verdict.status, "ANCHORS_OK")
        with self.subTest(edge="below band 3.5 fails"):
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, walks_512=3.5),
                after=_anchor_run("after", _T2, walks_512=3.5),
            ))
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertIsNone(verdict.main_result)
            walk_failures = [
                failure for failure in verdict.evidence["failures"]
                if failure["check"] == "dtlb_walk_count_tolerance_512"
            ]
            self.assertTrue(walk_failures)
            failure = walk_failures[0]
            self.assertEqual(failure["reference_median_count"], 7.75)
            self.assertEqual(failure["tolerance_band"], [3.875, 11.625])
            self.assertAlmostEqual(failure["median_count"], 3.5)
            self.assertAlmostEqual(failure["deviation_count"], 4.25)
        with self.subTest(edge="above band 12.0 fails"):
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, walks_512=12.0),
                after=_anchor_run("after", _T2, walks_512=12.0),
            ))
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertTrue(any(
                failure["check"] == "dtlb_walk_count_tolerance_512"
                for failure in verdict.evidence["failures"]
            ))

    def test_512_walk_mutual_count_tolerance(self):
        # 判据 3 互判（v4.4）：|before − after| ≤ max(3, 0.5×池参照
        # median) = 3.875 walks/窗（同一量化结构）。
        with self.subTest(edge="mutual deviation 3.875 passes"):
            # before=3.875（带边，参照检查过）与 after=7.75 差恰 3.875。
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, walks_512=3.875),
                after=_anchor_run("after", _T2, walks_512=7.75),
            ))
            self.assertEqual(verdict.status, "ANCHORS_OK")
        with self.subTest(edge="mutual deviation 4.0 fails"):
            # 两者各自在容差带内（参照检查过），互判差 4.0 >3.875 → 仅
            # 互判失败（隔离验证互判独立生效）。
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, walks_512=3.875),
                after=_anchor_run("after", _T2, walks_512=7.875),
            ))
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            failures = verdict.evidence["failures"]
            self.assertEqual(
                [failure["check"] for failure in failures],
                ["dtlb_walk_count_before_after_mutual"],
            )
            mutual = failures[0]
            self.assertAlmostEqual(mutual["median_count_before"], 3.875)
            self.assertAlmostEqual(mutual["median_count_after"], 7.875)
            self.assertAlmostEqual(mutual["deviation_count"], 4.0)
            self.assertEqual(mutual["tolerance"], 3.875)

    def test_3072_first_block_self_calibrates_later_blocks_compare(self):
        # ④判据 4（v4.4）：首块自校准保留——基线 = 首块 anchor-before
        # 的 3072 组 median；后续块 median ∈ 基线 median ± 1.5×W(m,3072)
        # （W 取自池）。判据 2 的池带对首块照常适用。
        first = validate_anchors(_block(after=_anchor_run("after", _T2)))
        self.assertEqual(first.status, "ANCHORS_OK")
        baseline = first.baseline_3072
        center_05 = _REF["bands"][("l1d_tlb_refill_per_1k", 3072)]["center"]
        # 缺省 fixture 取池中心 → 基线 median 即池中心（±loads 往返末位）。
        self.assertAlmostEqual(
            baseline["l1d_tlb_refill_per_1k"]["median"], center_05
        )
        # 第二块与基线一致 → 通过且回显同一基线。
        same = validate_anchors(
            _block(after=_anchor_run("after2", _T2)),
            prior_3072_baseline=baseline,
        )
        self.assertEqual(same.status, "ANCHORS_OK")
        self.assertIs(same.baseline_3072, baseline)
        # 判据 4 隔离：基线 median = C−W（在池带内），第二块 = C+W（也
        # 在池带内、判据 2 过）——与基线差 2W > 1.5W → 仅判据 4 失败。
        entry = _REF["bands"][("l1d_tlb_refill_per_1k", 3072)]
        walk_3072 = _REF["bands"][("dtlb_walk_per_1k", 3072)]["center"]
        prior = {
            "l1d_tlb_refill_per_1k": {
                "median": entry["center"] - entry["spread"],
            },
            "dtlb_walk_per_1k": {"median": walk_3072},
        }
        drifted = validate_anchors(
            _block(
                before=_anchor_run(
                    "before2", _T0,
                    r05_3072=entry["center"] + entry["spread"]),
                after=_anchor_run(
                    "after2", _T2,
                    r05_3072=entry["center"] + entry["spread"]),
            ),
            prior_3072_baseline=prior,
        )
        self.assertEqual(drifted.status, "BLOCK_FAILED")
        self.assertIsNone(drifted.main_result)
        self.assertTrue(any(
            failure["check"]
            == "l1d_tlb_refill_per_1k_within_3072_baseline_band"
            for failure in drifted.evidence["failures"]
        ))
        self.assertFalse(any(
            failure["check"] == "l1d_tlb_refill_per_1k_band_3072"
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
        # 判据 2 互判（v4.4）：|before − after| ≤ 1.5W——各自都在池带内、
        # 但彼此之间漂移超阈也判失。
        with self.subTest(mode="latency drift"):
            # before 在下带边、after 在上带边：各自参照检查过（带边
            # inclusive），互判差 3W > 1.5W → 仅互判失败。
            band = _REF["bands"][("latency_ns", 512)]["band"]
            verdict = validate_anchors(_block(
                before=_anchor_run("before", _T0, lat_512=band[0]),
                after=_anchor_run("after", _T2, lat_512=band[1]),
            ))
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertEqual(
                [failure["check"] for failure in verdict.evidence["failures"]],
                ["latency_ns_before_after_band_512"],
            )
        with self.subTest(mode="R value drift"):
            # 两者各自在池带内（C∓W，距带边 0.5W），互判差 2W > 1.5W
            # → 仅互判失败。
            entry = _REF["bands"][("l1d_tlb_refill_per_1k", 512)]
            verdict = validate_anchors(_block(
                before=_anchor_run(
                    "before", _T0,
                    r05_512=entry["center"] - entry["spread"]),
                after=_anchor_run(
                    "after", _T2,
                    r05_512=entry["center"] + entry["spread"]),
            ))
            self.assertEqual(verdict.status, "BLOCK_FAILED")
            self.assertEqual(
                [failure["check"] for failure in verdict.evidence["failures"]],
                ["l1d_tlb_refill_per_1k_before_after_band_512"],
            )

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

    def test_env_gate_short_circuits_before_reference_load(self):
        # env 失真块先短路结案：即使参照 run 缺失（本会 TlbError），也
        # 干净结案 BLOCK_FAILED——锚点失真不依赖参照分布。
        after = _anchor_run("after", _T2,
                            failed_records=[_failed_env_record(_T2)])
        block = _block(after=after)
        with tempfile.TemporaryDirectory() as tmp, _references_root(Path(tmp)):
            verdict = validate_anchors(block)
        self.assertEqual(verdict.status, "BLOCK_FAILED")
        self.assertTrue(any(
            failure["check"] == "environment_gate"
            for failure in verdict.evidence["failures"]
        ))

    def test_anchor_rejected_counts_are_in_evidence(self):
        # 锚点 run 的 rejected 样本计数（如 multiplex 拒绝）进 verdict
        # evidence——审计面不缺段；余下 9 样本恒定，判定不受影响。
        before = _anchor_run("before", _T0)
        before.ok_records[0]["metrics"][1]["observations"][3][
            "time_running_ns"] = 0  # multiplex：running<enabled → 拒绝
        verdict = validate_anchors(
            _block(before=before, after=_anchor_run("after", _T2))
        )
        self.assertEqual(verdict.status, "ANCHORS_OK")
        self.assertEqual(verdict.evidence["anchor_rejected"],
                         {"before": 1, "after": 0})
        # 判失路径同样带计数（此处两锚点无 rejected → 全 0）。
        band = _REF["bands"][("latency_ns", 512)]["band"]
        drifted = validate_anchors(_block(
            before=_anchor_run("before2", _T0, lat_512=band[1] + 0.5),
            after=_anchor_run("after2", _T2, lat_512=band[1] + 0.5),
        ))
        self.assertEqual(drifted.status, "BLOCK_FAILED")
        self.assertEqual(drifted.evidence["anchor_rejected"],
                         {"before": 0, "after": 0})


class TestAnchorReferences(unittest.TestCase):
    """§6.2.5 参照分布的运行时现读现算（v4.4 池化：方差表征 6 run；
    C = 逐 run median 的 median、W = 逐 run median 的 max−min、带 =
    C±1.5W，不写死数字——仓内数据修正走 revision history，参照系自
    动跟踪修正）。"""

    def test_pool_membership_is_pinned(self):
        # 池成员与制度硬钉（v4.4）：模块池名单 = 任务书 6 run；每 run
        # 的每条 ok 记录都是 8 环锚点制度（loads == 8 × slots）——防
        # 止再次锚定制度不匹配的参照（v4.1 旧正控 2048 环的教训）。
        self.assertEqual(list(sm8650_tlb._ANCHOR_REF_POOL_RUNS), _POOL_RUNS)
        for run in sm8650_tlb._ANCHOR_REF_POOL_RUNS:
            path = (_REPO_ROOT / "data" / "public" / "runs" / run
                    / "records.jsonl")
            seen = 0
            for line in path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                params = record.get("params", {})
                if record.get("status") != "ok":
                    continue
                seen += 1
                slots = params["buffer_kb"] * 1024 // params.get("stride", 64)
                self.assertEqual(params["loads"], 8 * slots)
            self.assertEqual(seen, 2, f"{run}: 应为 512+3072 两个 base case")

    def test_pool_references_from_synthetic_pool(self):
        # 合成 6-run 池喂 _pool_references：C/W/band 与 walk 池参照计
        # 数按定义计算（逐 run median → median / max−min / C±1.5W）。
        runs = [
            _anchor_run(f"pool-{index}", _T0,
                        lat_512=2.5 + 0.1 * index, walks_512=5.0 + index)
            for index in range(6)
        ]
        references = sm8650_tlb._pool_references(runs)
        entry = references["bands"][("latency_ns", 512)]
        self.assertAlmostEqual(entry["center"], 2.75)   # (2.7+2.8)/2
        self.assertAlmostEqual(entry["spread"], 0.5)    # 3.0−2.5
        self.assertAlmostEqual(entry["band"][0], 2.75 - 0.75)
        self.assertAlmostEqual(entry["band"][1], 2.75 + 0.75)
        # walk 池参照 = median([5,6,7,8,9,10]) = 7.5 → max(3, 0.5×7.5)。
        self.assertEqual(references["walk512_median_count"], 7.5)
        with self.subTest(guard="pool must be anchor experiment runs"):
            rogue = _loaded_run("rogue", _MAIN_ID,
                                _anchor_run("x", _T0).ok_records)
            with self.assertRaises(TlbError):
                sm8650_tlb._pool_references([*runs[:5], rogue])
        with self.subTest(guard="pool size pinned at 6"):
            with self.assertRaises(TlbError):
                sm8650_tlb._pool_references(runs[:5])

    def test_references_match_independent_recomputation(self):
        # 真实池回归钉：模块现算与本测试独立重算逐位一致（全表）；任务
        # 书 v4.4 §6.2.5 备查值核对防数据错读；_anchor_references() 进
        # 程内只算一次（lazy 缓存，重复调用返回同一对象）。
        self.assertIs(sm8650_tlb._anchor_references(),
                      sm8650_tlb._anchor_references())
        references = sm8650_tlb._compute_anchor_references(
            _REPO_ROOT / "data" / "public" / "runs"
        )
        self.assertEqual(len(references["bands"]), len(_REF["bands"]))
        for key, entry in _REF["bands"].items():
            module_entry = references["bands"][key]
            self.assertEqual(module_entry["center"], entry["center"])
            self.assertEqual(module_entry["spread"], entry["spread"])
            self.assertEqual(module_entry["band"], entry["band"])
        self.assertEqual(references["walk512_median_count"],
                         _REF["walk512_median_count"])
        # 任务书 v4.4 §6.2.5 括号备查值（"判定以现算为准"，此处核对防
        # 数据错读）。
        self.assertAlmostEqual(
            _REF["bands"][("latency_ns", 512)]["center"], 2.69, places=2)
        self.assertAlmostEqual(
            _REF["bands"][("latency_ns", 512)]["spread"], 0.086, places=2)
        self.assertAlmostEqual(
            _REF["bands"][("latency_ns", 3072)]["center"], 8.01, places=2)
        self.assertAlmostEqual(
            _REF["bands"][("latency_ns", 3072)]["spread"], 0.70, places=2)
        self.assertAlmostEqual(
            _REF["bands"][("l1d_tlb_refill_per_1k", 512)]["center"],
            285.5, places=1)
        self.assertAlmostEqual(
            _REF["bands"][("l1d_tlb_refill_per_1k", 3072)]["center"],
            1301.1, places=1)
        # walk 池参照 median 现算 = 7.75 walks/窗（容差带
        # [3.875, 11.625]），与任务书 v4.4 勘误后括号备查值一致
        # （d1243a3：7.5 只能由 median_low 得到，与规范聚合
        # statistics.median 口径不符，勘误已落）；本钉独立重算钉现算。
        self.assertEqual(_REF["walk512_median_count"], 7.75)

    def test_verdict_evidence_carries_band_details(self):
        # 判定证据带 band 明细（center/spread/band），与独立重算逐位一
        # 致；判据 2 覆盖面 = 全部 (metric, buffer) 减去 512 R_0x34
        # （走判据 3）。
        verdict = validate_anchors(_block(after=_anchor_run("after", _T2)))
        self.assertEqual(verdict.status, "ANCHORS_OK")
        seen = set()
        for check in verdict.evidence["checks"]:
            name = check["check"]
            if "_before_after_" in name:
                continue
            if name.endswith("_band_512") or name.endswith("_band_3072"):
                field, _, buffer = name.rpartition("_band_")
                entry = _REF["bands"][(field, int(buffer))]
                self.assertEqual(check["center"], entry["center"])
                self.assertEqual(check["spread"], entry["spread"])
                self.assertEqual(check["band"], list(entry["band"]))
                seen.add((field, int(buffer)))
            elif name == "dtlb_walk_count_tolerance_512":
                self.assertEqual(check["reference_median_count"],
                                 _REF["walk512_median_count"])
                seen.add(("walk512",))
        self.assertEqual(
            seen,
            {key for key in _REF["bands"] if key != ("dtlb_walk_per_1k", 512)}
            | {("walk512",)},
        )

    def test_missing_or_incomplete_pool_runs_are_hard_errors(self):
        # fail-closed：池 run 缺失、带失败记录、buffer 组不全或损坏
        # JSON → TlbError，不静默降级为跳过判定。
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "runs"
            with self.subTest(case="pool missing"):
                with self.assertRaises(TlbError):
                    sm8650_tlb._compute_anchor_references(root)
            _write_pool(root)
            with self.subTest(case="complete synthetic pool computes"):
                references = sm8650_tlb._compute_anchor_references(root)
                self.assertEqual(len(references["bands"]), 8)
            with self.subTest(case="pool run with failed records"):
                run_dir = root / _POOL_RUNS[0]
                record = json.loads(
                    (run_dir / "records.jsonl").read_text(encoding="utf-8")
                    .splitlines()[0]
                )
                record["status"] = "failed"
                record["metrics"] = []
                with open(run_dir / "records.jsonl", "a",
                          encoding="utf-8") as handle:
                    handle.write(json.dumps(record) + "\n")
                with self.assertRaises(TlbError):
                    sm8650_tlb._compute_anchor_references(root)
            with self.subTest(case="corrupt records.jsonl"):
                # 损坏 JSON 同样 fail-closed 为 TlbError（JSONDecodeError
                # 不外泄）。先重建干净池再损坏其一。
                _write_pool(root)
                run_dir = root / _POOL_RUNS[1]
                (run_dir / "records.jsonl").write_text(
                    '{"schema_version": "2.0", corrupt\n', encoding="utf-8"
                )
                with self.assertRaises(TlbError):
                    sm8650_tlb._compute_anchor_references(root)
            with self.subTest(case="buffer group missing"):
                _write_pool(root)
                run_dir = root / _POOL_RUNS[2]
                lines = (run_dir / "records.jsonl").read_text(
                    encoding="utf-8").splitlines()
                kept = [
                    line for line in lines
                    if json.loads(line)["params"]["buffer_kb"] == 512
                ]
                (run_dir / "records.jsonl").write_text(
                    "\n".join(kept) + "\n", encoding="utf-8"
                )
                with self.assertRaises(TlbError):
                    sm8650_tlb._compute_anchor_references(root)


def _pool_record(buffer_kb, loads, walk_count=8.0):
    """池 fail-closed fixture 的最小 ok 记录（_reference_values 的消费
    面：params + 四个被读 metric 的 observations）。"""
    def _observations(value):
        return [{"sample_index": index, "value": value} for index in range(2)]

    return {
        "schema_version": "2.0",
        "status": "ok",
        "params": {"buffer_kb": buffer_kb, "loads": loads},
        "metrics": [
            {"name": "latency_ns", "observations": _observations(2.7)},
            {"name": "pmu.cycles.count",
             "observations": _observations(7.5 * loads)},
            {"name": "pmu.l1d_tlb_refill.count",
             "observations": _observations(285.0 * loads / 1000.0)},
            {"name": "pmu.dtlb_walk.count",
             "observations": _observations(walk_count)},
        ],
    }


def _write_pool(root):
    """在 root 下落 6 个最小合法池 run（records + manifest）。"""
    root.mkdir(parents=True, exist_ok=True)
    for name in _POOL_RUNS:
        run_dir = root / name
        run_dir.mkdir(parents=True, exist_ok=True)
        records = [
            _pool_record(512, 65536),
            _pool_record(3072, 393216),
        ]
        (run_dir / "records.jsonl").write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )
        (run_dir / "run-manifest.json").write_text(json.dumps({
            "schema_version": "1.0",
            "experiment_id": _ANCHOR_ID,
            "summary": {"total": 2, "ok": 2, "failed": 0,
                        "skipped": 0, "unsupported": 0},
        }), encoding="utf-8")


# ---------------------------------------------------------------------------
# §7 Phase D THP cohort 分级 / 停止预算 / 转化表 + §7 Phase C Q3 默认终态
#
# cohort 输入行与 AnalysisResult.groups 同形——分级只消费已过
# analyze_records 拒绝机制的有效样本；budget/转化表消费原始 records（含
# 失败记录），policy 归属取自 records 的 params 策略旗标 / 观测 requested
# 字段（确定性来源，不读时钟或随机源）。
# ---------------------------------------------------------------------------


def _all_keys(node):
    """递归收集嵌套 dict/list 的全部键（Q3 "无成本值" 断言用）。"""
    keys = set()
    if isinstance(node, dict):
        for key, value in node.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(node, list):
        for item in node:
            keys |= _all_keys(item)
    return keys


def _cohort_row(buffer_kb, seed, backing, latencies,
                refill_per_1k=300.0, walk_per_1k=1.0):
    """Phase D cohort 分级输入行（per-(buffer × seed × 实际 backing) 的有
    效样本集，同 AnalysisResult.groups 形）。"""
    return {
        "buffer_kb": buffer_kb,
        "seed": seed,
        "page_policy_actual": backing,
        "samples": [{
            "latency_ns": float(latency),
            "l1d_tlb_refill_per_1k": float(refill_per_1k),
            "dtlb_walk_per_1k": float(walk_per_1k),
        } for latency in latencies],
    }


def _thp_record(seed=42, *, buffer_kb=2304, latencies=(2.4,) * 10,
                multiplexed=()):
    """Phase D -T case 记录：params thp=1（无 base_pages），观测 requested
    =thp-madvise——budget/转化表的 policy 归属两来源保持一致。"""
    record = _record(buffer_kb=buffer_kb, seed=seed, backing="thp",
                     latencies=latencies, multiplexed=multiplexed)
    del record["params"]["base_pages"]
    record["params"]["thp"] = 1
    for metric in record["metrics"]:
        for observation in metric["observations"]:
            observation["page_policy_requested"] = "thp-madvise"
    return record


def _failed_thp_record(seed=20260928, *, buffer_kb=2304, reason="probe-exit-1"):
    """Phase D 失败 case：空 metrics + 结构化 failure（schema v2）。"""
    record = _thp_record(seed=seed, buffer_kb=buffer_kb)
    record["status"] = "failed"
    record["metrics"] = []
    record["failure"] = {"reason": reason, "detail": "synthetic Phase D failure"}
    return record


class TestThpCohortGrading(unittest.TestCase):
    """§7 Phase D cohort 分级（P0-5）：比较级 ≥5 / 描述级 3–4 / <3 →
    INSUFFICIENT_COHORT；跨 seed 同制度合并、异制度分列；mixed 不并入 thp。"""

    def test_five_valid_samples_are_comparative_with_median(self):
        # ① 5 个有效样本 → 比较级：median [p25, p75] 齐备（满足 §6.3 的
        # ≥5 取 median 纪律），终态无（可进入正式 cohort 比较）。
        row = _cohort_row(512, 42, "thp", [2.0, 2.1, 2.2, 2.3, 4.0])
        cohorts = grade_thp_cohorts([row])["cohorts"]
        self.assertEqual(len(cohorts), 1)
        cohort = cohorts[0]
        self.assertEqual(cohort["cohort"], "thp")
        self.assertTrue(cohort["merged"])
        unit = cohort["units"][0]
        self.assertEqual(unit["grade"], "comparative")
        self.assertIsNone(unit["terminal"])
        self.assertEqual(unit["valid_samples"], 5)
        self.assertEqual(unit["seeds"], [42])
        # 三个 Q4 预注册指标（latency / R_0x05 / R_0x34）都有统计。
        self.assertEqual(set(unit["stats"]), {"latency_ns",
                                              "l1d_tlb_refill_per_1k",
                                              "dtlb_walk_per_1k"})
        self.assertEqual(unit["stats"]["latency_ns"]["median"], 2.2)
        self.assertEqual(unit["stats"]["latency_ns"]["p25"], 2.1)
        self.assertEqual(unit["stats"]["latency_ns"]["p75"], 2.3)

    def test_four_valid_samples_are_descriptive_without_median(self):
        # ② 4 个 → 描述级：只报转化计数与描述性原始观测，**不输出**
        # cohort median；未达比较级 → 终态 INSUFFICIENT_COHORT。
        row = _cohort_row(512, 42, "thp", [2.0, 2.1, 2.2, 2.3])
        unit = grade_thp_cohorts([row])["cohorts"][0]["units"][0]
        self.assertEqual(unit["grade"], "descriptive")
        self.assertEqual(unit["terminal"], "INSUFFICIENT_COHORT")
        self.assertNotIn("stats", unit)
        self.assertEqual(unit["observations"]["latency_ns"], [2.0, 2.1, 2.2, 2.3])

    def test_two_valid_samples_are_insufficient_cohort(self):
        # ③ 2 个 → INSUFFICIENT_COHORT（预注册终态，不追加尝试）。
        row = _cohort_row(512, 42, "thp", [2.0, 2.1])
        unit = grade_thp_cohorts([row])["cohorts"][0]["units"][0]
        self.assertEqual(unit["grade"], "insufficient")
        self.assertEqual(unit["terminal"], "INSUFFICIENT_COHORT")
        self.assertNotIn("stats", unit)
        self.assertNotIn("observations", unit)

    def test_cross_seed_same_regime_merges_counts(self):
        # ④ 跨 seed 同制度（median 偏差 ≤10% 且 [p25,p75] 两两相交）→
        # 合并计样本数。4 seed × 10 = 40 → 比较级。
        rows = [_cohort_row(512, seed, "thp", [2.0 + 0.01 * k for k in range(10)])
                for seed in (42, 7, 1337, 20260928)]
        cohort = grade_thp_cohorts(rows)["cohorts"][0]
        self.assertTrue(cohort["merged"])
        self.assertNotIn("regime_failures", cohort)
        unit = cohort["units"][0]
        self.assertEqual(unit["seeds"], [7, 42, 1337, 20260928])
        self.assertEqual(unit["valid_samples"], 40)
        self.assertEqual(unit["grade"], "comparative")
        # 合并不要求分布全等：偏差 7% ≤10% 且区间相交的同制度 seed 对也合并。
        rows = [_cohort_row(512, 42, "thp", [1.9] * 3 + [2.0] * 4 + [2.1] * 3),
                _cohort_row(512, 7, "thp", [2.033] * 3 + [2.14] * 4 + [2.247] * 3)]
        cohort = grade_thp_cohorts(rows)["cohorts"][0]
        self.assertTrue(cohort["merged"])
        self.assertEqual(cohort["units"][0]["valid_samples"], 20)

    def test_cross_seed_regime_split_lists_per_seed(self):
        # ④ 异制度 → 按 seed 分列报告（每 seed 自成报告单元、各自分级）。
        rows = [_cohort_row(512, 42, "thp", [2.0] * 10),
                _cohort_row(512, 7, "thp", [2.0] * 10),
                _cohort_row(512, 1337, "thp", [2.42] * 10)]  # median 偏差 21%
        cohort = grade_thp_cohorts(rows)["cohorts"][0]
        self.assertFalse(cohort["merged"])
        self.assertEqual(len(cohort["units"]), 3)
        self.assertEqual([unit["seeds"] for unit in cohort["units"]],
                         [[7], [42], [1337]])
        for unit in cohort["units"]:
            self.assertEqual(unit["valid_samples"], 10)
            self.assertEqual(unit["grade"], "comparative")
        self.assertTrue(any(
            failure["seeds"] == [42, 1337] and not failure["intervals_intersect"]
            for failure in cohort["regime_failures"]
        ))
        # 合取的另一支也要钉：median 偏差 9% ≤10% 但 [p25,p75] 不相交 → 分列。
        rows = [_cohort_row(512, 42, "thp", [2.0] * 10),
                _cohort_row(512, 7, "thp", [2.18] * 10)]
        cohort = grade_thp_cohorts(rows)["cohorts"][0]
        self.assertFalse(cohort["merged"])
        self.assertEqual(len(cohort["units"]), 2)
        failure = cohort["regime_failures"][0]
        self.assertLessEqual(failure["median_deviation"], 0.10)
        self.assertFalse(failure["intervals_intersect"])

    def test_mixed_backing_is_not_merged_into_thp(self):
        # ⑥ 同一 -T case 内逐进程实际 backing 不同：analyze_records 按
        # actual backing 分列（§9.3 ④），cohort 分级同样分列——mixed 样本
        # 不补 thp 的计数（若并入，thp 会显示 10 → 钉死分列）。
        record = _thp_record(seed=42)
        for metric in record["metrics"]:
            for index in (7, 8, 9):
                metric["observations"][index]["page_policy_actual"] = "mixed"
        result = analyze_records([record], "run-a")
        groups = {group["page_policy_actual"]: group
                  for group in result.groups}
        self.assertEqual(set(groups), {"thp", "mixed"})
        self.assertEqual(len(groups["thp"]["samples"]), 7)
        self.assertEqual(len(groups["mixed"]["samples"]), 3)
        cohorts = {cohort["cohort"]: cohort
                   for cohort in grade_thp_cohorts(result.groups)["cohorts"]}
        self.assertEqual(cohorts["thp"]["units"][0]["valid_samples"], 7)
        self.assertEqual(cohorts["thp"]["units"][0]["grade"], "comparative")
        self.assertEqual(cohorts["mixed"]["units"][0]["valid_samples"], 3)
        self.assertEqual(cohorts["mixed"]["units"][0]["grade"], "descriptive")

    def test_cohort_row_contract_errors(self):
        # 契约缺项硬错误：未知 backing / 空样本 / 缺数值字段；空输入 → 空表。
        self.assertEqual(grade_thp_cohorts([]), {"cohorts": []})
        with self.subTest(case="unknown backing"):
            with self.assertRaises(TlbError):
                grade_thp_cohorts([_cohort_row(512, 42, "weird", [2.0])])
        with self.subTest(case="empty samples"):
            row = _cohort_row(512, 42, "thp", [2.0])
            row["samples"] = []
            with self.assertRaises(TlbError):
                grade_thp_cohorts([row])
        with self.subTest(case="missing metric field"):
            row = _cohort_row(512, 42, "thp", [2.0])
            del row["samples"][0]["dtlb_walk_per_1k"]
            with self.assertRaises(TlbError):
                grade_thp_cohorts([row])

    def test_seed_deviation_at_ten_percent_boundary_merges(self):
        # 边界：median 偏差恰好 10%（≤ 阈值判同制度，取 > 才分列）且
        # [p25,p75] 相交 → 合并。median 20.0/22.0：|22−20|/20 与字面量
        # 0.10 为同一 double（2/20 的最近舍入），判定不依赖浮点运气。
        rows = [_cohort_row(512, 42, "thp", [20.0] * 6 + [22.0] * 4),
                _cohort_row(512, 7, "thp", [20.0] * 4 + [22.0] * 6)]
        cohort = grade_thp_cohorts(rows)["cohorts"][0]
        self.assertTrue(cohort["merged"])
        self.assertNotIn("regime_failures", cohort)
        unit = cohort["units"][0]
        self.assertEqual(unit["seeds"], [7, 42])
        self.assertEqual(unit["valid_samples"], 20)
        self.assertEqual(unit["grade"], "comparative")


class TestQ3DefaultOutcome(unittest.TestCase):
    """§7 Phase C Q3 默认终态（P1-6）：关联型报告 + MODEL_UNIDENTIFIABLE；
    本计划不含冻结模型规格 → 绝不输出成本值。"""

    def test_missing_g3_yields_model_unidentifiable_without_cost(self):
        # ⑤ G3 缺失 → MODEL_UNIDENTIFIABLE；不得声称"已检验 data-miss 共线
        # 性"（§9.3 ⑬）；输出无任何成本字段（递归扫描所有键）。
        verdict = adjudicate_q3(g3_executed=False)
        self.assertEqual(verdict["status"], "MODEL_UNIDENTIFIABLE")
        evidence = verdict["evidence"]
        self.assertFalse(evidence["g3_executed"])
        self.assertFalse(evidence["data_miss_collinearity_checked"])
        self.assertTrue(evidence["mmutc_confound_unresolved"])
        keys = _all_keys(verdict)
        self.assertFalse([key for key in keys if "cost" in key.lower()],
                         f"cost-like keys present: {sorted(keys)}")

    def test_g3_executed_still_defaults_without_frozen_model_spec(self):
        # G3 执行也不自动升级：G3 只解决"没测 data miss"，不解决因果识别；
        # 成本型升级须实施计划另行冻结模型规格——本计划不含 → 传入即硬错误。
        points = [{"pages": 2048, "dtlb_walk_per_1k": 1.2, "cyc_per_load": 3.0},
                  {"pages": 512, "dtlb_walk_per_1k": 0.01, "cyc_per_load": 2.0}]
        verdict = adjudicate_q3(g3_executed=True, anchors_comparable=True,
                                association_points=points)
        self.assertEqual(verdict["status"], "MODEL_UNIDENTIFIABLE")
        self.assertTrue(verdict["evidence"]["g3_executed"])
        # 关联数据占位原样回显、按页数排序（无成本值）。
        self.assertEqual([point["pages"] for point in verdict["association_points"]],
                         [512, 2048])
        self.assertFalse([key for key in _all_keys(verdict)
                          if "cost" in key.lower()])
        with self.assertRaises(TlbError):
            adjudicate_q3(g3_executed=True, model_spec={"name": "ad-hoc"})

    def test_evidence_marks_model_spec_unfrozen(self):
        # evidence 显式登记"模型规格未冻结"：审计侧可机读区分默认终态与
        # （未来）已冻结模型的判定，不靠 status 文案推断。
        verdict = adjudicate_q3()
        self.assertIs(verdict["evidence"]["model_spec_frozen"], False)


class TestThpProcessBudget(unittest.TestCase):
    """§7 Phase D 停止预算：每（buffer × policy）≤40 进程次（4 seed × 10），
    失败/被拒样本计入额度（§9.3 ⑮ 失败计额）。"""

    def test_budget_counts_failed_records_toward_cap(self):
        # ⑦ 3 case × 10 进程 + 1 失败 case（计 10）= 40 → 恰好到上限不超；
        # 再加一个 ok case → 50 → 超支。
        ok = [_thp_record(seed=seed) for seed in (42, 7, 1337)]
        budget = audit_thp_budget([*ok, _failed_thp_record()])
        self.assertEqual(budget["cap"], 40)
        entry = budget["entries"][0]
        self.assertEqual(entry["buffer_kb"], 2304)
        self.assertEqual(entry["policy"], "thp-madvise")
        self.assertEqual(entry["processes_used"], 40)
        self.assertEqual(entry["ok_records"], 3)
        self.assertEqual(entry["failed_records"], 1)
        self.assertFalse(entry["exceeded"])
        over = audit_thp_budget([*ok, _thp_record(seed=20260928),
                                 _failed_thp_record(seed=5)])
        entry = over["entries"][0]
        self.assertEqual(entry["processes_used"], 50)
        self.assertTrue(entry["exceeded"])

    def test_rejected_samples_still_count_toward_budget(self):
        # 被拒样本（multiplex）进程已产生 → 计入额度（10 观测 = 10 进程次）。
        entry = audit_thp_budget([_thp_record(multiplexed=(3, 4))])["entries"][0]
        self.assertEqual(entry["processes_used"], 10)
        self.assertEqual(entry["ok_records"], 1)

    def test_budget_is_per_buffer_per_policy(self):
        # (buffer × policy) 各自计额：-B 与 -T 同 buffer 分列、互不占额。
        base_record = _record(buffer_kb=2304, seed=42, latencies=(2.4,) * 10)
        budget = audit_thp_budget([base_record, _thp_record(seed=42)])
        keys = [(entry["buffer_kb"], entry["policy"])
                for entry in budget["entries"]]
        self.assertEqual(keys, [(2304, "base-madvise"), (2304, "thp-madvise")])
        for entry in budget["entries"]:
            self.assertEqual(entry["processes_used"], 10)

    def test_budget_exactly_over_cap(self):
        # 边界：41 进程次 > 40 → 超支（40 恰好不超已在 ⑦ 钉过）。
        records = [_thp_record(seed=seed) for seed in (42, 7, 1337, 20260928)]
        records.append(_thp_record(seed=5, latencies=(2.4,)))
        entry = audit_thp_budget(records)["entries"][0]
        self.assertEqual(entry["processes_used"], 41)
        self.assertTrue(entry["exceeded"])


class TestThpConversionTable(unittest.TestCase):
    """§7 Phase D 必报转化表（选择偏差披露）：请求次数 → 实际 backing 构成
    → 失败数 → 进入分析样本数。"""

    def test_conversion_table_flow(self):
        full_thp = _thp_record(seed=42)                       # 10 × thp
        mixed_case = _thp_record(seed=7)                      # 5 thp + 5 mixed
        for metric in mixed_case["metrics"]:
            for index in range(5):
                metric["observations"][index]["page_policy_actual"] = "mixed"
        rejected_case = _thp_record(seed=1337, multiplexed=(0, 1))  # 8 有效
        failed = _failed_thp_record()                         # 计 10 请求
        table = build_thp_conversion(
            [full_thp, mixed_case, rejected_case, failed], "run-a"
        )
        self.assertEqual(len(table), 1)
        entry = table[0]
        self.assertEqual(entry["buffer_kb"], 2304)
        self.assertEqual(entry["policy"], "thp-madvise")
        self.assertEqual(entry["requested"], 40)
        self.assertEqual(entry["backing"], {"thp": 23, "mixed": 5})
        self.assertEqual(entry["failed_records"], 1)
        self.assertEqual(entry["failure_reasons"], {"probe-exit-1": 1})
        self.assertEqual(entry["analysis_samples"], 28)
        self.assertEqual(entry["rejected_samples"], 2)

    def test_requested_policy_disagreement_is_hard_error(self):
        # policy 归属两来源（params 旗标 / 观测 requested）不一致 → 硬错误，
        # 不猜测归属。
        record = _thp_record()  # params thp=1
        for metric in record["metrics"]:
            for observation in metric["observations"]:
                observation["page_policy_requested"] = "base-madvise"
        with self.assertRaises(TlbError):
            audit_thp_budget([record])
        with self.assertRaises(TlbError):
            build_thp_conversion([record], "run-a")


class TestRequestedPolicyAttribution(unittest.TestCase):
    """policy 归属的次要路径：params 旗标归一（同 adapter _binary_flag）、
    观测回退、双缺省 "default"、互斥/未知取值硬错误。"""

    def test_mutually_exclusive_flags_are_hard_error(self):
        record = _thp_record()  # params thp=1
        record["params"]["base_pages"] = 1
        with self.assertRaisesRegex(TlbError, "mutually exclusive"):
            audit_thp_budget([record])

    def test_unknown_requested_observation_is_hard_error(self):
        record = _record(buffer_kb=2304, seed=42, latencies=(2.4,) * 10)
        for metric in record["metrics"]:
            for observation in metric["observations"]:
                observation["page_policy_requested"] = "mystery"
        with self.assertRaisesRegex(TlbError, "unknown page_policy_requested"):
            audit_thp_budget([record])

    def test_string_zero_flag_is_off(self):
        # 字符串 "0" = OFF（真值判定会误判为 ON 并与观测冲突——钉死归一）。
        record = _record(buffer_kb=2304, seed=42, latencies=(2.4,) * 10)
        record["params"]["thp"] = "0"  # OFF：不与 base_pages=1 互斥
        entry = audit_thp_budget([record])["entries"][0]
        self.assertEqual(entry["policy"], "base-madvise")

    def test_string_one_flag_is_on(self):
        record = _thp_record()
        record["params"]["thp"] = "1"
        entry = audit_thp_budget([record])["entries"][0]
        self.assertEqual(entry["policy"], "thp-madvise")

    def test_non_binary_flag_value_is_hard_error(self):
        for bad in (2, "yes", 0.5):
            with self.subTest(value=bad):
                record = _thp_record()
                record["params"]["thp"] = bad
                with self.assertRaisesRegex(TlbError, "must be 0 or 1"):
                    audit_thp_budget([record])

    def test_observation_fallback_without_flags(self):
        # params 无旗标 → 由观测的 page_policy_requested 回退归属。
        record = _record(buffer_kb=2304, seed=42, latencies=(2.4,) * 10)
        del record["params"]["base_pages"]
        entry = audit_thp_budget([record])["entries"][0]
        self.assertEqual(entry["policy"], "base-madvise")

    def test_no_flag_no_observation_defaults(self):
        # params 无旗标 + 观测无 requested 字段 → "default"（不猜测）。
        record = _record(buffer_kb=2304, seed=42, latencies=(2.4,) * 10)
        del record["params"]["base_pages"]
        for metric in record["metrics"]:
            for observation in metric["observations"]:
                del observation["page_policy_requested"]
        entry = audit_thp_budget([record])["entries"][0]
        self.assertEqual(entry["policy"], "default")


# ---------------------------------------------------------------------------
# §5.3 固定开销拟合判定（adjudicate_fixed_overhead）
#
# fixture 为精确线性 C = a + b·N 的合成中位计数点。需要逐位精确的测试
# （阈值边界/离散度/确定性）用 tiers (8,16,24)：Σloads = slots×48 可被 3
# 整除 → n̄ 在 double 下精确表示，整数 a/b 经闭式最小二乘逐位回收——边界
# 断言不依赖浮点运气。协议档 (8,64,256) 的测试用容差断言（浮点回收误差
# 源自大数抵消，量级 ≪ 断言 delta）。
# ---------------------------------------------------------------------------

_OVERHEAD_EVENT = "pmu.cycles.count"
_OVERHEAD_SEEDS = (42, 7, 1337, 20260928)


def _overhead_row(buffer_kb, slots, loads, seed, event, count):
    """§5.3 判定的单行输入：(buffer × 长度 × seed × 事件) 的中位计数点。"""
    return {"buffer_kb": buffer_kb, "slots": slots, "loads": loads,
            "seed": seed, "event": event, "count": float(count)}


def _overhead_rows(*, a, b, buffers=(512, 16384), seeds=_OVERHEAD_SEEDS,
                   tiers=(8, 64, 256), event=_OVERHEAD_EVENT):
    """精确线性 C = a + b·N 的逐 case median 计数点（两点 × 长度 × seed）。"""
    rows = []
    for buffer_kb in buffers:
        slots = buffer_kb * 1024 // 64
        for seed in seeds:
            for tier in tiers:
                loads = slots * tier
                rows.append(_overhead_row(buffer_kb, slots, loads, seed, event,
                                          a + b * loads))
    return rows


class TestFixedOverheadAdjudication(unittest.TestCase):
    """§5.3（任务书 309–323 行冻结规则）：逐事件拟合 C_e(N)=a_e+b_e·N，
    正式窗口长度下 |a_e|/C_e(N) ≤5% 判边界开销可忽略，超过标注"含固定
    开销"；跨 seed 斜率离散度只报告不设阈值。"""

    def test_exact_linear_points_recover_intercept_and_slope(self):
        # ① 精确线性 C = 100 + 2N（协议档 8/64/256，2 buffer × 4 seed ×
        # 3 长度）：每组拟合在浮点容差内回收 a=100、b=2。
        rows = _overhead_rows(a=100, b=2)
        self.assertEqual(len(rows), 2 * 4 * 3)
        result = adjudicate_fixed_overhead(rows)
        judgments = result["judgments"]
        self.assertEqual([j["buffer_kb"] for j in judgments], [512, 16384])
        for judgment in judgments:
            self.assertEqual(judgment["event"], _OVERHEAD_EVENT)
            self.assertEqual([entry["seed"] for entry in judgment["per_seed"]],
                             [7, 42, 1337, 20260928])
            self.assertEqual(judgment["n_formal"],
                             judgment["buffer_kb"] * 1024 // 64 * 8)
            for entry in judgment["per_seed"]:
                self.assertAlmostEqual(entry["a"], 100.0, delta=1e-5)
                self.assertAlmostEqual(entry["b"], 2.0, delta=1e-9)
                self.assertLessEqual(entry["ratio_at_formal"], 0.05)
            self.assertTrue(judgment["negligible"])
            self.assertNotIn("note", judgment)

    def test_ratio_above_threshold_is_not_negligible_and_noted(self):
        # ② a 占正式窗口 6%（>5%）→ negligible=False + "含固定开销"。
        # tiers (8,16,24) + 整数参数：a=196608、b=47、N_formal=65536 →
        # C_formal=3276800，196608/3276800=3/50，IEEE 除法正确舍入结果与
        # 字面量 0.06 是同一 double。
        rows = _overhead_rows(a=196608, b=47, buffers=(512,), seeds=(42,),
                              tiers=(8, 16, 24))
        judgment = adjudicate_fixed_overhead(rows)["judgments"][0]
        self.assertEqual(judgment["worst_abs_ratio"], 0.06)
        self.assertFalse(judgment["negligible"])
        self.assertEqual(judgment["note"], "含固定开销")

    def test_ratio_at_five_percent_boundary_is_negligible(self):
        # ③ ratio 恰为 5%（≤ 取边界）→ negligible=True。65536/1310720
        # = 1/20，除法正确舍入结果与字面量 0.05 是同一 double。
        rows = _overhead_rows(a=65536, b=19, buffers=(512,), seeds=(42,),
                              tiers=(8, 16, 24))
        judgment = adjudicate_fixed_overhead(rows)["judgments"][0]
        self.assertEqual(judgment["worst_abs_ratio"], 0.05)
        self.assertTrue(judgment["negligible"])
        self.assertNotIn("note", judgment)

    def test_missing_length_tier_is_hard_error(self):
        # ④ 组内长度档缺失（只剩 2 档）→ TlbError（协议偏离 fail-closed）；
        # 多出第 4 档同样拒绝。
        rows = _overhead_rows(a=100, b=2, buffers=(512,), seeds=(42,),
                              tiers=(8, 64))
        with self.assertRaises(TlbError):
            adjudicate_fixed_overhead(rows)
        with self.subTest(case="extra tier"):
            rows = _overhead_rows(a=100, b=2, buffers=(512,), seeds=(42,),
                                  tiers=(8, 16, 64, 256))
            with self.assertRaises(TlbError):
                adjudicate_fixed_overhead(rows)

    def test_duplicate_point_is_hard_error(self):
        # ⑤ (buffer, event, seed, 长度) 重复 → TlbError（即使去重后恰好
        # 3 档，重复本身是协议偏离，不许静默）。
        rows = _overhead_rows(a=100, b=2, buffers=(512,), seeds=(42,),
                              tiers=(8, 16, 24))
        rows.append(dict(rows[0]))
        with self.assertRaises(TlbError):
            adjudicate_fixed_overhead(rows)

    def test_bad_counts_are_hard_errors(self):
        # ⑥ count 为负 / 非数值 / 非有限（NaN、inf 不是中位计数）→ TlbError。
        base = _overhead_rows(a=100, b=2, buffers=(512,), seeds=(42,),
                              tiers=(8, 16, 24))
        for label, bad in (("negative", -1.0), ("string", "100"),
                           ("nan", float("nan")), ("inf", float("inf"))):
            with self.subTest(label=label):
                rows = [dict(row) for row in base]
                rows[0]["count"] = bad
                with self.assertRaises(TlbError):
                    adjudicate_fixed_overhead(rows)

    def test_slope_spread_reports_across_seeds_without_threshold(self):
        # ⑦ 跨 seed 斜率离散度：b 不同 → >0（(4−2)/4=0.5）；全同 → 0.0。
        # 只报告不设阈值（§5.3 未冻结数值门槛，不发明）。
        divergent = _overhead_rows(a=100, b=2, buffers=(512,), seeds=(42,),
                                   tiers=(8, 16, 24))
        divergent += _overhead_rows(a=100, b=4, buffers=(512,), seeds=(7,),
                                    tiers=(8, 16, 24))
        judgment = adjudicate_fixed_overhead(divergent)["judgments"][0]
        self.assertEqual(judgment["slope_spread_rel"], 0.5)
        same = _overhead_rows(a=100, b=2, buffers=(512,), seeds=(42, 7),
                              tiers=(8, 16, 24))
        judgment = adjudicate_fixed_overhead(same)["judgments"][0]
        self.assertEqual(judgment["slope_spread_rel"], 0.0)

    def test_output_is_deterministic_and_sorted(self):
        # ⑧ 乱序输入 → 输出排序稳定（judgments 按 (buffer_kb, event)、
        # per_seed 按 seed）；两次调用逐等。
        rows = (_overhead_rows(a=100, b=2, buffers=(512, 16384), seeds=(42, 7),
                               tiers=(8, 16, 24), event="pmu.dtlb_walk.count")
                + _overhead_rows(a=100, b=2, buffers=(512, 16384), seeds=(42, 7),
                                 tiers=(8, 16, 24), event="pmu.cycles.count"))
        first = adjudicate_fixed_overhead(rows)
        self.assertEqual(first, adjudicate_fixed_overhead(rows))
        self.assertEqual(first, adjudicate_fixed_overhead(list(reversed(rows))))
        keys = [(j["buffer_kb"], j["event"]) for j in first["judgments"]]
        self.assertEqual(keys, sorted(keys))
        for judgment in first["judgments"]:
            self.assertEqual([entry["seed"] for entry in judgment["per_seed"]],
                             [7, 42])

    def test_floor_event_zero_formal_count_is_not_negligible(self):
        # ⑨ floor 事件全零计数（a=b=0 → C_formal=0）→ ratio=inf →
        # negligible=False：近零计数不产生"可忽略"判定（C_e(N)≤0 时比值
        # 视为无穷）；max|b|=0 时 slope_spread_rel 定义为 0.0。
        rows = _overhead_rows(a=0, b=0, buffers=(512,), seeds=(42,),
                              tiers=(8, 16, 24))
        judgment = adjudicate_fixed_overhead(rows)["judgments"][0]
        self.assertEqual(judgment["per_seed"][0]["ratio_at_formal"],
                         float("inf"))
        self.assertEqual(judgment["worst_abs_ratio"], float("inf"))
        self.assertEqual(judgment["slope_spread_rel"], 0.0)
        self.assertFalse(judgment["negligible"])
        self.assertEqual(judgment["note"], "含固定开销")

    def test_latency_rows_are_rejected(self):
        # ⑩ latency_ns 是墙钟量，不在 §5.3 拟合范围 → TlbError（防误消费）。
        rows = _overhead_rows(a=100, b=2, buffers=(512,), seeds=(42,),
                              tiers=(8, 16, 24), event="latency_ns")
        with self.assertRaises(TlbError):
            adjudicate_fixed_overhead(rows)

    def test_row_contract_errors(self):
        # 字段缺失/类型错/取值越界 → TlbError；空输入 → 空判定表（同
        # grade_thp_cohorts 空表先例）。
        self.assertEqual(adjudicate_fixed_overhead([]), {"judgments": []})
        base = _overhead_rows(a=100, b=2, buffers=(512,), seeds=(42,),
                              tiers=(8, 16, 24))
        for key in ("buffer_kb", "slots", "loads", "seed", "event", "count"):
            with self.subTest(missing=key):
                rows = [dict(row) for row in base]
                del rows[0][key]
                with self.assertRaises(TlbError):
                    adjudicate_fixed_overhead(rows)
        bad_values = [
            ("buffer_kb", "512"), ("buffer_kb", 0),
            ("slots", 8192.0), ("slots", 0),
            ("loads", True), ("loads", 0),
            ("seed", -1), ("seed", "42"),
            ("event", ""), ("event", 123),
            ("count", True),
        ]
        for key, bad in bad_values:
            with self.subTest(**{key: bad}):
                rows = [dict(row) for row in base]
                rows[0][key] = bad
                with self.assertRaises(TlbError):
                    adjudicate_fixed_overhead(rows)
        with self.subTest(case="slots disagree within buffer"):
            # slots 是 buffer 的纯函数（调用方派生 buffer_kb×1024/stride），
            # 同 buffer 不一致即混入异协议数据 → TlbError。
            rows = [dict(row) for row in base]
            rows[0]["slots"] = 4096
            with self.assertRaises(TlbError):
                adjudicate_fixed_overhead(rows)
        with self.subTest(case="row is not an object"):
            with self.assertRaises(TlbError):
                adjudicate_fixed_overhead([None])
        for bad_param in (0, -8, 2.5, "8"):
            with self.subTest(formal_loads_per_slot=bad_param):
                with self.assertRaises(TlbError):
                    adjudicate_fixed_overhead(
                        base, formal_loads_per_slot=bad_param
                    )


if __name__ == "__main__":
    unittest.main()
