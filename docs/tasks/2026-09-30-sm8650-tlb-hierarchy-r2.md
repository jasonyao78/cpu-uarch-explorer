# SM8650 Cortex-X4 TLB 层级探测 · 第二次战役（r2）任务书 v1.1

> 版本：v1.5（2026-10-01；v1.0 → v1.1（REV-TLB-R2）→ v1.2（REV-M0-BATCH 首层）→ v1.3（REV-M0-BATCH 两层回执 2026-10-01）→ v1.4（收口复核 MB-03/07 再修 2026-10-01）→ **v1.5（M0-4b TLB set 移植落地 + M0-5 pilot 脚手架 2026-10-01）**，处置见 §10.3）

## 1. 任务契约与有限终点

### 1.1 任务对象

在第一次战役终态（L1 refill 转折区 [120,1024] 页、walk onset [2560,3072] 页）之上，用方法增量回答其遗留开放问题。工程路径（三层架构）：数据管道层跨探头复用；探头层按形状归属——容量/拐点系并入 `ptr_chase`，set/way 系新建 ABI 合规探头；判据层每问预注册冻结。证据一律由管道产出；`docs/` 原型**不可产证据**（§2.3）。

### 1.2 科学问题（v1.1 重订；每问独立终态）

**Q-A（分布效应判别，必做）**——估计量：**分布形态是否改变 L1 refill 行为**（不预承诺方向与机制）。

- v1.0 归因跳跃撤销（F1）：分布差异**不能**直接证明 PFN 着色（L1 dTLB 全相联，TRM 明示），分布一致也**不能**唯一证明渐进饱和；HPA/PTE_CONT/页表局部性/数据 cache 竞争/替换与投机行为均为竞争解释。
- 几何变量独立定义与控制（F1）：

| 变量 | 定义 | 控制 |
|---|---|---|
| page set | 实际访问的 N 个 VPN 集合 | 连续 / 大步距 / 稀疏随机**集合**分别构造；禁止用打乱顺序冒充随机集合 |
| visit order | 同集合上的遍历顺序 | 各集合统一随机环协议；顺序/逆序为独立对照 |
| in-page offset | 页内指针所在 cache line | **节点地址策略独立实现**（REV-M0-BATCH C7）：`node[i] = base + page_id[i]×page_size + offset(i)`，offset 是**页 ID 的函数**（同页跨访问保持一致），按 permutation 建链；**禁止改 stride 模拟**（同时改变页集合与几何）。校验：指针对齐、不跨页、每页恰一节点、无重复地址；record 记 requested/realized offset policy + distinct pages + VA span + cache-line footprint。归属 M0-4/Phase A，**正式测量前必须完成** |
| mapping span | 保留 VA 范围与页表覆盖 | 与 N/驻留字节**分字段**记录；大步距扩大的是地址跨度不只是 TLB 压力 |
| allocation epoch | 重新分配/进程实例 | seed 重复与重分配导致的 PFN 布局变化分别留存 |

- HPA 处置（F1）：`AnonHugePages=0` 只证明未观察到 THP backing，**不证明**无 PTE_CONT 或无硬件聚合（TRM `HPA_L1_DIS/HPA_DIS`，复位默认 ≠ 实际状态）；HPA 状态实查或显式 `UNKNOWN` 进 record，作 Q-A 解释边界。
- 终态：`DISTRIBUTION_SENSITIVE` / `NO_DIFFERENCE_DETECTED`（附差异区间与检出能力）/ `INCONCLUSIVE`；`ATTRIBUTED(...)` 为**升级态**，仅在正交对照（in-page offset / 数据 cache 压力分离）通过后启用。

**Q-B（L2 冲突行为，必做）**——两个并列估计量，任务内二选一定型（F2：v1.0 的 T/T2 同 set 双链不构成对照，两组各自自冲突）：

