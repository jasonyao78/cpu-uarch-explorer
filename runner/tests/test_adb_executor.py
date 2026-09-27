# SPDX-License-Identifier: Apache-2.0
"""AdbExecutor 与 adb deploy 的契约测试（Android 平台接入）。

守三条契约：
1. 命令构造：adb shell + cd 工作目录 + exec + shlex 引用（toybox sh）；
2. 设备序列号不进配置——单设备免 serial，多设备走 ANDROID_SERIAL；
3. 结果语义与 Local/Ssh 对齐（永不抛异常）；deploy 按 transport 分支
   （adb push / scp）。
全部 mock subprocess，不依赖真机。
"""

import subprocess
import unittest
from unittest import mock

from runner.deploy import deploy_if_needed
from runner.errors import RunnerError
from runner.executor import make_executor
from runner.executor.adb import AdbExecutor
from runner.executor.local import ExecutionResult


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode,
                                       stdout=stdout, stderr=stderr)


class TestAdbCommandConstruction(unittest.TestCase):
    def _capture(self, executor, argv, prefix=()):
        with mock.patch("runner.executor.adb.subprocess.run") as m:
            m.return_value = _completed(0, "out", "")
            return executor.execute(argv, prefix), m

    def test_single_device_no_serial(self):
        ex = AdbExecutor()
        res, m = self._capture(ex, ["./probe", "-b", "64"])
        cmd = m.call_args.args[0]
        self.assertEqual(cmd[:2], ["adb", "shell"])          # 无 -s 段
        self.assertIn("cd /data/local/tmp 2>/dev/null; exec ./probe -b 64", cmd[2])
        self.assertEqual((res.returncode, res.stdout), (0, "out"))

    def test_shell_metachars_quoted(self):
        ex = AdbExecutor()
        _, m = self._capture(ex, ["./probe", "--opt", "a;b $(x)"])
        self.assertIn("'a;b $(x)'", m.call_args.args[0][2])

    def test_failure_modes_converged(self):
        ex = AdbExecutor()
        with mock.patch("runner.executor.adb.subprocess.run") as m:
            m.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=1)
            self.assertTrue(ex.execute(["p"]).timed_out)
            m.side_effect = OSError("device offline")
            res = ex.execute(["p"])
            self.assertIsNone(res.returncode)
            self.assertIn("device offline", res.stderr)

    def test_freq_snapshot_falls_back(self):
        # scaling_cur_freq 失败 → cpuinfo_cur_freq 兜底（Android root 前场景）
        ex = AdbExecutor()
        with mock.patch("runner.executor.adb.subprocess.run") as m:
            m.return_value = _completed(0, "2265600\n", "")
            snap = ex.freq_snapshot("0")
            self.assertEqual(snap["khz"], 2265600)
            m.side_effect = OSError("offline")
            self.assertIsNone(ex.freq_snapshot("0"))


class TestTransportSelection(unittest.TestCase):
    def test_adb_selected_from_platform(self):
        ex = make_executor({"target": {"transport": "adb",
                                       "adb_workdir": "/data/local/tmp/cpu-uarch"}})
        self.assertIsInstance(ex, AdbExecutor)

    def test_deploy_push_branches_adb(self):
        import hashlib
        import tempfile
        from pathlib import Path
        platform = {"target": {"transport": "adb"},
                    "probes": {"ptr_chase": {"local": "__L__", "remote": "/data/local/tmp/cpu-uarch/ptr_chase"}}}
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "ptr_chase"
            local.write_bytes(b"\x7fELF aarch64")
            platform["probes"]["ptr_chase"]["local"] = str(local)
            sha = hashlib.sha256(local.read_bytes()).hexdigest()

            class FakeExec:
                _sha = None
                def execute(self, argv, command_prefix=()):
                    cmd = " ".join(str(a) for a in argv)
                    if cmd.startswith("sha256sum"):
                        if self._sha is None:
                            return ExecutionResult(1, "", "No such file", "fake")
                        return ExecutionResult(0, f"{self._sha}  x", "", "fake")
                    if cmd.startswith("mkdir"):
                        return ExecutionResult(0, "", "", "fake")
                    return ExecutionResult(1, "", "unscripted", "fake")

            pushes = []
            fake_exec = FakeExec()
            def fake_push(*_args):  # autospec 透传 _default_push 的三参签名
                pushes.append(1)
                fake_exec._sha = sha

            import runner.deploy as deploy_mod
            with mock.patch.object(deploy_mod, "_default_push", side_effect=fake_push, autospec=True):
                remote = deploy_if_needed(platform, "ptr_chase", fake_exec)
            self.assertEqual(remote, "/data/local/tmp/cpu-uarch/ptr_chase")
            self.assertEqual(len(pushes), 1)


if __name__ == "__main__":
    unittest.main()
