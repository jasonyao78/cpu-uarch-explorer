# SPDX-License-Identifier: Apache-2.0
"""Read-only Android measurement-state collection and pure output parsers.

The collector deliberately does not try to make the device quiet. It records
the state that can invalidate a latency block; mutation belongs to environment
controllers and is journaled separately. Required command or parse failures are
fatal so a run cannot silently lose its environmental evidence.
"""

from __future__ import annotations

import re

from ..errors import RunnerError
from ..executor.adb import AdbExecutor


_CPUFREQ_SCRIPT = (
    ": cpu_uarch_state_cpufreq_v1; "
    "for p in /sys/devices/system/cpu/cpufreq/policy*; do "
    "n=${p##*/}; g=$(cat $p/scaling_governor) || exit 1; "
    "lo=$(cat $p/scaling_min_freq) || exit 1; "
    "hi=$(cat $p/scaling_max_freq) || exit 1; "
    "cur=$(cat $p/scaling_cur_freq) || exit 1; "
    "printf '%s|%s|%s|%s|%s\\n' \"$n\" \"$g\" \"$lo\" \"$hi\" \"$cur\"; done"
)


def _parse_error(detail: str) -> RunnerError:
    return RunnerError("env-snapshot-parse-failed", detail)


def _required_match(pattern: str, text: str, field: str, flags: int = 0) -> re.Match[str]:
    match = re.search(pattern, text, flags)
    if not match:
        raise _parse_error(f"missing Android snapshot field: {field}")
    return match


def _bool(text: str, field: str) -> bool:
    if text == "true":
        return True
    if text == "false":
        return False
    raise _parse_error(f"invalid boolean for {field}: {text!r}")


def parse_cpufreq(text: str) -> dict[str, dict[str, int | str]]:
    """Parse ``policy|governor|min|max|cur`` rows emitted by the rooted script."""
    policies: dict[str, dict[str, int | str]] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.strip().split("|")
        if (len(fields) != 5 or not re.fullmatch(r"policy\d+", fields[0]) or
                not re.fullmatch(r"[A-Za-z0-9_-]+", fields[1]) or
                not all(value.isdigit() for value in fields[2:])):
            raise _parse_error(f"malformed cpufreq row: {line!r}")
        policy, governor, min_text, max_text, cur_text = fields
        if policy in policies:
            raise _parse_error(f"duplicate cpufreq policy: {policy}")
        min_khz, max_khz, cur_khz = map(int, (min_text, max_text, cur_text))
        if min_khz <= 0 or max_khz <= 0 or cur_khz <= 0 or min_khz > max_khz:
            raise _parse_error(f"invalid cpufreq values for {policy}")
        policies[policy] = {
            "governor": governor,
            "min_khz": min_khz,
            "max_khz": max_khz,
            "cur_khz": cur_khz,
        }
    if not policies:
        raise _parse_error("no cpufreq policies found")
    return policies


def parse_device_state(power_text: str, deviceidle_text: str,
                       airplane_text: str) -> dict:
    """Parse explicit power/DeviceIdle state; never infer it from a key event."""
    wakefulness = _required_match(
        r"\bmWakefulness=([^\s]+)", power_text, "power.wakefulness").group(1)
    powered = _bool(_required_match(
        r"\bmIsPowered=(true|false)", power_text, "power.powered").group(1),
        "power.powered")
    screen_on = _bool(_required_match(
        r"\bmScreenOn=(true|false)", deviceidle_text, "power.screen_on").group(1),
        "power.screen_on")
    force_idle = _bool(_required_match(
        r"\bmForceIdle=(true|false)", deviceidle_text,
        "device_idle.force_idle").group(1), "device_idle.force_idle")
    charging = _bool(_required_match(
        r"\bmCharging=(true|false)", deviceidle_text,
        "device_idle.charging").group(1), "device_idle.charging")
    states = _required_match(
        r"\bmState=([^\s]+)\s+mLightState=([^\s]+)", deviceidle_text,
        "device_idle.state/light_state")
    airplane = airplane_text.strip()
    if airplane not in ("0", "1"):
        raise _parse_error(f"invalid airplane_mode_on value: {airplane!r}")
    return {
        "power": {"wakefulness": wakefulness, "powered": powered,
                  "screen_on": screen_on},
        "device_idle": {"force_idle": force_idle, "state": states.group(1),
                        "light_state": states.group(2), "charging": charging},
        "airplane_mode": airplane == "1",
    }


