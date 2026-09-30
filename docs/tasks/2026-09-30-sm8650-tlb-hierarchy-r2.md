# SM8650 Cortex-X4 TLB 层级探测 · 第二次战役（r2）任务书 v1.0

> 版本：v1.0（2026-09-30 立项）
> 基线：`main @ 9316853`（第一次战役集成终点）
> 前身：第一次战役终审（`docs/reviews/2026-09-28-sm8650-tlb-hierarchy.md`，终态 Q1–Q4 已定）+ 三视角架构审阅 12 条发现（2026-09-30，其中 5 条落为本任务书 M0 硬性修正案）
> 方法资产：`docs/cpu-uarch-deep-analysis/`（TLB 深度分析报告 v1.6、方法迁移矩阵 v0.2、原型探针 v2.2——角色见 §2.3）
> 分支：`codex/sm8650-tlb-hierarchy-r2`（worktree `cpu-uarch-explorer-tlb-r2`）；有限终点与退役严格按 AGENTS.md 铁律 7 与 §10.3

## 1. 任务契约与有限终点

### 1.1 任务对象

在第一次战役已确立的 L1 refill 转折区 [120, 1024] 页与 walk onset [2560, 3072] 页之上，用**方法增量**回答其遗留的开放问题。方法增量四件（来自深度分析报告 §5 与原型 v2.2，均经四轮外部评审修订）：

1. 真集合三分布对照（连续 / 大步距 / 随机集合）；
2. prime+probe way 跳变（filler 独立映射 + 按候选假设避目标 set + T/T2 真实交替对照）；
3. L2 索引哈希假设族 H1~H4 检验（探索性目标，非承诺目标）；
4. K 独立链 + WALK_PERCYC/CPU_CYCLES 比值（有效在飞占用，非队列深度）。

工程路径（三层架构，2026-09-30 拍板）：**数据管道层**（Probe ABI / record schema / runner / 锚点 / quarantine / SHA manifest）跨探头复用；**探头层**按方法形状归属——容量/拐点系并入 `probes/cache-mem/ptr_chase.cpp` 模式增量，set/way 系新建 ABI 合规探头；**判据层**每问预注册冻结。证据一律由管道产出；`docs/` 下原型探针**不可产证据**（§2.3）。

### 1.2 科学问题（预注册；每问独立终态）

- **Q-A（归因判别，必做）**：L1 refill 密度转折在不同页集合分布下的拐点比较。
  - 预注册方向：大步距/随机集合拐点**显著提前**于连续集合（超预注册阈值）→ 支持"结构相关冲突（PFN 着色/索引共振）"归因；三分布拐点一致 → 支持"渐进饱和"归因；介于两者之间 → 报告差异区间不裁决。
  - 终态语义：`ATTRIBUTED(gradual_saturation|structural_conflict)` / `CONSISTENT_ACROSS_DISTRIBUTIONS` / `DISTRIBUTION_SENSITIVE` / `LEFT_CENSORED` / `RIGHT_CENSORED`。
- **Q-B（L2 set 有效相联度，必做）**：prime+probe + T/T2 对照的 refill 跳变。
  - **命名纪律（预注册）**：受 walk-cache 中间级条目共存（TRM Table 5-1，条目 bit[46] 区分）与替换策略影响，测量对象命名"**混合条目有效相联度**"，不命名裸 way 数；"w=8→9 干净跳变"仅为理想预期，**判据是 T（同假设 set）与 T2（异 set）对照的差异方向**。
  - 门控不依赖 `0x2f`（见 §5.1 其第一次战役正控失败先例）：`0x05` 差分 + `probe_ns` 上界双门控。
  - 终态语义：`JUMP_IDENTIFIED`（附理想预期偏差说明）/ `CONTROL_ONLY`（仅对照差异可读）/ `GATE_FAILED` / `H_NOT_FOUND`（假设族全拒时）。
- **Q-C（L2 索引哈希假设族，探索性）**：H1~H4（位选 / 相邻字段 XOR / 高位折叠 / 三字段 XOR）检验。
  - 预注册声明：有限样本只支持"候选保留/排除"，**不支持全域唯一**；H4 含 ASID 位变体当前不测试；哈希不命中 H1~H4 属正常科学结局，终态如实报告，不迭代假设族超预算（超预算转 §11）。
