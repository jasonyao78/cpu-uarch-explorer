# SPDX-License-Identifier: Apache-2.0
"""报告 CLI：python -m analysis.cli report --run <run目录> [--out <输出目录>]

默认输出到 run 目录内（report.md + latency.svg），作为该次实验的派生档案
随记录一并入库。退出码：0 成功 / 1 输入错误（与 runner 阶梯一致）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .chart import latency_svg
from .load import load_run
from .report import _series_by_control, build_report


def _cmd_report(args) -> int:
    try:
        run = load_run(args.run)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if not run.ok_records:
        print(f"error: no ok records in {args.run}", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else Path(args.run)
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_name = "latency.svg"

    series = {label: [(kb, v) for kb, v, _ in pts]
              for label, pts in _series_by_control(run).items()}
    svg = latency_svg(series, title=f"{run.manifest.get('experiment_id', 'latency sweep')} "
                                    f"@ {run.ok_records[0]['target'].get('target_id', '?')}")
    (out_dir / svg_name).write_text(svg, encoding="utf-8")
    report = build_report(run, svg_name)
    (out_dir / "report.md").write_text(report, encoding="utf-8")
    print(f"report: {out_dir}/report.md\nchart:  {out_dir}/{svg_name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analysis", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("report", help="为一个 run 目录生成报告")
    p.add_argument("--run", required=True, help="run 目录（含 records.jsonl）")
    p.add_argument("--out", default=None, help="输出目录（默认写回 run 目录）")
    p.set_defaults(fn=_cmd_report)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
