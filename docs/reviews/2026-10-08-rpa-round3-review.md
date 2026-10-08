# RPA 第三轮收口复核（2026-10-08）

**结论：本包不通过，Phase A v1.8 正式冻结不予确认。三项旧阻塞中，RV2-01 与 RV2-03 关闭，RV2-02 未关闭。** 预热身份和提交卫生已有可复现的行为修正，不再重复要求处理；剩余问题集中在新 A1 判据实现及其标定合同。

## 1. 基线与方法

- 作者回执：r2 `1b47948`，`docs/reviews/2026-10-08-rpa-round3-response.md`；任务书 v1.8 = `14d6307`。
- 实现：m0b `5ccb841`；main `2fa8d5d`。两份被审代码与提交一致；main 的两份既有文档修改未触碰。
- CTest 从 `git archive 5ccb841` 导出干净已跟踪源文件，在临时树内按仓库 preset configure/build/test。
- 用真实 planner/adapter/engine 和已归档 public records 复核兼容；engine executor 为 fake。新增判据反例是合成输入；选址真值直接包含生产 `probes/common/tlb_set_collect.h`，只做整数 VA 运算。
- 不执行 adb、手机二进制或 Linux 内核 perf。NDK 结果为 Android arm64 syntax-only；完整目标构建、部署和设备验证仍归上板 Agent。

脚本：[review_rpa_round3_20261008.py](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/scripts/review_rpa_round3_20261008.py)，复用上轮已提交的 `review_rpa_v2_20261007.py`。证据目录 `docs/reviews/evidence/2026-10-08-rpa-round3/`。

## 2. 三项旧阻塞的裁定

| 旧项 | 本轮裁定 | 独立证据 |
|---|---|---|
| RV2-01 预热身份 | **关闭**，限本轮反例与旧战役兼容范围 | 真实 plan 的 passes=2/4、同 `-n4194304`、异 `-w16384/32768` 记录现在产生不同 digest；cohort 和 main 图表均命名拒绝。51 runs/295 records 去除 identity 元数据后的统计与旧分析器一致，cohort 一致；实际 B/T 合并、四张 SVG 与报告也一致。 |
| RV2-02 A1 消费/标定 | **未关闭** | 代码实体与 11 项测试确实存在，但预测公式、平台/删失、审计/覆盖存在确定性反例；两阶段数值确定程序仍未具体化，见下文。 |
| RV2-03 CTest 注册 | **关闭** | `5ccb841` 包含 `67fb6aa` 的注册。干净提交快照 configure/build/CTest 全过 **20/20**，包含 `tlb_set_collect_golden`。 |

合并单元内检查预热身份的修正达到本轮关闭条件。历史统计不变的口径允许 identity 元数据变化，不能再写“旧 digest 恒 None”。不以元数据演进为理由重新打开 RV2-01。

## 3. RV2-02 未关闭的事实依据

### R3-A / P1：预测混淆收集假设与硬件假设，排除了匹配的 H3/H4

位置：[predicted_hw_sets](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:56)、[adjudicate_h](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:142)。

设 C 为**收集器假设**，T 为**被检验的硬件索引模型**。生产收集器按 `index_C(va)==target` 选页。因此，当 C=T 时，每个选中页必满足 `index_T(va)==target`。这条自一致性由函数定义直接推出，无需目标板测量。

本轮对四个纯区域，实际高字段 `[5,6,7,8]`、target=7、W=12，直接运行共享头中的收集器并用同一生产索引函数计算模型真值：

| 收集 C / 检验 T | 生产定义的 set 集合 | 新消费者预测 |
|---|---|---|
| H1 / H1 | `{7}` | `{7}` |
| H2 / H2 | `{7}` | `{7}` |
| H3 / H3 | `{7}` | `{0,1,2,15}` |
| H4 / H4 | `{7}` | `{0,1,2,15}` |

`target⊕hi` 是特定**交叉模型**的关系，例如 H3 选址在 H1 模型下的 set 编号；不能代替 H3 选址在 H3 模型下的预测。当前 API 只有一个 hypothesis，缺少这一区分。