- **Q-D（翻译并行在飞占用，必做）**：K 独立链扫描的 walk_inflight_per_cycle（= WALK_PERCYC/CPU_CYCLES，同窗口比值，剔除首轮）。
  - **排除对照（预注册强制）**：固定 K 变每链工作集 N（分离 MSHR/load queue 限制）；DTLB_WALK(0x34) 计数 + 时延分解；平台期结论措辞限"**该负载下的有效在飞占用**"，排除发射/缓存/内存带宽限制前不宣称硬件队列深度（外部评审3 裁定，继承）。

### 1.3 非目标

- 不反推物理 entry 数（授权边界，同第一次战役任务书 §3.3；TRM 值可引用、可校准、不可由测量外推）。
- 不把哈希检验结论命名为"已逆向真实哈希"。
- I 侧（iTLB 48 条短跳板探针）本期不做，后移（立项条件见 §11）。
- ROB 另立项（OI-12 边界重开决策不属于本任务）。
- 不移植 AArch64-Explore/Apple 或任何外平台数值。
- 不做 mixed-THP 队列逐槽位归属；不估算 TLB 收益占比。

### 1.4 有限终点（AGENTS.md 铁律 7 原文照录）

> 功能分支以"预注册任务完成或正式判定不可完成"为终点——科学问题未解不等于分支不能结束；未竟问题一律登记 `docs/open-items.md`（铁律 0），不得靠永续分支兜底。worktree 回收与分支删除分两步：worktree 回收看使命完成/工作树干净/无进程依赖/数据分层处置；分支删除须 main 集成 + 完整测试 + 推送之后。

本任务的"预注册任务完成" = M0–M4 全部执行并按 §10 终态结案；OPEN 是合法终态。

## 2. 证据基线与待决清单

### 2.1 第一次战役终审终态（回指，不复述细节）

| Q | 终态 | 数值 |
|---|---|---|
| Q1 L1 refill 转折 | INTERVAL_IDENTIFIED | [120, 1024] 页，宽饱和区 |
| Q2a walk onset | INTERVAL_IDENTIFIED | [2560, 3072] 页 |
| Q2b L2 层级 | 0x2d QUALIFIED；0x2f SEMANTICS_UNVERIFIED | 层级辨识仅 0x2d+Gate0 承担 |
| Q2c L2 effective reach | 未授权（保持 OPEN） | — |
| Q3 暴露成本 | MODEL_UNIDENTIFIABLE | 反相关，单调性不成立 |
| Q4 THP cohort | 机制方向一致（受限比较级） | 3072KiB mixed：lat -12.4%、R_0x05 -82% |

### 2.2 遗留开放项（本任务的输入约束）

- **OI-12**（跨日基线移动，未归因；3072 KiB 跨日 +3.6% 摆动量级）：任何新锚点带必须引用该量级校准；**本任务禁止照搬 ≤1.2%/≤3% 级经验阈值**。
- **OI-13**（分析器硬编码 G0 metric 集）：本任务事件组（含 0x2d/0x11/0x8128 等）不是 G0 集合——**触发其关闭条件，M0 必做**（§4.2）。
- **OI-14**（TLB 战役后置）：r0p3 vs Issue 05 逐字差异未核；路线 B（可控 VA 布局）立项条件未触发。

### 2.3 方法原型（角色声明，预注册冻结）

`docs/cpu-uarch-deep-analysis/tlb-deep-analysis/probes/` 下 `tlb_capacity_probe.c` / `l2_set_probe.c`（v2.2）为**方法原型**：已经过四轮外部评审修订，算法蓝本有效；但其输出无 ABI 契约、无 smaps 端点核验、无锚点门——**禁止作为证据探针上板采数**。其上板合法性仅限 §5.2 可行性冒烟（产物为备忘录，不入 `data/public/runs/`）。本任务证据探针 = ptr_chase 模式增量 + 新 tlb-set 探头（M0 后）。

## 3. 术语、事件表与结论权限

### 3.1 事件表（资格状态随 Gate 0 更新）

| 事件 | 语义 | 第一次战役资格 | 本任务用途 |
|---|---|---|---|
| 0x05 L1D_TLB_REFILL | L1 dTLB 从 L2 TLB 回填 | QUALIFIED | Q-A 主信号；Q-B 门控差分 |
| 0x34 DTLB_WALK | 引发 ≥1 次 walk 的 D 侧访问 | QUALIFIED | Q-D 计数分解；walk 侧交叉 |
| 0x2d L2D_TLB_REFILL | L2 TLB 被回填（I/D 共触发） | QUALIFIED | Q-B 主信号（unified 口径，数据链主导性须论证） |
| 0x2f L2D_TLB | L2 TLB access | **SEMANTICS_UNVERIFIED**（方向反降+分布重叠） | 仅作 G0-1 复验对象；判据不依赖 |
| 0x11 CPU_CYCLES | 周期 | 待 G0-2 资格 | Q-D 比值分母 |
| 0x8128 DTLB_WALK_PERCYC | 每周期在飞 walk 数累计 | 待 G0-2 资格 | Q-D 比值分子 |

