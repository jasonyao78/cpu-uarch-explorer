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


def _parse_accepted_nonbaseline(conditions: dict, maxima: dict) -> frozenset[str]:
    """解析 preconditions.accepted_nonbaseline.cpufreq_max_khz（充电态协议，
    2026-10-07 任务书 v1.5 增补）：列出的 policy 的 scaling_max 偏离期望
    从"违规"降级为"命名告警"（accepted-nonbaseline:* 码）——只降级、不豁免
    记录：实际值仍随 snapshot 全量入档。校验：名单必须是非空字符串列表且
    每个名字都在 cpufreq_max_khz 期望表里（对无期望的 policy 降级无意义）。"""
    raw = conditions.get("accepted_nonbaseline")
    if raw is None:
        return frozenset()
    if not isinstance(raw, dict):
        raise _invalid("accepted_nonbaseline must be a dict")
    names = raw.get("cpufreq_max_khz", [])
    if (not isinstance(names, list) or not names
            or not all(isinstance(n, str) and n for n in names)):
        raise _invalid("accepted_nonbaseline.cpufreq_max_khz must be a "
                       "non-empty string list")
    unknown = [n for n in names if n not in maxima]
    if unknown:
        raise _invalid("accepted_nonbaseline.cpufreq_max_khz names not in "
                       f"cpufreq_max_khz expectations: {unknown!r}")
    if set(names) == set(maxima):
        raise _invalid("accepted_nonbaseline.cpufreq_max_khz must not cover "
                       "all policies——测量核所在 policy 必须保持硬门禁"
                       "（充电态 cap 迁移到测量核是主要威胁）")
    return frozenset(names)


def evaluate_preconditions_full(snapshot: dict, policy: dict) -> tuple[list[str], list[str]]:
    """(hard violations, accepted-nonbaseline warnings)。warnings 不阻塞执行，
    但必须可见入档（engine 写入 policy_result.accepted_nonbaseline）——
    降级是显式实验条件（充电态），不是放行缺口。"""
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
    accepted = _parse_accepted_nonbaseline(conditions, maxima)

    violations: list[str] = []
    warnings: list[str] = []
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
                if name in accepted:
                    warnings.append(
                        f"accepted-nonbaseline:cpufreq-max-mismatch:{name}")
                else:
                    violations.append(f"cpufreq-max-mismatch:{name}")
        if snapshot["thermal"]["max_cpu_c"] > float(temp_limit):
            violations.append("thermal-over-limit")
    except (KeyError, TypeError) as exc:
        raise RunnerError("env-snapshot-parse-failed",
                          f"snapshot lacks policy field: {exc}") from exc
    return sorted(set(violations)), sorted(set(warnings))


def evaluate_preconditions(snapshot: dict, policy: dict) -> list[str]:
    """Return sorted hard-violation codes; malformed policy raises RunnerError.

    accepted_nonbaseline 降级项不在返回值中（它们是告警不是违规）——
    需要告警可见性时用 evaluate_preconditions_full。"""
    violations, _ = evaluate_preconditions_full(snapshot, policy)
    return violations


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


def _accepted_from_stable_field(path: str, accepted: frozenset[str]) -> bool:
    """stable_fields 展开的 cpufreq.<policy>.max_khz 漂移是否落在已接纳
    非基线名单内（仅 max_khz 字段可降级；governor/min_khz 漂移永远硬）。"""
    parts = path.split(".")
    return (len(parts) == 3 and parts[0] == "cpufreq"
            and parts[2] == "max_khz" and parts[1] in accepted)


def evaluate_stability_full(before: dict, after: dict, policy: dict) -> tuple[list[str], list[str]]:
    """(hard drift violations, accepted-nonbaseline drift warnings)。"""
    fields = _expect_type(policy.get("stable_fields"), list,
                          "policy.stable_fields")
    if not all(isinstance(path, str) and path for path in fields):
        raise _invalid("policy.stable_fields must contain non-empty strings")
    conditions = policy.get("preconditions")
    maxima = (conditions or {}).get("cpufreq_max_khz", {})
    accepted = _parse_accepted_nonbaseline(conditions or {}, maxima)
    violations: list[str] = []
    warnings: list[str] = []
    for path in fields:
        before_values = _stable_values(before, path)
        after_values = _stable_values(after, path)
        for concrete in sorted(set(before_values) | set(after_values)):
            if before_values.get(concrete) != after_values.get(concrete):
                if _accepted_from_stable_field(concrete, accepted):
                    warnings.append(f"accepted-nonbaseline:state-drift:{concrete}")
                else:
                    violations.append(f"state-drift:{concrete}")
    return sorted(set(violations)), sorted(set(warnings))


def evaluate_stability(before: dict, after: dict, policy: dict) -> list[str]:
    """Return sorted hard drift codes（accepted_nonbaseline 降级项除外）。"""
    violations, _ = evaluate_stability_full(before, after, policy)
    return violations


def collect_environment_state(executor, policy: dict) -> dict:
    """Select a collector by protocol name, not by target id."""
    collector = policy.get("collector")
    if collector == "android-controlled-quiet-v2":
        return collect_android_state(executor)
    raise RunnerError("env-snapshot-unsupported",
                      f"unsupported measurement environment collector: {collector!r}")
