# MB-06 / OI-13 / Phase A 送审包复核（2026-10-07）

**裁定：本包不通过；Phase A 正式矩阵暂不冻结。** MB-03、MB-07 的原收口问题可关闭；MB-06 的 bool/int 分组子项和五字段核验子项成立，但纵贯契约尚未完成。OI-13 只能保持部分关闭。当前有五项 P1，不能将历史 MB-03/07 清零等同于本次代码与正式采样出口全部通过。

输入：r2 `d086173` 的[送审包](2026-10-07-mb06-oi13-phase-a-package.md)与任务书 v1.5；实现 m0b `0b8c8b1`；图表 main `9093f4a`。本次只评审代码、预注册设计、合成反例和已归档公共记录。**没有执行 adb、手机探针或目标 PMU 验证**；交叉编译与设备验收仍由上板 Agent 完成。

## 1. 关闭对账

| 项 | 裁定 | 当前证据与边界 |
|---|---|---|
| MB-03 原消费/通用 ID 缺陷 | 可关闭 | chains/未知 swept 参数受控拒绝；新形状不依赖 chase 的 buffer/stride；结构化 PMU 参数可进通用 ID；真实 tlb_set 的 W=4/12 进入不同 argv。四项针对性回归通过。闭环不表示 K 链 kernel 已实现。 |
| MB-07 原缺点报告缺陷 | 可关闭 | 删除 4–32 MiB 之间的 walk 指标、保留两侧点后，CLI 成功且披露 22 个跳过点；明确“非本数据集重判”，将历史 onset 区间标为“当前曲线不支持”。完整旧数据四图+报告 5/5 文件字节一致。 |
| MB-06 类型分组子项 | 成立 | True/1 分为两组；残差参数不同也在第一次聚合中分组。完整纵贯关闭不成立，见 PA-01/02。 |
| MB-06 requested→realized 子项 | 部分成立 | set_target 99 vs 请求 7 正确拒绝；五个已登记字段的检查已接线。模式绕过、其他关键参数、realized 入档仍有缺口。 |
| OI-13 | 部分关闭 | 原非 G0 接纳、锚点解耦与缺项降级成果可保留；extras 派生/消费尚未实现。所谓“唯一余项=图表 1 failure”与现状不符。 |
| Phase A | 不予冻结 | A1 的实际地址域、判别式及矩阵缺口；A3 的实验范围和估计量不支持目标结论。 |

两层集成可用于消除缺陷、建立组合回归，但本裁定不授权将当前矩阵作为已冻结的正式采样计划。历史 M0 评审文档保留，最新状态以本复核及 open-items 的增补为准。

## 2. P1 发现与最小关闭条件

### PA-01：残差身份在 AnalysisResult 出口丢失，下游重新合并实验条件

实现位置：m0b `analysis/sm8650_tlb.py:854–903,1153–1160`；main `analysis/tlb_figures.py:90–109`。

`_residual_identity(params)` 进入内部分组键，却没有进入导出的 `group.identity`；后者仍只有四个旧维度。samples 的内部 identity 也被删除。cohort 与扫描曲线的拒绝守卫只读导出的 identity，无法看见 set_hypothesis / loads_per_slot 等残差条件。

合成复现：同 buffer/seed/backing、set_hypothesis=1/2 的两条合法 latency 记录，初次聚合为两组，各自 cycles/load 中位数约 **0.03128 与 100**；两组导出 identity 均为四个 None。图表将它们合成 **50.01564** 的一个点，cohort 将两组样本拼为 **4 个样本**。以上数值仅为 **SYNTHETIC 反例**，不是硬件测量。

这违反“任何 params 差异阻止合并”的纵贯承诺，也绕过 MB-04 的已有守卫；“分成两组”测试不能证明消费链安全。tlb_set pilot 本身无 latency 帧，这个反例针对分析器公开契约和后续扩展的合法输入，不要求强塞 pilot 到旧分析器。

**关闭条件**：导出完整的类型规范身份或可审计 descriptor 身份；所有二次聚合按身份分系列，或对未支持的身份受控拒绝。回归必须从 analyze_records 产出贯穿 cohort/图表/报告消费点，不能只检查 group 数量。

### PA-02：descriptor 可以绕过核验，且 realized 域没有进入结构化记录

实现位置：m0b `runner/adapters/ptr_chase.py:187–280`、`runner/engine.py:307`；探针自描述 `probes/cache-mem/ptr_chase.cpp:610–627`。

复现结果：

- 请求 tlb_set，输出只有 `latency_ns=1.25`，仍被当作 legacy chase 成功解析；expected 检查只在 stdout 自报 `mode=tlbset` 后执行。
- 请求 regions=4、filler=512、scatter=1、seed=42，输出 regions=1、filler=0、scatter=0、seed=99，仍成功。
- 请求含 `l2d_tlb_refill`，输出只含 L1 事件，仍成功；没有针对缺失关键判据事件的命名状态。
- `set_domain=single-region-fallback` 被接纳本身可以是合法降级，但该字段与其余 self-description 都未随 parse_output 返回。14 条已归档 pilot 记录中，**0/14** 序列化含 `set_domain`。原始 stdout 仍可能可审计，不能把它等同于“realized-only 只入档”或将来直接消费 record 的 realized descriptor。

