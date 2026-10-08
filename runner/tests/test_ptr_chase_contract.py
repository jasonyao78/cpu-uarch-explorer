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
        self.assertEqual(metrics[0]["page_policy_actual_before"], "platform-default")
        self.assertEqual(metrics[0]["page_policy_actual_after"], "platform-default")
        self.assertEqual(metrics[0]["anon_huge_kb_before"], 0)
        self.assertEqual(metrics[0]["anon_huge_kb_after"], 0)
        self.assertEqual(metrics[0]["page_backing_endpoints_equal"], 1)

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

    def test_parser_preserves_equal_measurement_window_backing_endpoints(self):
        stdout = (
            "latency_ns=1.25 page_policy=thp-mixed page_kb=0 "
            "page_policy_requested=thp-madvise page_policy_actual=mixed "
            "anon_huge_kb=2048 "
            "page_policy_actual_before=mixed page_policy_actual_after=mixed "
            "anon_huge_kb_before=2048 anon_huge_kb_after=2048 "
            "page_backing_endpoints_equal=1"
        )
        metric = self.adapter.parse_output(stdout, "")[0]
        self.assertEqual(metric["page_policy_actual_before"], "mixed")
        self.assertEqual(metric["page_policy_actual_after"], "mixed")
        self.assertEqual(metric["anon_huge_kb_before"], 2048)
        self.assertEqual(metric["anon_huge_kb_after"], 2048)
        self.assertEqual(metric["page_backing_endpoints_equal"], 1)

    def test_parser_refuses_incomplete_or_inconsistent_window_backing_audit(self):
        prefix = (
            "latency_ns=1.25 page_policy=thp-mixed page_kb=0 "
            "page_policy_requested=thp-madvise page_policy_actual=mixed "
            "anon_huge_kb=2048 "
        )
        invalid = (
            prefix + "page_policy_actual_before=mixed",
            prefix
            + "page_policy_actual_before=base page_policy_actual_after=mixed "
            + "anon_huge_kb_before=0 anon_huge_kb_after=2048 "
            + "page_backing_endpoints_equal=1",
            prefix
            + "page_policy_actual_before=mixed page_policy_actual_after=mixed "
            + "anon_huge_kb_before=1024 anon_huge_kb_after=2048 "
            + "page_backing_endpoints_equal=1",
            prefix
            + "page_policy_actual_before=mixed page_policy_actual_after=mixed "
            + "anon_huge_kb_before=2048 anon_huge_kb_after=2048 "
            + "page_backing_endpoints_equal=0",
        )
        for stdout in invalid:
            with self.subTest(stdout=stdout), self.assertRaises(ParseError):
                self.adapter.parse_output(stdout, "")

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

    def test_seed_param_builds_dash_s_and_output_records_seed(self):
        argv = self.adapter.build_argv(
            {"buffer_kb": 64, "stride": 64, "loads": 8000, "warmup": 1000, "seed": 7})
        self.assertIn("-S", argv)
        self.assertEqual(argv[argv.index("-S") + 1], "7")
        proc = self._run(argv)
        self.assertEqual(proc.returncode, 0, f"probe rejected -S: {proc.stderr}")
        metrics = self.adapter.parse_output(proc.stdout, proc.stderr)
        self.assertEqual(metrics[0]["seed"], 7)

    def test_seed_default_preserves_historical_chain(self):
        argv = self.adapter.build_argv(
            {"buffer_kb": 64, "stride": 64, "loads": 8000, "warmup": 1000})
        self.assertNotIn("-S", argv)
        proc = self._run(argv)
        self.assertEqual(proc.returncode, 0, f"probe rejected default run: {proc.stderr}")
        metrics = self.adapter.parse_output(proc.stdout, proc.stderr)
        self.assertEqual(metrics[0]["seed"], 42)

    def test_seed_garbage_is_input_error(self):
        proc = self._run(["-b", "64", "-s", "64", "-n", "8000", "-S", "abc"])
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("latency_ns", proc.stdout)
        with self.assertRaises(ParseError):
            self.adapter.build_argv(
                {"buffer_kb": 64, "stride": 64, "loads": 8000,
                 "warmup": 1000, "seed": "abc"})

    def test_seed_is_recorded_per_metric(self):
        stdout = (
            "latency_ns=1.25 seed=1337 "
            "pmu_cycles_type=8 pmu_cycles_config=17 pmu_cycles_count=100 "
            "pmu_cycles_time_enabled_ns=1000 pmu_cycles_time_running_ns=1000"
        )
        metrics = self.adapter.parse_output(stdout, "")
        self.assertEqual([metric["seed"] for metric in metrics], [1337, 1337])

    def test_vma_base_is_recorded(self):
        argv = self.adapter.build_argv(
            {"buffer_kb": 64, "stride": 64, "loads": 8000, "warmup": 1000})
        proc = self._run(argv)
        self.assertEqual(proc.returncode, 0)
        metric = self.adapter.parse_output(proc.stdout, proc.stderr)[0]
        self.assertIn("vma_base", metric)
        self.assertRegex(metric["vma_base"], r"^0x[0-9a-f]+$")

    def test_parser_records_vma_base_and_refuses_non_hex(self):
        metric = self.adapter.parse_output(
            "latency_ns=1 vma_base=0x7f12ab", "")[0]
        self.assertEqual(metric["vma_base"], "0x7f12ab")
        # 负例逐枚钉死：非 hex、大写前缀、大写数字、缺前缀、无数字。
        for bad in ("xyz", "0X7f12ab", "0x7F12AB", "7f12ab", "0x"):
            with self.subTest(vma_base=bad):
                with self.assertRaises(ParseError):
                    self.adapter.parse_output(
                        f"latency_ns=1 vma_base={bad}", "")

    def test_vma_base_is_recorded_per_metric(self):
        # 每 metric 扇出：latency 与 PMU 计数带同一样本的 vma_base。
        stdout = (
            "latency_ns=1.25 vma_base=0x7f12ab000 "
            "pmu_cycles_type=8 pmu_cycles_config=17 pmu_cycles_count=100 "
            "pmu_cycles_time_enabled_ns=1000 pmu_cycles_time_running_ns=1000"
        )
        metrics = self.adapter.parse_output(stdout, "")
        self.assertEqual([metric["vma_base"] for metric in metrics],
                         ["0x7f12ab000", "0x7f12ab000"])

    def test_legacy_output_without_vma_base(self):
        # 旧版探针输出（无 vma_base 字段）→ 任何 metric 都不补该键
        # （布局观测缺失即缺失，不编造）。
        metrics = self.adapter.parse_output(
            "latency_ns=1.25 "
            "pmu_cycles_type=8 pmu_cycles_config=17 pmu_cycles_count=100 "
            "pmu_cycles_time_enabled_ns=1000 pmu_cycles_time_running_ns=1000",
            "")
        self.assertEqual(len(metrics), 2)
        for metric in metrics:
            self.assertNotIn("vma_base", metric)

    def test_tlb_set_mode_is_unsupported_on_macos(self):
        # M0-4b：set 模式与 legacy PMU 同口径——非 Linux exit 2（能力不支持），
        # 不伪装成可执行
        argv = self.adapter.build_argv({
            "set_hypothesis": 1, "set_target": 7, "set_window": 8,
            "set_rounds": 20, "set_pool_pages": 65536,
            "set_filler_pages": 512, "set_regions": 4,
            "pmu_events": [{"name": "l1d_tlb_refill", "type": 8,
                            "config": 0x5}],
        })
        self.assertIn("--tlb-set-mode", argv)
        proc = self._run(argv)
        self.assertEqual(proc.returncode, 2, f"stderr={proc.stderr}")
        self.assertIn("unsupported", proc.stderr)


