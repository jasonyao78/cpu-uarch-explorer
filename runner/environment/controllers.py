# SPDX-License-Identifier: Apache-2.0
"""变更控制器：声明式 spec（governor=performance）→ 目标机状态操作。

控制器只做四件事：inspect（读实际值）/ validate / apply / verify。
apply 经执行器通道执行，可能因 sudo 权限失败——**非交互通道不挂起等
密码**，失败返回结构化提示（RunnerError），journal 记录 before 值后
安全退出（系统未被改变，无需 restore）。

CpufreqGovernorController：Linux 保留包装脚本接口；Android 以 policy 为
单位采集 governor/min/max 的完整 before 状态，只改变 governor，并在恢复
时逐 policy 回写原值（单读 cpu0 会掩盖半新半旧状态）。requires_privilege
为 True——CLI 层强制 --allow-mutation 门控。
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from ..errors import RunnerError


class Controller(Protocol):
    key: str
    requires_privilege: bool

    def inspect(self, executor) -> str: ...
    def validate(self, requested: str) -> None: ...
    def apply(self, executor, requested: str) -> str: ...  # 成功返回 ""，失败抛 RunnerError


class CpufreqGovernorController:
    """Linux cpufreq governor 变更（第一个受控项，2026-09-25 讨论裁定）。

    提权通道按执行器分流：Linux = sudoers 白名单包装脚本（最小权限）；
    Android = su -c 直写 sysfs（KernelSU LKM，无白名单脚本概念）。Android
    inspect 返回 canonical JSON；该 JSON 只供 journal 的内部 restore 路径，
    用户请求仍是经过白名单校验的 governor 名。"""
    key = "cpufreq.governor"
    requires_privilege = True
    _GOVERNOR = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    _ANDROID_WRITE = (
        "for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do "
        "echo {gov} > $c 2>/dev/null || exit 1; done"
    )
    _ANDROID_INSPECT = (
        ": cpu_uarch_cpufreq_inspect_v1; "
        "for p in /sys/devices/system/cpu/cpufreq/policy*; do "
        "n=${p##*/}; g=$(cat $p/scaling_governor) || exit 1; "
        "lo=$(cat $p/scaling_min_freq) || exit 1; "
        "hi=$(cat $p/scaling_max_freq) || exit 1; "
        "printf '%s|%s|%s|%s\\n' \"$n\" \"$g\" \"$lo\" \"$hi\"; done"
    )

    @staticmethod
    def _valid_governor(value: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z0-9_-]+", value))

    @classmethod
    def _parse_android_state(cls, value: str) -> dict[str, dict[str, int | str]]:
        try:
            raw = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise RunnerError("env-invalid-request", "invalid cpufreq restore state JSON") from exc
        if not isinstance(raw, dict) or not raw:
            raise RunnerError("env-invalid-request", "cpufreq restore state must be a non-empty object")
        state: dict[str, dict[str, int | str]] = {}
        for policy, fields in raw.items():
            if not re.fullmatch(r"policy\d+", str(policy)) or not isinstance(fields, dict):
                raise RunnerError("env-invalid-request", f"invalid cpufreq policy state: {policy!r}")
            governor = fields.get("governor")
            min_khz = fields.get("min_khz")
            max_khz = fields.get("max_khz")
            if not isinstance(governor, str) or not cls._valid_governor(governor):
                raise RunnerError("env-invalid-request", f"unsafe governor value: {governor!r}")
            if (isinstance(min_khz, bool) or not isinstance(min_khz, int) or min_khz <= 0 or
                    isinstance(max_khz, bool) or not isinstance(max_khz, int) or max_khz <= 0 or
                    min_khz > max_khz):
                raise RunnerError("env-invalid-request", f"invalid cpufreq limits for {policy}")
            state[str(policy)] = {"governor": governor,
                                  "min_khz": min_khz, "max_khz": max_khz}
        return state

    def _inspect_android(self, executor) -> str:
        res = executor.execute(["su", "-c", self._ANDROID_INSPECT])
        if res.returncode != 0:
            raise RunnerError("env-inspect-failed",
                              f"cannot inspect Android cpufreq policies: {res.stderr.strip()[:160]}")
        state: dict[str, dict[str, int | str]] = {}
        for line in res.stdout.splitlines():
            parts = line.strip().split("|")
            if len(parts) != 4 or not re.fullmatch(r"policy\d+", parts[0]):
                raise RunnerError("env-inspect-failed", f"malformed cpufreq policy row: {line!r}")
            policy, governor, min_text, max_text = parts
            if not self._valid_governor(governor) or not min_text.isdigit() or not max_text.isdigit():
                raise RunnerError("env-inspect-failed", f"malformed cpufreq policy row: {line!r}")
            state[policy] = {"governor": governor,
                             "min_khz": int(min_text), "max_khz": int(max_text)}
        if not state:
            raise RunnerError("env-inspect-failed", "no Android cpufreq policies found")
        return json.dumps(state, sort_keys=True, separators=(",", ":"))

    def inspect(self, executor) -> str:
        from ..executor.adb import AdbExecutor
        if isinstance(executor, AdbExecutor):
            return self._inspect_android(executor)
        res = executor.execute(["cat", self._GOVERNOR])
        if res.returncode != 0:
            raise RunnerError("env-inspect-failed",
                              f"cannot read {self._GOVERNOR}: {res.stderr.strip()[:120]}")
        return res.stdout.strip()

    def validate(self, requested: str) -> None:
        if requested.startswith("{"):
            self._parse_android_state(requested)
            return
        if not self._valid_governor(requested):
            raise RunnerError("env-invalid-request", f"unsafe governor value: {requested!r}")

    def apply(self, executor, requested: str) -> str:
        self.validate(requested)
        from ..executor.adb import AdbExecutor  # 延迟导入：避免 controllers→executor 环
        if isinstance(executor, AdbExecutor):
            if requested.startswith("{"):
                target = self._parse_android_state(requested)
                current = self._parse_android_state(self._inspect_android(executor))
                if set(target) != set(current):
                    raise RunnerError("env-apply-failed",
                                      "cpufreq policy set changed since transaction start")
                commands = [": cpu_uarch_cpufreq_restore_v1"]
                for policy in sorted(target, key=lambda p: int(p.removeprefix("policy"))):
                    wanted = target[policy]
                    present = current[policy]
                    base = f"/sys/devices/system/cpu/cpufreq/{policy}"
                    limit_writes = [("scaling_min_freq", wanted["min_khz"]),
                                    ("scaling_max_freq", wanted["max_khz"])]
                    if wanted["min_khz"] > present["max_khz"]:
                        limit_writes.reverse()
                    for field, value in limit_writes:
                        commands.append(f"echo {value} > {base}/{field} || exit 1")
                    commands.append(
                        f"echo {wanted['governor']} > {base}/scaling_governor || exit 1")
                script = "; ".join(commands)
            else:
                script = self._ANDROID_WRITE.format(gov=requested)
            res = executor.execute(["su", "-c", script])
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
            actual = self.inspect(executor)
            from ..executor.adb import AdbExecutor
            if isinstance(executor, AdbExecutor):
                state = self._parse_android_state(actual)
                if expected.startswith("{"):
                    return state == self._parse_android_state(expected)
                return all(fields["governor"] == expected for fields in state.values())
            return actual == expected
        except RunnerError:
            return False


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


_CONTROLLERS = {
    "governor": CpufreqGovernorController,
    "cpufreq.governor": CpufreqGovernorController,
    "thermal": SvcThermalDaemonController,
    "svc.thermal": SvcThermalDaemonController,
}


def controller_from_key(key: str) -> Controller:
    """Resolve both CLI aliases and durable canonical journal keys."""
    try:
        return _CONTROLLERS[key]()
    except KeyError as exc:
        raise RunnerError(
            "env-unknown-controller",
            f"unsupported environment controller: {key!r}") from exc


def make_controller(spec: str) -> tuple[Controller, str]:
    """Parse ``alias=value`` while journals retain each controller's key."""
    key, sep, value = spec.partition("=")
    if not sep:
        raise RunnerError("env-invalid-request", f"environment spec lacks '=': {spec!r}")
    return controller_from_key(key), value
