# SPDX-License-Identifier: Apache-2.0
"""环境事务模型：host 级状态变更（governor/hugepage 等）的受控应用与恢复。

2026-09-25 讨论裁定（OI-9 蓝图"借模型、重新实现接线"；GB10 环境事务
设计为参照，不照搬其未完工实现）：锁频等变更是 **host 级状态突变**，
不走 command_prefix（prefix 只影响子进程），必须走事务——

  未完成事务阻塞 → 加锁 → journal 记录 before 值 → apply → verify
  → 执行测量 work() → 逆序 restore → verify restored → journal 终态

崩溃/中断（SIGINT→KeyboardInterrupt）自动走恢复路径；journal 持久在
data/private/env-journals/（本地，永不入库），崩溃后可用
`runner.cli env restore` 人工重放。sudo 不在非交互通道里挂起等待：
apply 失败给结构化提示（NOPASSWD sudoers 配方或手动执行）。

已知简化（留待后续硬化）：单操作者假设（journal 阻塞 + flock 劝告性
检查）；SIGTERM 不转换（仅 SIGINT）；远端锁依赖 ssh 断连时远端
SIGHUP 释放 flock。
"""

from .coordinator import (EnvironmentError_, execute_environment_tx,  # noqa: F401
                          reconcile_unfinished, restore_transaction,
                          specs_from_host_requirements)
from .journal import Journal, JournalStore

__all__ = ["EnvironmentError_", "Journal", "JournalStore",
           "execute_environment_tx", "reconcile_unfinished",
           "restore_transaction", "specs_from_host_requirements"]
