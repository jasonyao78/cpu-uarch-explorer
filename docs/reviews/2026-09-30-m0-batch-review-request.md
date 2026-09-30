# M0 批次评审请求（r2 战役 · 数据管道地基）

> 日期：2026-09-30。评审对象：SM8650 TLB r2 战役的 M0 六项（代码侧五项完成，M0-5 剩设备侧 pilot）。
> 评审依据链：任务书 v1.1（`docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md`）→ 前置评审 REV-TLB-R2-20260930（`docs/reviews/2026-09-30-sm8650-tlb-r2-first-principles.md`，13 项发现处置见任务书 §10.3）。
> 意见回执编号：请沿用 **REV-M0-BATCH-20260930** 登记（格式同 REV-TLB-R2：发现 ID + 优先级 + 源码位置 + 复核证据）。

## 1. 上下文（1 页）

r2 战役在第一次战役（`9316853`，291 records 终审终态已定）基础上，用方法增量（三分布对照 / prime+probe / 哈希假设族 / K 链并行度）回答其遗留开放问题。M0 = 数据管道地基里程碑，六项中 M0-1/2/3/4/6 为纯软件项（本次评审对象），M0-5（锚点池）按 v1.1 顺序"先 pilot 后池"依赖设备，不在本次范围。

## 2. 评审范围与证据（两层）

**层 A = `codex/sm8650-tlb-hierarchy-r2`（`3e539c6`，含 REV-M0-BATCH 首层处置；快照标签 `m0-review-snapshot` = `adaac4d`）——状态：已有提交、待验收**

| 提交 | 内容 | 验证 |
|---|---|---|
| `a104dbf` | 任务书 v1.0 立项 | — |
| `69806f6` | 原型 v2.3（F3 三缺陷修复；评审方 UBSan harness 复核通过） | 对方脚本 |
| `3ef8398` | 任务书 v1.1（F1/F2/F4/F5/F6/F7/F8/F9 处置 + R1–R4 登记） | — |
| `6aede89` | 执行端探测方案设计（L0–L3，ROB/ALU-FPU/I 侧） | — |
| `2c07ce1` | REV-TLB-R2 评审归档 + 合成复核脚本 | 脚本可运行 |
| `a9e7cde` | **M0-1**：页策略/smaps 机械抬升为 `probes/common/`（probe_common） | CTest 18 + runner 154 + analysis 140 |
| `0169d78` | **M0-2**：关闭 OI-13（超集放行/命名降级/INCOMPUTABLE 守卫/锚点-主体解耦） | 同上 + 新增 TestMetricContract 4 项 |
| `adaac4d` | **M0-6**：原型角色头 | 两原型编译 |

**层 B = 开发前沿 `codex/sm8650-tlb-r2-m0b`（变基后 `154679b`+；MB-01~04/07 已修）**——状态：已有提交、待验收。

**出口口径区分**：代码侧出口 = 两层 P1 清零 + 层 B 合并入 r2 主分支；**完整 M0 出口 = 代码侧出口 + M0-5（设备侧 pilot 与锚点池）**——M0-5 不在本评审批次。

| 提交 | 内容 | 验证 |
|---|---|---|
| `c89630b` | **M0-3**：PerfWindow（GROUP 原子读，decode 纯函数黄金测试钉 R2 布局） | CTest 19 |
| `5a07722` | **M0-4**：planner `probe_shape` 派分缝 + 分析身份键（旧记录分组行为回归钉住） | runner 156 + analysis 142 + CTest 19 |

复现：`cmake --preset macos-arm64-release && cmake --build --preset macos-arm64-release && ctest --preset macos-arm64-release`；`.venv/bin/python -m unittest discover -s runner/tests -t .` 与 `analysis/tests`。

## 3. 评审问题清单（引导注意力）

**Q1（最高）· M0-2 守卫覆盖对账。** 缺失 PMU 事件 → 派生字段 None + 判据入口守卫 INCOMPUTABLE，但只覆盖 `detect_knee_candidates` 与 `detect_walk_onset` 两个入口。请核查其余 `groups[*]` 字段消费方（Q3 关联判据、THP cohort 分级、fixed-overhead fitting、锚点 `_anchor_groups`、markdown 报告器）对 None 的行为：是命名降级、TypeError 暴死、还是静默错算？要求产出"消费点清单 vs 守卫覆盖"对账表，缺口按 P1 处理。

**Q2 · 与 main 图表线的结构兼容性。** M0-2 使 `bimodal`/派生字段可为 None 并新增 `metric_contract`、`identity` 字段；main 已推进至 `d1e256c`（图表生成线 `459b135` 起）。图表路径对 None/新字段是否安全未验证——请评估兼容性风险等级与是否需要在 r2 合并前补验证。

**Q3 · Linux 路径证据等级。** GuardedMap 是重写实现（非逐字搬）、PerfWindow Linux syscall 层、守卫 VMA 路径——本机 macOS CTest 全部不执行 Linux 分支（零执行覆盖）。请裁定：接受"代码审查级"证据（合并后 Xeon/设备侧验证），还是要求先验再合并？

**Q4 · M0-4 扩展缝充分性。** `probe_shape` 派分 + 身份键是否足以承接 tlb-set 探头（Phase B），还是上线前需要完整 descriptor schema（requested-vs-realized geometry 分字段入 record）？后者若必须，请给最小字段集。

**Q5 · 任务书 v1.1 两处留白。** Q-B"B1/B2 二选一定型"无定型判据；Q-A in-page offset 对照在 ptr_chase"每页一节点"建链下的实现路径未细化。请要求补预注册或给出实现建议。

## 4. 边界声明（诚实底牌）

1. R1–R3（ROB 骨架确定性缺陷）**未修**——属 ROB 项目（main `9a2642c`，r2 基线之外），已由 REV-TLB-R2-20260930 登记跟踪；
2. r2 基于 `9316853`，**main 未同步**（已至 `d1e256c`，含图表线与 ROB 骨架），合并前需显式同步与冲突核对；
3. 契约修订后**旧 49 runs 的重放幂等性未验证**（新分析器跑旧数据应得同一终态）；
4. M0-5 未做（设备侧 pilot 阻塞）；执行端探针（ROB/ALU-FPU/I 侧）仅有设计文档；
5. 评审期间开发在 m0b 堆叠分支继续，两层的评审意见将同时处置。

## 5. 出口标准

M0 完成 = 本批次评审通过（P1 清零）+ 层 A/层 B 合并入 `codex/sm8650-tlb-hierarchy-r2` + main 同步核对。之后进入 Gate 0（事件资格复验 + 冒烟）。
