# REV-M0-BATCH 收口复核回执（MB-03/07 清零申请）

日期：2026-10-01。输入：评审[收口复核](2026-10-01-m0-closure-review.md)（c66c792）。代码基线：**m0b `ee736ed`、main `9093f4a`**、r2 本文档提交。本轮只处置 MB-03/07 两项 P1 + MB-02 口径残留；MB-05/06 维持原登记触发点（见末节）。

## 1. MB-03 处置（m0b `ee736ed`）

评审三个反例逐条处置，全部改为 **plan 期受控拒绝或真实消费**：

| 反例 | 处置 |
|---|---|
| §2.1 chains=1/2 记录成两个条件、argv 完全相同 | **撤 `_PASSTHROUGH_PARAMS`**。chains/chain_distribution/node_offset_policy/mapping_span_kb 原生探针无 argv 协议——语义未实现的维度不再进 case_params（证据通道），sweep/fixed 它们在 plan 期 `does not consume` 命名拒绝；探针真实实现后经 shape deriver 登记消费再放行 |
| §2.2 通用形状 KeyError('buffer_kb') + pmu_events 被拒 | chase 几何读法移入 `ptr_chase` 分支，通用形状零 chase 隐含契约；通用 case_id = case_params 规范化枚举：int/str 直进段、**结构化参数（pmu_events 列表）canonical JSON 的 sha256-12 进段**、bool fail-closed（不与 int 1 混淆） |
| §2.3 未知 swept 参数靠进 ID 段静默放行 | swept 参数的 ID 段机制收紧为 **消费白名单** `_CHASE_ID_SEGMENT_PARAMS`（= deriver 真实输入 loads_per_slot/min_loads/warmup/warmup_passes，即 overhead 触发案例的既有行为）；`unsupported_dimension` 类未知 swept 参数落入 leftover 命名拒绝。另补：ptr_chase 形状 swept pmu_events 命名拒绝（结构化值进不了模板 ID，不给"撞重复 id 守卫才炸"的模糊出路） |

**评审原话采纳**："保留未来扩展缝无需提前实现所有 K 链探针，但至少验证两条不同的新形状条件走到不同执行入参，并有 realized 自证；未支持条件受控失败"——两条不同 ways 的通用形状 case 现在生成不同 id（`exp:c0-ways8` / `exp:c0-ways9`），不同 pmu_events 列表生成不同 hash 段（钉桩测试覆盖）。

## 2. MB-07 处置（main `9093f4a`）

采用评审给的**方案一**（历史终审引用与当前缺点图明确区分，撤虚假重判声明）：

- 缺点数据模式（skipped 非空）：报告顶部加警示横幅"缺点数据再生成——未对缺点数据执行重判"；终态表标题改为"**历史终审引用：2026-09-28 冻结；非本数据集重判**"；
- **冻结判定区间按当前曲线覆盖就地标注**：`main()` 用当前 refill/walk 曲线评估 knee 区 [480,4096] KiB 与 onset 区 [10240,12288] KiB 的支持度（`claim_support`），不受支持的区间在终态表与图读法中原地加"〔当前曲线不支持〕"标注；`claim_support=None`（未评估）按全不支持保守标注；
- "相关区间的科学结论按可用点重判"的虚假声明**撤除**，数据局限段改为"未对缺点数据执行重判……完整网格恢复前不应引用被标注内容"；
- **完整数据路径逐字不变**（所有改动门控在 degraded 分支，回归见 §4）。

不采用方案二（接入实际判据重分析）：图表附件的职责是复现冻结终审的图表附件，重判入口在判定分析器，不在图表模块（评审明示"不要求图表模块新建一套统计判据"）。

## 3. MB-02 口径残留（顺手清零，非新增范围）

`probes/common/perf_window.h` 头注第 8 行"按身份（非位置）"、第 13 行"窗口 delta"与已实现层次矛盾——改为准确声明："事件→值映射（实现层次见契约注，不再宣称按身份非位置）"；mux 判定已具现、**窗口时间差分/有效性 API 尚未交付（MB-05 后置）**。任务书 M0-3 事件口径表述随 §10.3 同步。

## 4. 回归与复核证据

| 检查 | 结果 |
|---|---|
| m0b runner | **161/161**（+3：未实现语义参数拒绝 / 未知 swept 拒绝 / 通用形状无 chase 几何 / 通用形状结构化 ID / swept pmu_events 拒绝等 5 新测试，替换 4 个旧钉桩） |
| m0b analysis | **149/149** |
| m0b preset build + CTest | **19/19** |
| main analysis | **170/170**（+3：缺点标注 / 保守缺省 / 完整数据不变） |
| 评审反例复现（本机合成） | chains/unsupported → RunnerError；tlb-set 通用形状 → 正常 id；通用形状+pmu_events → hash 段 id（§1 表） |
| **评审验收场景端到端**（m0b 分析器 + main 图表 overlay，复刻"删除 4096≤buffer<32768 walk 指标、保留最大端点"） | rc=0；22 个降级点 stderr 披露；报告含横幅、"按可用点重判"声明**不存在**、onset 区间被标注、Q2a 终态行不再原样出现、knee 判定保留（7/7 检查通过） |
| `review_m0_closure_perf.py`（MB-01/02/05 层，未动） | 全项符合（读长 4 规格、名称对齐、move 关闭 2 FD） |

说明：评审的 `review_m0_closure_seams.py` 在基线上会如期在 `chains_sweep` 步抛出（该步期望旧行为）——它钉的是缺陷现场，不是修复后行为；修复后证据以上表"评审反例复现 + 验收场景端到端"为准。若评审希望保留该脚本可复跑，可在 `chains_sweep`/`unsupported_sweep` 两步包 `attempt()` 后重跑，预期 `ok=False, exception=RunnerError`。

完整 M0 其余验收边界（Linux/SM8650 执行证据、短窗能力真机、S6 GROUP read）按评审 c66c792 的分工保留：上板验证由其他 Agent 负责，已有独立的冒烟证据链（runbook §6：S1–S5 全过、S6 跳过登记）。

## 5. MB-05/06 时点确认（维持原登记，不扩大本批）

- **MB-05 窗口差分/有效性**：首个短窗 pilot 前交付——M0-5 pilot 已手动启动（CALIBRATION/PILOT 标签、锚点池只用 pilot 数据），**正式 Phase A 矩阵冻结前**完成；
- **MB-06 descriptor 最小契约**：首个依赖新条件契约的 Phase A/K 链采样前交付。与本批 MB-03 的衔接已就位：plan 侧未实现语义维度现在受控拒绝，K 链等维度一旦探针实现，经 shape deriver 登记消费即接入——descriptor 契约（requested→canonical→realized→identity 纵贯）在那时闭环。分析器侧 identity 分组（bool/int 合并等）随 MB-06 一并处置。

请评审按 §1/§2 两项 P1 复核清零，MB-03/07 清零后执行两层集成与 main 组合验证（本批两层的基线即待合并提交）。
