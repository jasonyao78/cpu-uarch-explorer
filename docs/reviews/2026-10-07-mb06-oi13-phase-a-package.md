# 送审包：MB-06 关闭 + OI-13 状态 + Phase A 矩阵冻结（2026-10-07）

致评审方。代码基线：**m0b `0b8c8b1`**（含 M0-4b 移植 `fb746c6`、充电态协议 `31c333a`、pilot 数据 `8fba5c3`）、main `9093f4a`、r2 任务书 v1.5（本文档同提交）。本包对应收口复核 §5 的"首个依赖新条件的 Phase A 采样前完成"的最小交付：**MB-06 descriptor 最小契约关闭 + OI-13 状态终稿 + Phase A 正式矩阵设计冻结**。

## 1. MB-06 关闭对账

| 收口复核要求 | 处置 | 证据 |
|---|---|---|
| bool True 与 integer 1 直接输入仍合并 | **已修**：分析器分组键采用**类型规范身份**（bool 先于 int 判定；键形 (type_tag, repr)）；同时引入**类型规范残差**——`_IDENTITY_PARAM_KEYS` 之外的任何 params 差异（含类型差异）也阻止合并 | 新测试 `TestDescriptorCanonicalIdentity`：True/1 → 2 组；H1/H2 → 2 组；loads_per_slot 8/16 → 2 组；旧记录仍 1 组 |
| requested→canonical→执行→realized 纵贯 | **已修**：adapter `parse_output(stdout, stderr, expected=None)` 第三参携带 plan case_params（engine 传入）；tlb_set 探针自描述字段（set_hypothesis/set_target/set_target2/set_window/set_rounds）与请求不一致或未报告 → ParseError（执行漂移 fail-closed）；`set_domain` 为 realized-only 只入档不核验 | 新测试：一致通过 / target 99 vs 7 拒 / 缺自描述字段拒；schema README 登记契约 |
| params 类型规范化与 canonical identity | 类型规范标签 + 残差身份如上；**报告面 identity 字典保持 legacy 原值**（兼容性见 §3 重放） | `runner/schema/README.md` 2026-10-07 两条登记 |
| probe_shape 与身份维度 schema 登记 | §5.3 已登记（2026-10-01），本次补登记 descriptor 核验契约 | 同上 |

**边界声明**：MB-06 的关闭范围 = 评审收口复核 §4 表格的"最小 descriptor 契约"（纵贯一致性 + 类型规范身份）。pilot/tlb_set 记录的判读仍走直接提取（无 latency 帧，不进 `analyze_records`）；Phase A 判读脚本将消费 params + realized descriptor，不新建统计判据。

## 2. OI-13 状态终稿

**分析侧（m0b）已关闭**（非本次新修，是 M0-2 批次已落、经评审 seams 脚本多轮验证的部分）：`analyze_records` 对超集 metric 集放行（多出指标按名忽略、per-observation 原样保留）；缺失项命名降级（派生字段 None + `group.metric_contract.missing` 逐名登记 + 判据入口 INCOMPUTABLE 守卫）；latency 缺失保持硬错误（无样本帧）。C2 的"缺失集进分组键"保证组内样本集合恒一致。

**剩余唯一事项 = merge 时更新**：main 侧 `analysis/tests/test_tlb_figures.py::test_missing_metric_fails` 的旧契约期望（缺指标 → 退出 1）在 r2 合并时改为命名降级口径（1 failure 为预期口径差异）——任务书 §11-9 已预登记。此事项不阻塞 Phase A（Phase A 不消费 main 图表路径）。

## 3. 回归证据

| 检查 | 结果 |
|---|---|
| m0b runner / analysis / CTest | **182 / 153 / 19** 全过 |
| 战役 runs 重放（旧分析器 `3e539c6` vs 本次） | **51/51 逐字一致**（49 战役 + 2 充电态锚点；含 cohort 分级）——类型规范身份对旧数据零扰动 |
| 评审反例复现 | True/1 与 H1/H2 合并缺陷 → 现为 2 组（§1 表） |
| NDK 语法检查 | 通过（`0b8c8b1` 未改探针 C++，继承 `fb746c6` 检查） |

## 4. Phase A 正式矩阵设计冻结（任务书 §5.5 全文）

- **A1 H 假设裁决**（16 cases）：H1–H4 × target {7,42,100,200}，W=12，r20，regions 4；判别式 = **区域隔离测试**（H3/H4 折叠 VPN[23:16]，隔离区域内收集会改变集合隶属 → onset 移动；H1/H2 不移动）+ 全域 onset 跨 target 一致性；多候选并存按 Q-C EQUIVALENT_ON_TEST_DOMAIN 终态登记。
- **A2 way 数精测**（14 cases）：W [6..12] × seed {42,1337}；onset = §5.4 冻结判据（首个 0x2d ≥3.0/轮）；≥2 seed 一致才成立；H 依赖 A1 裁决后由分析侧拍板写配置。
- **A3 set 数饱和**（10 cases）：N [1..256] set × 8 页/set；0x2d onset 的 N 与 TRM 256 比较；命名权限 = 与 TRM 一致才允许"结构验证通过"。
- 每块前 2-case 标定复测 + 锚点夹块（charging-thermal）；停止线：标定不过即停块。

**请评审事项**：① MB-06 关闭与 OI-13 状态终稿复核；② Phase A 冻结判据的预注册确认（特别是 A1 区域隔离判别式与 onset ≥3.0/轮 阈值）——判据一旦确认，Phase A 配置随即写就，等 MB-03/07 清零 + 两层集成后执行。
