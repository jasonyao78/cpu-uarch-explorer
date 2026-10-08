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
import re
from pathlib import Path

from runner.environment.coordinator import (EnvironmentError_,
                                            execute_environment_tx,
                                            restore_transaction)
from runner.environment.journal import JournalStore, Mutation
from runner.environment.controllers import make_controller
from runner.errors import RunnerError
from runner.executor.adb import AdbExecutor
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
            self.governor = cmd.split()[-1]
            return ExecutionResult(0, "", "", "fake")
        return ExecutionResult(1, "", "unscripted command", "fake")


class FakeLock:
    def __init__(self):
        self.acquired = self.released = False

    def acquire(self):
        self.acquired = True

    def release(self):
        self.released = True


class FakeAdbExecutor(AdbExecutor):
    """Android 假执行器（isinstance AdbExecutor 走 su -c 分支）：
    governor 文件语义 + su 可控成败。语义按 controller 实现：调
    `su -c 'for c in .../scaling_governor; do echo <value> > $c ...; done'`。"""

    def __init__(self, governor="walt", su_ok=True):
        self.governor = governor
        self.min_khz = 556800
        self.max_khz = 2265600
        self.su_ok = su_ok

    def execute(self, argv, command_prefix=()):
        cmd = " ".join(str(a) for a in argv)
        if "cpu_uarch_cpufreq_inspect_v1" in cmd:
            return ExecutionResult(
                0, f"policy0|{self.governor}|{self.min_khz}|{self.max_khz}\n", "", "fake")
        if cmd.startswith("cat") and "scaling_governor" in cmd:
            return ExecutionResult(0, self.governor + "\n", "", "fake")
        if cmd.startswith("su -c"):
            if not self.su_ok:
                return ExecutionResult(1, "", "su: permission denied", "fake")
            if "cpu_uarch_cpufreq_restore_v1" in cmd:
                base = r"/sys/devices/system/cpu/cpufreq/policy0/"
                min_match = re.search(rf"echo (\d+) > {base}scaling_min_freq", cmd)
                max_match = re.search(rf"echo (\d+) > {base}scaling_max_freq", cmd)
                gov_match = re.search(rf"echo ([A-Za-z0-9_-]+) > {base}scaling_governor", cmd)
                if not (min_match and max_match and gov_match):
                    return ExecutionResult(1, "", "malformed restore", "fake")
                self.min_khz = int(min_match.group(1))
                self.max_khz = int(max_match.group(1))
                self.governor = gov_match.group(1)
                return ExecutionResult(0, "", "", "fake")
            parts = cmd.split()
            value = parts[parts.index("echo") + 1]
            if any(ch in value for ch in "/ ;|&$`"):
                return ExecutionResult(1, "", "unsafe value", "fake")
            self.governor = value
            return ExecutionResult(0, "", "", "fake")
        return ExecutionResult(1, "", "unscripted command", "fake")


class FakeMultiPolicyAdbExecutor(AdbExecutor):
    """四 policy 假设备：覆盖异构 governor/min/max 的精确恢复契约。"""

    def __init__(self):
        self.policies = {
            "policy0": {"governor": "walt", "min_khz": 556800, "max_khz": 2265600},
            "policy2": {"governor": "schedutil", "min_khz": 614400, "max_khz": 2707200},
            "policy5": {"governor": "walt", "min_khz": 499200, "max_khz": 2707200},
            "policy7": {"governor": "powersave", "min_khz": 672000, "max_khz": 2745600},
        }

    def execute(self, argv, command_prefix=()):
        cmd = " ".join(str(a) for a in argv)
        if cmd.startswith("cat") and "cpu0/cpufreq/scaling_governor" in cmd:
            return ExecutionResult(0, self.policies["policy0"]["governor"] + "\n", "", "fake")
        if "cpu_uarch_cpufreq_inspect_v1" in cmd:
            rows = [f"{name}|{state['governor']}|{state['min_khz']}|{state['max_khz']}"
                    for name, state in sorted(self.policies.items())]
            return ExecutionResult(0, "\n".join(rows) + "\n", "", "fake")
        if cmd.startswith("su -c") and "scaling_governor" in cmd:
            if "cpu_uarch_cpufreq_restore_v1" in cmd:
                for field, key in (("scaling_min_freq", "min_khz"),
                                   ("scaling_max_freq", "max_khz"),
                                   ("scaling_governor", "governor")):
                    pattern = rf"echo ([^ ;]+) > /sys/devices/system/cpu/cpufreq/(policy\d+)/{field}"
                    for value, policy in re.findall(pattern, cmd):
                        self.policies[policy][key] = int(value) if key.endswith("khz") else value
            else:
                match = re.search(r"echo ([^ ;]+) > (?:.*scaling_governor|\$c)", cmd)
                if not match:
                    return ExecutionResult(1, "", "missing governor value", "fake")
                for state in self.policies.values():
                    state["governor"] = match.group(1)
            return ExecutionResult(0, "", "", "fake")
        return ExecutionResult(1, "", "unscripted: " + cmd, "fake")


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
        # 非零退出不能证明远端没有部分写入；恢复也无法执行时必须升级为
        # restore-failed 并保留阻塞 journal，不能假装环境已知干净。
        self.assertEqual(cm.exception.code, "env-restore-failed")
        self.assertEqual(ex.governor, "powersave")  # 系统未被改变
        self.assertEqual(len(self.store.unfinished()), 1)

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