把全域/两个隔离 scope 都设为同一合格锐曲线、onset=8，`adjudicate_h` 对 H1/H2 输出 supported，对 H3/H4 输出 inconsistent。原因是它强制 `len(predicted)==1`，而其自身错误公式在四个不同高字段下让 H3/H4 永不满足。这是判定偏置，正式采样不能弥补。

**关闭条件**：明确 C/T 两个角色和预测所需的地址信息；用生产收集器生成的实际 VA 作独立真值，覆盖四乘四模型关系，至少钉死所有 C=T 的单 set 自一致性。匹配的 H3/H4 在相同合格曲线下不能仅因高字段不同被拒绝。golden 不能继续以错误公式自身作为 oracle。

### R3-B / P1：平台检查恒不生效，边界/不足数据被升格为 sharp

位置：[classify_onset](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:77)。

`platform_peak` 初始化为首个达到 on 阈值的值，此后只取最大值，因此必有 `platform_peak≥on`。代码却检查 `platform_peak < on×0.8`；对于当前合法阈值，这个拒绝条件永不成立。它没有比较**后续平台相对过渡峰值**的维持程度。

以下均调用本次新入口，结果都是 sharp：

| W 顺序 | 输入 m(W) | 问题 |
|---|---|---|
| 6,8,10,12 | 0.2,8,3,3 | 后续只有峰值37.5%，不满足任务书80%平台规则 |
| 6,8,10,12 | 0.2,4,1.5,1.5 | 回落到 on 以下、floor 以上，仍被当成稳定锐 onset |
| 6,8,10,12 | 4,4,4,4 | 没有观察到低侧，属于左侧删失，不能精确声称 onset=6 |
| 6,8,10,12 | 0.1,0.2,0.5,4 | 只在末点越线，缺少后续平台证据，不能确认 sharp onset=12 |
| 12 | 4 | 单点同样被确认 sharp |

这些例子只检验冻结规则，不是 SM8650 性能数值。现有 11 项测试全绿，不能覆盖上述规则违例。

**关闭条件**：平台统计确实使用预定义的后续点，并与定义的过渡峰值比较；固定过渡“档数”的计数方式、最少点数、缺点/左删失/右删失/区间出口。边界数据不得默认按精确 sharp 处理。增加上述反例和有效正例；保持与任务书逐项一致。

### R3-C / P1：审计与矩阵覆盖未闭合，隔离 scope 并不保证高字段恒定

位置：[gate_record](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:26)、[check_l3_consistency](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:166)。

已验证混域标志能命名拒绝，共同 descriptor 不带一致性标志时可以通过，这部分成立。但：

- gate 放过节点总和与请求 W 不符、节点向量维数不符、缺失实际高字段的输入。前两项是入口防御反例，不能声称 gate 已重验所有审计不变量；adapter 的已有拒绝并未回归失败。
- gate **刻意放过 isolated+purity=0**，理由“只有一个区域不涉及折叠”不成立。合法的64MiB单区域基址可位于256MiB窗口的+224MiB。生产收集器的隔离 H1 选址确实跨实际 hi={90,91}，在 H3 模型下对应两个 set={92,93}。区域数为1不等于高字段数为1；这会破坏隔离对照依赖的常量置换关系。
- `check_l3_consistency({})` 和只有 target7 的输入均返回 consistent=true。缺少预注册的四个 target 被当成合格一致性。只比较 verdict 字符串也未定义 W={8,12} 的实际比较量。
- 缺少 scope1 时 L1 helper 仍可返回 supported。当前仅交付分散纯函数，尚无 records→审计→每case统计→L1/L2/L3覆盖校验→H* 的完整入口；检索生产 analysis/scripts 未找到调用该模块的组合路径。纯函数可以是 API，无需强制 CLI，但需要一个明确承担全链合同的顶层函数/调用路径。

**关闭条件**：把实际 record 接到必经 gate 和统计路径；按约定验证请求/realized 维数、总和、类型、实际高字段及有效样本。高字段不纯的隔离数据在依赖折叠预测时命名降级，或提供足以证明所选地址纯度的更细审计。显式校验scope、W、L2种子与四target的覆盖；缺失/拒绝不得变成通过。L3 两点比较应写出独立的比较量/容差。交付 fake runner→record→完整 A1 判定的正负金样，而不只是逐函数断言。

