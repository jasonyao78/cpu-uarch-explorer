# SPDX-License-Identifier: Apache-2.0
"""SM8650 X4 TLB Phase B 致密点生成器测试（任务书 v4.1 §6.2.4a/4b、§6.2.7、§6.2.8）。

钉住计划 Task 7 的七个验收向量与边界解析：

1. 4a：候选 [128,192] → 插入 144,160,176 + 64（去重升序，向下取整）；
2. 4b：onset (2048,4096) 独立生成（Q1 无候选时仍产出）；
3. §6.2.8-7：Q1 无候选 + Q2a 有 onset → 仅 4b 输出；两路皆无 → 不生成；
4. §6.2.8-4：并列候选按 p_i 升序取前 3；
5. §6.2.4a：候选区间 >3 时按 R_0x05 相对增量裁剪；
6. 输出配置含 generator.{input_run_sha256, rules_sha256, output_sha256}
   三字段，且 output_sha256 可复算（去掉 generator 块的规范化 JSON）；
7. §6.2.8-3：跨区间/跨路径重合插入点按页数去重，但各占来源区间额度；
   §6.2.8-2：区间内与既有页点重合的插入点丢弃且不计额。

另含形状合同：生成配置可被 runner.plan.build_plan 直接消费（真实
redmi-k70pro-01 平台），以及确定性（同输入同输出）与输入契约校验。
全部用合成输入，不依赖真实 run。
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from analysis.tlb_dense_gen import (
    DenseGenError,
    _rules_block_sha256,
    emit_dense_config,
)
from runner.plan import build_plan

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PLATFORM = json.loads(
    (_REPO_ROOT / "configs" / "platforms" / "redmi-k70pro-01.json").read_text(
        encoding="utf-8"
    )
)
_TASK_BOOK = _REPO_ROOT / "docs" / "tasks" / "2026-09-28-sm8650-tlb-hierarchy.md"

_INPUT_SHA = "ab" * 32
_RULES_SHA = "cd" * 32
_G0_NAMES = {"cycles", "mem_access_rd", "l1d_tlb_refill", "dtlb_walk"}
_SEEDS = [42, 7, 1337, 20260928]


def _interval(left, right, ratio):
    return {"left": left, "right": right, "refill_ratio": ratio}


def _coarse_result(knee=(), onset=()):
    return {
        "input_run_sha256": _INPUT_SHA,
        "knee": {"intervals": list(knee)},
        "onset": {"intervals": list(onset)},
    }


def _emit(result, **kwargs):
    kwargs.setdefault("rules_sha256", _RULES_SHA)
    return emit_dense_config(result, "v4.1-test", **kwargs)


def _pages(config):
    return [point["pages"] for point in config["generator"]["dense_points"]]


def _quota(config):
    return config["generator"]["quota"]


class TestKneePathInsertions(unittest.TestCase):
    """§6.2.4a：四分位点 + p_i/2 插入（验收向量 ①与向下取整/半点半径边界）。"""

    def test_interval_128_192_inserts_quartiles_and_half(self):
        # 验收向量①：候选 [128,192] → 144,160,176 + 64（去重升序）
        config = _emit(_coarse_result(knee=[_interval(128, 192, 2.5)]))
        self.assertEqual(_pages(config), [64, 144, 160, 176])
        self.assertEqual(
            config["execution"]["sweep"]["buffer"],
            ["256KiB", "576KiB", "640KiB", "704KiB"],
        )
        for point in config["generator"]["dense_points"]:
            self.assertEqual(
                point["sources"],
                [{"path": "knee", "interval_pages": [128, 192]}],
            )
        quota = _quota(config)
        self.assertEqual(quota["per_interval"][0]["inserted_pages"],
                         [64, 144, 160, 176])
        self.assertEqual(quota["per_interval"][0]["quota_points"], 4)
        self.assertEqual(quota["point_quota_total"], 4)
        self.assertEqual(quota["quota_cases"], 16)
        self.assertEqual(quota["main_cases"], 16)

    def test_non_integer_quartiles_floor(self):
        # §6.2.8-2 前半句：非整数页一律向下取整（合成区间 [33,100]，
        # Δ=67 → 49.75/66.5/83.25 → 49/66/83；p_i/2=16 < 32 不插入）
        config = _emit(_coarse_result(knee=[_interval(33, 100, 2.0)]))
        self.assertEqual(_pages(config), [49, 66, 83])

    def test_half_point_requires_p_i_half_at_least_32(self):
        # §6.2.4a：p_i/2 ≥ 32 才插入——[32,64] 的 p_i/2=16 不插入
        config = _emit(_coarse_result(knee=[_interval(32, 64, 2.5)]))
        self.assertEqual(_pages(config), [40, 48, 56])

    def test_within_interval_coincidence_dropped_without_quota(self):
        # §6.2.8-2：取整后与本区间既有页点（端点或已插入点）重合 → 丢弃
        # 且不计入额度。合成区间 [128,130]（Δ=2）：q1=128（=p_i，丢弃）、
        # q2=129、q3=129（与 q2 重合，丢弃）、half=64 插入。
        config = _emit(_coarse_result(knee=[_interval(128, 130, 2.0)]))
        self.assertEqual(_pages(config), [64, 129])
        entry = _quota(config)["per_interval"][0]
        self.assertEqual(entry["inserted_pages"], [64, 129])
        self.assertEqual(entry["dropped_pages"], [128, 129])
        self.assertEqual(entry["quota_points"], 2)
        self.assertEqual(_quota(config)["point_quota_total"], 2)


class TestOnsetPathIndependent(unittest.TestCase):
    """§6.2.4b/§6.2.8-7：onset 路径独立生成（验收向量②③）。"""

    def test_onset_interval_generates_same_insertion_rule(self):
        # 验收向量②：onset (2048,4096) → Δ=2048 → 四分位 2560/3072/3584
        # + p_i/2=1024；KiB 整除 1024 时用 MiB（粗扫配置同款约定：
        # 2048→"2MiB"、3072→"3MiB"，1536 非整数 MiB 才留 KiB）——
        # 10240/14336 KiB 恰为 10/14 MiB
        config = _emit(_coarse_result(onset=[_interval(2048, 4096, 1.0)]))
        self.assertEqual(_pages(config), [1024, 2560, 3072, 3584])
        self.assertEqual(
            config["execution"]["sweep"]["buffer"],
            ["4MiB", "10MiB", "12MiB", "14MiB"],
        )
        for point in config["generator"]["dense_points"]:
            self.assertEqual(
                point["sources"],
                [{"path": "onset", "interval_pages": [2048, 4096]}],
            )

    def test_no_knee_with_onset_emits_only_onset_points(self):
        # 验收向量③：Q1 无候选 + Q2a 有 onset → 仅 4b 输出（无 knee 标注）
        config = _emit(_coarse_result(onset=[_interval(256, 384, 1.2)]))
        self.assertEqual(_pages(config), [128, 288, 320, 352])
        self.assertEqual(
            {source["path"]
             for point in config["generator"]["dense_points"]
             for source in point["sources"]},
            {"onset"},
        )
        self.assertEqual(
            {entry["path"] for entry in _quota(config)["per_interval"]},
            {"onset"},
        )

    def test_both_paths_empty_is_not_generated(self):
        # §6.2.8-7：皆无 → 不生成（Phase B 配置不得存在）
        with self.assertRaises(DenseGenError):
            _emit(_coarse_result())

    def test_interval_with_no_surviving_points_is_error(self):
        # fail-closed：合成小区间 [32,33]（Δ=1 → 四分位取整后全部重合
        # 端点按 §6.2.8-2 丢弃；p_i/2=16 < 32 不插入）→ 致密点集合为空，
        # 不产出零 case 配置
        with self.assertRaises(DenseGenError):
            _emit(_coarse_result(knee=[_interval(32, 33, 2.0)]))


class TestIntervalClipping(unittest.TestCase):
    """§6.2.4a >3 裁剪与 §6.2.8-4 并列解析（验收向量④⑤）+ §6.2.7 预算级联。"""

    def test_tied_candidates_clip_by_left_endpoint_ascending(self):
        # 验收向量④：四个相对增量并列的候选，按 p_i 升序取前 3
        config = _emit(_coarse_result(knee=[
            _interval(512, 768, 2.0),
            _interval(64, 96, 2.0),
            _interval(256, 384, 2.0),
            _interval(128, 192, 2.0),
        ]))
        self.assertEqual(
            _pages(config),
            [32, 64, 72, 80, 88, 128, 144, 160, 176, 288, 320, 352],
        )
        clipped = _quota(config)["clipped_intervals"]
        self.assertEqual(len(clipped), 1)
        self.assertEqual(clipped[0]["path"], "knee")
        self.assertEqual(clipped[0]["interval_pages"], [512, 768])
        self.assertIn("§6.2.4a", clipped[0]["reason"])

    def test_more_than_three_intervals_clip_by_relative_delta(self):
        # 验收向量⑤：>3 区间按 R_0x05 相对增量降序保留前 3
        config = _emit(_coarse_result(knee=[
            _interval(128, 192, 2.0),
            _interval(256, 384, 3.0),
            _interval(512, 768, 2.5),
            _interval(1024, 2048, 4.0),
        ]))
        self.assertEqual(
            _pages(config),
            [128, 256, 288, 320, 352, 512, 576, 640, 704, 1280, 1536, 1792],
        )
        clipped = _quota(config)["clipped_intervals"]
        self.assertEqual([entry["interval_pages"] for entry in clipped],
                         [[128, 192]])
        kept = {(entry["path"], tuple(entry["interval_pages"]))
                for entry in _quota(config)["per_interval"]}
        self.assertEqual(kept, {("knee", (256, 384)), ("knee", (512, 768)),
                                ("knee", (1024, 2048))})

    def test_budget_cascade_drops_smallest_delta_interval(self):
        # §6.2.7：主体 ≤50 case（额度口径 = 插入点×来源区间×seed）。
        # 3 knee 区间 + 1 onset 区间 = 16 额定点 → 64 > 50 → 级联①裁掉
        # 相对增量最小的区间（onset，1.0）→ 48 ≤ 50。
        config = _emit(_coarse_result(
            knee=[_interval(128, 192, 4.0), _interval(256, 384, 3.0),
                  _interval(512, 768, 2.5)],
            onset=[_interval(2048, 4096, 1.0)],
        ))
        self.assertEqual(
            _pages(config),
            [64, 128, 144, 160, 176, 256, 288, 320, 352, 576, 640, 704],
        )
        clipped = _quota(config)["clipped_intervals"]
        self.assertEqual(len(clipped), 1)
        self.assertEqual(clipped[0]["path"], "onset")
        self.assertEqual(clipped[0]["interval_pages"], [2048, 4096])
        self.assertIn("§6.2.7", clipped[0]["reason"])
        quota = _quota(config)
        self.assertEqual(quota["quota_cases"], 48)
        self.assertEqual(quota["main_cases"], 48)
        self.assertLessEqual(quota["quota_cases"], quota["budget_main_cases"])


class TestGeneratorHashes(unittest.TestCase):
    """验收向量⑥：generator 三 SHA-256 字段 + 确定性。"""

    def test_generator_block_carries_three_hashes(self):
        config = _emit(_coarse_result(knee=[_interval(128, 192, 2.5)]))
        generator = config["generator"]
        for key in ("input_run_sha256", "rules_sha256", "output_sha256"):
            self.assertIn(key, generator)
        self.assertEqual(generator["input_run_sha256"], _INPUT_SHA)
        self.assertEqual(generator["rules_sha256"], _RULES_SHA)
        self.assertEqual(generator["rules_version"], "v4.1-test")
        # output_sha256 = 去掉 generator 块的规范化 JSON 的 SHA-256（可复算）
        payload = {key: value for key, value in config.items()
                   if key != "generator"}
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")
        self.assertEqual(generator["output_sha256"],
                         hashlib.sha256(canonical).hexdigest())

    def test_deterministic_replay(self):
        result = _coarse_result(
            knee=[_interval(128, 192, 2.5), _interval(512, 768, 3.0)],
            onset=[_interval(2048, 4096, 1.0)],
        )
        first = _emit(result)
        second = _emit(result)
        self.assertEqual(json.dumps(first, sort_keys=True, ensure_ascii=False),
                         json.dumps(second, sort_keys=True, ensure_ascii=False))
        self.assertEqual(first["generator"]["output_sha256"],
                         second["generator"]["output_sha256"])

    def test_rules_sha256_from_file_block(self):
        # _rules_block_sha256：### 6.2 起至 ### 6.3 前的文本块
        block = "### 6.2 analysis_rules v1（预注册冻结规则）\nline-1\nline-2\n"
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / "task-book.md"
            rules.write_text("# head\n\n" + block + "### 6.3 统计与数据分层\n",
                             encoding="utf-8")
            expected = hashlib.sha256(block.encode("utf-8")).hexdigest()
            self.assertEqual(_rules_block_sha256(rules), expected)
            config = emit_dense_config(
                _coarse_result(knee=[_interval(128, 192, 2.5)]),
                "v4.1-test",
                rules_path=rules,
            )
            self.assertEqual(config["generator"]["rules_sha256"], expected)

    def test_rules_block_markers_missing_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / "task-book.md"
            rules.write_text("### 6.1 固定探针协议\nno 6.2 block\n",
                             encoding="utf-8")
            with self.assertRaises(DenseGenError):
                _rules_block_sha256(rules)

    def test_rules_block_of_real_task_book(self):
        # 真实任务书可提取（不钉死哈希值——文件演进走版本号；只钉边界形态）
        digest = _rules_block_sha256(_TASK_BOOK)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(digest, _rules_block_sha256(_TASK_BOOK))
        text = _TASK_BOOK.read_text(encoding="utf-8")
        begin = text.index("### 6.2")
        end = text.index("### 6.3", begin)
        block = text[begin:end]
        self.assertIn("6.2.4a", block)
        self.assertIn("6.2.8", block)
        self.assertNotIn("### 6.3", block)


class TestCrossIntervalCoincidence(unittest.TestCase):
    """验收向量⑦：§6.2.8-3 跨区间重合去重但各占来源区间额度。"""

    def test_same_interval_from_both_paths_merges_points_not_quota(self):
        config = _emit(_coarse_result(
            knee=[_interval(128, 192, 2.5)],
            onset=[_interval(128, 192, 1.0)],
        ))
        # 输出按页数去重：4 个点，各带 knee+onset 双来源标注（排序固定）
        self.assertEqual(_pages(config), [64, 144, 160, 176])
        for point in config["generator"]["dense_points"]:
            self.assertEqual(
                point["sources"],
                [{"path": "knee", "interval_pages": [128, 192]},
                 {"path": "onset", "interval_pages": [128, 192]}],
            )
        quota = _quota(config)
        # 重合点仍各占其来源区间的额度计数（防止合并后隐性超支）：
        # 两区间各 4 点 → 额定点合计 8（预算口径 8×4=32 case），
        # 去重后实际 runner case = 4×4=16
        self.assertEqual(len(quota["per_interval"]), 2)
        self.assertEqual([entry["quota_points"]
                          for entry in quota["per_interval"]], [4, 4])
        self.assertEqual(quota["point_quota_total"], 8)
        self.assertEqual(quota["quota_cases"], 32)
        self.assertEqual(quota["main_cases"], 16)

    def test_partial_cross_interval_coincidence(self):
        # knee [128,192] 插入 64,144,160,176；onset [96,160]（Δ=64 →
        # 112,128,144 + 48）在 144 上重合：输出 7 个点，144 双来源；
        # 额度两区间各 4 点
        config = _emit(_coarse_result(
            knee=[_interval(128, 192, 2.5)],
            onset=[_interval(96, 160, 1.0)],
        ))
        self.assertEqual(_pages(config), [48, 64, 112, 128, 144, 160, 176])
        coincident = [point for point in config["generator"]["dense_points"]
                      if point["pages"] == 144][0]
        self.assertEqual([source["path"] for source in coincident["sources"]],
                         ["knee", "onset"])
        quota = _quota(config)
        self.assertEqual(quota["point_quota_total"], 8)
        self.assertEqual(quota["quota_cases"], 32)
        self.assertEqual(quota["main_cases"], 28)


class TestShapeContract(unittest.TestCase):
    """形状合同：生成配置可被 runner.plan.build_plan 直接消费（真实平台）。"""

    def test_build_plan_consumes_emitted_config(self):
        config = _emit(_coarse_result(knee=[_interval(128, 192, 2.5)]))
        # 序列化往返不丢结构（输出即可写 ptr-chase-sm8650-x4-tlb-dense.json）
        config = json.loads(json.dumps(config, ensure_ascii=False))
        plan = build_plan(config, _PLATFORM)
        self.assertEqual(plan.experiment_id, "ptr-chase-sm8650-x4-tlb-dense")
        self.assertEqual(plan.protocol_version, "1.2")
        self.assertEqual(len(plan.cases), 16)  # 4 致密点 × 4 seed
        self.assertTrue(all(case.repetitions == 10 for case in plan.cases))
        self.assertTrue(all(case.control.id == "x4-prime" for case in plan.cases))
        # sweep 展开顺序：buffer 外循环 × seed 内循环（sweep 键名排序）
        self.assertEqual(
            [case.param_value("buffer_kb") for case in plan.cases],
            [buffer for buffer in (256, 576, 640, 704) for _ in _SEEDS],
        )
        self.assertEqual(
            [case.param_value("seed") for case in plan.cases[:4]], _SEEDS)
        for case in plan.cases:
            slots = case.param_value("buffer_kb") * 1024 // case.param_value("stride")
            self.assertEqual(case.param_value("loads"), 8 * slots)
            self.assertEqual(case.param_value("warmup"), 2 * slots)
            self.assertEqual(case.param_value("warmup_passes"), 2)
            self.assertEqual(case.param_value("base_pages"), 1)
            self.assertEqual(
                {event["name"] for event in case.param_value("pmu_events")},
                _G0_NAMES,
            )


class TestInputContract(unittest.TestCase):
    """输入契约缺项一律 DenseGenError（fail-closed，不接受大概齐全）。"""

    def test_invalid_input_run_sha256(self):
        for bad in ("xyz", "AB" * 32, 123, None):
            with self.subTest(bad=bad):
                result = _coarse_result(knee=[_interval(128, 192, 2.5)])
                result["input_run_sha256"] = bad
                with self.assertRaises(DenseGenError):
                    _emit(result)

    def test_invalid_intervals(self):
        bad_intervals = (
            _interval(192, 128, 2.0),    # left >= right
            _interval(0, 128, 2.0),      # left < 1
            _interval(128, 192, 0),      # 非正相对增量
            _interval(128, 192, -1.0),
            _interval(128, 192, float("inf")),
            {"left": 128, "right": 192},  # 缺 refill_ratio
            {"left": 128.0, "right": 192, "refill_ratio": 2.0},
            [128, 192],                   # 非对象
        )
        for bad in bad_intervals:
            with self.subTest(bad=bad):
                with self.assertRaises(DenseGenError):
                    _emit(_coarse_result(knee=[bad]))

    def test_duplicate_interval_rejected(self):
        with self.assertRaises(DenseGenError):
            _emit(_coarse_result(knee=[_interval(128, 192, 2.0),
                                       _interval(128, 192, 3.0)]))

    def test_rules_sha256_and_path_mutually_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / "task-book.md"
            rules.write_text("### 6.2 x\n### 6.3 y\n", encoding="utf-8")
            with self.assertRaises(DenseGenError):
                emit_dense_config(
                    _coarse_result(knee=[_interval(128, 192, 2.5)]),
                    "v4.1-test",
                    rules_sha256=_RULES_SHA,
                    rules_path=rules,
                )

    def test_invalid_rules_sha256(self):
        with self.assertRaises(DenseGenError):
            emit_dense_config(
                _coarse_result(knee=[_interval(128, 192, 2.5)]),
                "v4.1-test",
                rules_sha256="not-a-sha",
            )

    def test_empty_rules_version_rejected(self):
        for bad in ("", 123):
            with self.subTest(bad=bad):
                with self.assertRaises(DenseGenError):
                    emit_dense_config(
                        _coarse_result(knee=[_interval(128, 192, 2.5)]),
                        bad,
                        rules_sha256=_RULES_SHA,
                    )


if __name__ == "__main__":
    unittest.main()
