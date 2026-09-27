# SPDX-License-Identifier: Apache-2.0
"""Engine 契约：adapter 附加字段（page_policy 等）必须随 ok 记录的 metric 入档。

回归锚点：2026-09-25 hp2m 参考 run 的 records 全部缺失 page_policy——
engine 重建 metric dict 时把 adapter parse_output 的附加字段丢弃了。
直接测 _run_case（白盒），假执行器返回带 page_policy 的合法输出。
"""

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

from runner.engine import _run_case
from runner.artifacts import ArtifactStore
from runner.executor.local import ExecutionResult
from runner.plan import Case, Control
from runner.resolve import ResolvedValue

PLATFORM = {"target": {"target_id": "fake-01", "transport": "local"},
            "aux_snapshots": [{"name": "gpu_util",
                               "command": ["nvidia-smi", "--query-gpu=utilization.gpu",
                                           "--format=csv,noheader"]}]}
PROBE_META = {"name": "ptr_chase", "protocol_version": "1.0",
              "implementation_id": "portable",
              "git": {"commit": "x" * 40, "dirty": False},
              "artifact": {"sha256": "y" * 64}}
SYSINFO = {"os_version": "t", "kernel": "t", "compiler": "t"}


class FakeExec:
    def __init__(self, aux_stdout="0 %"):
        self._aux_stdout = aux_stdout
        self.probe_calls = 0

    def execute(self, argv, command_prefix=()):
        if "nvidia-smi" in " ".join(str(a) for a in argv):
            return ExecutionResult(0, self._aux_stdout + "\n", "", "fake")
        self.probe_calls += 1
        return ExecutionResult(0, "latency_ns=1.0000 page_policy=hugepage-2m page_kb=2048\n",
                               "", "fake")

    def system_info(self):
        return SYSINFO

    def freq_snapshot(self, cpu_hint):
        return None


class MultiMetricExec(FakeExec):
    def execute(self, argv, command_prefix=()):
        if "nvidia-smi" in " ".join(str(a) for a in argv):
            return ExecutionResult(0, self._aux_stdout + "\n", "", "fake")
        self.probe_calls += 1
        return ExecutionResult(0, f"sample={self.probe_calls}\n", "", "fake")


class MultiMetricAdapter:
    def build_argv(self, params):
        return []

    def parse_output(self, stdout, stderr):
        sample = int(stdout.split("=", 1)[1])
        return [
            {
                "name": "latency_ns", "value": float(2 * sample - 1), "unit": "ns",
                "page_policy_requested": "base-madvise",
                "anon_huge_kb": 4 * (sample - 1),
            },
            {
                "name": "pmu.cycles.count", "value": float(100 * sample),
                "unit": "events", "pmu_type": 8, "pmu_config": 0x11,
                "time_enabled_ns": 1000 + sample,
                "time_running_ns": 1000 + sample,
            },
        ]


class MismatchedMetricAdapter(MultiMetricAdapter):
    def parse_output(self, stdout, stderr):
        metrics = super().parse_output(stdout, stderr)
        return metrics if "sample=1" in stdout else metrics[:1]


def _case() -> Case:
    params = (("buffer_kb", ResolvedValue(64, "s")), ("stride", ResolvedValue(64, "s")),
              ("loads", ResolvedValue(8000, "d")), ("warmup", ResolvedValue(0, "s")))
    return Case(id="c1", probe="ptr_chase",
                control=Control(id="ctl", mechanism="taskset", value="0"),
                params=params, repetitions=2)