- **B1 同 set 自冲突曲线**：N 页集中于候选 set，**负控 = 同样 N 页分散到多个候选 set**（访问数/节点偏移/代码路径/页策略匹配）；跨多目标 set 与独立 VA epoch 重复。
- **B2 单 victim 驱逐概率**：victim v 填入 → m 个候选同 set aggressor（须验证其实际进入 L2 查找）→ 经验证的 L1 驱逐 → 测 v；估计量 `P(v 被驱逐 | m, H, 协议)`，负控 = aggressor 置于其它候选 set。
- 协议纪律：先以**不依赖 H 的经验驱逐集**取得正控，再测候选 H（否则循环论证）；AB/BA 或随机配对次序（v1.0 固定先 T 后 T2 无次序平衡）；filler 避目标 leaf set **不保证**中间描述符不占目标 set——**先报告冲突曲线/概率，再有条件解释为"混合条目有效相联度"**；"8→9"仅适用于总竞争条目数口径，B2 的 victim 是否计入横轴须明示。
- 门控不依赖 0x2f：`0x05` 差分 + `probe_ns` 上界双门控。
- **定型预注册（REV-M0-BATCH C7 + MB-08 合格门，Phase B 正式采样前冻结）**：默认主估计量 = **B1 自冲突曲线**。**切换 B2 的合格门**（全部满足，非 OR）：① pilot 证明 B1 不合格（目标访问未实际暴露 L2 查找/仅驻留 L1，门控证据在档）；② B2 的正控 + 负控 + victim 二值分类器 + 误判率门全部达标；③ 切换决策按预注册规则在 pilot 后、正式矩阵前做出，**正式数据不得参与选择**。两方案均不合格 → `GATE_FAILED`/重新设计，不进入正式矩阵。试点与正式验证样本隔离（同 REV 批次纪律）。
- 终态：`CONFLICT_CURVE_IDENTIFIED` / `EVICTION_PROB_IDENTIFIED` / `CONTROL_ONLY` / `GATE_FAILED` / `H_NOT_FOUND`。

**Q-C（L2 索引哈希假设族，探索性）**——v1.0 的可区分性缺陷修正（F4：对齐 256 MiB 池内 VPN[23:16] 恒定，H3≡H1⊕常数、H4≡H2⊕常数，仅为 set 标签重命名）：

- 地址激励：多个**相隔 ≥256 MiB 的稀疏 VA 区域**显式翻转高字段；保留 VA 与触碰页分开规划（无需等量物理内存）。
- 训练/验证分离：候选只在**独立验证样本**上可被拒绝；报告"当前采样域内等价的假设组"。
- 终态：`CANDIDATE_RETAINED(H, 测试域)` / `HYPOTHESES_EQUIVALENT_ON_TEST_DOMAIN` / `ALL_REJECTED_ON_VALIDATION`。

**Q-D（翻译并行在飞占用，必做）**——v1.0 排除对照表述修正（F7：固定 K 变 N 同时改变翻译工作集/数据 footprint/页表覆盖/walk 率，**不是** MSHR/load queue 的独立控制）：

- 报告四曲线：`L̄=A/C`（平均在飞占用）、`λ=M/C`（walk-causing 率）、`T_eff=A/M`（有效驻留周期，恒等式解释边界）、`loads/cycle`；配置记录每链 N/总页数/总访问/物理数据 footprint。
- K 扫描两种条件：固定总页数 / 固定每链页数（验证前者确实 walk-active）；**低 walk、相近数据 cache 压力负控**判断 K 内核是否先被发射/数据 miss 限制。
- 比值配对规则（F9）：A/C 在同 observation 内计算，汇总用 ΣA/ΣC 或均值样本占用；**禁止** `median(A)/median(C)` 称为同窗比值。
- K 内核实现（F7）：小范围 K 的**显式寄存器独立链** + 反汇编核验链依赖与 spill；原型动态 `ps[k]` 双循环仅为算法示意。
- 措辞上限："该负载下的有效在飞占用"；不宣称硬件 walker 队列深度。

### 1.3 非目标

不反推物理 entry 数（TRM 可引用/校准/不可外推）；不命名哈希为唯一解；I 侧本期不做（§11）；ROB 另立项；不移植外平台数值；不做 mixed 逐槽位归属与收益占比；**v1.1 起新增：不把 INST_SPEC/INST_RETIRED 比值当作 ROB entry 数（R4，执行端约束预登记）**。

