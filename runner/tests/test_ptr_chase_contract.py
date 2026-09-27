# SPDX-License-Identifier: Apache-2.0
"""真实二进制契约测试（OI-9 修订纪律：fixture 必须真实捕获）。

adapter 生成的 argv 直接被**真实编译的 ptr_chase** 执行，stdout/stderr
再回给 parser——任何 argv/输出漂移都会在这里炸出来，而不是在实验数据里。
二进制未编译时 skip（不伪造通过）。
"""

import subprocess
import unittest
from pathlib import Path

from runner.adapters.ptr_chase import PtrChaseAdapter
from runner.errors import ParseError

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / "build" / "macos-arm64" / "release" / "probes" / "cache-mem" / "ptr_chase"


@unittest.skipUnless(BINARY.is_file(), f"ptr_chase not compiled: {BINARY}")
class TestPtrChaseContract(unittest.TestCase):
    def setUp(self):
        self.adapter = PtrChaseAdapter()

    def _run(self, argv):
        return subprocess.run([str(BINARY), *argv], capture_output=True, text=True, timeout=60)

    def test_argv_accepted_and_output_parses(self):
        argv = self.adapter.build_argv(
            {"buffer_kb": 64, "stride": 64, "loads": 8000, "warmup": 1000})
        proc = self._run(argv)
        self.assertEqual(proc.returncode, 0, f"probe rejected adapter argv: {proc.stderr}")
        metrics = self.adapter.parse_output(proc.stdout, proc.stderr)
        self.assertEqual(metrics[0]["name"], "latency_ns")
        self.assertGreater(metrics[0]["value"], 0.0)
        self.assertEqual(metrics[0]["warmup_loads"], 1000)
        self.assertAlmostEqual(metrics[0]["warmup_passes_effective"], 1000 / 1024, places=6)
        self.assertEqual(metrics[0]["warmup_state"], "warm")
        self.assertEqual(metrics[0]["page_policy_requested"], "default")
        self.assertEqual(metrics[0]["page_policy_actual"], "platform-default")
        self.assertEqual(metrics[0]["anon_huge_kb"], 0)

    def test_probe_abi_invalid_input_nonzero_exit(self):
        # Probe ABI（ADR-0006 §3）：非法输入非零退出，绝不静默产出记录
        proc = self._run(["-n", "1"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("latency_ns", proc.stdout)

    def test_thp_is_explicitly_unsupported_on_macos(self):
        proc = self._run(["-b", "64", "-s", "64", "-n", "8000", "-T"])
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("latency_ns", proc.stdout)

    def test_base_pages_are_explicitly_unsupported_on_macos(self):
        proc = self._run(["-b", "64", "-s", "64", "-n", "8000", "-B"])
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("latency_ns", proc.stdout)

    def test_conflicting_page_requests_are_input_error(self):
        proc = self._run(["-b", "64", "-s", "64", "-n", "8000", "-T", "-h"])
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("latency_ns", proc.stdout)

    def test_adapter_builds_thp_request_and_rejects_conflict(self):
        argv = self.adapter.build_argv(
            {"buffer_kb": 64, "stride": 64, "loads": 8000, "warmup": 1000, "thp": 1}
        )
        self.assertIn("-T", argv)
        with self.assertRaises(ParseError):
            self.adapter.build_argv({
                "buffer_kb": 64,
                "stride": 64,
                "loads": 8000,
                "warmup": 1000,
                "thp": 1,
                "hugepage": 1,
            })
        for invalid in (0.5, True, "01"):
            with self.subTest(invalid=invalid), self.assertRaises(ParseError):
                self.adapter.build_argv({
                    "buffer_kb": 64,
                    "stride": 64,
                    "loads": 8000,
                    "warmup": 1000,
                    "thp": invalid,
                })

    def test_adapter_builds_base_page_request_and_rejects_conflict(self):
        argv = self.adapter.build_argv({
            "buffer_kb": 64,
            "stride": 64,
            "loads": 8000,
            "warmup": 1000,
            "base_pages": 1,
        })
        self.assertIn("-B", argv)
        for conflicting_name in ("thp", "hugepage"):
            with self.subTest(conflicting_name=conflicting_name), self.assertRaises(ParseError):
                self.adapter.build_argv({
                    "buffer_kb": 64,
                    "stride": 64,
                    "loads": 8000,
                    "warmup": 1000,
                    "base_pages": 1,
                    conflicting_name: 1,
                })

    def test_adapter_builds_repeated_pmu_events(self):
        argv = self.adapter.build_argv({
            "buffer_kb": 64,
            "stride": 64,
            "loads": 8000,
            "warmup": 1000,
            "pmu_events": [
                {"name": "cycles", "type": 8, "config": 0x11},
                {"name": "l2d_cache_refill", "type": 8, "config": 0x17},
            ],
        })
        descriptors = [argv[index + 1] for index, value in enumerate(argv)
                       if value == "--pmu-event"]
        self.assertEqual(descriptors, ["cycles:8:17", "l2d_cache_refill:8:23"])

    def test_well_formed_pmu_event_is_unsupported_on_macos(self):
        proc = self._run([
            "-b", "64", "-s", "64", "-n", "8000",
            "--pmu-event", "cycles:8:0x11",
        ])
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("latency_ns", proc.stdout)

    def test_malformed_pmu_event_is_input_error(self):
        proc = self._run([
            "-b", "64", "-s", "64", "-n", "8000",
            "--pmu-event", "not-a-descriptor",
        ])
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("latency_ns", proc.stdout)

        duplicate = self._run([
            "-b", "64", "-s", "64", "-n", "8000",
            "--pmu-event", "cycles:8:0x11",
            "--pmu-event", "cycles:8:0x17",
        ])
        self.assertEqual(duplicate.returncode, 1)
        self.assertNotIn("latency_ns", duplicate.stdout)

    def test_parser_refuses_nan_inf_and_garbage(self):
        for bad in ("latency_ns=nan", "latency_ns=inf", "", "no fields here"):
            with self.assertRaises(ParseError, msg=f"{bad!r} must be refused"):
                self.adapter.parse_output(bad, "")

    def test_parser_refuses_invalid_warmup_audit_fields(self):
        invalid = (
            "latency_ns=1 warmup_loads=-1 warmup_passes_effective=1 warmup_state=warm",
            "latency_ns=1 warmup_loads=1.5 warmup_passes_effective=1 warmup_state=warm",
            "latency_ns=1 warmup_loads=1 warmup_passes_effective=nan warmup_state=warm",
            "latency_ns=1 warmup_loads=1 warmup_passes_effective=1 warmup_state=cold",
        )
        for stdout in invalid:
            with self.assertRaises(ParseError, msg=f"{stdout!r} must be refused"):
                self.adapter.parse_output(stdout, "")

    def test_parser_preserves_requested_and_actual_page_policy(self):
        stdout = (
            "latency_ns=1.25 page_policy=thp-mixed page_kb=0 "
            "page_policy_requested=thp-madvise page_policy_actual=mixed "
            "anon_huge_kb=2048"
        )
        metric = self.adapter.parse_output(stdout, "")[0]
        self.assertEqual(metric["page_policy_requested"], "thp-madvise")
        self.assertEqual(metric["page_policy_actual"], "mixed")
        self.assertEqual(metric["anon_huge_kb"], 2048)
        self.assertEqual(metric["page_kb"], 0)

        base = self.adapter.parse_output(
            "latency_ns=1.0 page_policy=base-madvise-4k page_kb=4 "
            "page_policy_requested=base-madvise page_policy_actual=base "
            "anon_huge_kb=0",
            "",
        )[0]
        self.assertEqual(base["page_policy_requested"], "base-madvise")
        self.assertEqual(base["page_policy_actual"], "base")

    def test_parser_refuses_invalid_page_backing_fields(self):
        invalid = (
            "latency_ns=1 page_policy_requested=thp-madvise",
            "latency_ns=1 page_policy_requested=thp-madvise page_policy_actual=huge "
            "anon_huge_kb=0",
            "latency_ns=1 page_policy_requested=thp-madvise page_policy_actual=base "
            "anon_huge_kb=-1",
        )
        for stdout in invalid:
            with self.assertRaises(ParseError, msg=f"{stdout!r} must be refused"):
                self.adapter.parse_output(stdout, "")

    def test_parser_emits_one_metric_per_complete_pmu_event(self):
        stdout = (
            "latency_ns=1.25 "
            "pmu_cycles_type=8 pmu_cycles_config=17 pmu_cycles_count=0 "
            "pmu_cycles_time_enabled_ns=1000 pmu_cycles_time_running_ns=1000 "
            "pmu_l2d_cache_refill_type=8 pmu_l2d_cache_refill_config=23 "
            "pmu_l2d_cache_refill_count=250 "
            "pmu_l2d_cache_refill_time_enabled_ns=1001 "
            "pmu_l2d_cache_refill_time_running_ns=1001"
        )
        metrics = self.adapter.parse_output(stdout, "")
        self.assertEqual(
            [metric["name"] for metric in metrics],
            ["latency_ns", "pmu.cycles.count", "pmu.l2d_cache_refill.count"],
        )
        self.assertEqual(metrics[1]["value"], 0)
        self.assertEqual(metrics[1]["pmu_type"], 8)
        self.assertEqual(metrics[1]["pmu_config"], 0x11)
        self.assertEqual(metrics[1]["time_running_ns"], 1000)
        self.assertEqual(metrics[2]["value"], 250)

    def test_parser_rejects_incomplete_or_unscheduled_pmu_event(self):
        invalid = (
            "latency_ns=1 pmu_cycles_count=1",
            "latency_ns=1 pmu_cycles_type=8 pmu_cycles_config=17 "
            "pmu_cycles_count=1 pmu_cycles_time_enabled_ns=1000",
            "latency_ns=1 pmu_cycles_type=8 pmu_cycles_config=17 "
            "pmu_cycles_count=1 pmu_cycles_time_enabled_ns=1000 "
            "pmu_cycles_time_running_ns=0",
            "latency_ns=1 pmu_cycles_type=8 pmu_cycles_config=17 "
            "pmu_cycles_count=1 pmu_cycles_time_enabled_ns=999 "
            "pmu_cycles_time_running_ns=1000",
        )
        for stdout in invalid:
            with self.subTest(stdout=stdout), self.assertRaises(ParseError):
                self.adapter.parse_output(stdout, "")


if __name__ == "__main__":
    unittest.main()
