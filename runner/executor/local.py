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
