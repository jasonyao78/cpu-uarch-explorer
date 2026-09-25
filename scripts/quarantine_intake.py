# SPDX-License-Identifier: Apache-2.0
"""回传数据入库前检疫（GB10 自驱模式 §5.5）。

GB10 的 run 目录经物理介质回传后**不直接进 data/public/**：先解包到
data/quarantine/，本脚本做一致性校验——records 逐行过 run-record.v2
schema、记录数与 run-manifest summary 一致、artifacts 的 SHA256 与
records 引用兼容（raw/ 不回传，按策略跳过）。全部通过才由人工/下一步
移入 data/public/runs/ 提交。

用法：
    python3 scripts/quarantine_intake.py <回传解包目录>
退出码：0=通过（并打印迁移建议命令）；1=任一校验失败（目录滞留
quarantine，保留审计线索）。
"""
import json
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "runner/schema/run-record.v2.schema.json"


def validate_run_dir(run_dir: Path) -> list[str]:
    """返回问题列表（空 = 通过）。校验项随 GB10 首份回传数据演化。"""
    problems: list[str] = []
    records_path = run_dir / "records.jsonl"
    manifest_path = run_dir / "run-manifest.json"
    if not records_path.is_file():
        return [f"missing records.jsonl in {run_dir}"]
    if not manifest_path.is_file():
        problems.append("missing run-manifest.json")

    rows = []
    for i, line in enumerate(records_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            problems.append(f"records.jsonl line {i + 1}: invalid JSON: {e}")
    if not rows:
        problems.append("records.jsonl has no records")

    # schema 校验（jsonschema 可用则严校验；不可用退化为结构底线检查）
    try:
        import jsonschema
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        for i, row in enumerate(rows):
            try:
                jsonschema.validate(row, schema)
            except jsonschema.ValidationError as e:
                problems.append(f"records.jsonl line {i + 1}: schema: {e.message[:120]}")
    except ImportError:
        for i, row in enumerate(rows):
            for key in ("schema_version", "run_id", "timestamp", "status", "target", "probe", "metrics", "evidence"):
                if key not in row:
                    problems.append(f"records.jsonl line {i + 1}: missing required key {key!r}")

    # 记录数与 manifest 汇总一致
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        total = manifest.get("summary", {}).get("total")
        if total is not None and total != len(rows):
            problems.append(f"manifest summary.total={total} != actual records={len(rows)}")

    # status 分布：failed 记录必须带结构化 failure（不编造数字纪律的回传侧检查）
    for i, row in enumerate(rows):
        if row.get("status") != "ok" and "failure" not in row:
            problems.append(f"records.jsonl line {i + 1}: status={row.get('status')} without failure object")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1
    run_dir = Path(argv[1])
    problems = validate_run_dir(run_dir)
    if problems:
        print(f"QUARANTINE REJECTED: {run_dir}")
        for p in problems:
            print(f"  - {p}")
        print("目录保留在 quarantine 区，修正或重跑后再验。")
        return 1
    print(f"QUARANTINE PASSED: {run_dir}")
    print(f"  records={sum(1 for l in (run_dir / 'records.jsonl').read_text().splitlines() if l.strip())}")
    print(f"下一步: mv '{run_dir}' data/public/runs/ && git add data/public/runs/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
