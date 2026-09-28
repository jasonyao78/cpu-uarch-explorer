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
                expected_case_counts = {
                    "ptr-chase-sm8650-x4-l2-base.json": 14,
                    "ptr-chase-sm8650-x4-l2-thp.json": 14,
                    "ptr-chase-sm8650-x4-l2-fine.json": 21,
                    "ptr-chase-sm8650-x4-pmu-ctrl-cache.json": 5,
                    "ptr-chase-sm8650-x4-pmu-ctrl-tlb.json": 2,
                }
                if path.name in expected_case_counts:
                    self.assertEqual(len(plan.cases), expected_case_counts[path.name])
                    self.assertTrue(all(case.repetitions == 10 for case in plan.cases))
                for case in plan.cases:
                    params = dict(case.params)
                    slots = case.param_value("buffer_kb") * 1024 // case.param_value("stride")
                    self.assertEqual(
                        case.param_value("warmup"),
                        case.param_value("warmup_passes") * slots,
                    )
                    self.assertEqual(params["warmup"].source, "derived")

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
