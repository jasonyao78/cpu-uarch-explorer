# SPDX-License-Identifier: Apache-2.0
"""Plan 契约：确定性展开、repetitions 真实消费、参数溯源。"""

import json
import unittest
from pathlib import Path

from runner.errors import RunnerError
from runner.plan import build_plan

ROOT = Path(__file__).resolve().parents[2]

SPEC = {
    "schema_version": "1.0",
    "id": "exp",
    "protocol_version": "1.0",
    "harness": "portable",
    "metrics": [{"name": "latency_ns", "unit": "ns"}],
    "parameters": [
        {"name": "stride", "type": "size", "default": "64B"},
        {"name": "warmup", "type": "int", "default": 1000},
        {"name": "repetitions", "type": "int", "default": 3},
    ],
    "execution": {
        "probe": "ptr_chase",
        "sweep": {"buffer": ["64KiB", "64MiB"]},
        "fixed_params": ["stride", "warmup"],
    },
}

PASS_SPEC = {
    **SPEC,
    "protocol_version": "1.1",
    "parameters": [
        {"name": "stride", "type": "size", "default": "64B"},
        {"name": "warmup_passes", "type": "int", "default": 2},
        {"name": "repetitions", "type": "int", "default": 3},
    ],
    "execution": {
        **SPEC["execution"],
        "sweep": {"buffer": ["4MiB", "12MiB", "32MiB"]},
        "fixed_params": ["stride", "warmup_passes"],
    },
}

PLATFORM = {
    "target": {"os": "darwin", "isa": "aarch64", "execution_kind": "native",
               "executor": "native", "target_id": "t-01"},
    "probes": {"ptr_chase": "build/macos-arm64/release/probes/cache-mem/ptr_chase"},
    "controls": [
        {"id": "c0", "control": {"mechanism": "qos", "value": "default"}, "command_prefix": []},
        {"id": "c1", "control": {"mechanism": "qos", "value": "background"},
         "command_prefix": ["/usr/sbin/taskpolicy", "-b"]},
    ],
}


