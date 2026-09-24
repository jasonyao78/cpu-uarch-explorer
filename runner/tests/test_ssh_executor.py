# SPDX-License-Identifier: Apache-2.0
"""SshExecutor 与 transport 工厂的契约测试（2026-09-25 Xeon 接入任务）。

守三条契约：
1. 远程命令构造安全（shlex 引用，元字符不会被远端 shell 二次解释）；
2. 结果语义与 LocalExecutor 对齐（永不抛异常，超时/启动失败收敛）；
3. 执行器选择只认 platform.target.transport（ADR-0006 正交分解，
   主流程零特判——平台特判进配置，不进代码）。
全部用 fake（mock subprocess），不依赖真机。
"""

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from runner.errors import RunnerError
from runner.executor import make_executor
from runner.executor.local import LocalExecutor
from runner.executor.ssh import SshExecutor


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode,
                                       stdout=stdout, stderr=stderr)


class TestSshCommandConstruction(unittest.TestCase):
    """远程命令构造：cd 前缀 + exec + 引用安全 + BatchMode 硬失败。"""

    def _capture(self, executor, argv, prefix=()):
        with mock.patch("runner.executor.ssh.subprocess.run") as m:
            m.return_value = _completed(0, "out", "")
            return executor.execute(argv, prefix), m

    def test_basic_command_shape(self):
        ex = SshExecutor("xeon-8481c-01", "~/cpu-uarch-explorer")
        res, m = self._capture(ex, ["./probe", "-b", "64"])
        cmd = m.call_args.args[0]
        self.assertEqual(cmd[:4], ["ssh", "-o", "BatchMode=yes", "xeon-8481c-01"])
        self.assertIn("cd ~/cpu-uarch-explorer && exec ./probe -b 64", cmd[4])
        self.assertEqual((res.returncode, res.stdout, res.stderr), (0, "out", ""))
        # raw_command 记录完整 ssh 命令行（requested/actual 双记录）
        self.assertIn("ssh", res.raw_command)
        self.assertIn("exec ./probe -b 64", res.raw_command)

    def test_command_prefix_prepended(self):
        ex = SshExecutor("h", "~")
        _, m = self._capture(ex, ["./probe"], ("taskset", "-c", "0"))
        self.assertIn("exec taskset -c 0 ./probe", m.call_args.args[0][4])

    def test_shell_metachars_quoted(self):
        # 守 Probe ABI 输出契约的安全前提：参数不会被远端 shell 解释
        ex = SshExecutor("h", "~")
        _, m = self._capture(ex, ["./probe", "--opt", "a;b $(touch /tmp/x)"])
        remote = m.call_args.args[0][4]
        self.assertIn("'a;b $(touch /tmp/x)'", remote)

    def test_failure_modes_converged(self):
        ex = SshExecutor("h", "~")
        with mock.patch("runner.executor.ssh.subprocess.run") as m:
            m.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=1)
            res = ex.execute(["./p"])
            self.assertTrue(res.timed_out and res.returncode is None)
            m.side_effect = OSError("No route to host")
            res = ex.execute(["./p"])
            self.assertIsNone(res.returncode)
            self.assertIn("No route to host", res.stderr)


class TestTransportSelection(unittest.TestCase):
    """工厂唯一选择点：transport 字段决定执行器，配置缺失早报错。"""

    def test_local_default(self):
        self.assertIsInstance(make_executor({"target": {}}), LocalExecutor)
        self.assertIsInstance(make_executor({"target": {"transport": "local"}}), LocalExecutor)

    def test_ssh_from_extension_fields(self):
        ex = make_executor({"target": {"transport": "ssh",
                                       "ssh_host": "xeon-8481c-01",
                                       "ssh_remote_root": "~/repo"}})
        self.assertIsInstance(ex, SshExecutor)

    def test_ssh_missing_host_rejected(self):
        with self.assertRaises(RunnerError):
            make_executor({"target": {"transport": "ssh"}})

    def test_unknown_transport_rejected(self):
        with self.assertRaises(RunnerError):
            make_executor({"target": {"transport": "carrier-pigeon"}})


class TestXeonPlatformPlanExpansion(unittest.TestCase):
    """Xeon 平台接入验收：plan 展开 14 case × taskset 控制组，与 macbook
    平台走同一 build_plan——跨平台零特判是框架核心宣称，此测试钉住它。"""

    def test_xeon_plan(self):
        from runner.plan import build_plan
        from runner.spec import load_experiment, load_platform
        root = Path(__file__).resolve().parent.parent.parent
        spec = load_experiment(root / "configs/experiments/ptr-chase-cache-sweep.json")
        platform = load_platform(root / "configs/platforms/xeon-8481c-01.json")
        plan = build_plan(spec, platform)
        self.assertEqual(len(plan.cases), 14)  # 14 档 buffer × 1 控制组
        self.assertTrue(all(c.control.mechanism == "taskset" for c in plan.cases))
        self.assertTrue(all(c.control.command_prefix == ("taskset", "-c", "0")
                            for c in plan.cases))
        self.assertEqual(plan.target["transport"], "ssh")
        self.assertEqual(plan.target["target_id"], "xeon-8481c-01")


class TestFreqSnapshot(unittest.TestCase):
    """频率快照契约（measurement-discipline §5）：scaling_cur_freq 解析、
    读失败返回 None（字段省略而非编造）。守 macOS 无频率接口的现实。"""

    def test_ssh_freq_snapshot_parses(self):
        ex = SshExecutor("h", "~")
        with mock.patch("runner.executor.ssh.subprocess.run") as m:
            m.return_value = _completed(0, "2000000\n", "")
            self.assertEqual(ex.freq_snapshot("0"), {"khz": 2000000, "source": "scaling_cur_freq"})

    def test_ssh_freq_snapshot_failure_is_none(self):
        ex = SshExecutor("h", "~")
        with mock.patch("runner.executor.ssh.subprocess.run") as m:
            m.return_value = _completed(1, "", "No such file")
            self.assertIsNone(ex.freq_snapshot("0"))
            m.return_value = _completed(0, "not-a-number\n", "")
            self.assertIsNone(ex.freq_snapshot("0"))


if __name__ == "__main__":
    unittest.main()
