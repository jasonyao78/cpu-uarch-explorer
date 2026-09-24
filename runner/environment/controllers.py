# SPDX-License-Identifier: Apache-2.0
"""变更控制器：声明式 spec（governor=performance）→ 目标机状态操作。

控制器只做四件事：inspect（读实际值）/ validate / apply / verify。
apply 经执行器通道执行，可能因 sudo 权限失败——**非交互通道不挂起等
密码**，失败返回结构化提示（RunnerError），journal 记录 before 值后
安全退出（系统未被改变，无需 restore）。

CpufreqGovernorController：写全部 CPU 的 scaling_governor（测量可能
迁移或扩核；单核写会留半新半旧状态）。requires_privilege 为 True——
CLI 层强制 --allow-mutation 门控。
"""

from __future__ import annotations

from typing import Protocol

from ..errors import RunnerError


class Controller(Protocol):
    key: str
    requires_privilege: bool

    def inspect(self, executor) -> str: ...
    def apply(self, executor, requested: str) -> str: ...  # 成功返回 ""，失败抛 RunnerError


class CpufreqGovernorController:
    """Linux cpufreq governor 变更（第一个受控项，2026-09-25 讨论裁定）。"""
    key = "cpufreq.governor"
    requires_privilege = True
    _GOVERNOR = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"

    def inspect(self, executor) -> str:
        res = executor.execute(["cat", self._GOVERNOR])
        if res.returncode != 0:
            raise RunnerError("env-inspect-failed",
                              f"cannot read {self._GOVERNOR}: {res.stderr.strip()[:120]}")
        return res.stdout.strip()

    def validate(self, requested: str) -> None:
        if not requested or any(ch in requested for ch in "/ ;|&$`"):
            raise RunnerError("env-invalid-request", f"unsafe governor value: {requested!r}")

    def apply(self, executor, requested: str) -> str:
        self.validate(requested)
        # 写全部 CPU：单核写会留下半新半旧的系统状态。
        script = (f"for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do "
                  f"echo {requested} | sudo -n tee $c > /dev/null || exit 1; done")
        res = executor.execute(["sudo", "-n", "sh", "-c", script])
        if res.returncode != 0:
            raise RunnerError(
                "env-apply-failed",
                f"governor apply failed: {res.stderr.strip()[:160]}"
                " | 非交互 sudo 不可用时的出路：① sudoers NOPASSWD 授权"
                "（echo 'michael ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/devices/system/cpu/*/cpufreq/scaling_governor'"
                " | sudo tee /etc/sudoers.d/cpu-uarch-probe）② 手动执行上述 for 循环后重试")
        return ""

    def verify(self, executor, expected: str) -> bool:
        try:
            return self.inspect(executor) == expected
        except RunnerError:
            return False


def make_controller(spec: str) -> tuple[Controller, str]:
    """spec 'governor=performance' → (controller, requested)。新增受控项
    在此登记——与 make_executor 同一"唯一选择点"纪律。"""
    key, _, value = spec.partition("=")
    if key == "governor":
        return CpufreqGovernorController(), value
    raise RunnerError("env-unknown-controller", f"unsupported env spec: {spec!r} (supported: governor=<name>)")
