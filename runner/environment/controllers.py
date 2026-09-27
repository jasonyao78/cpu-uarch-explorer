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
    """Linux cpufreq governor 变更（第一个受控项，2026-09-25 讨论裁定）。

    提权通道按执行器分流：Linux = sudoers 白名单包装脚本（最小权限）；
    Android = su -c 直写 sysfs（KernelSU LKM，无白名单脚本概念——validate
    已拦截 shell 元字符，注入安全）。"""
    key = "cpufreq.governor"
    requires_privilege = True
    _GOVERNOR = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    _ANDROID_WRITE = (
        "for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do "
        "echo {gov} > $c 2>/dev/null || exit 1; done"
    )

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
        from ..executor.adb import AdbExecutor  # 延迟导入：避免 controllers→executor 环
        if isinstance(executor, AdbExecutor):
            res = executor.execute(["su", "-c", self._ANDROID_WRITE.format(gov=requested)])
            if res.returncode != 0:
                raise RunnerError(
                    "env-apply-failed",
                    f"governor apply failed: {res.stderr.strip()[:160]}"
                    " | Android 出路：确认 KernelSU Root 生效且授权 shell（adb shell su -c id）")
            return ""
        # 经 sudoers 单命令白名单授权的包装脚本（最小权限：免密 sudo 仅限此
        # 脚本；脚本内有 performance/powersave 参数白名单与 root 属主加固——
        # 部署步骤见 docs/runbooks/xeon-governor-lock.md，人工一次性完成）。
        res = executor.execute(["sudo", "-n", "/usr/local/bin/cpu-uarch-set-governor", requested])
        if res.returncode != 0:
            raise RunnerError(
                "env-apply-failed",
                f"governor apply failed: {res.stderr.strip()[:160]}"
                " | 非交互 sudo 不可用时的出路：① 按 runbook 部署包装脚本 + sudoers"
                " 白名单（docs/runbooks/xeon-governor-lock.md 路径 A）"
                " ② 路径 B：人工执行 governor 切换后重试")
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
    if key == "thermal":
        return SvcThermalDaemonController(), value
    raise RunnerError("env-unknown-controller", f"unsupported env spec: {spec!r} (supported: governor=<name>, thermal=stopped|running)")


class SvcThermalDaemonController:
    """Android 温控守护抑制（2026-09-27 热管理层系统分析裁定）：测量窗口内
    stop mi_thermald（restore 时 start），防止其动态下调 scaling_max 污染
    锁频测量——governor 只锁到 scaling_max，锁不住守护对 cap 本身的调节。

    实测依据：stop 后重启 mi_thermald 把 policy7 scaling_max 2745600→3110400
    （实锤其为 scaling_max 活动控制者）；3302400 为 boost 频率（miperf perf
    lock 管辖），stop 守护 + performance 负载下 cur_freq 仍封顶 2745600。

    安全窗口：仅分钟级微基准且 Tj<95°C（当前实测负载 Tj 78-84°C）；
    长跑 benchmark（GB6/SPEC）禁止抑制——必须留热保护。"""
    key = "svc.thermal"
    requires_privilege = True
    _SVC = "mi_thermald"

    def _require_adb(self, executor):
        from ..executor.adb import AdbExecutor  # 延迟导入：避免 controllers→executor 环
        if not isinstance(executor, AdbExecutor):
            raise RunnerError("env-unsupported-platform",
                              "svc.thermal only supported on Android (adb executor)")
        return executor

    def inspect(self, executor) -> str:
        res = self._require_adb(executor).execute(["su", "-c", f"getprop init.svc.{self._SVC}"])
        if res.returncode != 0:
            raise RunnerError("env-inspect-failed",
                              f"cannot read {self._SVC} state: {res.stderr.strip()[:120]}")
        return res.stdout.strip()

    def validate(self, requested: str) -> None:
        if requested not in ("stopped", "running"):
            raise RunnerError("env-invalid-request",
                              f"unsupported thermal daemon state: {requested!r} (stopped|running)")

    def apply(self, executor, requested: str) -> str:
        self.validate(requested)
        action = "stop" if requested == "stopped" else "start"
        res = self._require_adb(executor).execute(["su", "-c", f"{action} {self._SVC}"])
        if res.returncode != 0:
            raise RunnerError("env-apply-failed",
                              f"thermal daemon {action} failed: {res.stderr.strip()[:160]}")
        return ""

    def verify(self, executor, expected: str) -> bool:
        try:
            return self.inspect(executor) == expected
        except RunnerError:
            return False
