# SPDX-License-Identifier: Apache-2.0
"""加载 run 目录：records.jsonl + run-manifest.json。

只读层。status != ok 的记录不参与曲线与表格，但会在报告中单列——
失败的实验也是实验档案的一部分（measurement-discipline：可审计）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunData:
    """一个 run 目录的全部内容。"""
    run_dir: Path
    manifest: dict
    ok_records: list[dict]
    failed_records: list[dict]


def load_run(run_dir: str | Path) -> RunData:
    """加载 run 目录；缺 records.jsonl 时报错（目录可能不是 run 产出）。"""
    run_dir = Path(run_dir)
    records_path = run_dir / "records.jsonl"
    if not records_path.is_file():
        raise FileNotFoundError(f"records.jsonl not found: {run_dir} (not a run directory?)")
    manifest_path = run_dir / "run-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}

    ok, failed = [], []
    for line in records_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        if record.get("schema_version") != "2.0":
            continue  # 只消费 v2 记录；旧版由历史归档另行处理
        (ok if record.get("status") == "ok" else failed).append(record)
    return RunData(run_dir=run_dir, manifest=manifest,
                   ok_records=ok, failed_records=failed)