这里还存在两种不同事实：输出 `set_regions=4` 是请求/预约数量；即使核验了它，也不能证明四个区域实际参与访问（PA-03）。

**关闭条件**：由请求决定解析形状并验证输出模式；覆盖会改变实验条件的参数与必要事件；将 realized 域、实际访问几何和有效性保存在结构化记录中，requested 与 realized 分开。fallback 可以保留，但必须命名降级并禁止用于 H 高位判别。schema 登记应对应实际持久化路径及端到端测试，不能只登记预期行为。

### PA-03：多区域预约不等于多区域激励，当前收集器会在首区域取满

实现位置：m0b `probes/cache-mem/ptr_chase.cpp:260–280,378–412`。

`collect_set_addrs` 顺序遍历区域，第一区域找到 need 个地址即停止；没有每区域配额或 active-region 断言。复核直接提取并编译生产选址函数，使用与四区域预约布局相容的数值 VA，不解引用、不执行 PMU。

对 **H1–H4 × target {7,42,100,200}，W=12** 全部 16 条输入，结果均为：

```text
selected=12 active_region_mask=1 same_as_isolated0=1
```

四区域全域收集得到的地址与仅 region 0 收集逐个相同。因此原始输出 `set_domain=multi-region` 只证明预约分支，不能支持“F4 高位等价已打破”。这不是断言所有 ASLR 布局必定如此，而是合法布局上的生产代码反例，已经足以否定当前保证。

**关闭条件**：按显式配额/交错规则跨高字段取样；验证实际访问地址跨越预期高字段，输出 active-region 计数/每区域节点数及候选集合摘要。对不足域命名降级；在 H 判据入口校验实际域，而不是仅看预约成功字符串。手机验证可补证，但不能修复逻辑上未激励的输入域。

### PA-04：A1 区域隔离判别式不是充分判别式，16 cases 也未包含所需对照

任务书 `§5.5:160,165`；四个 H 的公式在 m0b `ptr_chase.cpp:245–251`。

第一性原理：若区域内 `c=VPN[23:16]` 恒定，按代码定义有

```text
H3(vpn) = H1(vpn) XOR c
H4(vpn) = H2(vpn) XOR c
```

这只是给 set 编号加固定置换；区域内冲突等价类不变。固定 target 时地址成员可能改变，**成员改变不推出 conflict onset 必然移动**。隔离后某候选没有移动，也不能据此拒绝它。可识别性必须来自实际跨区域地址的不同冲突关系及受控对照，而不是公式是否含高位。

当前 A1 只有 H×target、固定 W=12；没有“全域 vs 区域 k”的配对 case，也没有 W 扫描，因而无法产出文中的 onset 曲线移动。收集器也没有隔离选择参数。总则两个 seed 与 A1 16 cases 的关系未写清。

**关闭条件**：先用具体 VA 给出 H 候选预测的冲突分区/可区分对照表；列出跨区域与隔离操作、扫描或明确的固定 W 估计量、配对/重复/分配规则及可辨认条件。不可区分时保留 EQUIVALENT_ON_TEST_DOMAIN；不得按 target 数或高位公式本身授予唯一 H。修订 case 数和预算后再冻结。

### PA-05：A3 没有越过声称的容量线，且单 set 冲突不能识别 set 数

任务书 `§5.5:162,167`；native/runner 当前接口只支持目标 set、可选 target2 和 scatter，没有任意 N 个 set×每 set W 个节点的构造/输出。

按本计划自己的假设，`N≤256`、`8 页/set`，所以 **8N≤2048**；不可能观测设计所声称的“总数超过 2048 时跳变”。无需假定真实 SM8650 的结构即能证明这个范围错误。与此同时 pilot 文档已报告 W=8 的单目标 0x2d 超过 3/轮；把同样的每 set 负载复制到 N 个集合，可能从 N=1 起就越阈值，不能将首次越阈值的 N 当作总 set 数。

set/way/capacity/replacement/filler 压力是不同因素；TRM 数字匹配只是与一个模型相容，不足以“结构验证通过”。锚点延迟 regime 带也不能直接充当 N 的误差带。

**关闭条件**：明确估计量究竟是整体 translation reach、有效冲突集合数还是 set 数；实现并审计 N-set 构造，控制每 set 占用与 filler 竞争，覆盖目标阈值两侧，给出排除 per-set 替换及其他层级瓶颈的对照。若当前方法不可识别 set 数，应保留有效冲突/容量区间结果或 MODEL_UNIDENTIFIABLE，而不是扩大命名权限。

## 3. P2 与口径修订