### 3.2 命名与分栏纪律（继承战役 §10.1 三栏）

直接实测 / 派生（DERIVED）/ 微架构解释（TRM 声称 / Explore 方法 / 本机观测，三段分标）。TRM 层级名（L1 dTLB / L2 TLB / MMUTC / walker）与测量定义区间分栏；"混合条目有效相联度"、"有效在飞占用"为测量定义名，不映射为物理结构名。

### 3.3 来源层级

TRM Issue 05 逐字核对（第一次战役已完成）；r0p3 差异未核（OI-14 触发条件未变）。本任务书 TRM 引用一律注明 Issue 05；r0p3 补核后如有差异以 r0p3 为准并修订映射。

## 4. M0：架构修正案（先于一切采数的工程里程碑）

> 三视角审阅（2026-09-30）12 条发现中的架构级 5 条全部落位于此；M0 未完成不得进入 Gate 0 之后的任何采数。

- **M0-1 共享探针支撑库**：把 `ptr_chase.cpp` 内部的页策略/smaps 端点核验（`read_anon_huge_kb` / `classify_page_backing` / PROT_NONE 守卫 VMA）抬升为共享组件（`probes/common/`，与既有 `perf_counter.h` 同级），供 ptr_chase 模式增量与新 tlb-set 探头共用；消除"新探头复制 or 丢纪律"的二选一。
- **M0-2 关闭 OI-13**：`analyze_records` 对超集 metric 集放行（required ⊆ present 派生字段）；`validate_anchors` 增加"主体非 G0 时 main_result 显式跳过/降级"模式（锚点判定与主体分析解耦）；缺失项逐一枚名降级语义。**禁止**以"直接提取复刻"绕行（Phase C 先例封死）。含 test(analysis) 钉住。
- **M0-3 新统计量锚点参照池**：为"每次访问 refill 率"与"窗口内 event delta"两类新统计量建方差表征参照池（复用 v4.4 方法），**引用 OI-12 量级校准**。
- **M0-4 原型角色头**：docs/ 两原型 README/文件头加"方法原型，不可产证据"声明（一行，防漂移误用）。
- M0 每项 = 独立提交 + 双评审（规范+质量，同战役纪律）。

## 5. Gate 0：事件资格复验

### 5.1 引用与复验项

- 引用第一次战役 Gate 1 结论（0x05/0x34/0x2d QUALIFIED；0x2f SEMANTICS_UNVERIFIED，原始数据在档）——**引用不复验**。
- **G0-1 0x2f 复验（唯一复验项）**：在两阶段窗口协议下重测 0x2f（已知冲突 vs 非冲突对照）：若恢复 → Q-B 门控可升级为含 0x2f 三事件版；若仍反降 → 判据定型为 0x05 差分 + probe_ns 上界双门控（预注册默认路径）。
- **G0-2 新事件资格**：0x11 / 0x8128 逐项正控（enabled==running、与 0x34 的共变方向检查；判定规则冻结于本节，评审后不再改）。
- **G0-3 空窗底噪**：`-w 0` 空窗对照列为 Q-B 强制 case（0x2d 含 I 侧贡献的底噪扣除依据）。

### 5.2 可行性冒烟（原型合法性边界，唯一允许原型上板的环节）

对象：docs/ 原型 v2.2 两文件。产出：**冒烟备忘录**（0x2f 窗口协议下行为、门控可达性、页守卫/交叉编译链、K 链内存可行性），**不入 runs/、不进对比表**。冒烟失败项 → 对应判据重设计后再进 M1。

## 6. 实验协议、预注册规则与统计

### 6.1 固定协议

- 容量系（Q-A）：ptr_chase 新增建链分布模式（linear / strided-set / random-set / permuted-order 对照），页粒度 sweep 复用战役配置族（`-s 4096`）；ABI/页策略/smaps 全继承（M0-1 后）。
- set 系（Q-B/Q-C）：新探头 `probes/tlb-set/`（C++ ABI 合规，算法蓝本 = 原型 l2_set_probe v2.2：filler 独立映射 + 无交集断言 + 按 H 过滤目标 set + 分阶段 PMU 增量 + round 0 剔除 + T/T2 交替 + `-w 0` 空窗）。
- 并行度系（Q-D）：K 交错追逐为 ptr_chase 模式（单独预注册；与 ptr_chase "必须单链"教训（4 链 MLP 摊薄）的关系在模式文档中显式说明：估计量不同——延迟 vs 并行在飞占用）。