class TestTlbSetAdapterContract(unittest.TestCase):
    """M0-4b：tlb_set 形状的 adapter 契约（合成输出级；真机执行归上板）。

    不依赖编译产物——argv 构造与输出解析在任何平台可测。"""
    def setUp(self):
        self.adapter = PtrChaseAdapter()

    def _params(self, **over):
        params = {
            "set_hypothesis": 1, "set_target": 7, "set_window": 8,
            "set_rounds": 20, "set_pool_pages": 65536,
            "set_filler_pages": 512, "set_regions": 4,
            "pmu_events": [
                {"name": "l1d_tlb_refill", "type": 8, "config": 0x5},
                {"name": "l2d_tlb_refill", "type": 8, "config": 0x2d},
                {"name": "l2d_tlb", "type": 8, "config": 0x2f},
            ],
        }
        params.update(over)
        return params

    def test_build_argv_consumes_all_set_params(self):
        argv = self.adapter.build_argv(
            self._params(set_target2=100, seed=42))
        joined = " ".join(argv)
        self.assertIn("--tlb-set-mode", joined)
        for flag in ("--set-hypothesis 1", "--set-target 7", "--set-window 8",
                     "--set-rounds 20", "--set-pool-pages 65536",
                     "--set-filler 512", "--set-regions 4",
                     "--set-target2 100", "-S 42", "-B"):
            self.assertIn(flag, joined)
        for event in ("l1d_tlb_refill:8:5", "l2d_tlb_refill:8:45",
                      "l2d_tlb:8:47"):
            self.assertIn(f"--pmu-event {event}", joined)

    def test_scatter_flag_emitted_only_when_set(self):
        argv = self.adapter.build_argv(self._params(set_scatter=1))
        self.assertIn("--set-scatter", " ".join(argv))
        argv = self.adapter.build_argv(self._params(set_scatter=0))
        self.assertNotIn("--set-scatter", " ".join(argv))

    def test_missing_required_param_fails_closed(self):
        for missing in ("set_window", "set_hypothesis", "set_target"):
            params = self._params()
            del params[missing]
            with self.assertRaisesRegex(ParseError, missing):
                self.adapter.build_argv(params)

    def test_legacy_params_never_take_set_branch(self):
        argv = self.adapter.build_argv(
            {"buffer_kb": 64, "stride": 64, "loads": 8000, "warmup": 1000})
        self.assertNotIn("--tlb-set-mode", " ".join(argv))

    def test_parse_tlbset_output_roundtrip(self):
        stdout = (
            "mode=tlbset set_hypothesis=1 set_target=7 set_window=8 set_rounds=20 "
            "set_filler=512 set_regions=4 set_domain=multi-region page_kb=4 seed=42 "
            "window_valid_rounds=19 window_invalid_rounds=0 window_mux_rounds=0 "
            "valid_rounds=19 probe_ns=1500 "
            "pmu_l1d_tlb_refill_count=8.0 pmu_l1d_tlb_refill_valid_rounds=19 "
            "pmu_l2d_tlb_refill_count=0.2 pmu_l2d_tlb_refill_valid_rounds=19 "
            "pmu_l2d_tlb_count=8.1 pmu_l2d_tlb_valid_rounds=19"
        )
        metrics = self.adapter.parse_output(stdout, "")
        by_name = {m["name"]: m["value"] for m in metrics}
        self.assertEqual(by_name["pmu.l1d_tlb_refill.count"], 8.0)
        self.assertEqual(by_name["pmu.l2d_tlb_refill.count"], 0.2)
        self.assertEqual(by_name["window_valid_rounds"], 19)
        self.assertEqual(by_name["window_mux_rounds"], 0)
        self.assertEqual(by_name["probe_latency_ns"], 1500)

    def test_parse_tlbset_output_without_events_fails_closed(self):
        stdout = ("mode=tlbset set_domain=multi-region "
                  "window_valid_rounds=19 window_invalid_rounds=0 "
                  "window_mux_rounds=0 valid_rounds=19 probe_ns=1")
        with self.assertRaisesRegex(ParseError, "no pmu"):
            self.adapter.parse_output(stdout, "")

    def test_parse_legacy_output_stays_on_chase_branch(self):
        # 回归：legacy 输出（无 mode=tlbset）不因 parser 分支改变语义
        metrics = self.adapter.parse_output("latency_ns=1.25", "")
        self.assertEqual(metrics[0]["name"], "latency_ns")

    def test_descriptor_consistency_accepts_matching_realized(self):
        # MB-06：requested→realized 一致 → 通过
        stdout = (
            "mode=tlbset set_hypothesis=1 set_target=7 set_window=8 set_rounds=20 "
            "set_domain=multi-region window_valid_rounds=19 window_invalid_rounds=0 "
            "window_mux_rounds=0 valid_rounds=19 probe_ns=1500 "
            "pmu_l1d_tlb_refill_count=8.0 pmu_l1d_tlb_refill_valid_rounds=19"
        )
        metrics = self.adapter.parse_output(
            stdout, "",
            {"set_hypothesis": 1, "set_target": 7, "set_window": 8,
             "set_rounds": 20})
        self.assertEqual(metrics[0]["name"], "window_valid_rounds")

    def test_descriptor_mismatch_fails_closed(self):
        # 探针自描述与请求不符 = 执行漂移，ParseError
        stdout = (
            "mode=tlbset set_hypothesis=1 set_target=99 set_window=8 set_rounds=20 "
            "set_domain=multi-region window_valid_rounds=19 "
            "window_invalid_rounds=0 window_mux_rounds=0 valid_rounds=19 "
            "probe_ns=1500 pmu_l1d_tlb_refill_count=8.0 "
            "pmu_l1d_tlb_refill_valid_rounds=19"
        )
        with self.assertRaisesRegex(ParseError, "descriptor mismatch"):
            self.adapter.parse_output(
                stdout, "",
                {"set_hypothesis": 1, "set_target": 7, "set_window": 8})

    def test_descriptor_missing_realized_field_fails_closed(self):
        stdout = (
            "mode=tlbset set_hypothesis=1 set_window=8 "
            "set_domain=multi-region window_valid_rounds=19 "
            "window_invalid_rounds=0 window_mux_rounds=0 valid_rounds=19 "
            "probe_ns=1500 pmu_l1d_tlb_refill_count=8.0 "
            "pmu_l1d_tlb_refill_valid_rounds=19"
        )
        with self.assertRaisesRegex(ParseError, "did not report"):
            self.adapter.parse_output(
                stdout, "", {"set_hypothesis": 1, "set_target": 7,
                             "set_window": 8})

    def test_shape_decided_by_request_not_output(self):
        # PA-02：请求 tlb_set 而输出 legacy → 拒绝（不再按输出自报定形）
        with self.assertRaisesRegex(ParseError, "shape mismatch"):
            self.adapter.parse_output(
                "latency_ns=1.25", "",
                {"set_hypothesis": 1, "set_target": 7, "set_window": 8})
        # 反向：请求 legacy 而输出 tlbset → 拒绝
        with self.assertRaisesRegex(ParseError, "shape mismatch"):
            self.adapter.parse_output(
                "mode=tlbset set_hypothesis=1 set_window=8 "
                "set_domain=multi-region window_valid_rounds=19 "
                "window_invalid_rounds=0 window_mux_rounds=0 valid_rounds=19 "
                "probe_ns=1 pmu_l1d_tlb_refill_count=1.0 "
                "pmu_l1d_tlb_refill_valid_rounds=19",
                "", {"buffer_kb": 64, "stride": 64, "loads": 8000,
                     "warmup": 1000})

    def test_condition_param_drift_rejected(self):
        # PA-02：regions/filler/scatter/seed 漂移必须拒绝
        stdout = (
            "mode=tlbset set_hypothesis=1 set_target=7 set_window=8 "
            "set_rounds=20 set_pool_pages=65536 set_filler_pages=512 "
            "set_regions=1 scatter=0 set_region_scope=-1 set_nsets=0 "
            "set_active_regions=1 set_target_region_nodes=8 "
            "set_domain=single-region-fallback page_kb=4 seed=99 "
            "window_valid_rounds=19 window_invalid_rounds=0 "
            "window_mux_rounds=0 valid_rounds=19 probe_ns=1500 "
            "pmu_l1d_tlb_refill_count=8.0 pmu_l1d_tlb_refill_valid_rounds=19"
        )
        with self.assertRaisesRegex(ParseError, "set_regions"):
            self.adapter.parse_output(
                stdout, "",
                {"set_hypothesis": 1, "set_target": 7, "set_window": 8,
                 "set_regions": 4, "set_filler_pages": 512, "seed": 42})
        with self.assertRaisesRegex(ParseError, "seed"):
            self.adapter.parse_output(
                stdout, "",
                {"set_hypothesis": 1, "set_target": 7, "set_window": 8,
                 "set_regions": 1, "set_filler_pages": 512, "seed": 42})

    def test_missing_requested_event_rejected(self):
        stdout = (
            "mode=tlbset set_hypothesis=1 set_target=7 set_window=8 "
            "set_rounds=20 set_pool_pages=65536 set_filler_pages=512 "
            "set_regions=4 scatter=0 set_region_scope=-1 set_nsets=0 "
            "set_active_regions=4 set_target_region_nodes=3,3,3,3 "
            "set_domain=multi-region page_kb=4 seed=42 "
            "window_valid_rounds=19 window_invalid_rounds=0 "
            "window_mux_rounds=0 valid_rounds=19 probe_ns=1500 "
            "pmu_l1d_tlb_refill_count=8.0 pmu_l1d_tlb_refill_valid_rounds=19"
        )
        with self.assertRaisesRegex(ParseError, "missing"):
            self.adapter.parse_output(
                stdout, "",
                {"set_hypothesis": 1, "set_target": 7, "set_window": 8,
                 "pmu_events": [
                     {"name": "l1d_tlb_refill", "type": 8, "config": 5},
                     {"name": "l2d_tlb_refill", "type": 8, "config": 45}]})

    def test_parse_realized_extracts_incentive_audit(self):
        stdout = (
            "mode=tlbset set_hypothesis=1 set_target=7 set_window=8 "
            "set_rounds=20 set_pool_pages=65536 set_filler_pages=512 "
            "set_regions=4 scatter=0 set_region_scope=-1 set_nsets=0 "
            "set_active_regions=4 set_target_region_nodes=3,3,3,3 "
            "set_domain=multi-region page_kb=4 seed=42 "
            "window_valid_rounds=19 window_invalid_rounds=0 "
            "window_mux_rounds=0 valid_rounds=19 probe_ns=1500 "
            "pmu_l1d_tlb_refill_count=8.0 pmu_l1d_tlb_refill_valid_rounds=19"
        )
        realized = self.adapter.parse_realized(stdout)
        self.assertEqual(realized["set_domain"], "multi-region")
        self.assertEqual(realized["set_active_regions"], 4)
        self.assertEqual(realized["set_target_region_nodes"], [3, 3, 3, 3])
        self.assertEqual(realized["set_hypothesis"], 1)
        self.assertEqual(self.adapter.parse_realized("latency_ns=1.25"), {})

    def test_parse_realized_rejects_invalid_tokens(self):
        # RPA-03：非法 token 拒绝而非静默删除（评审复现："2,bad,2,2" 被
        # 静默解析成 [2,2,2]）
        base = (
            "mode=tlbset set_hypothesis=1 set_target=7 set_window=8 "
            "set_rounds=20 set_pool_pages=65536 set_filler_pages=512 "
            "set_regions=4 scatter=0 set_region_scope=-1 set_nsets=0 "
            "set_active_regions=4 set_target_region_nodes=2,bad,2,2 "
            "set_domain=multi-region page_kb=4 seed=42 "
            "window_valid_rounds=19 window_invalid_rounds=0 "
            "window_mux_rounds=0 valid_rounds=19 probe_ns=1500 "
            "pmu_l1d_tlb_refill_count=8.0 pmu_l1d_tlb_refill_valid_rounds=19"
        )
        with self.assertRaisesRegex(ParseError, "invalid token"):
            self.adapter.parse_realized(base)
        clean = (
            "mode=tlbset set_hypothesis=1 set_target=7 set_window=8 "
            "set_rounds=20 set_pool_pages=65536 set_filler_pages=512 "
            "set_regions=4 scatter=0 set_region_scope=-1 set_nsets=0 "
            "set_active_regions=4 set_target_region_nodes=2,2,2,2 "
            "set_domain=multi-region page_kb=4 seed=42 "
            "window_valid_rounds=19 window_invalid_rounds=0 "
            "window_mux_rounds=0 valid_rounds=19 probe_ns=1500 "
            "pmu_l1d_tlb_refill_count=8.0 pmu_l1d_tlb_refill_valid_rounds=19"
        )
        bad_active = clean.replace("set_active_regions=4",
                                   "set_active_regions=oops")
        with self.assertRaisesRegex(ParseError, "not an integer"):
            self.adapter.parse_realized(bad_active)

    def test_parse_realized_invariants_with_expected(self):
        stdout = (
            "mode=tlbset set_hypothesis=1 set_target=7 set_window=8 "
            "set_rounds=20 set_pool_pages=65536 set_filler_pages=512 "
            "set_regions=4 scatter=0 set_region_scope=-1 set_nsets=0 "
            "set_active_regions=4 set_target_region_nodes=2,2,2,2 "
            "set_domain=multi-region page_kb=4 seed=42 "
            "window_valid_rounds=19 window_invalid_rounds=0 "
            "window_mux_rounds=0 valid_rounds=19 probe_ns=1500 "
            "pmu_l1d_tlb_refill_count=8.0 pmu_l1d_tlb_refill_valid_rounds=19"
        )
        expected = {"set_window": 8, "set_regions": 4,
                    "set_region_scope": -1, "set_nsets": 0}
        # 一致例（sum=8==window）通过：
        self.assertEqual(
            self.adapter.parse_realized(stdout, expected)["set_active_regions"], 4)
        # sum 违例：
        bad = stdout.replace("set_target_region_nodes=2,2,2,2",
                             "set_target_region_nodes=3,3,3,3")
        with self.assertRaisesRegex(ParseError, "node sum"):
            self.adapter.parse_realized(bad, expected)
        # scope 隔离违例
        iso_bad = stdout.replace("set_region_scope=-1", "set_region_scope=1")
        with self.assertRaisesRegex(ParseError, "scope isolation"):
            self.adapter.parse_realized(iso_bad,
                                        {**expected, "set_region_scope": 1})


if __name__ == "__main__":
    unittest.main()