### 1.4 有限终点（铁律 7，同 v1.0）

## 2. 证据基线与待决清单

### 2.1 第一次战役终态与 2.2 遗留项

同 v1.0（Q1 [120,1024]、Q2a [2560,3072]、0x2d QUALIFIED、0x2f UNVERIFIED、Q3 不可识别、Q4 受限一致；OI-12/13/14）。**编号冲突处置（F9）**：open-items 现存两个 OI-12（ROB 项目 / 跨日基线），本任务引用"跨日基线"时写 **OI-12(baseline)**，ROB 项维持 OI-12(rob)；唯一化重编号属 main 侧维护项（§11）。

### 2.3 方法原型（角色声明，v1.1 更新）

原型 `l2_set_probe.c` 已升 **v2.3**：F3a filler 越界（映射池 +256 页头程 + 硬上界 + 结构化失败）、F3b `-w 0` 除零（空窗模式 + `collect_set_addrs` 内部守卫，评审方 UBSan harness 复核通过）、F3 尾统计逐轮失效——**已修**。**仍为设计蓝本的已知限制（不修，移植版承担）**：F2 对照构造、F4 地址激励、F5 短窗 PMU 协议。原型上板合法性仅限 §5.2 冒烟。

## 3. 术语、事件表与结论权限

### 3.1 事件表（v1.1：继承既有资格，F9 修正"新事件"表述）

| 事件 | 既有资格（战役/注册表） | 本任务动作 |
|---|---|---|
| 0x05 / 0x34 / 0x2d | QUALIFIED（战役 Gate 1） | 直接继承，引用不复验 |
| 0x2f | SEMANTICS_UNVERIFIED | G0-1 唯一复验项 |
| 0x11 CPU_CYCLES / 0x8128 DTLB_WALK_PERC | **已在 `configs/pmu-event-registry.json` qualified**（长链作用域） | **继承**；新增短窗/K 链作用域验证（G0-2），不重复资格化 |

### 3.2 三栏分标与命名（同 v1.0，新增"冲突曲线/驱逐概率优先于有效相联度命名"）

### 3.3 来源层级（同 v1.0；r0p3 核对仍挂 OI-14）

## 4. M0：最小多探针纵向闭环（v1.1 扩展，F5/F6 落位）

> M0 未完成不得进入 Gate 0 之后的采数。每项独立提交 + 双评审。

- **M0-1 共享运行支撑层**（F6/评审 §3）：从 ptr_chase 抬升 `probes/common/`——RAII 映射与守卫、**合法地址池**、页 backing 审计（smaps 端点）、timer、CPU/MIDR 身份；与既有 `perf_counter.h` 同级。页策略不再随探头复制。
- **M0-2 部分关闭 OI-13（REV-M0-BATCH C6 口径收紧）**：超集放行仅保留事件**名字**（per-observation 编码仍在 records.jsonl 原始件可审计，AnalysisResult 不派生 extras 字段）；"锚点/主体解耦 + 缺失项命名降级 + 契约进分组键"已完成；**OI-13 保持未闭环**（余量：extras 派生字段与消费语义，转 §11 跟踪）。**保留** per-observation 事件编码/窗口/页审计/分母契约（F6：宽容读字段 ≠ 宽容合并实验条件）。
- **M0-3 PerfWindow 短窗能力**（F5）：perf **GROUP 原子启停/组读**，`read_format = nr, time_enabled, time_running, values[]`（**按实际布局解码，按事件 ID 映射**——Linux 布局非 nr,values[],ena,run；ROB 骨架 R2 即此错）；显式 privilege scope（排除内核或显式记录）；阶段标记；窗口 delta 的 enabled/running；读数失败逐轮失效；CPU 归属。长链旧模式并存。
- **M0-4 planner 解耦与判据身份**（F6）：probe descriptor/adapter 提供参数规范化与**实际几何派生**（page count / VA span / node offset policy / chains / allocation-round-phase-pair / realized geometry vs requested params 分字段入 record）；planner 退化为通用控制（sweep 展开、随机化/配对次序、预算）；**消除 ptr_chase 专属参数派生**（现 planner 对任意 probe 名派生 buffer/stride/slots/loads/warmup）。分析器分组键扩展（buffer/seed/backing/ring_passes → +分布/offset/K/span），**禁止跨条件合并**；每问声明事件依赖（缺无关事件不阻止计算，缺必要事件输出显式不可计算）。
- **M0-5 锚点参照池**（顺序修正，F8）：**先 pilot 后池**——安全性修正（原型 v2.3 同款缺陷扫描）→ 能力/窗口 pilot（标 `CALIBRATION/PILOT`，raw 留存）→ 独立校准样本冻结阈值 → 正式矩阵。新统计量池**不得**用旧长链率代替短窗 delta。
- **M0-6 原型角色头**：docs/ 原型 README 加"方法原型，不可产证据"（v2.3 已含评审注记，补角色行）。

