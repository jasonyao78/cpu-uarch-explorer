# SPDX-License-Identifier: Apache-2.0
"""Engine 契约：adapter 附加字段（page_policy 等）必须随 ok 记录的 metric 入档。

回归锚点：2026-09-25 hp2m 参考 run 的 records 全部缺失 page_policy——
engine 重建 metric dict 时把 adapter parse_output 的附加字段丢弃了。
直接测 _run_case（白盒），假执行器返回带 page_policy 的合法输出。
"""

import tempfile
import unittest
from pathlib import Path

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

    def execute(self, argv, command_prefix=()):
        if "nvidia-smi" in " ".join(str(a) for a in argv):
            return ExecutionResult(0, self._aux_stdout + "\n", "", "fake")
        return ExecutionResult(0, "latency_ns=1.0000 page_policy=hugepage-2m page_kb=2048\n",
                               "", "fake")

    def system_info(self):
        return SYSINFO

    def freq_snapshot(self, cpu_hint):
        return None


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


if __name__ == "__main__":
    unittest.main()