### R3-D / P1：两阶段隔离原则认可，数值确定程序仍只有“复核并冻结”

位置：[任务书v1.8](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md:174)。

v1.8 明确标定数据不进入正式 H* 曲线，这项补充接受。但未给出如何由标定输入得到 on/平台比、允许取值、通过/失败或 STOP 的决策程序；新增模块也没有相应冻结接口/产物。“用标定块+合成曲线推演复核数值”仍保留未约束的选择自由度，不能据此声称确定程序已冻结。

现有2-case块只有空窗与scatter W=8，能验证底噪和负控，不能单独识别冲突过渡与平台维持比。这点在上轮已明确，本轮仍沿用相同标定块。

**关闭条件（仍是上轮的两种选项）**：①预先固定现有数值，标定只做明确的资格核验，失败停块不调数；或②预注册专用CALIBRATION输入、数值选择/失败规则，产出可审计的阈值与配置/代码/数据锚定，之后独立验证。程序可以是可审查的决策表，不强制写成函数；评审方不代指定阈值。先修判据数学错误，再作数值标定。

## 4. 新鲜回归与真实数据兼容

| 检查 | 本轮独立结果 |
|---|---|
| m0b runner | 192/192 |
| m0b analysis（含作者A1金样） | 169/169 |
| main analysis | 171/171 |
| main图表/m0b分析器组合 | 25/25 |
| 干净5ccb841 native preset构建/CTest | 全过，20/20 |
| NDK27.2三源码syntax-only | 通过 |
| 旧战役51runs/295records | 统计与cohort均51/51一致，identity元数据除外 |
| 实际固定名单图表路径 | 四SVG、report.md共5/5内容一致；B/T合并cohort一致 |

真实图表比较使用旧分析器 `3e539c6` + 图表 `9093f4a` 对当前 m0b分析器 + main图表；消费固定public名单，实际执行load_campaign/build_figures/build_report。以上支持预热兼容项关闭，不能代替新A1判据正确性。

## 5. 行动项、边界与出口

1. 优先修 R3-A 的角色区分与生产地址真值，再修 R3-B 的分类/删失规则；用独立oracle改写金样。
2. 组合完整A1 record入口和覆盖门，关闭 R3-C；统一任务书、API返回语义与正负集成样本。
3. 选择 R3-D 的一个最小标定合同，预注册后再交上板Agent执行；本轮不要求现在给出未经测量的阈值。
4. 锁定新提交，软件回归和两层/main整树集成后重送审；通过后再开展设备标定、数值冻结及独立正式矩阵。A3继续条件后置。

已关闭RV2-01/03不因第二项返工而重新打开。残留P2：`_residual_digest`的“旧记录恒None”docstring与新实现矛盾；C++金样跨界注释仍沿用“64MiB必不跨256MiB”的错误说明，需随A1几何修复纠正。main整曲线首次承载非legacy条件时，需验证跨buffer的条件标签/分系列规则；本轮已验证的是旧名单兼容及同合并单元拒绝，不扩展为任意新实验图表已合格。

**最终裁定：两个旧阻塞关闭，一个旧阻塞未关闭；本包不通过，v1.8不得宣告正式冻结。** 可以继续软件修复、集成和标定包准备；手机验证仍由其他Agent执行。

## 6. 复现

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python \
  /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/scripts/review_rpa_round3_20261008.py \
  --tree /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b \
  --main-tree /Users/michaelyao/workspace/cpu-uarch-explorer \
  --r2-tree /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2 \
  --out /private/tmp/rpa-round3-diagnostics.json
```

证据：`diagnostics.json`、`runner.log`、`analysis.log`、`main-analysis.log`、`clean-ctest.log`、`ndk-syntax.log`、`verification-manifest.json`。NDK成功日志为空，命令与退出码由manifest锚定。诊断退出码0只代表完成执行；具体反例和裁定以上表为准。
