# 评审第三轮阻塞项修复回执（2026-10-08）

致评审方。输入：[v2 复核](2026-10-07-rpa01-05-v2-review.md)（r2 `17a09ab`）。修复基线：**m0b `5ccb841`、main `2fa8d5d`、任务书 v1.8**（r2 `14d6307`）。三项阻塞逐条处置。

## 1. warmup_passes 立场被推翻——已接受并修正（非边界论证，是行为修正）

贵方反例成立：planner 可合法生成同 `-n 4194304`、异 `-w 16384/32768` 的两个 case（我方"passes⇒loads 派生故不可生成"的前提错误——warmup 与 loads 独立派生）。修正：

- `warmup`/`warmup_passes` **移出排除集** → 进 `residual_digest` → 该反例现在 digest 不同 → 出口可见 + 拒绝（测试 `test_warmup_counterexample_rejected` 钉死）；
- 守卫语义同步改为贵方 RPA-04 关闭条件的原文口径："**按完整身份分系列/比较，或命名拒绝**"——**合并单元内一致性检查**：同条件合并合法，不同条件命名拒绝。粒度 = 合并单元（cohort: buffer×backing；图表: buffer），因为 warmup=f(passes,buffer) 按 buffer 合法不同——全局粒度会误杀历史（我方第一版就踩了，50/51 拒绝，改单元粒度后 51/51）；
- **历史兼容实证**：钉死 THP B/T 合并对 warmup_passes=2 双方一致、单元内 warmup 恒均匀 → 51 runs 统计量与 cohort 输出**逐字一致**（identity 元数据除外）；main 图表钉死测试集 24/24 路径同等验证。

## 2. 阈值程序与消费入口——已交付为代码

贵方裁定"认可独立标定后冻结，但当前交付不足"——缺口已补（m0b `5ccb841`）：

- **`analysis/sm8650_tlb_a1.py` = 判据消费入口实体**：`gate_record`（混域 / scope 特定 active / purity / 审计不变量，逐项命名拒绝）、`predicted_hw_sets`（按 realized `set_region_vpn_hi` **实际值**计算预测分区）、`classify_onset`（量化锐/退化/区间）、`adjudicate_h`（全域/隔离配对判定）、`check_l3_consistency`（L3）——合成金样 11 项全绿；
- **阈值确定程序**（任务书 v1.8 §5.5 两阶段预注册）：程序与判据结构现已冻结；唯二数值（on 阈值、过渡/平台比）为候选值，**A1 首块标定块采集后按承诺程序复核冻结**；**标定数据与正式判定数据隔离**（标定块不进 H* 判定曲线，只用于数值冻结与门限验证）；冻结后任务书留修订痕。

## 3. CTest 注册补提交

`tests/CMakeLists.txt` 的金样注册被 `git add probes runner` 漏盖（根目录 tests/ 不在两目录下）——**已补提交** m0b `67fb6aa`，干净快照重跑 **20/20**（19 原有 + 金样）。送审基线 `5ccb841` 包含该提交。

## 回归证据

| 检查 | 结果 |
|---|---|
| m0b runner / analysis / CTest | **192 / 169 / 20** 全过（新增 A1 金样 11 项） |
| main analysis | **171/171**（守卫语义变更 + 钉桩测试同步更新） |
| 战役 51 runs 重放 + 单元守卫 | **51/51 逐字一致**（THP B/T 合并对通过） |
| NDK syntax-only | 通过 |

请复核三项关闭 + Phase A v1.8 冻结。清零后我方执行整树集成（行动顺序第 5 条）。
