# SM8650 TLB 战役管线增量分析：机制层设计与理由（2026-09-30）

> 分析对象：TLB 战役（任务书 `docs/tasks/2026-09-28-sm8650-tlb-hierarchy.md`
> v4.4）给 ptr_chase 管线引入的**机制增量**及其设计理由。
> 基准：main @ `bc96ff1`（含图表扩展）。读者：工程师（不需要微架构背景）。
> 与 `docs/design/ptr-chase-pipeline-analysis.md`（2026-09-25 快照）的关系：
> **增量快照**——原文描述的"基础管线"本文不重复；本文只写战役**改了什么、
> 为什么**。所有事实可在仓内复核，关键处给文件锚点。
> **不写**：战役结论（在 `docs/reviews/2026-09-28-sm8650-tlb-hierarchy.md`
> 终审及分阶段文档）、规则本体（在任务书）、传播性读法（在
> `docs/reports/2026-09-30-sm8650-tlb/report.md`）。

## 1. 一张图：战役给管线加了什么

```text
probes/cache-mem/ptr_chase.cpp
  └─ ＋vma_base 输出字段（每样本建链缓冲区起始 VA）         §2.1
configs/pmu-event-registry.json（新）
  └─ PMU 事件资格注册表（CANDIDATE/QUALIFIED 两级）         §2.2
configs/experiments/ptr-chase-sm8650-x4-tlb-*.json（15 份）
  └─ 阶段化配置族（锚点/正控/粗扫/致密/长训练/开销扫描/关联/THP） §2.3
runner/plan.py
  └─ ＋case id 通用段 + 唯一性硬断言 + 段值白名单           §2.4
runner/engine.py + runner/environment/（P0″ 首战接线；本战役为第二
  └─ 每 case 前后环境门禁（quiet-state，fail-closed）          §2.5
     次实战、最大规模验证）
analysis/sm8650_tlb.py（新）
  └─ 判定分析器：分组/拒绝 → knee/onset 终态机 → 锚点块判定
     → cohort 分级/转化表/预算审计 → Q3/固定开销判定        §2.6–2.9
analysis/tlb_dense_gen.py（新）
  └─ 致密点生成器（三哈希锚定的确定性配置生成）             §2.7
analysis/chart.py 泛化 + analysis/tlb_figures.py（新）
  └─ 战役图表层（密度曲线 + 区间着色 + 参考线）             §2.10
```

主线流向：`任务书冻结规则 → 配置族 → runner 块执行（门禁夹持）→
分析器判定（不入库函数不出结论）→ 评审文档/报告`。

## 2. 各机制的设计理由

### 2.1 探针 `vma_base` 字段（探针唯一改动）

**改动**：`ptr_chase.cpp:69` 输出注释段与运行时输出新增
`vma_base=0x…`（建链缓冲区起始 VA，字符串不转 int）；
adapter 按 `^0x[0-9a-f]+$` 校验后写入**每条** metric（`runner/
adapters/ptr_chase.py`）；schema 登记（`runner/schema/README.md:64`）。

**为什么**：Q1 的布局敏感性判别需要逐样本的虚拟地址证据——固定
`-S` seed 只改访问顺序不改地址集合，进程间 ASLR 差异是仅有的布
局观测面（任务书"路线 A"）。设计取舍：不做可控布局（路线 B 要
改建链模式、扩 ABI、扩 scope）——先观测，观测到敏感再立项。
**铁律 4 形态**：扩展字段登记到 schema README，不破坏旧读者（旧
输出无此字段时 metric 不补键，不编造——adapter 测试钉死）。

### 2.2 PMU 事件资格注册表（`configs/pmu-event-registry.json`）

**改动**：新文件，11 条记录（5 战役前 QUALIFIED + 4 Gate 1 新
QUALIFIED + 2 SEMANTICS_UNVERIFIED 保 candidate）；守卫
`runner/tests/test_pmu_registry.py`（必需键/枚举/平行数组等长/
(midr,config) 唯一/review_ref 落盘）。

