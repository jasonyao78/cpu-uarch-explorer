# SPDX-License-Identifier: Apache-2.0
"""SSH 远程执行器（Transport=ssh / Executor=native；2026-09-25 Xeon 接入任务）。

与 LocalExecutor 同一 execute(argv, command_prefix) 契约：经 ssh 在目标机
cd 到远端仓库根后执行探针命令，stdout/stderr/returncode 语义与本地完全
一致；raw_command 记录完整 ssh 命令行（requested/actual 双记录原则）。

配置与安全约定（铁律 2：设备匿名化）：
- host 是 ssh config 别名（如 xeon-8481c-01），真实 IP 只存在于本机
  ~/.ssh/config 与 data/private/hosts.md，平台配置与 git 仓永不出现。
- BatchMode=yes：任何交互提示（密码 / host key）直接失败——执行器不
  等人；失败收敛为 returncode=None，由上层记结构化 failure（与本地
  执行器相同的"永不抛异常"契约）。
- argv 经 shlex.quote 进入远端 shell：探针参数含空格或 shell 元字符
  不会被二次解释（Probe ABI 输出契约的安全前提）。
"""

from __future__ import annotations

import shlex
import subprocess

from .local import ExecutionResult


class SshExecutor:
    def __init__(self, host: str, remote_root: str, timeout_s: float = 600.0):
        self._host = host
        self._remote_root = remote_root
        self._timeout_s = timeout_s

    def execute(self, argv: list[str], command_prefix: tuple[str, ...] = ()) -> ExecutionResult:
        """在目标机执行一条命令（远端 cwd = remote_root），语义同 LocalExecutor：
        永不抛异常，超时 / 无法启动 / ssh 失败都收敛为 ExecutionResult。"""
        remote_cmd = " ".join(shlex.quote(str(a))
                              for a in list(command_prefix) + [str(a) for a in argv])
        shell_line = f"cd {self._cd_target()} && exec {remote_cmd}"
        cmd = ["ssh", "-o", "BatchMode=yes", self._host, shell_line]
        raw_command = " ".join(shlex.quote(c) for c in cmd)
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

    def _cd_target(self) -> str:
        """构造远端 cd 目标：~ 必须保持不引用——单引号内的 ~ 不会展开，
        cd '~' 会去找名为 "~" 的字面目录（2026-09-25 测试抓住的真实缺陷）。"""
        if self._remote_root == "~":
            return "~"
        if self._remote_root.startswith("~/"):
            return "~/" + shlex.quote(self._remote_root[2:])
        return shlex.quote(self._remote_root)

    def system_info(self) -> dict:
        """在目标机采集 os_version/kernel/compiler——run-record.environment
        必须描述目标机而非本机（ssh 平台的数据是在远端测的）。采集失败时
        返回 unknown 值，不编造（measurement-discipline）。"""
        res = self.execute(["sh", "-c", "uname -s; uname -r; cc --version 2>/dev/null | head -1"])
        if res.returncode != 0:
            return {"os_version": "unknown", "kernel": "unknown", "compiler": "unknown"}
        lines = res.stdout.splitlines()
        return {
            "os_version": lines[0].strip() if len(lines) > 0 else "unknown",
            "kernel": lines[1].strip() if len(lines) > 1 else "unknown",
            "compiler": lines[2].strip() if len(lines) > 2 else "unknown",
        }