## 5. Gate 0（v1.1 更新）

- 引用战役 Gate 1（0x05/0x34/0x2d QUALIFIED；0x2f UNVERIFIED）——引用不复验。
- **G0-1**：0x2f 在两阶段窗口协议下复验（唯一复验项；判据默认路径不变）。
- **G0-2**：0x11/0x8128 的**短窗/K 链作用域**验证（继承长链资格；enabled==running + 同窗 GROUP 读完整性 + 与 0x34 共变方向）。
- **G0-3**：`-w 0` 空窗、无冲突同长度窗、重复次数尺度扫描 = Q-B/Q-D 的**强制**开销标定 case（F5：减法后的负值保留并解释，不截零；多实验状态下验证 I 侧底噪，不预设统一可减）。

### 5.2 可行性冒烟（同 v1.0；产物为备忘录）

对象含原型 v2.3 与 ROB 骨架**缺陷确认项**（R1–R3 已由评审方合成复核证实，属 ROB 项目范围，本任务只引用不修——§10.3）。

## 5.3 M0-4b：TLB set prime+probe 移植版与 M0-5 pilot 脚手架（v1.5 新增）

**背景**：pilot（B1 自冲突曲线 + G0-3 标定）建立在原型 l2_set_probe 的 prime+probe 窗口协议上，而原型上板合法性仅限 §5.2 冒烟（v1.3 §5 明令）——v1.5 完成工程路径 A 承诺的移植，pilot 从此"可按按钮"。

**移植落点**（m0b `fb746c6` 探针/runner + `19aa529` 配置）：

| 组件 | 内容 |
|---|---|
| ptr_chase `--tlb-set-mode` | 原型 v2.3 方法的证据探针版。**F5**：PMU 走 PerfWindow GROUP 原子读 + `window_delta` 有效性（mux 轮计数披露不进均值；任一事件打开失败 = 协议无效 exit 1，不做逐事件 n/a）；**F4**：`--set-regions`（默认 4）跨 256MiB 边界的稀疏 VA 区域激励，预约失败回退单区域并输出 `set_domain=single-region-fallback` 命名降级；**G0-3**：`--set-window 0` 空窗、`--set-scatter` 无冲突负控（W 页各落不同 set）；T/T2 无交集断言、filler 独立映射按候选 H 过滤、4K 硬门、round 0 冷启动剔除——全部继承原型评审修复口径 |
| perf_window.h | `open_typed()`（ARM 平台 PMU type 动态，SM8650 = 8）；`open()` 保持 RAW 兼容 |
| runner `tlb_set` 形状 | `_derive_tlb_set_case_params` 真实消费 set_* 参数族（MB-03 契约通道）；hugepage/thp 在 plan 期命名拒绝（4K 强制）；通用 case_id 规范化枚举 |
| adapter | build_argv / parse_output 双分支：legacy 逐字不变；tlb_set 分支 fail-closed（缺必需参数/缺事件输出即 ParseError），metrics = `pmu.<label>.count`（probe 段窗口差分均值）+ `window_*_rounds` + `probe_latency_ns` |
| schema 登记 | `runner/schema/README.md`：`execution.probe_shape` + 8 个 `set_*` 参数（2026-10-01） |

