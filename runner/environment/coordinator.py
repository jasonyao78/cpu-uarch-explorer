# SPDX-License-Identifier: Apache-2.0
"""事务协调器：锁 → journal(before) → apply → verify → work() → 逆序 restore。

GB10 模型重实现的接线层（OI-9 裁定）。互斥两层：journal 未完成事务
阻塞（单操作者假设的硬互斥）+ 目标机 flock 劝告性检查（跨工具最佳
努力；持有期间防止别的 shell 改 governor）。中断（SIGINT）经
KeyboardInterrupt 进入恢复路径后重抛；SIGTERM 不转换（已知简化）。

锁实现：local = fcntl.flock 本机文件；ssh = 后台 ssh + 远端 flock
持有进程（ssh 断连 → 远端 SIGHUP → 锁释放）。锁接口可注入（测试用
假锁）。
"""

from __future__ import annotations

import fcntl
import subprocess
from pathlib import Path

from ..errors import RunnerError
from ..executor import make_executor
from .controllers import make_controller
from .journal import Journal, JournalStore, Mutation, default_store


class EnvironmentError_(RunnerError):
    """环境事务类错误（退出码 1 家族）。"""


class _LocalFlock:
    def __init__(self, root: Path):
        self._root = Path(root)
        self._f = None

    def acquire(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        self._f = open(self._root / "mutation.lock", "w", encoding="utf-8")
        try:
            fcntl.flock(self._f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._f.close()
            self._f = None
            raise EnvironmentError_("env-locked", "local mutation lock held by another process")

    def release(self) -> None:
        if self._f is not None:
            fcntl.flock(self._f.fileno(), fcntl.LOCK_UN)
            self._f.close()
            self._f = None


class _RemoteFlock:
    """后台 ssh 持有远端 flock：acquire 读回执行确认；-n 非阻塞，被占即失败。"""

    def __init__(self, host: str, remote_root: str):
        self._host = host
        self._statedir = f"{remote_root}/.local-state/cpu-uarch-explorer"
        self._proc = None

    def acquire(self) -> None:
        script = (f"mkdir -p {self._statedir} && "
                  f"flock -n {self._statedir}/mutation.lock -c 'echo ACQUIRED; sleep 86400'")
        self._proc = subprocess.Popen(
            ["ssh", "-o", "BatchMode=yes", self._host, script],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        line = self._proc.stdout.readline().strip()
        if line != "ACQUIRED":
            self._proc.terminate()
            self._proc = None
            raise EnvironmentError_("env-locked", f"remote mutation lock held (host {self._host})")

    def release(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            self._proc.wait(timeout=10)
            self._proc = None


def _default_lock(platform: dict):
    target = platform.get("target", {})
    if target.get("transport", "local") == "ssh":
        return _RemoteFlock(target["ssh_host"], target.get("ssh_remote_root", "~"))
    from .journal import default_store  # 复用私有存储根推导
    return _LocalFlock(default_store().root)


def _apply_all(executor, journal: Journal, specs: list[str]) -> None:
    journal.transition("applying")
    for spec in specs:
        controller, requested = make_controller(spec)
        before = controller.inspect(executor)  # 变更前实际值：restore 的依据
        journal.mutations.append(Mutation(controller=controller.key, requested=requested, before=before))
        try:
            controller.apply(executor, requested)
            after = controller.inspect(executor)
        except RunnerError as e:
            journal.mutations[-1].apply_error = str(e)
            journal.transition("apply-failed")
            # 统一提升为环境事务错误家族（code/message 保留），CLI 与测试
            # 面对单一异常类型
            raise EnvironmentError_(e.code, str(e)) from e
        journal.mutations[-1].after = after
        if not controller.verify(executor, requested):
            journal.transition("apply-failed")
            raise EnvironmentError_("env-verify-failed",
                                    f"{controller.key}: requested {requested!r} but actual {after!r}")
    journal.transition("applied")


def _restore_all(executor, journal: Journal) -> None:
    journal.transition("restoring")
    failures = []
    for m in reversed(journal.mutations):  # 逆序恢复（GB10 模型）
        if not m.after:
            continue  # apply 未成功的不碰
        controller, _ = make_controller(f"{m.controller.split('.')[-1]}={m.requested}")
        try:
            controller.apply(executor, m.before)
        except RunnerError as e:
            failures.append(f"{m.controller}: {e}")
    journal.transition("restored" if not failures else "restore-failed")
    if failures:
        raise EnvironmentError_("env-restore-failed", " | ".join(failures))


def execute_environment_tx(platform: dict, specs: list[str], work, *,
                           allow_mutation: bool = False,
                           store: JournalStore | None = None,
                           lock=None, executor=None, note: str = "") -> dict:
    """应用 specs → 执行 work() → 恢复。返回 run 汇总（work 的返回值）。

    门控：--allow-mutation 缺失直接拒绝（CLI 负责传）；存在未完成事务
    直接拒绝（journal 互斥）。任何路径都保证 journal 落盘到终态。"""
    if not allow_mutation:
        raise EnvironmentError_("env-mutation-not-allowed",
                                "host mutation requires explicit --allow-mutation")
    store = store or default_store()
    unfinished = store.unfinished()
    if unfinished:
        raise EnvironmentError_("env-unfinished-tx",
                                f"unfinished transactions exist: {[j.tx_id for j in unfinished]}"
                                " — resolve with: runner.cli env restore --tx <id>")
    executor = executor or make_executor(platform)
    lock = lock if lock is not None else _default_lock(platform)
    journal = store.new(platform.get("target", {}).get("target_id", "unknown"), note=note)

    lock.acquire()
    try:
        store.save(journal)
        try:
            _apply_all(executor, journal, specs)
        except BaseException:
            store.save(journal)  # apply-failed 终态必须落盘，否则 unfinished 永久阻塞
            raise
        store.save(journal)
        try:
            result = work()
        except BaseException:
            store.save(journal)
            try:
                _restore_all(executor, journal)
            finally:
                store.save(journal)
            raise
        _restore_all(executor, journal)
        store.save(journal)
        return result
    finally:
        lock.release()


def restore_transaction(tx_id: str, platform: dict, *, store: JournalStore | None = None,
                        executor=None) -> None:
    """崩溃后人工重放：按 journal 的 before 值逆序恢复（幂等：仅处理
    after 已写入的 mutation；已 restored 的 journal 直接返回）。"""
    store = store or default_store()
    journal = store.load(tx_id)
    if journal.state == "restored":
        return
    executor = executor or make_executor(platform)
    lock = _default_lock(platform)
    lock.acquire()
    try:
        _restore_all(executor, journal)
        store.save(journal)
    finally:
        lock.release()


def reconcile_unfinished(platform: dict, *, store: JournalStore | None = None,
                         executor=None) -> list[Journal]:
    """启动前调和：检测未完成事务并**自动完成恢复**（任务书 §2.1 中断恢复
    实证——kill -INT 留下的 applied/applying 事务在下次运行前被 restore，
    而不是永远硬拒绝）。恢复失败的事务保持未完结并返回，由调用方拒绝运行。

    状态语义：applied=中断于测量中（直接逆序恢复）；applying=中断于
    apply 中（先落 applied 标记再过恢复路径，after 为空的 mutation 不动）。"""
    store = store or default_store()
    executor = executor or make_executor(platform)
    lock = _default_lock(platform)
    remaining: list[Journal] = []
    for journal in store.unfinished():
        lock.acquire()
        try:
            if journal.state == "applying":
                journal.transition("applied")  # 已过白名单：applying→applied
            _restore_all(executor, journal)
            store.save(journal)
        except EnvironmentError_:
            store.save(journal)
            remaining.append(journal)
        finally:
            lock.release()
    return remaining


def specs_from_host_requirements(host_requirements: dict) -> list[str]:
    """平台/实验声明的 host_requirements（{"cpufreq.governor": "performance"}）
    → coordinator spec 列表（"governor=performance"）。未知键在 make_controller
    处报错——声明即校验。"""
    return [f"{key.split('.')[-1]}={value}" for key, value in host_requirements.items()]
