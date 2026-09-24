# SPDX-License-Identifier: Apache-2.0
"""本地 subprocess 执行器（Transport=local / Executor=native）。

调度控制通过 command_prefix 实现（如 macOS 的 `taskpolicy -b` 置
BACKGROUND QoS → E-core；OI-5 实测 QoS→P/E 分流可靠生效）。requested
控制值与实际执行命令都进入 run 记录（requested/actual 双记录原则）。
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    returncode: int | None  # None = 超时被杀
    stdout: str
    stderr: str
    raw_command: str
    timed_out: bool = False


class LocalExecutor:
    def __init__(self, timeout_s: float = 600.0):
        self._timeout_s = timeout_s

    def execute(self, argv: list[str], command_prefix: tuple[str, ...] = ()) -> ExecutionResult:
        """同步执行一条命令（可选控制前缀，如 taskpolicy -b），捕获 stdout/stderr。
        永不抛异常：超时/无法启动也收敛为 ExecutionResult（returncode=None），
        由上层映射为结构化 failure——执行层不决定语义。"""
        cmd = list(command_prefix) + [str(a) for a in argv]
        raw_command = " ".join(cmd)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self._timeout_s)
            return ExecutionResult(returncode=proc.returncode, stdout=proc.stdout,
                                   stderr=proc.stderr, raw_command=raw_command)
        except subprocess.TimeoutExpired as e:
            return ExecutionResult(returncode=None,
                                   stdout=(e.stdout or "") if isinstance(e.stdout, str) else "",
                                   stderr=(e.stderr or "") if isinstance(e.stderr, str) else "",
                                   raw_command=raw_command, timed_out=True)
        except OSError as e:
            return ExecutionResult(returncode=None, stdout="", stderr=str(e),
                                   raw_command=raw_command)

    def system_info(self) -> dict:
        """本机环境采集：os/kernel/compiler（LocalExecutor 场景），供
        run-record.environment 使用；与 SshExecutor.system_info 同名字段、
        同一口径，engine 不关心数据来自哪一侧。"""
        from ..records import local_system_info
        return local_system_info()

    def freq_snapshot(self, cpu_hint: str) -> dict | None:
        """本机频率快照：Linux 读 cpufreq sysfs；macOS 无用户态频率接口
        （v0.3 §2.1 已知约束）返回 None——engine 据此省略字段，不编造。"""
        path = f"/sys/devices/system/cpu/cpu{cpu_hint or '0'}/cpufreq/scaling_cur_freq"
        try:
            with open(path, "r", encoding="utf-8") as f:
                return {"khz": int(f.read().strip()), "source": "scaling_cur_freq"}
        except OSError:
            return None
