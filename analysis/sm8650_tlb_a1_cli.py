# SPDX-License-Identifier: Apache-2.0
"""A1 两阶段文件入口：只读采样档案，写冻结/裁定 JSON；不执行设备操作。"""
import argparse
import json
from pathlib import Path
import sys

from runner.records import write_json_atomic
from .sm8650_tlb import TlbError
from .sm8650_tlb_a1 import run_a1_adjudication
from .sm8650_tlb_a1_freeze import freeze_a1_from_runs, load_audited_run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    freeze = sub.add_parser('freeze')
    freeze.add_argument('--floor-run', type=Path, required=True)
    freeze.add_argument('--scatter-run', type=Path, required=True)
    freeze.add_argument('--out', type=Path, required=True)
    adjudicate = sub.add_parser('adjudicate')
    adjudicate.add_argument('--run', type=Path, action='append', required=True)
    adjudicate.add_argument('--frozen-file', type=Path, required=True)
    adjudicate.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'freeze':
            output = freeze_a1_from_runs(args.floor_run, args.scatter_run)
            if args.out.exists() and json.loads(args.out.read_text()) != output:
                raise TlbError('a1: existing frozen file differs; choose a new artifact path')
            if not args.out.exists():
                write_json_atomic(args.out, output)
            print(json.dumps({'frozen': output['frozen'], 'artifact_sha256': output['artifact_sha256']}))
            return 0 if output['frozen'] else 2
        records, inputs = [], []
        for directory in args.run:
            loaded, anchor = load_audited_run(directory)
            records.extend(loaded)
            inputs.append(anchor)
        frozen = json.loads(args.frozen_file.read_text())
        output = run_a1_adjudication(records, frozen)
        output.update(frozen_artifact_sha256=frozen['artifact_sha256'],
                      formal_inputs=sorted(inputs, key=lambda a: a['directory']))
        write_json_atomic(args.out, output)
        print(json.dumps({'h_star': output['h_star'], 'h_star_status': output['h_star_status']}))
        return 0
    except (TlbError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
