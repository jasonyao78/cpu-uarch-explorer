# SPDX-License-Identifier: Apache-2.0
"""run-record v2 构建与落盘（JSONL，ADR-0003；原子写，OI-9 蓝图）。

- JSONL 逐行追加，每行 flush+fsync：中途崩溃不丢已完成的 case。
- 汇总文件（manifest 等）走 write_json_atomic：tmp → fsync → replace
  → 父目录 fsync，读者永远看到完整文件或不存在。
"""

from __future__ import annotations

import json
import os
import platform as plat
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_provenance(repo_root: Path) -> dict:
    """采集仓库谱系：HEAD commit 与 dirty 状态（不含未跟踪文件——构建产物
    不算脏；内容被修改才算，对应"这数字是哪版代码测的"）。"""
    def _git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(repo_root), *args],
                              capture_output=True, text=True).stdout.strip()
    commit = _git("rev-parse", "HEAD")
    dirty = bool(_git("status", "--porcelain", "--untracked-files=no"))
    return {"commit": commit, "dirty": dirty}


def compiler_version() -> str:
    try:
        first = subprocess.run(["cc", "--version"], capture_output=True, text=True).stdout.splitlines()
        return first[0] if first else "unknown"
    except OSError:
        return "unknown"


def local_system_info() -> dict:
    """本机环境采集：os_version/kernel/compiler。LocalExecutor 直接使用；
    SshExecutor 在目标机采集同名字段——两边口径一致，engine 合并 control
    入档（run-record.environment 描述的是目标机）。"""
    return {
        "os_version": plat.mac_ver()[0] if plat.system() == "Darwin" else plat.platform(),
        "kernel": plat.release(),
        "compiler": compiler_version(),
    }


def environment_block(control_mechanism: str, control_value: str,
                      system_info: dict | None = None) -> dict:
    """组装 environment 段：默认本机采集；engine 传入执行器采集的
    system_info（ssh 场景为目标机）时以传入为准。"""
    info = system_info if system_info is not None else local_system_info()
    return {
        **info,
        "control": {"mechanism": control_mechanism, "value": control_value},
    }


def build_run_record(*, status: str, target: dict, probe: dict, environment: dict,
                     params: dict, params_provenance: dict, metrics: list[dict],
                     raw_command: str, failure: dict | None = None,
                     provenance: str = "MEASURED", access_class: str = "PUBLIC") -> dict:
    """组装 run-record v2（条件规则见 schema：ok 必须有 metrics；非 ok 必须有 failure）。"""
    record = {
        "schema_version": "2.0",
        "run_id": str(uuid.uuid4()),
        "timestamp": now_iso(),
        "status": status,
        "target": target,
        "probe": probe,
        "environment": environment,
        "params": params,
        "params_provenance": params_provenance,
        "metrics": metrics,
        "evidence": {"provenance": provenance},
        "access_class": access_class,
        "raw_command": raw_command,
    }
    if failure is not None:
        record["failure"] = failure
    return record


class JsonlWriter:
    """逐行持久追加：每行写完即 fsync，崩溃最多丢当前行。"""

    def __init__(self, path: Path):
        self._f = open(path, "a", encoding="utf-8")

    def append(self, obj: dict) -> None:
        self._f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self._f.flush()
        os.fsync(self._f.fileno())

    def close(self) -> None:
        self._f.close()


def write_json_atomic(path: Path, obj) -> None:
    """fsync → replace → parent fsync：要么完整可见，要么不存在。"""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def write_jsonl_atomic(path: Path, rows) -> None:
    """JSONL 版本的原子写：每行一条记录（ADR-0003），tmp → fsync → replace。"""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def _fsync_dir(dir_path) -> None:
    dir_fd = os.open(dir_path, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