### 6.2 冻结判据（草案，评审后冻结，改判据走战役 v4.2→v4.4 同款修订映射）

1. Q-A：三分布拐点 = 冻结算法（复用战役 adjudicate_knee 家族）各自产出；分布间拐点差 > 预注册阈值（待 M0-3 方差池标定后写死）→ DISTRIBUTION_SENSITIVE。
2. Q-B：门控（0x05 差分 ≈ 预期 + probe_ns 上界）→ T 组 w 扫描 refill/轮 与 T2 组对照差异方向为主判据；理想跳变位置仅作参照。
3. Q-D：平台判定 = 比值序列（剔除首轮 + 空窗底噪扣除）+ 排除对照（固定 K 变 N）一致性。
4. fail-closed 语义、重试占额、预算核算全部沿用战役 §6.2.5/§6.2.7。

### 6.3 对比矩阵协议规则（预注册）

与第一次战役数字的对比**仅限同统计量**（如 R_0x05 密度区间 vs 本战役同口径区间）；跨协议量（窗口 refill/率 vs 扫描密度）只作机制互证，不进同表比较。

### 6.4 统计与数据分层

schema 演进走仓规铁律 4（additionalProperties=true、登记 `runner/schema/README.md`；新指标入 metrics 命名空间）；fail-closed 块留档 quarantine；raw 不入库走 SHA manifest；quiet-state 门禁与 raw 环境快照复用战役机制。

## 7. 分阶段矩阵与执行预算

| 阶段 | 内容 | 出口 |
|---|---|---|
| M0 | §4 四项修正案 | 双评审通过 |
| Gate 0 | §5（含冒烟） | 事件资格表定稿 |
| Phase A | Q-A 三分布扫描（ptr_chase 模式） | Q-A 终态 |
| Phase B | tlb-set 探头 + Q-B/Q-C | 终态（Q-C 探索性如实结） |
| Phase C | Q-D K 链 + 排除对照 | 终态 |
| Phase D | 终审：终态裁定 + 对比报告 + 后置项落位 | 退役清单 |

预算：**先测后写死**（同战役 §7 原则）；Phase A/B/C 各自的重试占额与 fail-closed 留档规则在阶段配置中冻结。规模预期参照战役（其纯执行约 1.5 小时、291 case）——本战役探头多一个新形状，预算上调系数待 Phase A 实测后写死。

## 8. 漂移、设备状态与重启

复用战役 §8 机制：限额 drift 观察期、quiet-state 逐 case 门禁、raw 环境快照在档；跨日基线移动 >3% 触发即冻结该日数据块并按 OI-12 流程登记（不现场重锚）。

## 9. 实现与 TDD

- CMake 注册新探头（ADR-0008 构建树单一入口）；ABI 契约测试（仿 `26ca7ed` protocol guard 先例）；新判据进 test(analysis) 钉住（仿 `4885a9f`）；每里程碑提交粒度同战役（config/data/docs/fix/test/feat 分类型）。
- 代码改动双评审（规范+质量）；探针 Git 提交哈希随 record 入档（schema 既有 `probe_git_commit` 字段）。

## 10. 报告纪律、终态与分支退役

三栏制（§3.2）；终态表逐 Q 独立；对比报告 = 终审终态 × 本战役终态逐项对照（同统计量行直接比，跨协议行标"机制互证"）；退役按铁律 7 两步骤（worktree 回收与分支删除分别核条件），退役清单模板沿用战役终审 §9。

## 11. 后置项登记（铁律 0）

1. r0p3 vs Issue 05 逐字核对（继承 OI-14，触发条件不变）。
2. I 侧短跳板探针立项条件：D 侧 Q-B/Q-C 终态落地后评估（前端混淆更重，独立任务书）。
3. ROB 工程对接边界重开决策（OI-12 拍板复审，本任务不提供输入）。
4. H1~H4 全拒后的假设族扩展（H5+：乘法哈希/ASID 位/多字段变体）——超本任务预算，登记后另立项。
5. 冒烟备忘录中未关闭的可行性问题（若有）。