**为什么**：事件的"可采集"与"可解释"是两回事（任务书 S4）——
raw 编码能 open 不代表语义可信。把资格做成**带溯源的数据记录**
（source_doc/revision/正控 run/outcome/review_ref/validity_scope）
而不是分析器常量：资格状态随数据演化、评审可审计、分析器
（`sm8650_tlb.py:318 load_registry`）运行时读它做门控——未注册
事件的结论自动降级 SEMANTICS_UNVERIFIED，但**不阻断其正控采集**
（否则 Gate 1 自身无法完成）。Gate 1 的两个否定结果（`0x2f` 方向
反降、`0x8138` 无信号条件）即本机制的产出。

### 2.3 阶段化配置族（15 份 tlb-* 实验配置）

**形态**：锚点（`tlb-anchor`，512/3072 KiB 两点）/正控（ctrl 系
列，Gate 1 各事件组）/粗扫（coarse 13 档×2 seed）/致密（dense，
生成器产出）/长训练（dense-long，512 环）/开销扫描（overhead，
§5.3 固定开销的 2 点 × 3 长度 × 4 seed）/关联（assoc-g2/g3）/
THP（thp-base/thp-madvise）。

**为什么拆多份**：`execution.sweep` 是笛卡尔积——一份配置表达不
了"锚点 2 case + 主体 26 case"这种异构矩阵；拆文件让每份的
plan 展开可独立守卫（`runner/tests/test_plan.py` 的
expected_case_counts + 参数钉 + 事件三元组钉——事件钉升级到
(name,type,config) 三元组是因为评审实证过"改错 0x2d→0x2c 能静默
通过名集合钉"）。**守卫先行是 TDD 的延续**：配置先于数据被测
试钉住，执行期零参数解释（plan 期报错，run 期不做参数解释——
GB10 静默降级教训的对冲结构，`runner/plan.py:156` `build_plan`
docstring）。

### 2.4 case id 通用段（`runner/plan.py`，战役中的潜伏 bug 修复）

**改动**：sweep 了模板未覆盖的参数（如 `loads_per_slot`）时 id 自
动追加 `-{name}{value}` 段（白名单字符校验）；`build_plan` 返回
前 case id 唯一性硬断言。

**为什么**：case id 是 raw 样本文件名与 manifest id 的命名键
（`runner/artifacts.py:71`）——首个 sweep `loads_per_slot` 的配置
（开销扫描 24 case）会让 24 case 塌缩成 8 个 id，raw 样本按名
覆盖写、SHA256 锚定失效（铁律 1 级事故）。**这是配置守卫逼出来
的修复**：overhead 配置的守卫测试让缺口在 plan 预览期现形，而
不是在设备上跑完后发现样本互覆。教训形态：通用机制（任何 swept
参数进 id）+ 纵深断言（唯一性硬失败），而非单点补丁。

### 2.5 环境门禁的实战接线与验证（runner/engine.py + environment/）

**现状更正**（相对 09-25 快照的"已实现未接线"）：environment 事
务（durable journal + 逆序恢复，`runner/environment/coordinator.py`
/`journal.py`）在 **P0″ 战役（2026-09-28，前一次 cache 战役的
demand/prefetch 复测，分析器 `analysis/sm8650_x4_p0prime.py`）首次
接线实战**并有真实拦截（drift 事件被前置门禁 fail-closed 拦下，
见 `docs/reviews/2026-09-28-sm8650-x4-p0prime.md`）；TLB 战役是它
的**第二次实战、迄今最大规模验证**。机制：每 case 前
`collect_environment_state` + 前置门禁，不合格不执行 probe
（`environment-precondition-failed`）；后置漂移保留 raw 但空
metrics（`environment-postcondition-failed`）。唯一 host mutation
= governor → performance（durable journal + 事后精确恢复 walt，
runbook `redmi-controlled-quiet-state-v2.md`）。

**为什么值得单独一节**：它是战役数据可信度的**第一道墙**。TLB
战役的证据：正式采集全部落在限额画像值窗口内（画像值 = 各
cpufreq policy 的厂商限额档位 2265600/2707200/2707200/2745600
kHz，窗口由 quiet-state 门禁逐 case 验证）；全战役 **11890/11890**
条 PMU 观测 running==enabled（49 个 run 全量复算口径）。门禁在
TLB 战役不是形式：锚点判据 fail-closed 过 **4 个块**——Phase A
两块（判据校准前的结构性误报，见 §2.8）、Phase B 长训练首块一次
**真实瞬态**（512 KiB anchor-before 的 regime 异值）、Phase D -B
首块一次**边际**（512 latency 越带 +0.4%）——性质不同但全部留
档入库（fail-closed 不是失败，是门禁在工作的证据）。

