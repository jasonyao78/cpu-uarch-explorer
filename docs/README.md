# docs/ 文档地图

> 本仓文档按**类型**分目录，本文件是入口索引。一次实验战役的完整结论链：
> 任务书（`tasks/`）→ 实施计划（`superpowers/plans/`）→ 数据（`../data/public/runs/`）
> → 评审裁定（`reviews/`）→ 传播报告（`reports/`）。

## 目录职责

| 目录 | 职责 | 何时写入 |
|---|---|---|
| `requirements/` | 需求基线与 CHANGELOG | 需求修订时 |
| `adr/` | 架构决策记录 | 架构决策时 |
| `design/` | 框架设计文档 | 设计变更时 |
| `methodology/` | 测量纪律、注释纪律 | 方法学修订时 |
| `tasks/` | 任务书（预注册规范） | 任务立项/修订时 |
| `superpowers/` | 实施计划与执行记录 | 计划编制/执行时 |
| `reviews/` | 评审与裁定归档（外部评审 + 本仓自评判定：Gate/Phase/战役终审） | 评审/裁定产出时 |
| `reports/` | 面向读者的传播报告（同事版/对外版） | 报告产出时 |
| `runbooks/` | 操作规程 | 流程固化时 |
| `learning/` | 个人学习笔记（开源时可整目录移除） | 随时 |
| `reference-materials/` | 外部资料登记（元数据/短摘；全文按版权处置，见根目录 `reference-materials.md`） | 资料纳入时 |
| `cpu-uarch-deep-analysis/` | 源码/原理级深度分析线（common/rob/tlb 子树；独立维护） | 该线自行维护 |

顶层散件（`open-items.md`、`reference-materials.md`、`gem5-d9300-intake.md`）
是制度性单文件，留在 `docs/` 根部不另立目录。

## 单次 run 的派生报告

`data/public/runs/<run>/report.md` + `latency.svg` 是单 run 的机器生成摘要
（`python -m analysis.cli report --run <run目录>` 生成），随数据走、不入
`reviews/`。多 run 块结构（锚点前→主体→锚点后）的战役，其报告层在
`reviews/`（判定）与 `reports/`（传播），不在 run 目录内补 report.md。

## 结论入口索引

| 主题 | 任务书/规范 | 评审/裁定 | 传播版报告 |
|---|---|---|---|
| SM8650 TLB 层级探测（2026-09-30 退役） | `tasks/2026-09-28-sm8650-tlb-hierarchy.md`（v4.4） | `reviews/2026-09-28-sm8650-tlb-hierarchy.md`（终审；分阶段：`reviews/2026-09-29-sm8650-tlb-gate1.md`、`reviews/2026-09-30-sm8650-tlb-phase-{a,b,c,d}.md`） | `reports/2026-09-30-sm8650-tlb/report.md`（四图 + 同事版读法） |
| SM8650 cache/L2（裁定 OPEN/INCONCLUSIVE） | —（证据重审制，无独立任务书） | `reviews/2026-09-28-sm8650-x4-p0prime.md`、`reviews/2026-09-27-sm8650-cache-evidence-reassessment.md`、`reviews/2026-09-28-sm8650-x4-l2-fine-sweep.md`、`reviews/2026-09-28-sm8650-pmu-positive-control.md`、`reviews/2026-09-27-sm8650-llcc-pmu-smoke.md` | — |
| GB10 借鉴迁移评审 | — | `reviews/2026-09-24-gb10-borrow-review.md` | — |

新增战役/主题时在本表加一行；裁定文档进 `reviews/`、传播报告进
`reports/`，两者通过本表互相可达。
