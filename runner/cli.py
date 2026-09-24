# SPDX-License-Identifier: Apache-2.0
"""CLI：python -m runner.cli plan|run

  plan  预览确定性 case 集合（含参数溯源），不执行、不写盘
  run   执行并落盘 run-record v2 JSONL + 原始样本 + manifests
"""

from __future__ import annotations

import argparse
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


def _cmd_plan(args) -> int:
    """plan 子命令：打印确定性 case 预览（含参数来源与重复次数），无副作用。"""
    spec = load_experiment(args.experiment)
    platform = load_platform(args.platform)
    plan = build_plan(spec, platform)
    print(f"experiment={plan.experiment_id} protocol={plan.protocol_version} "
          f"cases={len(plan.cases)} target={plan.target.get('target_id')}")
    for case in plan.cases:
        params = ", ".join(f"{k}={v.value}[{v.source}]" for k, v in case.params)
        print(f"  {case.id}  reps={case.repetitions}  prefix={' '.join(case.control.command_prefix) or '-'}\n"
              f"      {params}")
    return EXIT_OK


def _cmd_run(args) -> int:
    spec = load_experiment(args.experiment)
    platform = load_platform(args.platform)
    plan = build_plan(spec, platform)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.out) / f"{stamp}-{plan.experiment_id}"
    if args.env:
        # host 级状态变更（如锁频）走环境事务：apply→run→restore，journal
        # 全留痕；--allow-mutation 是显式授权门（2026-09-25 讨论裁定）
        from .environment import execute_environment_tx
        summary = execute_environment_tx(
            platform, args.env,
            work=lambda: run_plan(plan, platform, run_dir, _REPO_ROOT),
            allow_mutation=args.allow_mutation,
            note=f"experiment={plan.experiment_id}")
    else:
        summary = run_plan(plan, platform, run_dir, _REPO_ROOT)
    print(f"run_dir={run_dir}\nsummary={summary}")
    return EXIT_OK if summary["failed"] == 0 else EXIT_RUN_FAILURES


def _cmd_env(args) -> int:
    """env 子命令：status 列出未完成事务；restore 按 journal 重放恢复。"""
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
            levels = ", ".join(f"L{e['level']}{e['type'][0]}={e['size']}"
                               for e in cap["values"]["levels"])
            print(f"[ok] {name}: {levels}")
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
        if name == "run":
            p.add_argument("--out", default="data/public/runs")
            p.add_argument("--env", action="append", default=None,
                           help="host 级变更 spec（如 governor=performance），走环境事务")
            p.add_argument("--allow-mutation", action="store_true",
                           help="--env 的显式授权门")
        if name == "capabilities":
            p.add_argument("--out", default="data/public/capabilities")
        if name == "env":
            p.add_argument("action", choices=["status", "restore"])
            p.add_argument("--tx", default=None, help="restore 的事务 id")
        p.set_defaults(fn=fn)
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except RunnerError as e:
        print(f"error[{e.code}]: {e}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