### 2.6 判定分析器骨架（`analysis/sm8650_tlb.py`）

**形态**：公共函数族——`load_registry`（注册表门控）、
`analyze_records`（逐样本校验与分组）、`adjudicate_knee` /
`detect_walk_onset`（终态机）、`group_block` / `validate_anchors`
（块归组与锚点判定）、`grade_thp_cohorts` / `build_thp_conversion` /
`audit_thp_budget`（THP 三件套）、`adjudicate_q3` /
`adjudicate_fixed_overhead`（Q3 与固定开销）、`build_markdown` 等；
契约 = "逐样本证据链"（schema v2、metric 集合精确相等、
sample_index 对齐、PMU 编码/seed 逐样本一致、running==enabled、
multiplex 拒绝——multiplex = PMU 计数器复用导致的非全程计数，
time_running<time_enabled 的样本拒绝并登记、同记录其余样本保留、
全失败 run 进 rejected 不抛错）；分组键 (run_label, buffer_kb,
seed, page_policy_actual, ring_passes)。

**为什么"判定全部落在入库分析器"**：cache 战役的 P0 翻车（预注
册门禁事后改写）证明**ad-hoc 看图判定不可信**。TLB 战役的
所有"结论"（knee/onset/锚点/cohort/Q3）都是可复算的函数输出——
评审就是逐数字重放这些函数。模块刻意与 P0″ 分析器并列复制契约链
而不共享实现（两任务的冻结规则各自演化，共享会把一方的规则漂
移传染给另一方）。

### 2.7 knee/onset 终态机 + 致密点生成器

**knee/onset**（`adjudicate_knee:525`/`detect_walk_onset:644`）：
任务书 §6.2.2/6.2.3 的三条件判定 + §6.2.8 边界解析（左删失优先——
左删失 = 曲线在扫描下界已处高位、转折在下界左侧不可见、不得误报
为下界值；无膝点/双膝点/边界点各有终态）——**判定规则先于数据冻结**，
Phase A 数据进来后没有人手调过阈值。致密点生成器
（`tlb_dense_gen.py:261 emit_dense_config`）把"Phase A 候选区 →
Phase B 点位"做成确定性函数 + 三哈希审计块（input_run/rules/
output SHA-256），**禁止看图后人工改点**——生成配置带
`generator` 块入档（schema 登记 `runner/schema/README.md:20`）。

**为什么**：预注册的约束力来自"看到结果后无法改判据"。生成器
把点位选择也关进规则里——Phase B 的 8 个点（48/104/112/120 +
1024/2560/3072/3584 页）没有任何一个是人挑的。

### 2.8 锚点块结构与池化判据（战役最硬的方法学产物）

**块结构**：`group_block`（:1300）按 experiment_id 定角色 + probe
SHA-256 一致 + manifest 时序不交叠三关联；`validate_anchors`
（:1613）执行任务书 §6.2.5 判据（环境门禁 → 池带参照 → 计数容差
→ 3072 跨块基线 → 前后互判）；锚点失真 → 整块 fail-closed，块内
数据不进入判定但留档入库。

**判据形式的演化（v4.1→v4.4，任务书卷首修订映射留痕）**：
v4.1 的 3% 单点参照 + IQR 互覆盖 → v4.2 发现参照制度失配（2048
环 vs 8 环）→ v4.3 地板量化指标改计数容差 → **v4.4 方差表征池
化**（6 个锚点 run 连跑实测方差，判据带 = median ± 1.5×实测全距，
运行时现算不写死）。演化驱动力：前两种形式在 n=10 下结构上必
然误报（IQR 宽与跨 run median 摆动同量级）；池带形式此后仍抓到
过一次真实瞬态（Phase B 长训练首块）——**校准让门禁更宽但更有
效**：宽到不拦采样运气，仍能拦 regime 断裂。

