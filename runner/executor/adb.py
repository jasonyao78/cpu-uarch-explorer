# SPDX-License-Identifier: Apache-2.0
"""ADB 执行器（Transport=adb / Executor=native；Android 平台接入）。

与 LocalExecutor/SshExecutor 同一 execute(argv, command_prefix) 契约：
经 adb shell 在设备上 cd 到工作目录后执行探针命令，stdout/stderr/
returncode 语义一致；raw_command 记录完整 adb 命令行。

设备选择约定：单设备时 adb 自动命中（serial 不入库——设备标识，铁律 2
匿名化）；多设备时用 adb 原生 ANDROID_SERIAL 环境变量。工作目录默认
/data/local/tmp（shell 可写，重启保留）。

sh 方言：Android 的 /system/bin/sh 为 toybox，POSIX 子集——采集脚本只
用 for/cat/echo/参数展开（已验证 2026-09-27 K70 Pro 未 root 可读）。
"""

from __future__ import annotations

import shlex
import subprocess

from .local import ExecutionResult

_DEFAULT_WORKDIR = "/data/local/tmp"


class AdbExecutor:
    def __init__(self, serial: str | None = None, workdir: str = _DEFAULT_WORKDIR,
                 timeout_s: float = 600.0):
        self._serial = serial
        self._workdir = workdir
        self._timeout_s = timeout_s

    def _base(self) -> list[str]:
        # 设备序列号不进平台配置/仓库；多设备场景用 ANDROID_SERIAL（adb 原生约定）
        return ["adb"] + (["-s", self._serial] if self._serial else []) + ["shell"]

    def execute(self, argv: list[str], command_prefix: tuple[str, ...] = ()) -> ExecutionResult:
        """在设备上执行一条命令（cwd = workdir），语义同 LocalExecutor：
        永不抛异常，超时/设备离线/命令失败都收敛为 ExecutionResult。"""
        remote_cmd = " ".join(shlex.quote(str(a))
                              for a in list(command_prefix) + [str(a) for a in argv])
        # cd 容错：工作目录可能尚未创建（deploy 才 mkdir）——采集脚本全用
        # 绝对路径，cd 失败退回默认目录不影响正确性；探针场景 deploy 先行建目录
        shell_line = f"cd {shlex.quote(self._workdir)} 2>/dev/null; exec {remote_cmd}"
        cmd = self._base() + [shell_line]
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

    def system_info(self) -> dict:
        """设备环境采集：os_version=Android 版本（getprop）、kernel=uname -r、
        compiler=unknown（设备无工具链——不编造，measurement-discipline）。"""
        res = self.execute(["sh", "-c", "getprop ro.build.version.release; uname -r"])
        if res.returncode != 0:
            return {"os_version": "unknown", "kernel": "unknown", "compiler": "unknown"}
        lines = res.stdout.splitlines()
        return {
            "os_version": f"Android {lines[0].strip()}" if lines and lines[0].strip() else "unknown",
            "kernel": lines[1].strip() if len(lines) > 1 else "unknown",
            "compiler": "unknown",
        }

    def freq_snapshot(self, cpu_hint: str) -> dict | None:
        """设备频率快照：scaling_cur_freq 在 Android 上常限 root，回退
        cpuinfo_cur_freq（shell 可读）；两者皆失败返回 None。"""
        res = self.execute(["sh", "-c",
                            f"cat /sys/devices/system/cpu/cpu{cpu_hint or '0'}/cpufreq/scaling_cur_freq "
                            f"2>/dev/null || cat /sys/devices/system/cpu/cpu{cpu_hint or '0'}/cpufreq/cpuinfo_cur_freq"])
        if res.returncode != 0:
            return None
        try:
            return {"khz": int(res.stdout.strip()), "source": "cpufreq (scaling or cpuinfo)"}
        except ValueError:
            return None
