# SPDX-License-Identifier: Apache-2.0
"""环境事务模型契约（2026-09-25 讨论裁定的落地验证）。

守四条契约：
1. 正常路径：apply → work → 逆序 restore，journal 终态 restored，
   目标机状态回到 before 值；
2. work 抛异常：恢复仍然发生，异常原样上抛（测量失败不留下脏状态）；
3. apply 失败（如非交互 sudo 不可用）：journal apply-failed，系统未被
   改变，错误结构化（RunnerError 家族）；
4. 未完成事务阻塞新事务（单操作者互斥基石）；restore 幂等。
FakeExecutor 维护可变 governor 状态；锁为假锁；store 用临时目录。
"""

import tempfile
import unittest
from pathlib import Path

from runner.environment.coordinator import (EnvironmentError_,
                                            execute_environment_tx,
                                            restore_transaction)
from runner.environment.journal import JournalStore, Mutation
from runner.environment.controllers import make_controller
from runner.errors import RunnerError
from runner.executor.local import ExecutionResult

PLATFORM = {"target": {"target_id": "fake-01", "transport": "local"}}


class FakeEnvExecutor:
    """可变状态假执行器：governor 文件语义 + sudo 可控成败。

    sudo 语义按现行 controller 实现：调包装脚本
    `sudo -n /usr/local/bin/cpu-uarch-set-governor <value>`。"""

    def __init__(self, governor="powersave", sudo_ok=True):
        self.governor = governor
        self.sudo_ok = sudo_ok

    def execute(self, argv, command_prefix=()):
        cmd = " ".join(str(a) for a in argv)
        if cmd.startswith("cat") and "scaling_governor" in cmd:
            return ExecutionResult(0, self.governor + "\n", "", "fake")
        if "cpu-uarch-set-governor" in cmd:
            if not self.sudo_ok:
                return ExecutionResult(1, "", "sudo: a password is required", "fake")
            value = cmd.split()[-1]
            if value not in ("performance", "powersave"):
                return ExecutionResult(1, "", "usage: cpu-uarch-set-governor performance|powersave", "fake")
            self.governor = value
            return ExecutionResult(0, "", "", "fake")
        return ExecutionResult(1, "", "unscripted command", "fake")


class FakeLock:
    def __init__(self):
        self.acquired = self.released = False

    def acquire(self):
        self.acquired = True

    def release(self):
        self.released = True


