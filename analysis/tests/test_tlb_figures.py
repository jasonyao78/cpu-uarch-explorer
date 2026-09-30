# SPDX-License-Identifier: Apache-2.0
"""TLB 战役图表生成器测试（analysis/tlb_figures.py）。

三层：
1. 纯函数钉（合成 analyze_records/grade_thp_cohorts 产出形）：逐点合并
   规则（(buffer,seed) 组中位数 → 重合点跨 run 合并 → 跨 seed 中位数的
   中位数）、cohort 展示值只取比较级单元 median（描述级/不足级不出点，
   遵守 §7 Phase D 分级纪律）；
2. CLI 合成数据端到端：四图 + report.md 产出、曲线点数钉、幂等（同输
   入必同输出）、fail-closed（缺 run / 缺 metric / 网格缺口 / 无比较级
   mixed → 非零退出 + stderr）；
3. 真实数据集形状钉（读仓内 data/public/runs，同 test_sm8650_tlb 池互
   钉先例）：20 点合并曲线、图 4 系列形状与 -82% 方向。数据修正走
   revision history 时本类随数据集一起更新。
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from analysis import tlb_figures
from analysis.sm8650_tlb import grade_thp_cohorts

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNS_ROOT = _REPO_ROOT / "data" / "public" / "runs"

_FIELD = "l1d_tlb_refill_per_1k"


def _group(buffer_kb: int, seed: int, field: str, median: float,
           backing: str = "base", ring_passes: int = 8) -> dict:
    """analyze_records 分组产出形的最小合成（纯函数测试用）。"""
    return {"buffer_kb": buffer_kb, "seed": seed, "page_policy_actual": backing,
            "ring_passes": ring_passes, field: {"median": median}}


def _unit(seeds, n, grade, median=None, terminal=None):
    unit = {"seeds": seeds, "valid_samples": n, "grade": grade, "terminal": terminal}
    if median is not None:
        unit["stats"] = {_FIELD: {"median": median}}
    return unit


class TestRunRosterPinned(unittest.TestCase):
    """run 名单与网格钉死战役数据集（出处：任务书 v4.4 §7 + 终审 §2）。"""

    def test_roster(self):
        self.assertEqual(tlb_figures.RUN_COARSE,
                         "20260930T004843Z-ptr-chase-sm8650-x4-tlb-coarse")
        self.assertEqual(tlb_figures.RUN_DENSE,
                         "20260930T010808Z-ptr-chase-sm8650-x4-tlb-dense")
        self.assertEqual(tlb_figures.RUN_THP_BASE,
                         "20260930T014014Z-ptr-chase-sm8650-x4-tlb-thp-base")
        self.assertEqual(tlb_figures.RUN_THP_MADVISE,
                         "20260930T013743Z-ptr-chase-sm8650-x4-tlb-thp-madvise")
        self.assertEqual(len(tlb_figures.COARSE_BUFFERS), 13)
        self.assertEqual(len(tlb_figures.COARSE_SEEDS), 2)
        self.assertEqual(len(tlb_figures.DENSE_BUFFERS), 8)
        self.assertEqual(len(tlb_figures.DENSE_SEEDS), 4)
        self.assertIn(4096, tlb_figures.COARSE_BUFFERS)  # 粗扫/致密重合点
        self.assertIn(4096, tlb_figures.DENSE_BUFFERS)


class TestSeedMedians(unittest.TestCase):
    def test_overlap_point_merges_per_seed_across_runs(self):
        # 4096 KiB 重合点：seed7 来自粗扫+致密两个 run → 各 run 组中位数的中位数
        groups = [_group(4096, 7, _FIELD, 100.0), _group(4096, 7, _FIELD, 300.0),
                  _group(4096, 42, _FIELD, 50.0)]
        self.assertEqual(tlb_figures.seed_medians(groups, _FIELD),
                         {(4096, 7): 200.0, (4096, 42): 50.0})

    def test_single_group_passthrough(self):
        self.assertEqual(tlb_figures.seed_medians([_group(128, 7, _FIELD, 4.5)], _FIELD),
                         {(128, 7): 4.5})


class TestMergeSeedMedians(unittest.TestCase):
    def test_median_of_seed_medians(self):
        out = tlb_figures.merge_seed_medians({(128, 7): 4.0, (128, 42): 6.0,
                                              (256, 42): 10.0})
        self.assertEqual(out, [(128, 5.0), (256, 10.0)])

    def test_sorted_by_buffer_and_deterministic(self):
        per_seed = {(512, 7): 1.0, (128, 7): 2.0, (128, 42): 4.0, (128, 1337): 9.0}
        first = tlb_figures.merge_seed_medians(per_seed)
        self.assertEqual(first, [(128, 4.0), (512, 1.0)])
        self.assertEqual(first, tlb_figures.merge_seed_medians(dict(per_seed)))


class TestCurveFromGroups(unittest.TestCase):
    def test_overlap_merge_then_across_seed_merge(self):
        # 4096：seed7 跨 run 合并 200，seed42 单侧 50 → 跨 seed median(50, 200)=125
        groups = [_group(4096, 7, _FIELD, 100.0), _group(4096, 7, _FIELD, 300.0),
                  _group(4096, 42, _FIELD, 50.0), _group(128, 7, _FIELD, 4.0)]
        self.assertEqual(tlb_figures.curve_from_groups(groups, _FIELD),
                         [(128, 4.0), (4096, 125.0)])


class TestCohortSeries(unittest.TestCase):
    def test_only_comparative_units_plotted(self):
        graded = {"cohorts": [
            {"buffer_kb": 3072, "cohort": "mixed", "merged": False,
             "units": [_unit([7], 4, "descriptive", terminal="INSUFFICIENT_COHORT"),
                       _unit([42], 5, "comparative", median=234.14)]},
            {"buffer_kb": 3072, "cohort": "base", "merged": True,
             "units": [_unit([7, 42], 65, "comparative", median=1299.56)]},
        ]}
        self.assertEqual(tlb_figures.cohort_series(graded),
                         {"base": [(3072.0, 1299.56)], "mixed": [(3072.0, 234.14)]})

    def test_unmerged_cohort_takes_median_of_unit_medians(self):
        graded = {"cohorts": [
            {"buffer_kb": 2304, "cohort": "base", "merged": False,
             "units": [_unit([7], 19, "comparative", median=1127.94),
                       _unit([42], 18, "comparative", median=1131.61)]},
        ]}
        self.assertEqual(tlb_figures.cohort_series(graded),
                         {"base": [(2304.0, 1129.775)]})

    def test_buffers_outside_figure_filtered(self):
        graded = {"cohorts": [
            {"buffer_kb": 512, "cohort": "base", "merged": True,
             "units": [_unit([7, 42], 80, "comparative", median=282.4)]},
        ]}
        self.assertEqual(tlb_figures.cohort_series(graded), {})


class TestCohortGradingLines(unittest.TestCase):
    def test_lines_carry_grade_and_terminal(self):
        graded = {"cohorts": [
            {"buffer_kb": 2304, "cohort": "mixed", "merged": False,
             "units": [_unit([7], 1, "insufficient", terminal="INSUFFICIENT_COHORT")]},
            {"buffer_kb": 3072, "cohort": "mixed", "merged": False,
             "units": [_unit([42], 5, "comparative", median=234.14)]},
        ]}
        lines = tlb_figures.cohort_grading_lines(graded)
        self.assertEqual(len(lines), 2)
        self.assertIn("2304 KiB × mixed", lines[0])
        self.assertIn("INSUFFICIENT_COHORT", lines[0])
        self.assertIn("seed42 comparative n=5", lines[1])


# --- CLI 端到端（合成 run，网格形状复刻钉死数据集） ---

_PMU_SPECS = (("pmu.cycles.count", 8, 0x11), ("pmu.mem_access_rd.count", 8, 0x66),
              ("pmu.l1d_tlb_refill.count", 8, 0x05), ("pmu.dtlb_walk.count", 8, 0x34))


def _record(buffer_kb: int, seed: int, latencies, *, backings=None,
            refill_per_1k=300.0, walk_per_1k=1.0, cyc_per_load=16.0,
            mem_rd_per_1k=1000.0, drop_metrics=()) -> dict:
    """满足 G0 证据契约的最小合成记录（仿 test_sm8650_tlb._record 模式）。

    loads = slots × 8（8 ring passes 正式窗口）；PMU 观测值按目标密度反推
    计数（派生口径 R = count/loads×1000、cyc/load = count/loads）。
    """
    loads = buffer_kb * 128
    n = len(latencies)
    backings = backings or ["base"] * n
    observations = [{"sample_index": i, "value": latencies[i], "seed": seed,
                     "page_policy_requested": "base-madvise",
                     "page_policy_actual": backings[i]} for i in range(n)]
    metrics = [{"name": "latency_ns", "value": latencies[0], "unit": "ns",
                "repetitions": n, "observations": observations}]
    targets = {"pmu.cycles.count": cyc_per_load * loads,
               "pmu.mem_access_rd.count": mem_rd_per_1k * loads / 1000.0,
               "pmu.l1d_tlb_refill.count": refill_per_1k * loads / 1000.0,
               "pmu.dtlb_walk.count": walk_per_1k * loads / 1000.0}
    for name, pmu_type, pmu_config in _PMU_SPECS:
        if name in drop_metrics:
            continue
        obs = [{"sample_index": i, "value": targets[name], "seed": seed,
                "pmu_type": pmu_type, "pmu_config": pmu_config,
                "time_enabled_ns": 1000, "time_running_ns": 1000,
                "page_policy_actual": backings[i]} for i in range(n)]
        metrics.append({"name": name, "value": targets[name], "unit": "count",
                        "repetitions": n, "observations": obs})
    return {"schema_version": "2.0", "timestamp": "2026-09-30T01:00:00Z",
            "status": "ok", "target": {"target_id": "redmi-k70pro-01"},
            "probe": {"name": "ptr_chase", "protocol_version": "1.2"},
            "params": {"buffer_kb": buffer_kb, "loads": loads, "stride": 64},
            "metrics": metrics}


def _write_run(run_dir: Path, records: list[dict]) -> None:
    run_dir.mkdir(parents=True)
    with open(run_dir / "records.jsonl", "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def _make_dataset(root: Path, *, drop_one_metric=False, skip_one_record=False,
                  thp_all_base=False) -> None:
    for name, buffers, seeds in (
        (tlb_figures.RUN_COARSE, tlb_figures.COARSE_BUFFERS, tlb_figures.COARSE_SEEDS),
        (tlb_figures.RUN_DENSE, tlb_figures.DENSE_BUFFERS, tlb_figures.DENSE_SEEDS),
    ):
        records = []
        for b in buffers:
            for s in seeds:
                if skip_one_record and (b, s) == (buffers[0], seeds[0]):
                    continue
                records.append(_record(
                    b, s, [2.0 + b / 4096.0] * 6, refill_per_1k=b / 4.0,
                    walk_per_1k=b / 8192.0,
                    drop_metrics=("pmu.dtlb_walk.count",) if drop_one_metric else ()))
        _write_run(root / name, records)
    _write_run(root / tlb_figures.RUN_THP_BASE, [
        _record(b, s, [8.0] * 6, refill_per_1k=1300.0)
        for b in tlb_figures.THP_BUFFERS for s in tlb_figures.THP_SEEDS
    ])
    # -T：3072/seed42 拿 5 mixed + 1 base（比较级 n=5）；2304/seed7 拿 1
    # mixed（不足级）——复刻真实 cohort 分级形状。
    records = []
    for b in tlb_figures.THP_BUFFERS:
        for s in tlb_figures.THP_SEEDS:
            if not thp_all_base and (b, s) == (3072, 42):
                records.append(_record(b, s, [7.0] * 6,
                                       backings=["mixed"] * 5 + ["base"],
                                       refill_per_1k=235.0))
            elif not thp_all_base and (b, s) == (2304, 7):
                records.append(_record(b, s, [7.2] * 6,
                                       backings=["mixed"] + ["base"] * 5,
                                       refill_per_1k=240.0))
            else:
                records.append(_record(b, s, [8.0] * 6, refill_per_1k=1300.0))
    _write_run(root / tlb_figures.RUN_THP_MADVISE, records)


def _run_cli(root: Path, out: Path):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = tlb_figures.main(["--runs-root", str(root), "--out", str(out)])
    return rc, stdout.getvalue(), stderr.getvalue()


class TestCli(unittest.TestCase):
    def test_end_to_end_synthetic(self):
        with tempfile.TemporaryDirectory() as d:
            root, out = Path(d) / "runs", Path(d) / "out"
            _make_dataset(root)
            rc, _, _ = _run_cli(root, out)
            self.assertEqual(rc, 0)
            names = ["refill-density.svg", "walk-onset.svg",
                     "latency-cycles.svg", "thp-cohort.svg"]
            for name in names:
                ET.fromstring((out / name).read_text(encoding="utf-8"))
            # 曲线点数钉：图 1/2 = 13+8-1（4096 重合合并）= 20；图 3 两系
            # 列 40；图 4 = base 2 点 + mixed 1 点（仅 3072 比较级）= 3
            counts = {name: (out / name).read_text(encoding="utf-8").count("<circle")
                      for name in names}
            self.assertEqual(counts, {"refill-density.svg": 20, "walk-onset.svg": 20,
                                      "latency-cycles.svg": 40, "thp-cohort.svg": 3})
            # 图 2 的 shaded/vlines 元素在
            walk_svg = (out / "walk-onset.svg").read_text(encoding="utf-8")
            self.assertIn("fill-opacity", walk_svg)
            self.assertIn("stroke-dasharray", walk_svg)
            self.assertIn("MMUTC 2048 项", walk_svg)
            md = (out / "report.md").read_text(encoding="utf-8")
            for needle in ("refill-density.svg", "walk-onset.svg", "latency-cycles.svg",
                           "thp-cohort.svg", "终态", "没测到什么", "复算",
                           "INSUFFICIENT_COHORT", "INTERVAL_IDENTIFIED",
                           "MODEL_UNIDENTIFIABLE", "analysis/sm8650_tlb.py"):
                self.assertIn(needle, md, f"report.md 缺少 {needle}")
            # 幂等：同输入必同输出
            out2 = Path(d) / "out2"
            rc, _, _ = _run_cli(root, out2)
            self.assertEqual(rc, 0)
            for name in names + ["report.md"]:
                self.assertEqual((out / name).read_bytes(), (out2 / name).read_bytes())

    def test_missing_run_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "runs"
            _make_dataset(root)
            shutil.rmtree(root / tlb_figures.RUN_DENSE)
            rc, _, err = _run_cli(root, Path(d) / "out")
            self.assertEqual(rc, 1)
            self.assertIn(tlb_figures.RUN_DENSE, err)

    def test_missing_metric_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "runs"
            _make_dataset(root, drop_one_metric=True)
            rc, _, err = _run_cli(root, Path(d) / "out")
            self.assertEqual(rc, 1)
            self.assertIn(tlb_figures.RUN_COARSE, err)

    def test_grid_gap_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "runs"
            _make_dataset(root, skip_one_record=True)
            rc, _, err = _run_cli(root, Path(d) / "out")
            self.assertEqual(rc, 1)
            self.assertIn(tlb_figures.RUN_COARSE, err)

    def test_no_comparative_mixed_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "runs"
            _make_dataset(root, thp_all_base=True)
            rc, _, err = _run_cli(root, Path(d) / "out")
            self.assertEqual(rc, 1)
            self.assertIn("mixed", err)


class TestRealDatasetShape(unittest.TestCase):
    """钉死数据集的真实形状（读仓内 data/public/runs；数据修正走 revision
    history 时本类随数据集一起更新——参照系自动跟踪，不钉具体浮点值）。"""

    def test_merged_curve_and_cohort_shape(self):
        scan_groups, thp_groups = tlb_figures.load_campaign(_RUNS_ROOT)
        refill = tlb_figures.curve_from_groups(scan_groups, "l1d_tlb_refill_per_1k")
        self.assertEqual(len(refill), 20)  # 13 粗扫 + 8 致密 − 4096 重合
        self.assertEqual([b for b, _ in refill][:4], [128, 192, 256, 384])
        graded = grade_thp_cohorts(thp_groups)
        series = tlb_figures.cohort_series(graded)
        self.assertEqual([b for b, _ in series["base"]], [2304.0, 3072.0])
        self.assertEqual([b for b, _ in series["mixed"]], [3072.0])
        # 终审 Q4：3072 mixed(seed42) vs base 的 R_0x05 ≈ -82%（方向钉）
        base3072 = dict(series["base"])[3072.0]
        mixed3072 = dict(series["mixed"])[3072.0]
        self.assertLess(mixed3072, base3072 * 0.25)

    def test_cli_against_repo_dataset(self):
        with tempfile.TemporaryDirectory() as d:
            rc, _, err = _run_cli(_RUNS_ROOT, Path(d) / "out")
            self.assertEqual(rc, 0, err)
            counts = {name: (Path(d) / "out" / name).read_text(encoding="utf-8").count("<circle")
                      for name in ("refill-density.svg", "walk-onset.svg",
                                   "latency-cycles.svg", "thp-cohort.svg")}
            self.assertEqual(counts, {"refill-density.svg": 20, "walk-onset.svg": 20,
                                      "latency-cycles.svg": 40, "thp-cohort.svg": 3})


if __name__ == "__main__":
    unittest.main()