| 项 | 事实 | 处置建议/触发 |
|---|---|---|
| PA-06 OI-13 全关闭口径 | extras 仍只在 metric_contract 中列名，未派生/消费；adjudicate_q3 的 `data_miss_collinearity_checked` 仍恒 False。任务书 M0-2 与 §11-9 自己也保留此余量。main+m0b 图表测试当前 **24/24**，不是 1 failure。 | 状态保持部分关闭；允许明确拆分并后置 extras 能力，但必须保留独立待办和触发条件。移除已过时测试叙述，禁止为凑“零失败”把整条曲线无观测仍应报错的测试改成成功。正式新事件组使用前完成对应消费路径。 |
| PA-07 `repr` 不是递归 canonical identity | 同一 JSON 对象 `{'a':1,'b':2}` 与反序插入形式被分为两组，语义相同、repr 不同；会因读写顺序而改变分组与样本量。 | 采用保留类型的递归规范表示；对象键排序、列表顺序保留。正式使用结构化 descriptor 前覆盖此例。 |
| PA-08 adapter Protocol 尚未演进 | engine 已统一调用第三参，`runner/adapters/base.py:22` 的 Protocol 仍只声明 stdout/stderr。当前唯一实际 adapter 和测试夹具已改，故不宣称现有 runner 暴死。 | 同步协议/注释和新 adapter 契约测试；新增 ROB/ALU/FPU adapter 前必须完成。 |
| PA-09 3/轮阈值的判定单位未闭合 | pilot 可用于提出操作阈值，r20 固定与冷轮剔除有明确价值。但“首个/持续≥3”未定义 10 repetitions 的汇总、置信/边际状态、非单调曲线与左右删失；A1/A3 两 seed 的计数也不明确。 | 3/轮可保留为候选操作阈值，不作物理 way/set 证明。正式采样前冻结按独立进程/分配汇总的决策规则；两 seed 一致是复现条件，不能替代不确定性处理。seed 当前主要改变 filler 顺序，不能假定目标链顺序也被随机化。 |

## 4. 本轮验证与证据等级

| 检查 | 本轮结果 | 证据等级 |
|---|---|---|
| m0b analysis | 153/153 | macOS 软件回归 |
| m0b runner | 182/182 | macOS 软件回归；受控环境夹具使用独立临时锁 |
| m0b macOS release configure/build + CTest | 成功；19/19 | 非 Linux 执行分支，不证明 GROUP read/guard VMA 在手机上的行为 |
| main analysis | 170/170 | main 自身软件回归 |
| main 图表 + m0b analyzer 组合 | 24/24 | 导入组合，不等同于实际 Git 合并完成 |
| MB-03 针对性路径 | 4/4 | 通用 ID/结构化 PMU/真实 tlb_set argv/未知参数 |
| MB-07 onset 缺口 | 明确历史引用 + 不支持标注 | 合成端到端消费链 |
| 对旧 `3e539c6` 战役重放 | 51 runs / 295 records；规范化 AnalysisResult 51/51、cohort 51/51 相同 | 已归档公共数据；不重验设备/raw 哈希 |
| 完整历史图表再生成 | 5/5 文件字节相同 | 同一 main 渲染器分别加载旧/新 analyzer |
| Android NDK 27.2 / arm64 API29 | 两源码 `-fsyntax-only` 成功 | 交叉目标编译前端；未生成/部署 Android 可执行程序 |
| PA-01/02/03 反例 | 均复现 | 合成输入、生产选址函数；无硬件计数/地址解引用 |

**重放措辞修正**：本次严格比较完整 `dataclasses.asdict(AnalysisResult)`，原始结构相等 **0/51**，原因是新增 identity 字段；仅删除新增且四项均 None 的 identity 后，51/51 相等。可称“旧语义/既有统计量与 cohort 一致”，不应不加限定地称完整输出“逐字一致”。真正文件字节一致的证据是本轮四图+报告 5/5。

复核脚本：[review_mb06_phasea_20261007.py](../../scripts/review_mb06_phasea_20261007.py)；结构化输出：[results.json](evidence/2026-10-07-mb06-phase-a/results.json)；软件测试日志及 SHA256 清单见同目录。脚本会记录观察到的缺陷，退出 0 表示诊断完成，**不表示本包通过**。

```bash
/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python \
  /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/scripts/review_mb06_phasea_20261007.py \
  --tree /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b \
  --main-tree /Users/michaelyao/workspace/cpu-uarch-explorer \
  --out /private/tmp/mb06-phasea-review.json
```

## 5. 发给行动方的回执

> MB-03/07 原收口问题已清零，历史处置可关闭。此次 MB-06/OI-13/Phase A 包暂不通过：残差身份在下游丢失、模式/realized descriptor 契约未贯通、多区域实际选址不足，以及 A1 判别式/矩阵和 A3 可识别性均有阻塞项。请按 PA-01–05 修复并补端到端反例，OI-13 保持部分关闭，重新冻结可实际执行的矩阵后送审。已有 pilot 可保留作该实际访问域上的校准材料；不能以 `multi-region` 预约标签授予高位 hash 判别证据。手机复核继续由上板 Agent 承担。

适用于后续 ROB/ALU/FPU 的工程原则：planner 与 kernel 消费契约、typed experiment identity、realized geometry/运行条件、metrics 应分别有明确接口；消费方必须按完整身份分系列或命名拒绝。当前将所有未知 params 放进隐藏分组键只能防止第一层混合，不能替代这些公共契约。本轮不扩大到实现其他单元探针。