**pilot 标定块**（三配置，CALIBRATION/PILOT 标签、raw 全量留存、锚点池只用 pilot 数据）：
- `ptr-chase-sm8650-x4-tlb-pilot-b1`：B1 自冲突曲线，set_window [1,2,4,6,8,9,10,12,16] × 10 rep（9 cases）；
- `ptr-chase-sm8650-x4-tlb-pilot-g03-empty`：空窗底噪（W=0，1 case）；
- `ptr-chase-sm8650-x4-tlb-pilot-g03-noconflict`：scatter [0,1] × rounds [10,40]（4 cases：无冲突同长度窗 + 重复尺度 + B1 同点对照）。
公共：H1/target 7/rounds 20/pool 65536 页/filler 512/regions 4/seed 42/三事件组+ cycles（0x05/0x2d/0x2f/0x11）/x4-prime 绑核。三配置已过 `runner.cli plan` 真实预览（14 cases，id 唯一）。

**判读口径登记**：0x2d 判据按**总竞争条目数**写（SMOKE-20261001：filler 过滤目标 set 后竞争 = W；冒烟实测跳变提前至 W=8 属预期形态，不改 B1 估计量）；F5 负值纪律适用（减法后负值保留解释，不截零）。

**充电态热策略协议（2026-10-07 增补，用户拍板：USB 充电为必须行为）**：不等待拔充电器、不写 sysfs、不改平台期望值。平台新增 `charging-thermal` 环境 profile（m0b `31c333a`）——policy0/2/5 的 scaling_max 被 MIUI 热策略压制登记为**显式接受的非基线条件**，从违规降级为命名告警（`accepted-nonbaseline:*` 随 record 入档，实际值全量留痕）；**硬护栏**：测量核 policy7 永不降级（cap 迁移到 X4 才是有效性威胁，代码层强制：全 policy 接纳 = 配置错误），governor/温度/唤醒态等非频率项不受降级影响。判读边界：充电态 pilot 与 campaign 1（电池态）基线**不跨 regime 直接比**；锚点池只用同 regime（充电态）锚点。pilot 上板统一用 `--environment-profile charging-thermal --allow-mutation`（kickoff 已更新）。

**遗留接口**：pilot 记录 metrics 为 `pmu.*.count` 窗口语义，分析器 G0 精确集不适用——pilot 判读按 Phase C 披露的直接提取复刻执行，**OI-13 关闭前**不用 `analyze_records` 主体路径（与评审 §4 边界一致）。MB-06 descriptor 契约仍是 Phase A/K 链正式采样前的关闭项。

### 5.4 M0-5 pilot 判读与校准冻结（2026-10-07 执行完毕，数据 m0b `8fba5c3`）

**数据**：充电态（charging-thermal profile）5 run / 18 record 零异常；块前/后锚点夹块；多区域激励全 140 raw 文件 `set_domain=multi-region` 零回退；`window_mux_rounds` 全 0；二进制 sha256 前缀 `1e03a658` 与 recipe 验证值一致。

**协议门核验（扣空窗底噪后）**：0x05/W = 4.05/8.5/17（W=4/8/16）✅ ≈W；0x2f/W ≈W（W≤12）✅。**scatter 负控（F2 级对照）**：W=8 同 L1 压力下 scatter=1 的 0x2d=0.0 vs scatter=0 的 5.1–7.5——0x2d 测的是 set 冲突本身，不是 L1-miss 驱动流量 ✅。

**校准冻结（Phase A 正式矩阵执行口径，取代一切旧参照）**：

| 项 | 冻结值 | 来源 |
|---|---|---|
| 空窗底噪/有效轮 | 0x05=2.0、0x2d=0.0、0x2f=2.0 | g03-empty |
| 无冲突上限（0x2d） | 0.0（W=8 scatter） | g03-noconflict |
| 协议门验收带 | 扣底噪后 0x05/W ∈ [0.85, 1.15] | pilot 全域 |
| **标准轮数** | **r20**（r10→r40 的 0x2d 5.1→5.95→7.5 轮数依赖已登记） | g03-noconflict × b1 |
| 0x2d onset 判据 | 确定 onset = 首个 0x2d ≥ 3.0/轮的 W；边际 onset 单独记 | 预注册 |