class TestPlan(unittest.TestCase):
    def test_case_expansion_controls_x_sweep(self):
        plan = build_plan(SPEC, PLATFORM)
        self.assertEqual(len(plan.cases), 4)  # 2 controls × 2 buffers
        self.assertEqual(len({c.id for c in plan.cases}), 4)  # 确定性唯一 id

    def test_experiment_can_select_named_platform_controls(self):
        selected = {
            **SPEC,
            "execution": {**SPEC["execution"], "controls": ["c1"]},
        }
        plan = build_plan(selected, PLATFORM)
        self.assertEqual(len(plan.cases), 2)
        self.assertEqual({case.control.id for case in plan.cases}, {"c1"})

    def test_unknown_or_empty_control_selection_fails_at_plan_time(self):
        for selection in ([], ["missing"], ["c0", "c0"], "c0"):
            with self.subTest(selection=selection):
                selected = {
                    **SPEC,
                    "execution": {**SPEC["execution"], "controls": selection},
                }
                with self.assertRaisesRegex(RunnerError, "execution.controls"):
                    build_plan(selected, PLATFORM)

    def test_repetitions_actually_consumed(self):
        # GB10 教训：samples=7 声明了却从不执行。这里 repetitions 必须落到每个 case。
        plan = build_plan(SPEC, PLATFORM)
        self.assertTrue(all(c.repetitions == 3 for c in plan.cases))
        cli = dict(SPEC["parameters"][2])  # noqa: F841 - 文档性注释
        plan5 = build_plan(SPEC, PLATFORM, cli_overrides={"repetitions": 5})
        self.assertTrue(all(c.repetitions == 5 for c in plan5.cases))

    def test_mib_unit_not_silently_downgraded(self):
        plan = build_plan(SPEC, PLATFORM)
        by_control = [c for c in plan.cases if c.control.id == "c0"]
        sizes = sorted(c.param_value("buffer_kb") for c in by_control)
        self.assertEqual(sizes, [64, 65536])  # 64MiB = 65536KB，不是 1024

    def test_param_provenance_recorded(self):
        plan = build_plan(SPEC, PLATFORM)
        case = plan.cases[0]
        prov = dict(case.params)
        self.assertEqual(prov["buffer_kb"].source, "experiment-sweep")
        self.assertEqual(prov["stride"].source, "spec-default")
        self.assertEqual(prov["loads"].source, "derived")

    def test_unknown_unit_fails_at_plan_time(self):
        bad = {**SPEC, "execution": {**SPEC["execution"], "sweep": {"buffer": ["64M"]}}}
        with self.assertRaises(RunnerError):
            build_plan(bad, PLATFORM)

    def test_missing_param_fails_loudly(self):
        bad = {**SPEC, "parameters": [p for p in SPEC["parameters"] if p["name"] != "stride"]}
        with self.assertRaises(RunnerError):
            build_plan(bad, PLATFORM)

    def test_loads_derivation(self):
        plan = build_plan(SPEC, PLATFORM)
        small = [c for c in plan.cases if c.param_value("buffer_kb") == 64][0]
        # 64KiB/64B = 1024 slots × 8 = 8192 < min_loads 4194304 → 取 min_loads，8 对齐
        self.assertEqual(small.param_value("loads"), 4194304)
        self.assertEqual(small.param_value("loads") % 8, 0)

    def test_warmup_passes_derive_complete_ring_traversals(self):
        plan = build_plan(PASS_SPEC, {**PLATFORM, "controls": []})
        by_buffer = {case.param_value("buffer_kb"): case for case in plan.cases}

        self.assertEqual(by_buffer[4096].param_value("warmup"), 2 * 4096 * 1024 // 64)
        self.assertEqual(by_buffer[12288].param_value("warmup"), 2 * 12288 * 1024 // 64)
        self.assertEqual(by_buffer[32768].param_value("warmup"), 2 * 32768 * 1024 // 64)
        self.assertEqual(by_buffer[4096].param_value("warmup_passes"), 2)
        self.assertEqual(dict(by_buffer[4096].params)["warmup"].source, "derived")
        self.assertEqual(
            dict(by_buffer[4096].params)["warmup_passes"].source,
            "spec-default",
        )

    def test_negative_warmup_passes_rejected(self):
        with self.assertRaisesRegex(RunnerError, "warmup_passes must be >= 1"):
            build_plan(PASS_SPEC, PLATFORM, cli_overrides={"warmup_passes": -1})

    def test_new_and_legacy_warmup_conflict_rejected(self):
        conflict = {
            **PASS_SPEC,
            "parameters": [
                *PASS_SPEC["parameters"],
                {"name": "warmup", "type": "int", "default": 1000},
            ],
            "execution": {
                **PASS_SPEC["execution"],
                "fixed_params": ["stride", "warmup", "warmup_passes"],
            },
        }
        with self.assertRaisesRegex(RunnerError, "cannot declare both"):
            build_plan(conflict, PLATFORM)

    def test_derived_warmup_signed_64_bit_overflow_rejected(self):
        overflow = {
            **PASS_SPEC,
            "execution": {
                **PASS_SPEC["execution"],
                "sweep": {"buffer": ["576460752303423488KiB"]},
            },
        }
        with self.assertRaisesRegex(RunnerError, "warmup loads exceed"):
            build_plan(overflow, PLATFORM)

    def test_legacy_exact_warmup_is_preserved(self):
        plan = build_plan(SPEC, {**PLATFORM, "controls": []})
        case = plan.cases[0]
        self.assertEqual(case.param_value("warmup"), 1000)
        self.assertEqual(dict(case.params)["warmup"].source, "spec-default")
        self.assertNotIn("warmup_passes", dict(case.params))

    def test_seed_sweep_expands_as_cross_product(self):
        spec = {
            **PASS_SPEC,
            "parameters": [
                *PASS_SPEC["parameters"],
                {"name": "seed", "type": "int", "default": 42},
            ],
            "execution": {
                **PASS_SPEC["execution"],
                "sweep": {
                    "buffer": ["4MiB", "12MiB", "32MiB"],
                    "seed": [42, 7, 1337, 20260928],
                },
            },
        }
        plan = build_plan(spec, {**PLATFORM, "controls": []})
        self.assertEqual(len(plan.cases), 12)
        self.assertEqual(
            {case.param_value("seed") for case in plan.cases},
            {42, 7, 1337, 20260928},
        )

    def test_swept_uncovered_param_enters_case_id(self):
        # 通用 id 段：模板（buffer/stride/seed/页策略旗标）未覆盖的 swept 参数
        # 按 sweep 名排序追加 -{name}{value}（overhead 触发：sweep loads_per_slot
        # 时 24 case 仅 8 唯一 id，raw 样本按 id 命名会互相覆盖）；未 sweep 时
        # 不得追加——由 tlb-ctrl id 稳定性钉反向保证
        spec = {
            **PASS_SPEC,
            "parameters": [
                *PASS_SPEC["parameters"],
                {"name": "loads_per_slot", "type": "int", "default": 8},
            ],
            "execution": {
                **PASS_SPEC["execution"],
                "sweep": {"buffer": ["4MiB"], "loads_per_slot": [8, 64]},
            },
        }
        plan = build_plan(spec, {**PLATFORM, "controls": []})
        self.assertEqual(
            [case.id for case in plan.cases],
            ["exp:uncontrolled:b4096K-s64B-loads_per_slot8",
             "exp:uncontrolled:b4096K-s64B-loads_per_slot64"],
        )

    def test_non_scalar_swept_param_in_case_id_fails_closed(self):
        # 列表/字典值字符串化进 id 会让 id 不可读且可能再引入碰撞：fail-closed
        events = [{"name": "cycles", "type": 8, "config": "0x11"}]
        spec = {
            **PASS_SPEC,
            "parameters": [
                *PASS_SPEC["parameters"],
                {"name": "pmu_events", "type": "pmu-event-list", "default": events},
            ],
            "execution": {
                **PASS_SPEC["execution"],
                "sweep": {"buffer": ["4MiB"], "pmu_events": [events]},
            },
        }
        with self.assertRaisesRegex(RunnerError, "non-scalar"):
            build_plan(spec, {**PLATFORM, "controls": []})

    def test_swept_case_id_segment_value_charset_fails_closed(self):
        # str sweep 值直接进 raw 样本文件名（artifacts 的 safe_case 只替换
        # "/"与":"，且唯一性断言作用于净化前 id）：含 "/"、空格等字符的值会
        # 绕过 plan 期防线后仍在落盘时互覆——白名单字符集 fail-closed
        spec = {
            **PASS_SPEC,
            "execution": {
                **PASS_SPEC["execution"],
                "sweep": {"buffer": ["4MiB"], "label": ["a/b"]},
            },
        }
        with self.assertRaisesRegex(RunnerError, "unsafe characters"):
            build_plan(spec, {**PLATFORM, "controls": []})

    def test_duplicate_case_ids_fail_at_plan_time(self):
        # 纵深防御：任何未来的 id 碰撞（如此处重复 sweep 值）必须炸在 plan 期，
        # 而不是 run 期由 artifacts 覆盖写静默吞掉 raw 样本
        spec = {
            **PASS_SPEC,
            "execution": {
                **PASS_SPEC["execution"],
                "sweep": {"buffer": ["512KiB", "512KiB"]},
            },
        }
        with self.assertRaisesRegex(RunnerError, "duplicate case ids"):
            build_plan(spec, {**PLATFORM, "controls": []})

    def test_current_ptr_chase_specs_use_pass_based_warmup_protocol(self):
        paths = sorted((ROOT / "configs" / "experiments").glob("ptr-chase*.json"))
        self.assertTrue(paths)
        platform = {**PLATFORM, "controls": []}

        for path in paths:
            with self.subTest(path=path.name):
                spec = json.loads(path.read_text(encoding="utf-8"))
                protocol_12_prefixes = (
                    "ptr-chase-sm8650-x4-l2-",
                    "ptr-chase-sm8650-x4-pmu-ctrl-",
                    "ptr-chase-sm8650-x4-p0prime-",
                    "ptr-chase-sm8650-x4-tlb-",
                )
                expected_protocol = (
                    "1.2" if path.name.startswith(protocol_12_prefixes) else "1.1"
                )
                self.assertEqual(spec["protocol_version"], expected_protocol)
                parameter_names = {param["name"] for param in spec["parameters"]}
                self.assertIn("warmup_passes", parameter_names)
                self.assertNotIn("warmup", parameter_names)
                self.assertIn("warmup_passes", spec["execution"]["fixed_params"])
                self.assertNotIn("warmup", spec["execution"]["fixed_params"])
                if path.name == "ptr-chase-cache-sweep-hp2m.json":
                    self.assertIn("thp", parameter_names)
                    self.assertNotIn("hugepage", parameter_names)

                case_platform = platform
                selected_controls = spec["execution"].get("controls")
                if selected_controls:
                    case_platform = {
                        **platform,
                        "controls": [
                            {
                                "id": control_id,
                                "control": {"mechanism": "taskset", "value": "7"},
                                "command_prefix": ["taskset", "80"],
                            }
                            for control_id in selected_controls
                        ],
                    }
                plan = build_plan(spec, case_platform)
                # 通用防线：任何配置的 case id 必须全唯一——raw 样本按 case id
                # 命名落盘（覆盖写），碰撞即样本互覆、manifest id 重复、SHA256
                # 锚定失效（overhead 24 case 仅 8 唯一 id 触发的修复，见
                # build_plan 通用 id 段与唯一性断言）
                self.assertEqual(
                    len({case.id for case in plan.cases}), len(plan.cases))
                # id 稳定性钉：通用 id 段不得改变既有配置的 id（sweep 集合未变
                # ⇒ id 逐字不变），下游 raw 样本/manifest 全部按 id 寻址
                if path.name == "ptr-chase-sm8650-x4-tlb-ctrl.json":
                    self.assertEqual(
                        [case.id for case in plan.cases],
                        ["ptr-chase-sm8650-x4-tlb-ctrl:x4-prime:b512K-s64B-seed42-base",
                         "ptr-chase-sm8650-x4-tlb-ctrl:x4-prime:b16384K-s64B-seed42-base"],
                    )
                expected_case_counts = {
                    "ptr-chase-sm8650-x4-l2-base.json": 14,
                    "ptr-chase-sm8650-x4-l2-thp.json": 14,
                    "ptr-chase-sm8650-x4-l2-fine.json": 21,
                    "ptr-chase-sm8650-x4-pmu-ctrl-cache.json": 5,
                    "ptr-chase-sm8650-x4-pmu-ctrl-tlb.json": 2,
                    "ptr-chase-sm8650-x4-p0prime-short-base.json": 56,
                    "ptr-chase-sm8650-x4-p0prime-long-base.json": 56,
                    "ptr-chase-sm8650-x4-p0prime-long-base-r2a.json": 16,
                    "ptr-chase-sm8650-x4-p0prime-long-base-r2b.json": 12,
                    "ptr-chase-sm8650-x4-p0prime-short-thp.json": 8,
                    "ptr-chase-sm8650-x4-p0prime-long-thp.json": 8,
                    "ptr-chase-sm8650-x4-tlb-anchor.json": 2,
                    "ptr-chase-sm8650-x4-tlb-ctrl.json": 2,
                    "ptr-chase-sm8650-x4-tlb-coarse.json": 26,
                    "ptr-chase-sm8650-x4-tlb-ctrl-g1.json": 2,
                    "ptr-chase-sm8650-x4-tlb-ctrl-g2.json": 2,
                    "ptr-chase-sm8650-x4-tlb-ctrl-g4.json": 4,
                    "ptr-chase-sm8650-x4-tlb-ctrl-g4-thp.json": 2,
                    "ptr-chase-sm8650-x4-tlb-overhead.json": 24,
                    "ptr-chase-sm8650-x4-tlb-thp-base.json": 12,
                    "ptr-chase-sm8650-x4-tlb-thp-madvise.json": 12,
                }
                if path.name in expected_case_counts:
                    self.assertEqual(len(plan.cases), expected_case_counts[path.name])
                    self.assertTrue(all(case.repetitions == 10 for case in plan.cases))
                # §9.3⑮/§6.2.5：锚点/正控/粗扫的 case 参数与执行顺序也要钉死，不只是 case 数。
                # 事件钉 (name, type, config) 三元组而非只钉名（规范评审实证：name 集合钉
                # 对 "0x2d"→"0x2c" 篡改无感——plan/adapter 只做结构校验，name↔config
                # 错配必须有自动化兜底层）；期望值写归一化后的 int 形态（0x2d==45），
                # 与 case.param_value("pmu_events") 返回形态对齐
                g0_events = {("cycles", 8, 0x11), ("mem_access_rd", 8, 0x66),
                             ("l1d_tlb_refill", 8, 0x05), ("dtlb_walk", 8, 0x34)}
                tlb_expectations = {
                    "ptr-chase-sm8650-x4-tlb-anchor.json": {
                        "buffers": [512, 3072],
                        "seeds": {42},
                    },
                    "ptr-chase-sm8650-x4-tlb-ctrl.json": {
                        "buffers": [512, 16384],
                        "seeds": {42},
                    },
                    "ptr-chase-sm8650-x4-tlb-coarse.json": {
                        "buffers": None,  # 26 case 只钉集合，顺序由 sweep 笛卡尔积决定
                        "buffer_set": {128, 256, 384, 512, 768, 1024, 1536, 2048,
                                       3072, 4096, 8192, 16384, 32768},
                        "seeds": {42, 7},
                    },
                    # Gate 1 正控（§5.1 ①②③ / §5.2 事件组）：各组事件三元组按 §3.1 表钉死
                    "ptr-chase-sm8650-x4-tlb-ctrl-g1.json": {
                        "buffers": [512, 16384],
                        "seeds": {42},
                        "events": g0_events | {("l2d_tlb_refill", 8, 0x2d),
                                               ("l2d_tlb", 8, 0x2f)},
                    },
                    "ptr-chase-sm8650-x4-tlb-ctrl-g2.json": {
                        "buffers": [512, 16384],
                        "seeds": {42},
                        # §5.2 G2 行原文：cycles+0x05+0x34+0x8136+0x8128，不含 mem_access_rd
                        "events": {("cycles", 8, 0x11), ("l1d_tlb_refill", 8, 0x05),
                                   ("dtlb_walk", 8, 0x34), ("dtlb_step", 8, 0x8136),
                                   ("dtlb_walk_percyc", 8, 0x8128)},
                    },
                    "ptr-chase-sm8650-x4-tlb-ctrl-g4.json": {
                        "buffers": [512, 16384, 2304, 3072],
                        "seeds": {42},
                        "events": {("cycles", 8, 0x11), ("l1d_tlb_refill", 8, 0x05),
                                   ("dtlb_walk", 8, 0x34),
                                   ("dtlb_walk_large", 8, 0x8138),
                                   ("dtlb_walk_small", 8, 0x813a)},
                    },
                    "ptr-chase-sm8650-x4-tlb-ctrl-g4-thp.json": {
                        "buffers": [2304, 3072],
                        "seeds": {42},
                        "events": {("cycles", 8, 0x11), ("l1d_tlb_refill", 8, 0x05),
                                   ("dtlb_walk", 8, 0x34),
                                   ("dtlb_walk_large", 8, 0x8138),
                                   ("dtlb_walk_small", 8, 0x813a)},
                        "page_policy": "thp",
                    },
                    # §5.3 固定开销扫描：两点 × 三长度 × 4 order_seed 全叉积
                    "ptr-chase-sm8650-x4-tlb-overhead.json": {
                        "buffers": [512] * 12 + [16384] * 12,
                        "buffer_set": {512, 16384},
                        "seeds": {42, 7, 1337, 20260928},
                        "loads_per_slot_sweep": [8, 64, 256],
                    },
                    # §7 Phase D THP cohort：-B/-T 同选点同 seed，G0 事件组
                    "ptr-chase-sm8650-x4-tlb-thp-base.json": {
                        "buffers": [512] * 4 + [2304] * 4 + [3072] * 4,
                        "seeds": {42, 7, 1337, 20260928},
                    },
                    "ptr-chase-sm8650-x4-tlb-thp-madvise.json": {
                        "buffers": [512] * 4 + [2304] * 4 + [3072] * 4,
                        "seeds": {42, 7, 1337, 20260928},
                        "page_policy": "thp",
                    },
                }
                if path.name in tlb_expectations:
                    expected = tlb_expectations[path.name]
                    if expected["buffers"] is not None:
                        self.assertEqual(
                            [case.param_value("buffer_kb") for case in plan.cases],
                            expected["buffers"],
                        )
                    else:
                        self.assertEqual(
                            {case.param_value("buffer_kb") for case in plan.cases},
                            expected["buffer_set"],
                        )
                    self.assertEqual(
                        {case.param_value("seed") for case in plan.cases},
                        expected["seeds"],
                    )
                    # G0 主曲线组（§5.2）是默认事件集；G1/G2/G4 各配置按组钉三元组
                    expected_events = expected.get("events", g0_events)
                    # base/thp 互斥（plan 期硬拒绝）：逐 case 钉本方旗标在场、
                    # 对方旗标缺席（-T 记录 params 只有 thp=1，见 §9.3 ⑮）
                    page_policy = expected.get("page_policy", "base")
                    # loads_per_slot 是派生中间量、不进 case.params：声明默认值与
                    # 派生 loads 两头钉（min_loads=4096 在最小 128KiB 档也不生效）；
                    # §5.3 开销扫描把它移进 sweep——改钉 sweep 声明与逐 case 反推
                    swept_lps = expected.get("loads_per_slot_sweep")
                    if swept_lps is None:
                        defaults = {p["name"]: p.get("default") for p in spec["parameters"]}
                        self.assertEqual(defaults["loads_per_slot"], 8)
                        self.assertIn("loads_per_slot", spec["execution"]["fixed_params"])
                    else:
                        self.assertEqual(spec["execution"]["sweep"]["loads_per_slot"],
                                         swept_lps)
                        self.assertNotIn("loads_per_slot",
                                         spec["execution"]["fixed_params"])
                        self.assertIn("min_loads", spec["execution"]["fixed_params"])
                    combos = set()
                    for case in plan.cases:
                        slots = (case.param_value("buffer_kb") * 1024
                                 // case.param_value("stride"))
                        if page_policy == "base":
                            self.assertEqual(case.param_value("base_pages"), 1)
                            self.assertNotIn("thp", dict(case.params))
                        else:
                            self.assertEqual(case.param_value("thp"), 1)
                            self.assertNotIn("base_pages", dict(case.params))
                        if swept_lps is None:
                            self.assertEqual(case.param_value("loads"), 8 * slots)
                        else:
                            # 逐 case 反推：loads == loads_per_slot × slots（min_loads 不生效）
                            self.assertEqual(case.param_value("loads") % slots, 0)
                            lps = case.param_value("loads") // slots
                            combos.add((case.param_value("buffer_kb"), lps,
                                        case.param_value("seed")))
                            # 通用 id 段：swept loads_per_slot 必须进 case id——
                            # 否则三档长度共享 id，raw 样本按 id 命名互相覆盖
                            self.assertIn(f"-loads_per_slot{lps}", case.id)
                        self.assertEqual(
                            {(event["name"], event["type"], event["config"])
                             for event in case.param_value("pmu_events")},
                            expected_events,
                        )
                    if swept_lps is not None:
                        # buffer × 长度 × seed 全叉积覆盖（缺档说明 sweep 笛卡尔积退化）
                        self.assertEqual(
                            combos,
                            {(buffer, lps, seed)
                             for buffer in expected["buffer_set"]
                             for lps in swept_lps
                             for seed in expected["seeds"]},
                        )
                for case in plan.cases:
                    params = dict(case.params)
                    slots = case.param_value("buffer_kb") * 1024 // case.param_value("stride")
                    self.assertEqual(
                        case.param_value("warmup"),
                        case.param_value("warmup_passes") * slots,
                    )
                    self.assertEqual(params["warmup"].source, "derived")

        # 计数登记不许悬空：列了期望 case 数的配置必须存在，否则缺失配置让守卫静默通过
        self.assertLessEqual(set(expected_case_counts), {p.name for p in paths})

    def test_thp_request_is_recorded_and_conflicts_are_rejected(self):
        thp_spec = {
            **PASS_SPEC,
            "parameters": [
                *PASS_SPEC["parameters"],
                {"name": "thp", "type": "int", "default": 1},
            ],
            "execution": {
                **PASS_SPEC["execution"],
                "fixed_params": ["stride", "warmup_passes", "thp"],
            },
        }
        plan = build_plan(thp_spec, {**PLATFORM, "controls": []})
        self.assertTrue(all(case.param_value("thp") == 1 for case in plan.cases))

        conflict = {
            **thp_spec,
            "parameters": [
                *thp_spec["parameters"],
                {"name": "hugepage", "type": "int", "default": 1},
            ],
            "execution": {
                **thp_spec["execution"],
                "fixed_params": ["stride", "warmup_passes", "thp", "hugepage"],
            },
        }
        with self.assertRaisesRegex(RunnerError, "cannot request both"):
            build_plan(conflict, PLATFORM)

    def test_invalid_thp_request_rejected(self):
        for invalid in (2, 0.5, True, "01"):
            with self.subTest(invalid=invalid):
                thp_spec = {
                    **PASS_SPEC,
                    "parameters": [
                        *PASS_SPEC["parameters"],
                        {"name": "thp", "type": "int", "default": invalid},
                    ],
                    "execution": {
                        **PASS_SPEC["execution"],
                        "fixed_params": ["stride", "warmup_passes", "thp"],
                    },
                }
                with self.assertRaisesRegex(RunnerError, "thp must be 0 or 1"):
                    build_plan(thp_spec, PLATFORM)

    def test_base_page_request_is_recorded_and_conflicts_are_rejected(self):
        base_spec = {
            **PASS_SPEC,
            "parameters": [
                *PASS_SPEC["parameters"],
                {"name": "base_pages", "type": "int", "default": 1},
            ],
            "execution": {
                **PASS_SPEC["execution"],
                "fixed_params": ["stride", "warmup_passes", "base_pages"],
            },
        }
        plan = build_plan(base_spec, {**PLATFORM, "controls": []})
        self.assertTrue(all(case.param_value("base_pages") == 1 for case in plan.cases))

        for conflicting_name in ("thp", "hugepage"):
            with self.subTest(conflicting_name=conflicting_name):
                conflict = {
                    **base_spec,
                    "parameters": [
                        *base_spec["parameters"],
                        {"name": conflicting_name, "type": "int", "default": 1},
                    ],
                    "execution": {
                        **base_spec["execution"],
                        "fixed_params": [
                            "stride", "warmup_passes", "base_pages", conflicting_name,
                        ],
                    },
                }
                with self.assertRaisesRegex(RunnerError, "page policies are mutually exclusive"):
                    build_plan(conflict, PLATFORM)

    def test_invalid_base_page_request_rejected(self):
        for invalid in (2, 0.5, True, "01"):
            with self.subTest(invalid=invalid):
                base_spec = {
                    **PASS_SPEC,
                    "parameters": [
                        *PASS_SPEC["parameters"],
                        {"name": "base_pages", "type": "int", "default": invalid},
                    ],
                    "execution": {
                        **PASS_SPEC["execution"],
                        "fixed_params": ["stride", "warmup_passes", "base_pages"],
                    },
                }
                with self.assertRaisesRegex(RunnerError, "base_pages must be 0 or 1"):
                    build_plan(base_spec, PLATFORM)

    def test_pmu_events_are_normalized_and_recorded(self):
        pmu_spec = {
            **PASS_SPEC,
            "parameters": [
                *PASS_SPEC["parameters"],
                {
                    "name": "pmu_events",
                    "type": "pmu-event-list",
                    "default": [
                        {"name": "cycles", "type": 8, "config": "0x11"},
                        {"name": "l2d_cache_refill", "type": 8, "config": 0x17},
                    ],
                },
            ],
            "execution": {
                **PASS_SPEC["execution"],
                "fixed_params": ["stride", "warmup_passes", "pmu_events"],
            },
        }
        plan = build_plan(pmu_spec, {**PLATFORM, "controls": []})
        expected = [
            {"name": "cycles", "type": 8, "config": 0x11},
            {"name": "l2d_cache_refill", "type": 8, "config": 0x17},
        ]
        self.assertTrue(all(case.param_value("pmu_events") == expected for case in plan.cases))
        self.assertTrue(all(
            dict(case.params)["pmu_events"].source == "spec-default"
            for case in plan.cases
        ))

    def test_invalid_pmu_events_fail_at_plan_time(self):
        invalid_lists = (
            [{"name": "Cycles", "type": 8, "config": 0x11}],
            [{"name": "cycles", "type": True, "config": 0x11}],
            [{"name": "cycles", "type": 1 << 32, "config": 0x11}],
            [{"name": "cycles", "type": 8, "config": "xyz"}],
            [
                {"name": "cycles", "type": 8, "config": 0x11},
                {"name": "cycles", "type": 8, "config": 0x17},
            ],
        )
        for invalid in invalid_lists:
            with self.subTest(invalid=invalid):
                spec = {
                    **PASS_SPEC,
                    "parameters": [
                        *PASS_SPEC["parameters"],
                        {"name": "pmu_events", "type": "pmu-event-list", "default": invalid},
                    ],
                    "execution": {
                        **PASS_SPEC["execution"],
                        "fixed_params": ["stride", "warmup_passes", "pmu_events"],
                    },
                }
                with self.assertRaisesRegex(RunnerError, "pmu_events"):
                    build_plan(spec, PLATFORM)


if __name__ == "__main__":
    unittest.main()
