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
from .plan import build_plan
from .spec import load_experiment, load_platform

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _cmd_plan(args) -> int:
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
    summary = run_plan(plan, platform, run_dir, _REPO_ROOT)
    print(f"run_dir={run_dir}\nsummary={summary}")
    return EXIT_OK if summary["failed"] == 0 else EXIT_RUN_FAILURES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="runner", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (("plan", _cmd_plan), ("run", _cmd_run)):
        p = sub.add_parser(name)
        p.add_argument("--experiment", required=True)
        p.add_argument("--platform", required=True)
        if name == "run":
            p.add_argument("--out", default="data/public/runs")
        p.set_defaults(fn=fn)
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except RunnerError as e:
        print(f"error[{e.code}]: {e}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