**B1 门状态**：pilot 未证伪 B1（协议门全过 + scatter 对照干净）→ B1 维持默认主估计量；正式矩阵前按 MB-08 合格门复核一次。

**pilot B1 曲线（0x2d/轮）**：W=1→0、2→0、4→0.2、6→0.5、8→5.95、9→6.65、10→7.2、12→12.0、16→11.8 → onset 区间 **[6,8] 页**（总竞争条目数=W 口径）。**只登记区间，不命名有效相联度**——Phase A 判据。

**锚点池登记（充电态 regime）**：b3072K 主锚 8.3535/8.3286（−0.30% 稳）；b512K 灵敏哨兵 [2.641, 2.749]（+4.09% 漂移已按 OI-12 调查：cycles 同步 +3.4% 非计时器假象，候选=network_stack 共跑干扰 + 电池状态迁移，未分离归因）。跨块可比门用 b3072K 主锚，b512K 作早期预警。**充电态锚点与 campaign 1 电池态基线不跨 regime 直接比。**

**登记观察（不判读，Phase A 处理）**：① 0x2f 在 W=16 饱和 ~15/轮（<W）；② 0x2d 的轮数依赖（替换态积累）；③ 锚点小 footprint 漂移对大 footprint 不敏感（与共跑干扰假设一致）。
> 修订依据：外部评审 REV-TLB-R2-20260930（第一性原理评审，13 项发现 F1–F9/R1–R4；归档于本分支 `docs/reviews/2026-09-30-sm8650-tlb-r2-first-principles.md`，合成复核脚本 `scripts/review_sm8650_tlb_r2.py`）。**逐条处置见 §10.3 修订映射**。
> 基线：`main @ 9316853`（第一次战役集成终点；main 此后已推进 `459b135..bc96ff1` 图表报告工作，Phase D 前须同步）。
> 方法资产：`docs/cpu-uarch-deep-analysis/`（TLB 报告 v1.6、矩阵 v0.2、原型 v2.3——角色见 §2.3）
> 分支：`codex/sm8650-tlb-hierarchy-r2`；有限终点与退役严格按铁律 7 与 §10.4

## 6. 实验协议、预注册规则与统计

### 6.1 固定协议（v1.1 更新）

容量系：ptr_chase + 分布/页内偏移模式（§1.2 Q-A 变量表）；set 系：`probes/tlb-set/` 新探头（B1/B2 估计量、经验驱逐集正控、AB/BA、GROUP 读）；并行度系：K 链独立 kernel（显式寄存器链 + 反汇编黄金检查）。

### 6.2 冻结判据（草案）

Q-A/Q-B/Q-C/Q-D 判据同 §1.2 各问；另冻结（F8/F9）：

- **3% 规则澄清**：OI-12(baseline) 的 +3.6% 是**调查触发器**（触发 regime 根因调查），**不是数据排除门**；两语义不得隐式等同。
- **统计单位**：rounds/访问 seed/重分配/跨 session 分层次；比较按 session/分配配对，区间估计按独立分配或 session 聚类 bootstrap；rounds 不作独立样本；宽区间 knee 用区间差与删失语义，不用两点估计裁决；多 H/多 set 的多重检验处理预注册。
- **事件率非概率**：refill/load 不自动是 [0,1] miss probability（战役 R_0x05 >1000/1k 已证）；victim 二值概率需单独定义分类器与误判率。
- **顺序**：安全性修正 → pilot → 独立校准冻结 → 正式矩阵（M0-5）；校准样本不再用于候选优胜验证。

### 6.3 对比矩阵（同 v1.0）

### 6.4 数据与 schema（同 v1.0 + realized geometry 字段经 M0-4 descriptor 入 record）

## 7. 分阶段矩阵与预算

