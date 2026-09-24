# SPDX-License-Identifier: Apache-2.0
"""Plan 契约：确定性展开、repetitions 真实消费、参数溯源。"""

import unittest

from runner.errors import RunnerError
from runner.plan import build_plan

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


if __name__ == "__main__":
    unittest.main()