class TestAndroidGovernorTx(unittest.TestCase):
    """Android 分支（2026-09-27 K70 Pro KernelSU Root 落地）：controller
    经 su -c 写全部 CPU governor；事务语义与 Linux 分支一致（apply →
    work → 逆序 restore、journal 留痕、su 失败结构化）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = JournalStore(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def _tx(self, executor, work=lambda: {"ok": 1}, specs=("governor=performance",)):
        return execute_environment_tx(PLATFORM, list(specs), work,
                                      allow_mutation=True, store=self.store,
                                      executor=executor, lock=FakeLock())

    def test_su_c_happy_path_restores(self):
        ex = FakeAdbExecutor(governor="walt")
        self.assertEqual(self._tx(ex), {"ok": 1})
        self.assertEqual(ex.governor, "walt")  # restore 回 before 值

    def test_su_failure_is_structured_and_no_mutation(self):
        ex = FakeAdbExecutor(su_ok=False)
        with self.assertRaises(EnvironmentError_) as cm:
            self._tx(ex)
        self.assertEqual(cm.exception.code, "env-restore-failed")
        self.assertEqual(ex.governor, "walt")
        self.assertEqual(len(self.store.unfinished()), 1)

    def test_linux_branch_rejects_su_form(self):
        # isinstance 分支保证：Linux 执行器永不收到 su -c——经 sudo 脚本路径成功
        ex = FakeEnvExecutor(governor="walt")
        self._tx(ex)
        self.assertEqual(ex.governor, "walt")  # restore 回 walt（非 Adb 亦走事务）

    def test_unsafe_governor_value_rejected_before_apply(self):
        ex = FakeAdbExecutor()
        with self.assertRaises(EnvironmentError_) as cm:
            self._tx(ex, specs=("governor=performance; rm -rf /",))
        self.assertEqual(cm.exception.code, "env-invalid-request")

    def test_all_policy_state_is_restored_exactly(self):
        ex = FakeMultiPolicyAdbExecutor()
        before = {name: dict(state) for name, state in ex.policies.items()}

        def assert_applied():
            self.assertEqual({state["governor"] for state in ex.policies.values()},
                             {"performance"})
            return {"ok": 1}

        self.assertEqual(self._tx(ex, work=assert_applied), {"ok": 1})
        self.assertEqual(ex.policies, before)


class FakeAdbThermalExecutor(AdbExecutor):
    """mi_thermald 假执行器：su -c stop/start 语义 + getprop 查询。"""

    def __init__(self, state="running"):
        self.svc_state = state

    def execute(self, argv, command_prefix=()):
        cmd = " ".join(str(a) for a in argv)
        if "getprop init.svc.mi_thermald" in cmd:
            return ExecutionResult(0, self.svc_state + "\n", "", "fake")
        if cmd == "su -c stop mi_thermald":
            self.svc_state = "stopped"
            return ExecutionResult(0, "", "", "fake")
        if cmd == "su -c start mi_thermald":
            self.svc_state = "running"
            return ExecutionResult(0, "", "", "fake")
        return ExecutionResult(1, "", "unscripted: " + cmd, "fake")


class TestThermalDaemonTx(unittest.TestCase):
    """thermal 抑制事务（2026-09-27 裁定）：测量窗口 stop mi_thermald，
    restore 回 before 值；非法值与非 adb 执行器结构化拒绝。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = JournalStore(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def _tx(self, executor, work=lambda: {"ok": 1}, specs=("thermal=stopped",)):
        return execute_environment_tx(PLATFORM, list(specs), work,
                                      allow_mutation=True, store=self.store,
                                      executor=executor, lock=FakeLock())

    def test_stop_restore_roundtrip(self):
        ex = FakeAdbThermalExecutor(state="running")
        self.assertEqual(self._tx(ex), {"ok": 1})
        self.assertEqual(ex.svc_state, "running")  # restore 回 before 值
        journal = self.store.load(next(iter(self.store.root.glob("*.json"))).stem)
        self.assertEqual(journal.state, "restored")
        self.assertEqual(journal.mutations[0].controller, "svc.thermal")

    def test_idempotent_when_already_stopped(self):
        ex = FakeAdbThermalExecutor(state="stopped")  # before=stopped → restore 也 stop
        self._tx(ex)
        self.assertEqual(ex.svc_state, "stopped")

    def test_invalid_state_rejected(self):
        ex = FakeAdbThermalExecutor()
        with self.assertRaises(EnvironmentError_) as cm:
            self._tx(ex, specs=("thermal=off",))
        self.assertEqual(cm.exception.code, "env-invalid-request")

    def test_linux_executor_structured_reject(self):
        ex = FakeEnvExecutor()
        # inspect 在事务 try 之外，不适用平台的拒绝以原始 RunnerError 上抛
        # （exit 1 家族，与 env-unknown-controller 同语义）
        with self.assertRaises(RunnerError) as cm:
            self._tx(ex)
        self.assertEqual(cm.exception.code, "env-unsupported-platform")
        self.assertIn("Android", str(cm.exception))

    def test_combined_with_governor(self):
        """锁频 + thermal 抑制同事务（平台 host_requirements 声明路径）。"""
        ex = FakeAdbExecutor(governor="walt")

        class Combined(FakeAdbExecutor, FakeAdbThermalExecutor):
            pass

        combined = Combined.__new__(Combined)
        FakeAdbExecutor.__init__(combined, governor="walt")
        combined.svc_state = "running"
        original_execute = combined.execute

        def dispatch(argv, command_prefix=()):
            cmd = " ".join(str(a) for a in argv)
            if "mi_thermald" in cmd:
                return FakeAdbThermalExecutor.execute(combined, argv, command_prefix)
            return original_execute(argv, command_prefix)

        combined.execute = dispatch
        self._tx(combined, specs=("governor=performance", "thermal=stopped"))
        self.assertEqual(combined.governor, "walt")       # governor 已 restore
        self.assertEqual(combined.svc_state, "running")   # thermal 已 restore

    def test_second_controller_failure_restores_first_mutation(self):
        class Combined(FakeAdbExecutor, FakeAdbThermalExecutor):
            pass

        combined = Combined.__new__(Combined)
        FakeAdbExecutor.__init__(combined, governor="walt")
        combined.svc_state = "running"
        governor_execute = combined.execute

        def dispatch(argv, command_prefix=()):
            cmd = " ".join(str(a) for a in argv)
            if "getprop init.svc.mi_thermald" in cmd:
                return ExecutionResult(0, combined.svc_state + "\n", "", "fake")
            if cmd == "su -c stop mi_thermald":
                return ExecutionResult(1, "", "simulated thermal apply failure", "fake")
            if cmd == "su -c start mi_thermald":
                combined.svc_state = "running"
                return ExecutionResult(0, "", "", "fake")
            return governor_execute(argv, command_prefix)

        combined.execute = dispatch
        with self.assertRaises(EnvironmentError_) as cm:
            self._tx(combined, specs=("governor=performance", "thermal=stopped"))
        self.assertEqual(cm.exception.code, "env-apply-failed")
        self.assertEqual(combined.governor, "walt")
        journal_path = next(iter(self.store.root.glob("*.json")))
        journal = self.store.load(journal_path.stem)
        self.assertEqual(journal.state, "restored")
        self.assertTrue(journal.mutations[1].apply_started)
        self.assertIn("simulated thermal apply failure", journal.mutations[1].apply_error)


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


class RestorePressureExecutor(FakeMultiPolicyAdbExecutor):
    """真实 Android 控制器替身：恢复时注入外部限频或中断。"""

    def __init__(self):
        super().__init__()
        self.cap_active = False
        self.interrupt_restore = False

    def execute(self, argv, command_prefix=()):
        restoring = "cpu_uarch_cpufreq_restore_v1" in " ".join(map(str, argv))
        if restoring and self.interrupt_restore:
            raise KeyboardInterrupt("interrupted during restore")
        result = super().execute(argv, command_prefix)
        if restoring and self.cap_active:
            self.policies["policy7"]["max_khz"] = 2496000
        return result


class TestRestoreDurability(unittest.TestCase):
    """BOARD-A1-THERMAL：重启回读恢复失败，并重放被中断的恢复。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = JournalStore(Path(self.tmp.name))
        self.executor = RestorePressureExecutor()
        self.lock = FakeLock()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, work):
        return execute_environment_tx(
            PLATFORM, ["governor=performance"], work, allow_mutation=True,
            store=self.store, executor=self.executor, lock=self.lock)

    def _reloaded(self):
        fresh = JournalStore(Path(self.tmp.name))
        return fresh, fresh.load(next(fresh.root.glob("*.json")).stem)

    def _cap(self):
        self.executor.cap_active = True
        return {"ok": 14, "failed": 34}

    def test_normal_work_restore_failure_is_durable_and_retryable(self):
        with self.assertRaises(EnvironmentError_) as caught:
            self._run(self._cap)
        self.assertEqual(caught.exception.code, "env-restore-failed")
        fresh, journal = self._reloaded()
        self.assertEqual(journal.state, "restore-failed")
        self.assertTrue(self.lock.released)
        self.assertEqual(self.executor.policies["policy7"]["governor"], "powersave")
        with self.assertRaises(EnvironmentError_) as blocked:
            self._run(lambda: self.fail("unfinished recovery must block work"))
        self.assertEqual(blocked.exception.code, "env-unfinished-tx")
        self.executor.cap_active = False
        restore_transaction(journal.tx_id, PLATFORM, store=fresh,
                            executor=self.executor, lock=FakeLock())
        self.assertEqual(fresh.load(journal.tx_id).state, "restored")
        self.assertEqual(fresh.unfinished(), [])
        self.assertEqual(self.executor.policies["policy7"]["max_khz"], 2745600)

    def test_explicit_restore_failure_is_durable_after_restart(self):
        with self.assertRaises(EnvironmentError_):
            self._run(self._cap)
        fresh, journal = self._reloaded()
        # 从独立的 applied 现场开始，不能让正常路径已存的 restore-failed
        # 掩盖显式 restore 漏 save；before/after 来自真实控制器事务。
        journal.state = "applied"
        fresh.save(journal)
        with self.assertRaises(EnvironmentError_):
            restore_transaction(journal.tx_id, PLATFORM, store=fresh,
                                executor=self.executor, lock=FakeLock())
        self.assertEqual(self._reloaded()[1].state, "restore-failed")

    def test_interrupted_restore_can_resume_from_persisted_restoring(self):
        def failed_work():
            self.executor.interrupt_restore = True
            raise RuntimeError("work failed first")
        with self.assertRaises(KeyboardInterrupt):
            self._run(failed_work)
        fresh, journal = self._reloaded()
        self.assertEqual(journal.state, "restoring")
        self.executor.interrupt_restore = False
        restore_transaction(journal.tx_id, PLATFORM, store=fresh,
                            executor=self.executor, lock=FakeLock())
        self.assertEqual(fresh.load(journal.tx_id).state, "restored")

    def test_reconcile_reloads_failure_and_can_finish_after_cap_clears(self):
        from runner.environment import reconcile_unfinished
        with self.assertRaises(EnvironmentError_):
            self._run(self._cap)
        fresh, journal = self._reloaded()
        pending = reconcile_unfinished(PLATFORM, store=fresh, executor=self.executor)
        self.assertEqual([j.state for j in pending], ["restore-failed"])
        self.assertEqual(fresh.load(journal.tx_id).state, "restore-failed")
        self.executor.cap_active = False
        self.assertEqual(reconcile_unfinished(PLATFORM, store=fresh,
                                             executor=self.executor), [])
        self.assertEqual(fresh.load(journal.tx_id).state, "restored")


    def test_created_journal_closes_without_device_mutation(self):
        from runner.environment import reconcile_unfinished
        journal = self.store.new("fake-01")
        self.store.save(journal)
        before = {p: dict(v) for p, v in self.executor.policies.items()}
        self.assertEqual(reconcile_unfinished(PLATFORM, store=self.store,
                                             executor=self.executor), [])
        self.assertEqual(self.store.load(journal.tx_id).state, "apply-failed")
        self.assertEqual(self.executor.policies, before)
        restore_transaction(journal.tx_id, PLATFORM, store=self.store,
                            executor=self.executor, lock=FakeLock())
        self.assertEqual(self.store.load(journal.tx_id).state, "apply-failed")


if __name__ == "__main__":
    unittest.main()