| 阶段 | 内容 | 出口 |
|---|---|---|
| M0 | §4 六项（v1.1 扩展） | 双评审通过 |
| Gate 0 | §5（含 pilot 标定块） | 事件资格 + 窗口能力定稿 |
| Phase A | Q-A（含 in-page offset 对照） | Q-A 终态 |
| Phase B | tlb-set 探头 + Q-B（B1/B2 定型）+ Q-C（多区域激励） | 终态 |
| Phase C | Q-D K 链 + 排除对照 | 终态 |
| Phase D | 终审 + 对比报告 + 后置项 | 退役清单 |

预算先测后写死；**Phase D 前同步 main（`459b135..bc96ff1` 图表报告线）**。

## 8. 漂移与设备状态（同 v1.0；跨日 >3% 触发调查不触发排除）

## 9. 实现与 TDD（同 v1.0；新增 GROUP 读黄金测试：合成 `[nr,ena,run,values]` 输入解码断言，防 R2 类布局回归）

## 10. 报告纪律、终态与分支退役

三栏制；终态表逐 Q；对比报告 = 战役终审 × 本战役逐项（同统计量比，跨协议标"机制互证"）；退役按铁律 7 两步骤。

### 10.3 修订映射（v1.0 → v1.1，REV-TLB-R2-20260930 处置）

| 发现 | 处置 |
|---|---|
| F1 Q-A 归因过强 | §1.2 Q-A 重订（估计量/几何变量表/HPA UNKNOWN/升级态） |
| F2 T/T2 非对照 | §1.2 Q-B 改 B1/B2 估计量 + 经验正控 + AB/BA |
| F3 原型确定性缺陷 | **已修**（原型 v2.3；评审方 UBSan 复核通过） |
| F4 采样域等价 | §1.2 Q-C 多区域激励 + EQUIVALENT_ON_TEST_DOMAIN 终态 |
| F5 短窗 PMU 协议 | M0-3 PerfWindow（GROUP 原子读）+ G0-3 强制标定 |
| F6 M0 覆盖不足 | M0-1/M0-4 支撑层 + planner 解耦 + 判据身份 |
| F7 Q-D 排除对照 | §1.2 Q-D 四曲线/两条件/负控/显式寄存器链 |
| F8 校准顺序 | M0-5 先 pilot 后池；§6.2 冻结顺序 |
| F9 合同漂移 | §3.1 继承资格；§2.2 OI-12 消歧；§6.2 3% 澄清/配对规则/事件率口径 |
| C1 Android/Linux 编译失败（PageBackingClass 未限定） | **已修**（两处 `probe_common::`；评审同款 NDK 27.2 语法检查通过） |
| C2 逐字段样本分裂 | **已修**（缺失集进分组键；组内样本集合恒一致；回归测试钉住） |
| C3 判据守卫绕过（knee floor / walk 逐样本） | **已修**（`adjudicate_knee` 入口守卫先于 floor；`walk_samples` 逐样本守卫；两种输入覆盖） |
| C4 锚点下游守卫 | **已修**（`_ANCHOR_REQUIRED_EVENTS` 不含 mem_rd——按评审裁定；锚点契约缺失 → BLOCK_FAILED 命名） |
| C5 报告/图表 None 回归 | **已修**（markdown 汇总与逐样本 None 安全、bimodal=None→n/a；**main 侧图表防护 = main `dd4e46a`**，复核脚本 TypeError 清零、overlay 19 项 0 error） |
| C6 OI-13 口径 | 交付范围收紧（本项上方 M0-2 改写）；余量转 §11 |
| C7 B1/B2 定型 / offset 策略 | 预注册补入 §1.2（pilot 定型 + 节点地址策略 + 校验规则） |
| MB-01 GROUP 读长误判 | **已修**（按实际返回字节判定；命名失败原因 last_error_） |
| MB-02 名称错位/越界 | **已修**（names_ 全程按 spec 身份占位 + value_index_ 映射；契约注释不再宣称按内核 ID 解码） |
| MB-03 planner 丢语义参数 | **已修**（_PASSTHROUGH 直通 case_params=证据通道；leftover plan 期拒绝；非 ptr_chase 通用 case_id；两条回归测试）→ **收口复核再修**（2026-10-01 m0b `ee736ed`：撤 _PASSTHROUGH——chains 等未实现语义维度 plan 期受控拒绝，不再"记录成条件、argv 相同"；chase 几何读法移入 ptr_chase 分支，通用形状不再 KeyError；通用 case_id 支持结构化参数 sha256 段、bool fail-closed；swept 参数消费白名单 = deriver 真实输入；4 反例 + 4 钉桩测试） |
| MB-04 二次聚合合并 K 条件 | **已修**（m0b cohort 拒绝非 legacy 身份；main seed_medians 同步拒绝——评审允许方案之一；seams 脚本第 87 行未包该异常属脚本预期旧行为） |
| MB-05 窗口完整性/所有权契约 | **部分修**（复制删除 + 转移语义已实现；窗口差分/有效性 API 转 §11-7） |
| MB-06 descriptor 最小契约 | 转 §11-8（按两层评审 §4 表格落地 requested→canonical→realized 链；Phase B 前核验） |
| MB-07 图表静默删点 | **已修**（main：跳点审计清单 + stderr 披露 + 报告局限段；空系列错误点名 run/buffer/seed/field）→ **收口复核再修**（2026-10-01 main `9093f4a`：缺点数据模式撤除虚假"按可用点重判"声明——终态表改标"历史终审引用（非本数据集重判）" + 顶部警示横幅；冻结判定区间（knee [480,4096] KiB / onset [10240,12288] KiB）按当前曲线覆盖就地标注〔当前曲线不支持〕；claim_support 缺省保守全标；完整数据路径逐字不变） |
| MB-08 B1→B2 切换 OR 条件 | **已修**（合格门三条件，见 §1.2 Q-B 定型预注册） |
| R1–R3 ROB 骨架确定性缺陷 | **属实（已复核）**；ROB 项目文件（main `9a2642c`，r2 基线之外），**不代修**——已由评审登记 REV-TLB-R2-20260930，ROB 项目关闭条件前置 |
| R4 INST_SPEC/RETIRED 口径 | §1.3 非目标预登记 + 执行端设计文档约束 |

