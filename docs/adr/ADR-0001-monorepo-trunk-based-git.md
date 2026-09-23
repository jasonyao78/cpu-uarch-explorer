# ADR-0001: Monorepo + trunk-based Git 过程管理

- 状态：已接受（2026-09-23）

## 背景

项目为单人主导的研究型仓库，未来转开源，要求实验可追溯（"某个结论出自哪版代码"）。备选：GitFlow（流程重，release 分支对基线管理不如 tag 直接）、无分支直推 main（历史不可回溯，违背可追溯原则）。

## 决策

- 单一 monorepo；gem5 等外部依赖以 submodule 置于 `third_party/`（见 ADR-0004）。
- `main` 为唯一长期分支，受保护；短生命周期分支前缀 `feat/ fix/ docs/ exp/ probe/`。
- Conventional Commits（`feat(probe): …`、`docs(requirements): …`）。
- 单人开发也走 PR + squash merge，评审记录即决策痕迹。
- 需求基线以 tag 管理（`req-v0.3`、`req-v0.4`…），需求文档入库 `docs/requirements/` 并维护 CHANGELOG。
- 数据原始层不进 git（`data/private/`、`data/restricted/` gitignore；原始 JSONL 由运行产生，仓库只放派生报告与参考数据）。
- pre-commit 钩子：secret 扫描 + SPDX 头检查（后续迭代接入）。

## 后果

- 历史清晰、基线可 tag 回溯；代价是单人 PR 流程带来少量仪式开销，可接受。
- CI（Xeon self-hosted runner）属 v0.4 之后事项，不阻塞本基线。