**为什么单独成节**：这是本战役对测量方法学的最大贡献——**先测
方差、再定门禁**（方差表征应当先于正式块执行，本案是两块
fail-closed 换来的教训，OI-12（跨日基线移动，注意与 ROB 线的同名
条目区分）已登记开放观察）。

### 2.9 THP cohort 机制与固定开销判定

**cohort 三件套**（`grade_thp_cohorts:961`/`build_thp_conversion:
880`/`audit_thp_budget:848`）：按**逐样本实际 backing** 分组
（mixed 永不并入 thp）、比较级 ≥5 有效样本才出 median（任务书
§6.3 的 ≥5 纪律下限）、转化表披露"请求→实际→失败→入分析"的选
择偏差、每 (buffer×policy) ≤40 进程次停止预算（失败计额）。**为什么**：
THP 达成是内核策略行为（3072 KiB 仅 37.5% 拿到 mixed）——不报
转化表就只看到了成功者，选择偏差被隐藏。

**固定开销**（`adjudicate_fixed_overhead:1133`）：PMU 窗比墙钟窗
宽（read-before-disable 是驱动约束不改）——用 8/64/256 环三长度
拟合 `C(N)=a+b·N`，正式窗口下 |a|/C(N) ≤5% 才可忽略（cycles 与
dtlb_walk 判"含固定开销"，报告须标注、转折判定改用斜率 b）。

### 2.10 图表层（`chart.py` 泛化 + `tlb_figures.py`）

**为什么 TLB 的图不是 latency 曲线**：Phase C 实测 walk 与延迟反
相关（中段延迟由 L1 refill 风暴主导）——latency-vs-buffer 图对
TLB 会讲错故事。TLB 的正确曲线是**事件密度曲线**（R_0x05、
R_0x34 随页数）。`chart.py` 泛化出轴标签/区间着色/参考线（含既
有网格线越界 bug 修复，sha256 钉显式重钉并登记沿革）；
`tlb_figures.py` 钉死数据集名单 + 两级中位数合并 + fail-closed
网格校验，同输入必同输出（再生 byte-identical 有测试钉）。

## 3. 复用指引（下一个探测战役该拿什么）

**直接拿走**：块结构 + 锚点判据池化形式（先把方差表征提到正式
块之前——本战役的正确顺序教训）；事件注册表与资格两级；配置
守卫三件套（case 数 + 参数钉 + 事件三元组钉）；致密点生成器模
式（规则产出点位，不人工选点）；cohort 转化表（任何"请求≠实
得"的对照都要报转化表）；fail-closed 块留档入库而非删除。

**已知会撞墙的缺口**（OI-13，`docs/open-items.md`）：
`analyze_records` 要求精确 G0 metric 集合——非 G0 事件组（如
Phase C 的 G2/G3）的主体 run 走不了 `validate_anchors` 的全路
径。**下一个需要非 G0 事件组做正式块级判定的实验（如 LLCC）必
须先关闭 OI-13**——超集放行、main_result 解耦、缺失项命名降级
语义，三个方向立项时评审，禁止再用"直接提取复刻"绕行。

**数据纪律提醒**：锚点判据的参照池/容差全部运行时现算——池数
据修订走 revision history（任务书 §6.2.5 备查值同步义务，测试
fixture 头有更新步骤）；不要把备查值当成可以手抄的常量。

## 4. 不在本文档的内容（边界）

- 战役结论与证据链：`docs/reviews/2026-09-28-sm8650-tlb-hierarchy.md`
  （终审）+ 分阶段文档；
- 判定规则本体与修订史：`docs/tasks/2026-09-28-sm8650-tlb-hierarchy.md`
  （v4.4，卷首 v4.1→v4.4 修订映射）；
- 同事/外部读法：`docs/reports/2026-09-30-sm8650-tlb/report.md`；
- 后置项与开放问题：`docs/open-items.md`（OI-12（跨日基线移动）
  /OI-13/OI-14——open-items.md 当前另有一个同号的 ROB 线 OI-12，
  引用时注意区分）。
- 基础管线（构建/runner 基本结构/schema 四类记录）：
  `docs/design/ptr-chase-pipeline-analysis.md`（2026-09-25 快照，其
  "environment 未接线"等过时表述以本文 §2.5 为准）。