### 10.4 分支退役（同 v1.0 §10.3）

## 11. 后置项登记（铁律 0）

1. r0p3 vs Issue 05 逐字核对（OI-14 触发不变）。
2. I 侧短跳板探针：立项条件 = 本战役 Q-B/Q-C 终态落地（设计输入见执行端设计文档）。
3. ROB 项目：R1–R3 缺陷修复为其关闭条件前置；OI-12(rob) 工程对接边界重开决策（本任务不提供输入）。
4. H1–H4 全拒后的 H5+ 假设族：超预算，另立项。
5. open-items 双 OI-12 唯一化重编号（main 侧维护）。
6. 冒烟未关闭项（若有）。
7. **PerfWindow 窗口完整性 API（MB-05 余量）**：~~snapshot 解码与 window validity 分离、前后差分（enabled/running 不随 RESET 清零）、正式窗口有效运行检查——Phase B 短窗 pilot 前完成~~ **API 层已交付（2026-10-01 m0b `44e3e3f`）**：`read_snapshot` 解码与解释分离、`window_delta` 纯函数（enabled/running 累计值跨 RESET 差分有效；命名否决 enabled-zero/mux-detected/enabled-regressed/nr-mismatch；RESET 值非单调标记 values_monotonic），6 个合成场景入黄金测试。剩余 = 真机窗口有效性证据（首个短窗 pilot 的 S6 类 case 随采数取得）。
8. **descriptor 最小证据契约（MB-06）**：按两层评审 §4 表格落地 requested → canonical plan → adapter/kernel → realized observation → identity-aware analysis 链；params 类型规范化与 canonical identity；schema README 登记 probe_shape 与身份维度。
9. OI-13 余量（REV-M0-BATCH C6）：extras 事件的派生字段与消费语义；overlay 测试 `test_missing_metric_fails` 的旧契约期望在 r2 合并时更新（缺指标从"受控退出 1"变为"命名降级"，1 failure 为预期口径差异）。
