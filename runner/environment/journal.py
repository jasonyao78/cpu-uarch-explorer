# SPDX-License-Identifier: Apache-2.0
"""Durable journal：host 级变更的持久审计与崩溃恢复锚点（GB10 模型重实现）。

journal 先于任何变更写入（先记账后动手）：每条 mutation 记录
requested/before/after 三值——restore 永远拿 before 实际值回写，
不依赖"系统默认值"这种会漂移的假设。状态机白名单拒绝非法迁移；
终态（restored/restore-failed/apply-failed）不可变。

存储：data/private/env-journals/<tx_id>.json（私有层，永不入库）；
原子写 tmp→fsync→replace→dir fsync（OI-9 蓝图 ResultStore 同款）。
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..records import now_iso, write_json_atomic

_TERMINAL = ("restored", "restore-failed", "apply-failed")
_TRANSITIONS = {
    "created": {"applying", "apply-failed"},
    "applying": {"applied", "apply-failed"},
    "applied": {"restoring"},
    "restoring": {"restored", "restore-failed"},
}


@dataclass
class Mutation:
    """一次控制器变更的审计记录：请求值、变更前实际值、变更后实际值。"""
    controller: str
    requested: str
    before: str
    after: str = ""
    apply_error: str = ""


@dataclass
class Journal:
    tx_id: str
    platform_id: str
    created_at: str = field(default_factory=now_iso)
    state: str = "created"
    mutations: list[Mutation] = field(default_factory=list)
    note: str = ""

    def transition(self, new_state: str) -> None:
        allowed = _TRANSITIONS.get(self.state, set())
        if self.state in _TERMINAL or new_state not in allowed:
            raise ValueError(f"illegal journal transition: {self.state} -> {new_state}")
        self.state = new_state


class JournalStore:
    """journal 的持久化：save 原子写；unfinished 列出未达终态的事务
    （协调器据此拒绝并发变更——单操作者假设下的互斥基石）。"""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def new(self, platform_id: str, note: str = "") -> Journal:
        return Journal(tx_id=uuid.uuid4().hex[:12], platform_id=platform_id, note=note)

    def save(self, journal: Journal) -> Path:
        path = self.root / f"{journal.tx_id}.json"
        write_json_atomic(path, asdict(journal))
        return path

    def load(self, tx_id: str) -> Journal:
        data = json.loads((self.root / f"{tx_id}.json").read_text(encoding="utf-8"))
        return Journal(tx_id=data["tx_id"], platform_id=data["platform_id"],
                       created_at=data["created_at"], state=data["state"],
                       mutations=[Mutation(**m) for m in data.get("mutations", [])],
                       note=data.get("note", ""))

    def unfinished(self) -> list[Journal]:
        out = []
        for path in sorted(self.root.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("state") not in _TERMINAL:
                out.append(self.load(data["tx_id"]))
        return out


def default_store() -> JournalStore:
    """默认存储位：data/private/env-journals/（私有层，gitignore 覆盖）。
    仓库根由模块位置推导（runner/environment/journal.py → 上三级）。"""
    repo_root = Path(__file__).resolve().parent.parent.parent
    return JournalStore(repo_root / "data" / "private" / "env-journals")
