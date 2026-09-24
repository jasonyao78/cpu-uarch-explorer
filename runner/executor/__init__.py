# SPDX-License-Identifier: Apache-2.0
"""执行器选择与工厂（ADR-0006 §1 正交分解：transport 决定执行通道）。

唯一选择点：主流程只跟 execute() 契约交互，新增传输方式在此登记。
平台/主机名特判不允许扩散到 engine（2026-09-25 Xeon 接入任务验收
标准第 2 条：主流程零特判）。
"""

from __future__ import annotations

from ..errors import RunnerError
from .local import LocalExecutor
from .ssh import SshExecutor


def make_executor(platform: dict):
    """按 platform.target.transport 构造执行器：local → LocalExecutor；
    ssh → SshExecutor（host/remote_root 取 target 扩展字段，登记于
    runner/schema/README.md）。"""
    transport = platform.get("target", {}).get("transport", "local")
    if transport == "local":
        return LocalExecutor()
    if transport == "ssh":
        target = platform["target"]
        host = target.get("ssh_host")
        if not host:
            raise RunnerError(
                "config-invalid",
                "transport=ssh requires target.ssh_host（ssh config 别名；"
                "真实地址见 data/private/hosts.md，禁止入库）")
        return SshExecutor(host, target.get("ssh_remote_root", "~"))
    raise RunnerError("config-invalid", f"unsupported transport: {transport!r}")


__all__ = ["LocalExecutor", "SshExecutor", "make_executor"]
