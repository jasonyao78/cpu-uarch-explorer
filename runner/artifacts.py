# SPDX-License-Identifier: Apache-2.0
"""原始样本落盘 + artifact-manifest（SHA256 谱系，ADR-0006 §4）。

每个 sample 的原始 stdout/stderr 原样保存，manifest 记 SHA256——
run-record 里的每个数字都能顺着 raw_samples_ref 回到原始输出。
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactStore:
    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.raw_dir = self.run_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.entries: list[dict] = []

    def register_file(self, path: Path, kind: str, notes: str = "") -> dict:
        """登记任意文件为 artifact：读字节算 SHA256，追加 manifest 条目并返回。"""
        data = Path(path).read_bytes()
        entry = {
            "schema_version": "1.0",
            "id": f"{kind}:{Path(path).name}",
            "kind": kind,
            "sha256": _sha256(data),
            "size_bytes": len(data),
            "created_at": _now_iso(),
            "path": str(Path(path).resolve()),
        }
        if notes:
            entry["notes"] = notes
        self.entries.append(entry)
        return entry

    def register_probe_binary(self, path: Path, git_commit: str, git_dirty: bool) -> dict:
        """登记 probe 二进制：SHA256 + 构建谱系（git commit/dirty），
        供 run-record.probe.artifact 引用——回答"这数字是哪版二进制测的"。"""
        entry = self.register_file(path, "probe-binary", notes="probe 可执行文件谱系")
        entry["source"] = {"commit": git_commit, "dirty": git_dirty}
        return entry

    def register_probe_binary_digest(self, display_path: str, sha256_hex: str,
                                     git_commit: str, git_dirty: bool) -> dict:
        """登记远端 probe 二进制（transport=ssh）：本机读不到远端字节，
        SHA256 由执行器通道在目标机采集后传入；其余谱系同本机登记。"""
        entry = {
            "schema_version": "1.0",
            "id": f"probe-binary:{Path(display_path).name}",
            "kind": "probe-binary",
            "sha256": sha256_hex,
            "created_at": _now_iso(),
            "path": display_path,
            "notes": "probe 可执行文件谱系（SHA256 经 ssh 在目标机采集）",
            "source": {"commit": git_commit, "dirty": git_dirty},
        }
        self.entries.append(entry)
        return entry

    def write_raw_sample(self, case_id: str, sample_index: int,
                         stdout: str, stderr: str) -> dict:
        """原始样本字节先落盘再算 SHA256，manifest id 即 raw_samples_ref 引用目标。"""
        safe_case = case_id.replace("/", "_").replace(":", "_")
        base = self.raw_dir / f"{safe_case}.s{sample_index}"
        # 注意：不能用 with_suffix——".s0" 会被当作后缀替换掉，导致重复样本互相覆盖
        out_path = base.with_name(base.name + ".stdout.txt")
        err_path = base.with_name(base.name + ".stderr.txt")
        out_path.write_text(stdout, encoding="utf-8")
        err_path.write_text(stderr, encoding="utf-8")
        payload = stdout.encode() + b"\n--- stderr ---\n" + stderr.encode()
        entry = {
            "schema_version": "1.0",
            "id": f"raw-samples:{safe_case}.s{sample_index}",
            "kind": "raw-samples",
            "sha256": _sha256(payload),
            "size_bytes": len(payload),
            "created_at": _now_iso(),
            "path": str(base.resolve()) + ".{stdout,stderr}.txt",
        }
        self.entries.append(entry)
        return entry
