# SPDX-License-Identifier: Apache-2.0
"""CLI 薄壳：参数解析 → 子命令分发 → 错误阶梯翻译（OI-9 蓝图）。

子命令与参数的唯一权威是 main() 里的 argparse 注册——不在此维护枚举
清单，避免第二份事实随代码漂移（历史 docstring 债，2026-09-27 清偿）：

    .venv/bin/python -m runner.cli --help            # 子命令清单
    .venv/bin/python -m runner.cli <子命令> --help   # 该子命令全部参数

退出码阶梯：0 全成功 / 1 配置或输入错误 / 2 有 case 失败（数据已落盘）。
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .engine import run_plan
from .errors import EXIT_OK, EXIT_RUN_FAILURES, EXIT_USAGE, RunnerError
from .executor import make_executor
from .plan import build_plan
from .records import now_iso, write_json_atomic
from .spec import load_experiment, load_platform
from .targets.capabilities import collect_all

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _resolve_environment_profile(platform: dict, name: str | None) -> tuple[dict, dict]:
    """Return an isolated active platform plus merged declarative mutations."""
    active = dict(platform)
    requirements = dict(platform.get("host_requirements") or {})
    if not name:
        return active, requirements
    profiles = platform.get("environment_profiles") or {}
    profile = profiles.get(name) if isinstance(profiles, dict) else None
    if not isinstance(profile, dict):
        raise RunnerError("config-invalid", f"unknown environment profile: {name!r}")
    profile_requirements = profile.get("host_requirements") or {}
    measurement_environment = profile.get("measurement_environment")
    if not isinstance(profile_requirements, dict) or not isinstance(measurement_environment, dict):
        raise RunnerError("config-invalid",
                          f"environment profile {name!r} requires host_requirements"
                          " and measurement_environment objects")
    for key, value in profile_requirements.items():
        if key in requirements and requirements[key] != value:
            raise RunnerError("env-conflicting-request",
                              f"conflicting declared requirement for {key}: "
                              f"{requirements[key]!r} vs {value!r}")
        requirements[key] = value
    active["measurement_environment"] = deepcopy(measurement_environment)
    active["active_environment_profile"] = name
    return active, requirements


def _resolve_environment_specs(requirements: dict,
                               cli_specs: list[str] | None) -> list[str]:
    """Merge declared and CLI mutations by canonical controller key."""
    from .environment import specs_from_host_requirements
    from .environment.controllers import make_controller
    requested_specs = specs_from_host_requirements(requirements) + list(cli_specs or [])
    resolved: list[str] = []
    seen: dict[str, str] = {}
    for spec in requested_specs:
        controller, requested = make_controller(spec)
        controller.validate(requested)
        previous = seen.get(controller.key)
        if previous is not None and previous != requested:
            raise RunnerError("env-conflicting-request",
                              f"conflicting requests for {controller.key}: "
                              f"{previous!r} vs {requested!r}")
        if previous is None:
            seen[controller.key] = requested
            resolved.append(spec)
    return resolved


def _cmd_plan(args) -> int:
    """plan 子命令：打印确定性 case 预览（含参数来源与重复次数），无副作用。"""
    spec = load_experiment(args.experiment)
    platform, requirements = _resolve_environment_profile(
        load_platform(args.platform), getattr(args, "environment_profile", None))
    plan = build_plan(spec, platform)
    print(f"experiment={plan.experiment_id} protocol={plan.protocol_version} "
          f"cases={len(plan.cases)} target={plan.target.get('target_id')}")
    if platform.get("active_environment_profile"):
        mutations = _resolve_environment_specs(requirements, None)
        print(f"environment_profile={platform['active_environment_profile']} "
              f"mutations={','.join(mutations) or '-'}")
    for case in plan.cases:
        params = ", ".join(f"{k}={v.value}[{v.source}]" for k, v in case.params)
        print(f"  {case.id}  reps={case.repetitions}  prefix={' '.join(case.control.command_prefix) or '-'}\n"
              f"      {params}")
    return EXIT_OK


def _cmd_run(args) -> int:
    spec = load_experiment(args.experiment)
    platform, requirements = _resolve_environment_profile(
        load_platform(args.platform), getattr(args, "environment_profile", None))
    plan = build_plan(spec, platform)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.out) / f"{stamp}-{plan.experiment_id}"
    specs = _resolve_environment_specs(requirements, args.env)
    if specs:
        # host 级状态变更（如锁频）走环境事务：apply→run→restore，journal
        # 全留痕；--allow-mutation 是显式授权门（2026-09-25 讨论裁定）
        from .environment import execute_environment_tx, reconcile_unfinished
        if not args.allow_mutation:
            raise RunnerError("env-mutation-not-allowed",
                              "environment profile mutations require --allow-mutation")
        # 声明式 host_requirements（平台/profile）+ CLI --env 叠加；启动前调和
        # 中断残留事务（任务书 §2.1：检测并完成 restore，而非硬拒绝）
        remaining = reconcile_unfinished(platform)
        if remaining:
            raise RunnerError("env-unfinished-tx",
                              f"reconcile failed for: {[j.tx_id for j in remaining]}"
                              " — 人工处理: runner.cli env status / restore --tx <id>")
        summary = execute_environment_tx(
            platform, specs,
            work=lambda: run_plan(plan, platform, run_dir, _REPO_ROOT),
            allow_mutation=args.allow_mutation,
            note=f"experiment={plan.experiment_id}")
    else:
        summary = run_plan(plan, platform, run_dir, _REPO_ROOT)
    print(f"run_dir={run_dir}\nsummary={summary}")
    return EXIT_OK if summary["failed"] == 0 else EXIT_RUN_FAILURES


def _cmd_env(args) -> int:
    """Inspect device state or manage durable mutation journals."""
    if args.action == "inspect":
        from .environment import (collect_environment_state,
                                  evaluate_preconditions_full)
        platform, requirements = _resolve_environment_profile(
            load_platform(args.platform), getattr(args, "environment_profile", None))
        policy = platform.get("measurement_environment")
        if not isinstance(policy, dict):
            raise RunnerError("config-invalid",
                              "env inspect requires --environment-profile")
        executor = make_executor(platform)
        snapshot = collect_environment_state(executor, policy)
        violations, warnings = evaluate_preconditions_full(snapshot, policy)
        mutation_specs = _resolve_environment_specs(requirements, None)
        covers_governor = any(spec.startswith("governor=") for spec in mutation_specs)
        covered = [violation for violation in violations
                   if covers_governor and
                   violation.startswith("cpufreq-governor-mismatch:")]
        uncovered = [violation for violation in violations if violation not in covered]
        print(json.dumps({
            "environment_profile": platform.get("active_environment_profile"),
            "snapshot": snapshot,
            "policy_result": {
                "valid": not uncovered,
                "ready_for_transaction": not uncovered,
                "violations": uncovered,
                "covered_by_mutation": covered,
                "observed_violations": violations,
                "accepted_nonbaseline": warnings,
            },
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return EXIT_OK if not uncovered else EXIT_USAGE

    from .environment import restore_transaction
    from .environment.journal import default_store
    store = default_store()
    if args.action == "status":
        unfinished = store.unfinished()
        total = len(list(store.root.glob("*.json"))) if store.root.exists() else 0
        print(f"journals={total} unfinished={len(unfinished)}")
        for j in unfinished:
            print(f"  unfinished tx={j.tx_id} state={j.state} note={j.note}")
        return EXIT_OK
    platform = load_platform(args.platform)
    restore_transaction(args.tx, platform)
    print(f"restored tx={args.tx}")
    return EXIT_OK


def _cmd_capabilities(args) -> int:
    """capabilities 子命令：经执行器通道采集平台能力事实（cache 拓扑 /
    cpufreq），写 capability-manifest JSON 入库——测量校验准绳
    （探测不到如实 unsupported，零损失；2026-09-25 讨论落定）。"""
    platform = load_platform(args.platform)
    executor = make_executor(platform)
    manifest = collect_all(executor, platform["target"])
    manifest["captured_at"] = now_iso()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tid = platform["target"].get("target_id", "unknown-target")
    path = out / f"{tid}-{stamp}.json"
    write_json_atomic(path, manifest)
    for name, cap in manifest["capabilities"].items():
        if not cap["supported"]:
            print(f"[--] {name}: unsupported ({cap['detail']})")
        elif name == "cache-topology":
            levels = ", ".join(f"L{e['level']}{e['type'][0] if e['type'] else '?' }={e['size']}"
                               for e in cap["values"]["levels"])
            print(f"[ok] {name}: {levels}")
        elif name == "core-topology" and cap["values"].get("source") == "linux-sysfs":
            cpus = cap["values"]["cpus"]
            caps_set = sorted({e["capacity"] for e in cpus.values()})
            print(f"[ok] {name}: {len(cpus)} cpus, capacity tiers={caps_set}, "
                  f"midr readable={'yes' if any(e['midr_el1'] for e in cpus.values()) else 'no'}")
        else:
            print(f"[ok] {name}: {cap['values']}")
    print(f"capability-manifest: {path}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。退出码阶梯：0 全成功 / 1 配置或输入错误 / 2 有 case 失败
    （数据已落盘，OI-9 蓝图 exit code 阶梯）。"""
    parser = argparse.ArgumentParser(prog="runner", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (("plan", _cmd_plan), ("run", _cmd_run),
                     ("capabilities", _cmd_capabilities), ("env", _cmd_env)):
        p = sub.add_parser(name)
        p.add_argument("--platform", required=True)
        if name in ("plan", "run"):
            p.add_argument("--experiment", required=True)
            p.add_argument("--environment-profile", default=None,
                           help="平台定义的环境 profile（显式选择，不设默认）")
        if name == "run":
            p.add_argument("--out", default="data/public/runs")
            p.add_argument("--env", action="append", default=None,
                           help="host 级变更 spec（如 governor=performance），走环境事务")
            p.add_argument("--allow-mutation", action="store_true",
                           help="--env 的显式授权门")
        if name == "capabilities":
            p.add_argument("--out", default="data/public/capabilities")
        if name == "env":
            p.add_argument("action", choices=["status", "inspect", "restore"])
            p.add_argument("--tx", default=None, help="restore 的事务 id")
            p.add_argument("--environment-profile", default=None,
                           help="inspect 使用的平台环境 profile")
        p.set_defaults(fn=fn)
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except RunnerError as e:
        print(f"error[{e.code}]: {e}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
