# SPDX-License-Identifier: Apache-2.0
"""Declarative evaluation for measurement-environment evidence.

Policy evaluation is pure: collectors acquire facts, controllers mutate state,
and this module decides whether the facts satisfy an experiment profile. A
violation is returned as a stable machine-readable code; malformed policy is a
configuration error.
"""

from __future__ import annotations

from numbers import Real

from ..errors import RunnerError
from .android_state import collect_android_state


def _invalid(detail: str) -> RunnerError:
    return RunnerError("env-policy-invalid", detail)


def _expect_type(value, expected, name: str):
    if not isinstance(value, expected):
        raise _invalid(f"{name} has invalid type")
    return value


def evaluate_preconditions(snapshot: dict, policy: dict) -> list[str]:
    """Return sorted violation codes; malformed policy raises RunnerError."""
    _expect_type(snapshot, dict, "snapshot")
    _expect_type(policy, dict, "policy")
    conditions = _expect_type(policy.get("preconditions"), dict,
                              "policy.preconditions")
    wakefulness = _expect_type(conditions.get("wakefulness"), list,
                               "preconditions.wakefulness")
    if not wakefulness or not all(isinstance(item, str) for item in wakefulness):
        raise _invalid("preconditions.wakefulness must be a non-empty string list")
    for key in ("screen_on", "force_idle", "active_camera"):
        _expect_type(conditions.get(key), bool, f"preconditions.{key}")
    services = _expect_type(conditions.get("services"), dict,
                            "preconditions.services")
    governor = _expect_type(conditions.get("cpufreq_governor"), str,
                            "preconditions.cpufreq_governor")
    maxima = _expect_type(conditions.get("cpufreq_max_khz"), dict,
                          "preconditions.cpufreq_max_khz")
    temp_limit = conditions.get("max_cpu_temp_c")
    if isinstance(temp_limit, bool) or not isinstance(temp_limit, Real):
        raise _invalid("preconditions.max_cpu_temp_c must be numeric")

    violations: list[str] = []
    try:
        if snapshot["power"]["wakefulness"] not in wakefulness:
            violations.append("wakefulness-mismatch")
        if snapshot["power"]["screen_on"] != conditions["screen_on"]:
            violations.append("screen-state-mismatch")
        if snapshot["device_idle"]["force_idle"] != conditions["force_idle"]:
            violations.append("force-idle-mismatch")
        if snapshot["camera"]["active"] != conditions["active_camera"]:
            violations.append("camera-active" if snapshot["camera"]["active"]
                              else "camera-inactive")
        for name, expected in services.items():
            if not isinstance(expected, str):
                raise _invalid(f"preconditions.services.{name} must be a string")
            if snapshot["services"].get(name) != expected:
                violations.append(f"service-mismatch:{name}")
        for name, fields in snapshot["cpufreq"].items():
            if fields["governor"] != governor:
                violations.append(f"cpufreq-governor-mismatch:{name}")
        for name, expected in maxima.items():
            if (isinstance(expected, bool) or not isinstance(expected, int) or
                    expected <= 0):
                raise _invalid(f"preconditions.cpufreq_max_khz.{name} must be positive int")
            actual = snapshot["cpufreq"].get(name, {}).get("max_khz")
            if actual != expected:
                violations.append(f"cpufreq-max-mismatch:{name}")
        if snapshot["thermal"]["max_cpu_c"] > float(temp_limit):
            violations.append("thermal-over-limit")
    except (KeyError, TypeError) as exc:
        raise RunnerError("env-snapshot-parse-failed",
                          f"snapshot lacks policy field: {exc}") from exc
    return sorted(set(violations))


def _stable_values(snapshot: dict, path: str) -> dict[str, object]:
    if path.startswith("cpufreq.*."):
        field = path.removeprefix("cpufreq.*.")
        if field not in ("governor", "min_khz", "max_khz", "cur_khz"):
            raise _invalid(f"unsupported stable field: {path}")
        try:
            return {f"cpufreq.{name}.{field}": values[field]
                    for name, values in snapshot["cpufreq"].items()}
        except (KeyError, TypeError) as exc:
            raise RunnerError("env-snapshot-parse-failed",
                              f"snapshot lacks stable field: {path}") from exc
    parts = path.split(".")
    value = snapshot
    try:
        for part in parts:
            value = value[part]
    except (KeyError, TypeError) as exc:
        raise RunnerError("env-snapshot-parse-failed",
                          f"snapshot lacks stable field: {path}") from exc
    return {path: value}


def evaluate_stability(before: dict, after: dict, policy: dict) -> list[str]:
    fields = _expect_type(policy.get("stable_fields"), list,
                          "policy.stable_fields")
    if not all(isinstance(path, str) and path for path in fields):
        raise _invalid("policy.stable_fields must contain non-empty strings")
    violations: list[str] = []
    for path in fields:
        before_values = _stable_values(before, path)
        after_values = _stable_values(after, path)
        for concrete in sorted(set(before_values) | set(after_values)):
            if before_values.get(concrete) != after_values.get(concrete):
                violations.append(f"state-drift:{concrete}")
    return sorted(set(violations))


def collect_environment_state(executor, policy: dict) -> dict:
    """Select a collector by protocol name, not by target id."""
    collector = policy.get("collector")
    if collector == "android-controlled-quiet-v2":
        return collect_android_state(executor)
    raise RunnerError("env-snapshot-unsupported",
                      f"unsupported measurement environment collector: {collector!r}")