def parse_camera(text: str) -> dict[str, bool | str]:
    """Use only the active-client block, excluding events and HAL device dumps."""
    match = _required_match(
        r"Active Camera Clients:\s*\n(.*?)\nAllowed user IDs:", text,
        "camera.active_clients", re.DOTALL)
    raw = match.group(1).strip()
    if not raw:
        raise _parse_error("empty Active Camera Clients block")
    return {"active": raw != "[]", "active_clients_raw": raw[:2000]}


def parse_thermal(text: str) -> dict:
    status_text = _required_match(
        r"Thermal Status:\s*(-?\d+)", text, "thermal.status").group(1)
    sensors: dict[str, float] = {}
    pattern = re.compile(
        r"Temperature\{mValue=(-?\d+(?:\.\d+)?),\s*mType=0,\s*"
        r"mName=([^,}]+),\s*mStatus=-?\d+\}")
    for value, name in pattern.findall(text):
        sensors[name.strip()] = float(value)
    if not sensors:
        raise _parse_error("no CPU thermal sensors found")
    return {"status": int(status_text), "max_cpu_c": max(sensors.values()),
            "cpu_sensors_c": sensors}


def parse_loadavg(text: str) -> dict[str, float]:
    fields = text.split()
    if len(fields) < 3:
        raise _parse_error("malformed /proc/loadavg")
    try:
        values = [float(value) for value in fields[:3]]
    except ValueError as exc:
        raise _parse_error("malformed /proc/loadavg") from exc
    return {"one": values[0], "five": values[1], "fifteen": values[2]}


def _run_required(executor: AdbExecutor, argv: list[str], name: str) -> str:
    result = executor.execute(argv)
    if result.returncode != 0:
        raise RunnerError(
            "env-snapshot-failed",
            f"Android state command {name} failed: {result.stderr.strip()[:160]}")
    return result.stdout


def collect_android_state(executor) -> dict:
    """Collect a complete Android state snapshot without changing device state."""
    if not isinstance(executor, AdbExecutor):
        raise RunnerError("env-snapshot-unsupported",
                          "android-controlled-quiet-v2 requires AdbExecutor")
    cpufreq = _run_required(
        executor, ["su", "-c", _CPUFREQ_SCRIPT], "cpufreq")
    power = _run_required(executor, ["dumpsys", "power"], "dumpsys power")
    idle = _run_required(executor, ["dumpsys", "deviceidle"], "dumpsys deviceidle")
    airplane = _run_required(
        executor, ["settings", "get", "global", "airplane_mode_on"], "airplane mode")
    camera = _run_required(
        executor, ["dumpsys", "media.camera"], "dumpsys media.camera")
    thermal = _run_required(
        executor, ["dumpsys", "thermalservice"], "dumpsys thermalservice")
    service = _run_required(
        executor, ["getprop", "init.svc.mi_thermald"], "mi_thermald service").strip()
    loadavg = _run_required(executor, ["cat", "/proc/loadavg"], "/proc/loadavg")
    if not service:
        raise _parse_error("empty mi_thermald service state")
    state = {
        "schema_version": "1.0",
        "cpufreq": parse_cpufreq(cpufreq),
        **parse_device_state(power, idle, airplane),
        "camera": parse_camera(camera),
        "thermal": parse_thermal(thermal),
        "services": {"mi_thermald": service},
        "loadavg": parse_loadavg(loadavg),
    }
    return state