class TestEnvironmentTx(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = JournalStore(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def _tx(self, executor, work, specs=("governor=performance",), lock=None, **kw):
        return execute_environment_tx(PLATFORM, list(specs), work,
                                      allow_mutation=True, store=self.store,
                                      executor=executor, lock=lock or FakeLock(), **kw)

    def test_happy_path_restores_before_value(self):
        ex, lock = FakeEnvExecutor(), FakeLock()
        result = self._tx(ex, lambda: {"ok": 1}, lock=lock)
        self.assertEqual(result, {"ok": 1})
        self.assertEqual(ex.governor, "powersave")  # restore 回 before 值
        self.assertTrue(lock.acquired and lock.released)
        journals = list(self.store.root.glob("*.json"))
        self.assertEqual(len(journals), 1)
        self.assertEqual(self.store.load(journals[0].stem).state, "restored")

    def test_work_failure_still_restores(self):
        ex = FakeEnvExecutor()
        def boom():
            raise RuntimeError("probe crashed")
        with self.assertRaises(RuntimeError):
            self._tx(ex, boom)
        self.assertEqual(ex.governor, "powersave")  # 脏状态不留
        self.assertEqual(self.store.unfinished(), [])

    def test_sudo_failure_is_structured_and_no_mutation(self):
        ex = FakeEnvExecutor(sudo_ok=False)
        with self.assertRaises(EnvironmentError_) as cm:
            self._tx(ex, lambda: None)
        self.assertEqual(cm.exception.code, "env-apply-failed")
        self.assertEqual(ex.governor, "powersave")  # 系统未被改变
        self.assertEqual(self.store.unfinished(), [])  # apply-failed 是终态

    def test_unfinished_tx_blocks_new_tx(self):
        ex = FakeEnvExecutor()
        journal = self.store.new("fake-01")
        journal.transition("applying")
        self.store.save(journal)
        with self.assertRaises(EnvironmentError_) as cm:
            self._tx(ex, lambda: None)
        self.assertEqual(cm.exception.code, "env-unfinished-tx")

    def test_allow_mutation_gate(self):
        ex = FakeEnvExecutor()
        with self.assertRaises(EnvironmentError_):
            execute_environment_tx(PLATFORM, ["governor=performance"], lambda: None,
                                   allow_mutation=False, store=self.store,
                                   executor=ex)

    def test_manual_restore_is_idempotent(self):
        ex = FakeEnvExecutor()
        self._tx(ex, lambda: None)
        tx_id = self.store.unfinished() or None
        journals = list(self.store.root.glob("*.json"))
        restore_transaction(journals[0].stem, PLATFORM, store=self.store, executor=ex)
        restore_transaction(journals[0].stem, PLATFORM, store=self.store, executor=ex)  # 幂等
        self.assertEqual(ex.governor, "powersave")

    def test_unknown_controller_rejected(self):
        with self.assertRaises(RunnerError):
            make_controller("filesystem=readonly")


class TestReconcileAndSpecs(unittest.TestCase):
    """中断恢复实证（任务书 §2.1/§5.2）：kill -INT 留下的未完成事务在下次
    运行前被检测并完成 restore；host_requirements 声明式换算。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = JournalStore(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_sigint_interrupted_journal_reconciled_before_next_run(self):
        ex = FakeEnvExecutor(governor="performance")  # 中断现场：已锁未恢复
        journal = self.store.new("fake-01")
        journal.mutations.append(Mutation(controller="cpufreq.governor",
                                          requested="performance", before="powersave",
                                          after="performance"))
        journal.transition("applying")
        journal.transition("applied")
        self.store.save(journal)

        from runner.environment import reconcile_unfinished
        remaining = reconcile_unfinished(PLATFORM, store=self.store, executor=ex)
        self.assertEqual(remaining, [])
        self.assertEqual(ex.governor, "powersave")  # 已逆序恢复
        self.assertEqual(self.store.load(journal.tx_id).state, "restored")

    def test_reconcile_failure_keeps_journal_blocking(self):
        ex = FakeEnvExecutor(governor="performance", sudo_ok=False)  # 恢复也失败
        journal = self.store.new("fake-01")
        journal.mutations.append(Mutation(controller="cpufreq.governor",
                                          requested="performance", before="powersave",
                                          after="performance"))
        journal.transition("applying")
        journal.transition("applied")
        self.store.save(journal)
        from runner.environment import reconcile_unfinished
        remaining = reconcile_unfinished(PLATFORM, store=self.store, executor=ex)
        self.assertEqual(len(remaining), 1)  # 仍阻塞，交由人工

    def test_keyboardinterrupt_in_work_still_restores(self):
        # SIGINT 经 KeyboardInterrupt 进入恢复路径（语义钉住，非行为验证）
        ex = FakeEnvExecutor()
        def interrupted():
            raise KeyboardInterrupt("simulated SIGINT")
        with self.assertRaises(KeyboardInterrupt):
            execute_environment_tx(PLATFORM, ["governor=performance"], interrupted,
                                   allow_mutation=True, store=self.store,
                                   executor=ex, lock=FakeLock())
        self.assertEqual(ex.governor, "powersave")

    def test_host_requirements_to_specs(self):
        from runner.environment import specs_from_host_requirements
        specs = specs_from_host_requirements({"cpufreq.governor": "performance"})
        self.assertEqual(specs, ["governor=performance"])


class TestRemoteFlockScript(unittest.TestCase):
    """远端锁脚本契约：非阻塞 flock + 旗标自释放循环（2026-09-26 orphan
    锁实证后的修正——release 不依赖 ssh 信号传播）。"""

    def test_holder_script_structure(self):
        from runner.environment.coordinator import _RemoteFlock
        script = _RemoteFlock("h", "~")._script()
        self.assertIn("flock -n", script)
        self.assertIn("mutation.lock.release", script)
        self.assertIn("while [ ! -f", script)   # 旗标循环
        self.assertIn("rm -f", script)          # acquire 前清残留旗标


if __name__ == "__main__":
    unittest.main()
