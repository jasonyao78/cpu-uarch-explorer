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
| SM8650 TLB r2 原A1（软件通过、热阻断后冻结为历史） | `tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md`（v1.9.1） | `reviews/2026-10-08-a1-software-exit-and-integration.md`；交接 `runbooks/2026-10-08-sm8650-a1-integrated-handoff.md` | — |
| SM8650 TLB/ROB 第一性原理有限路线（2026-10-11终态；物理参数未识别） | `design/2026-10-11-tlb-page-distribution.md`、`design/2026-10-11-tlb-walk-parallel.md`、`design/2026-10-11-rob-same-address-pair.md` | `reviews/2026-10-11-tlb-rob-identifiability.md`、`reviews/2026-10-11-tlb-rob-goal-ledger.md`、`reviews/2026-10-11-rob-same-address-pair-results.md` | —（本阶段结论、代码/commit索引合并于可识别性裁定） |
| GB10 借鉴迁移评审 | — | `reviews/2026-09-24-gb10-borrow-review.md` | — |

新增战役/主题时在本表加一行；裁定文档进 `reviews/`、传播报告进
`reports/`，两者通过本表互相可达。机制层（系统怎么工作、为什么
这样设计）的快照式分析进 `design/`——TLB 战役的管线增量分析：
`design/2026-09-30-sm8650-tlb-pipeline.md`（基础管线见
`design/ptr-chase-pipeline-analysis.md`，2026-09-25 快照）。

- 同映射cold-head独立反证：设计 `docs/design/2026-10-14-rob-cold-head-interleaved.md`；实施 `docs/superpowers/plans/2026-10-14-rob-cold-head-interleaved.md`；producer `probes/diagnostic/rob_cold_head_interleaved.c`；consumer `tools/diagnostic/rob_cold_head_interleaved_analysis.py`；controller `tools/diagnostic/run_sm8650_rob_cold_head_interleaved.py`；共享parser `tools/diagnostic/owned_roi_packets.py`。

- 同映射cold-head终态：`docs/reviews/2026-10-14-rob-cold-head-interleaved-results.md`；完整匿名counts/SHA及全部原门 `docs/reviews/evidence/2026-10-14-rob-cold-head-interleaved/`。

- Cold-head实际branch PC反证：设计 `docs/design/2026-10-14-rob-cold-head-branch-sites.md`；实施 `docs/superpowers/plans/2026-10-14-rob-cold-head-branch-sites.md`；producer `probes/diagnostic/rob_cold_head_branch_sites.c`、consumer `tools/diagnostic/rob_cold_head_branch_sites_analysis.py`、controller `tools/diagnostic/run_sm8650_rob_cold_head_branch_sites.py`。

- 分支PC机会资格终态：`docs/reviews/2026-10-14-rob-cold-head-branch-sites-results.md`；完整原门、匿名全窗与SHA `docs/reviews/evidence/2026-10-14-rob-cold-head-branch-sites/`。

- 当前packet LDR-PC cache剂量：设计 `docs/design/2026-10-14-rob-cold-head-packet-cache.md`；wrapper `probes/diagnostic/rob_cold_head_packet_cache.c`；consumer `tools/diagnostic/rob_cold_head_packet_cache_analysis.py`；controller `tools/diagnostic/run_sm8650_rob_cold_head_packet_cache.py`；计划 `docs/superpowers/plans/2026-10-14-rob-cold-head-packet-cache.md`。

- 当前packet cache反例报告 `docs/reviews/2026-10-14-rob-cold-head-packet-cache-results.md`；完整匿名差/原门/SHA `docs/reviews/evidence/2026-10-14-rob-cold-head-packet-cache/`。