class TestEngineMetricExtraFields(unittest.TestCase):
    def test_adapter_extra_fields_ride_into_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(Path(tmp) / "run")
            record = _run_case(_case(), PLATFORM, PROBE_META, "/probe",
                               FakeExec(), store, SYSINFO, PROBE_META["git"])
            self.assertEqual(record["status"], "ok")
            self.assertEqual(record["metrics"][0]["page_policy"], "hugepage-2m")

    def test_aux_snapshots_before_and_after(self):
        # GB10 §5.4：平台配置声明的只读快照（如 GPU 利用率）随 case 入档
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(Path(tmp) / "run")
            record = _run_case(_case(), PLATFORM, PROBE_META, "/probe",
                               FakeExec(aux_stdout="3 %"), store, SYSINFO, PROBE_META["git"])
            aux = record["environment"]["aux_snapshots"]["gpu_util"]
            self.assertEqual(aux["before"], "3 %")
            self.assertEqual(aux["after"], "3 %")

    def test_every_metric_preserves_per_sample_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(Path(tmp) / "run")
            with mock.patch.dict(
                "runner.engine._ADAPTERS", {"ptr_chase": MultiMetricAdapter()}
            ):
                record = _run_case(
                    _case(), PLATFORM, PROBE_META, "/probe",
                    MultiMetricExec(), store, SYSINFO, PROBE_META["git"],
                )

        self.assertEqual(record["status"], "ok")
        by_name = {metric["name"]: metric for metric in record["metrics"]}
        self.assertEqual(set(by_name), {"latency_ns", "pmu.cycles.count"})

        latency = by_name["latency_ns"]
        self.assertEqual(latency["value"], 2.0)
        self.assertEqual(latency["page_policy_requested"], "base-madvise")
        self.assertNotIn("anon_huge_kb", latency)
        self.assertEqual(
            [observation["value"] for observation in latency["observations"]],
            [1.0, 3.0],
        )
        self.assertEqual(
            [observation["sample_index"] for observation in latency["observations"]],
            [0, 1],
        )
        self.assertEqual(
            [observation["anon_huge_kb"] for observation in latency["observations"]],
            [0, 4],
        )
        self.assertTrue(all(
            observation["raw_sample_ref"].startswith("raw-samples:c1.s")
            for observation in latency["observations"]
        ))

        cycles = by_name["pmu.cycles.count"]
        self.assertEqual(cycles["value"], 150.0)
        self.assertEqual(cycles["pmu_type"], 8)
        self.assertEqual(cycles["pmu_config"], 0x11)
        self.assertNotIn("time_enabled_ns", cycles)
        self.assertEqual(
            [observation["time_enabled_ns"] for observation in cycles["observations"]],
            [1001, 1002],
        )

    def test_metric_set_drift_fails_the_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(Path(tmp) / "run")
            with mock.patch.dict(
                "runner.engine._ADAPTERS", {"ptr_chase": MismatchedMetricAdapter()}
            ):
                record = _run_case(
                    _case(), PLATFORM, PROBE_META, "/probe",
                    MultiMetricExec(), store, SYSINFO, PROBE_META["git"],
                )

        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["failure"]["reason"], "metric-aggregation-error")
        self.assertIn("metric set mismatch", record["failure"]["detail"])
        self.assertEqual(record["metrics"], [])


QUIET_POLICY = {
    "collector": "android-controlled-quiet-v2",
    "required": True,
    "preconditions": {
        "wakefulness": ["Dozing"], "screen_on": False, "force_idle": False,
        "active_camera": False, "services": {"mi_thermald": "running"},
        "cpufreq_governor": "performance",
        "cpufreq_max_khz": {"policy7": 2745600},
        "max_cpu_temp_c": 90.0,
    },
    "stable_fields": ["airplane_mode", "cpufreq.*.max_khz"],
}


def _quiet_snapshot():
    return {
        "schema_version": "1.0",
        "cpufreq": {"policy7": {"governor": "performance", "min_khz": 672000,
                                  "max_khz": 2745600, "cur_khz": 2745600}},
        "power": {"wakefulness": "Dozing", "powered": True, "screen_on": False},
        "device_idle": {"force_idle": False, "state": "ACTIVE",
                        "light_state": "ACTIVE", "charging": True},
        "airplane_mode": False,
        "camera": {"active": False, "active_clients_raw": "[]"},
        "thermal": {"status": 0, "max_cpu_c": 80.0,
                    "cpu_sensors_c": {"CPU7": 80.0}},
        "services": {"mi_thermald": "running"},
        "loadavg": {"one": 1.0, "five": 1.0, "fifteen": 1.0},
    }


class TestEngineEnvironmentGate(unittest.TestCase):
    def _run(self, snapshots):
        platform = {**PLATFORM, "aux_snapshots": [],
                    "measurement_environment": QUIET_POLICY}
        executor = FakeExec()
        with tempfile.TemporaryDirectory() as tmp:
            store = ArtifactStore(Path(tmp) / "run")
            with mock.patch("runner.engine.collect_environment_state",
                            side_effect=snapshots):
                record = _run_case(_case(), platform, PROBE_META, "/probe",
                                   executor, store, SYSINFO, PROBE_META["git"])
        return record, executor

    def test_valid_snapshots_are_recorded(self):
        before = _quiet_snapshot()
        record, executor = self._run([before, deepcopy(before)])
        self.assertEqual(record["status"], "ok")
        self.assertEqual(executor.probe_calls, 2)
        evidence = record["environment"]["state_snapshot"]
        self.assertEqual(evidence["before"], before)
        self.assertTrue(evidence["policy_result"]["valid"])

    def test_precondition_failure_prevents_probe_execution(self):
        before = _quiet_snapshot()
        before["camera"]["active"] = True
        record, executor = self._run([before])
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["failure"]["reason"],
                         "environment-precondition-failed")
        self.assertIn("camera-active", record["failure"]["detail"])
        self.assertEqual(executor.probe_calls, 0)
        self.assertEqual(record["metrics"], [])

    def test_postcondition_drift_invalidates_successful_samples(self):
        before = _quiet_snapshot()
        after = deepcopy(before)
        after["airplane_mode"] = True
        record, executor = self._run([before, after])
        self.assertEqual(executor.probe_calls, 2)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["failure"]["reason"],
                         "environment-postcondition-failed")
        self.assertIn("state-drift:airplane_mode", record["failure"]["detail"])
        self.assertEqual(record["metrics"], [])


if __name__ == "__main__":
    unittest.main()
