# 任务书：SM8650 Cortex-X4 TLB 层级探测（2026-09-28）

> **版本**：v4（取代 v3）。**v3→v4 修订映射**（对应"Software
> Optimization Guide 并列为原厂资料"输入）：
>
> | 输入项 | v4 修订位置 |
> |---|---|
> | *Cortex-X4 Core Software Optimization Guide*（PJDOC-1505342170-538636，Issue 3.0，r0p1）与 TRM 并列原厂资料，职责不同 | §2.2、§3.1、§6.6 |
> | **原厂资料核查门禁**（已控制/未控制/不适用清单） | §6.6（新增） |
> | Arm PDF 版权处置：全文 PDF 与提取文本**不入库**（封面明示"may not be reproduced…without written permission"），移至仓外 `cpu-uarch-ref/arm-docs/`；仓内只留引用元数据与短摘 | §3.1 出处注、§11 |
> | TRM/Guide 修订元数据落档（PDF 封面/修订记录为准，不凭 URL 推断） | §3.1 |
>
> **v2→v3 修订映射**（保留备查）：Arm TRM 升为首要语义源（§2.2、
> §3.1）；**M6 更正 MMUTC ≠ L2 TLB**（TRM §6.1：MMU = L1 TLB + L2
> TLB + MMUTC + translation table prefetcher；MMUTC 为 2048 项 8 路
> walk 缓存）；AArch64-Explore 方法学对照（§6.5）；版本冻结；
> `0x05`/`0x34` 事件文本经 TRM Issue 05 逐字核对。
>
> **前置阅读**：仓库根 `AGENTS.md`（铁律 0–7）、
> `docs/methodology/measurement-discipline.md`、
> `docs/reviews/2026-09-28-sm8650-x4-p0prime.md`、
> `docs/runbooks/redmi-manet-freq-control-chain.md`。
> **本任务与"科学问题未解"解耦**：达不到证据门槛时按 §10.2 终态如实
> 结案，不为得到数值追加实验。

## 1. 任务契约与有限终点

### 1.1 任务对象

- 设备：`redmi-k70pro-01`（SM8650，HyperOS 2.0.208，
  kernel 6.1.118-android14-11-ga3b9c44908dd-ab13320413，KernelSU root）。
- 固定核：**CPU7 / Cortex-X4**（midr `0x410fd821`，toybox `taskset 80`
  为 affinity 请求；执行位置证据见 §4 与 §11）。
- 探针：现有 `ptr_chase`（`stride=64 B` 随机依赖单环、同链展开 ×8、
  warmup 默认 2 完整环、PMU 同窗计数、backing 双端点审计、`-S` 记录
  种子）。artifact 以 run manifest 的 SHA-256 锚定，源码锚点随记录。
- 主实验映射：**4 KiB base（`-B`）**；`-B`/`-T` 实际 backing cohort
  仅用于 Q4。
- 分支：`codex/sm8650-tlb-hierarchy`（worktree
  `.worktrees/sm8650-tlb-hierarchy`）。

### 1.2 四个科学问题

- **Q1**：在 32–8192 个 4 KiB 页的预注册扫描范围内，判断 `0x05`
  event density **是否存在**可重复、可定位的容量型转折；存在则报告
  协议限定的 effective-reach 区间；否则按 §10.2 报告左删失
  （`LEFT_CENSORED`）/ 右删失（`RIGHT_CENSORED`）/ 连续变化 / 未识
  别。**不预设转折存在。**
- **Q2（三级授权）**：
  - **Q2a（必做）**：`0x34`（触发 walk 的访问事件密度）的
    **walk-onset 区间**（判定见 §6.2）；按 TRM 语义，`0x34` = 导致
    **L2 TLB refill（L2 miss → 发起 walk）的 data TLB 访问**；
  - **Q2b（有条件）**：**L2 TLB 层级**联合曲线（`0x2d/0x2f` 正控通
    过后）；`0x2d` 为 unified refill（含指令侧贡献），数据链主导性
    须另行论证，否则只称"unified 曲线"；
  - **Q2c（进一步有条件）**：协议限定的 L2 TLB effective reach——仅
    当 Q2b 成立、第二转折跨重复与训练稳定、且指令侧基线与其他路径
    不能充分解释时；否则终态 `WALK_ONSET_ONLY`。
  - **MMUTC（2048 项 8 路 walk 缓存）是 L2 TLB 之后的独立组件**：本
    任务无直接计数事件，**不对其做 reach/容量声明**；它作为 walk
    成本的混杂因素进入 Q3 的解释边界（§7 Phase C）。
- **Q3（默认关联型）**：translation/walk activity 与 cycles/load 的
  **关联曲线**；**成本型**"translation 暴露成本估计"仅当满足 §7
  Phase C 的排歧条件（含 data-miss 对照组 G3 与可识别性检查）时才
  升级报告，否则 `MODEL_UNIDENTIFIABLE`。
- **Q4**：mixed-THP 降延迟观察是否具有**一致的 translation 事件证
  据链**——进程级实际 backing cohort 对照；latency、`0x05`、`0x34`
  三指标各自预注册方向与最小可检测效应；**不要求、不暗示数值比例
  对应**，不估算 TLB 收益占比。

### 1.3 非目标

- 不反推 cache/LLCC 容量（X4 私有 L2 保持 OPEN/INCONCLUSIVE，
  OI-11；本任务不触碰）。
- 不反推 TLB 物理 entry 数、sets/ways（L1 dTLB 的 fully-associative
  属性与 MMUTC 的 2048 项/8 路除外——它们是 TRM 明示的结构参数，
  见 §3.1，可引用不可外推）、replacement 策略。
- 不把 `cycles/walk` 命名为实测 page-walk 硬件延迟。
- 不把 `0x05/loads`、`0x34/loads` 改写为"miss 概率"（见 §3.2）。
- 不做 mixed cohort 内逐槽位 THP 归属推断。
- 不把 `l1d_tlb_refill` 与 `dtlb_walk` 逐项相减当作 L2 TLB hit
  rate。
- 不把 mixed-THP 同步变化按比例分摊为 TLB 收益占比。
- 不把 AArch64-Explore 在 Apple CPU 上测得的 TLB 容量/延迟/编码移
  植为 X4 结论（§2.2 证据隔离）。
- 不扩展 v0.4、LLCC、PFN 着色、多链、RISC-V、路线 B（可控布局）
  等工作（各有归属，见 §11）。

### 1.4 有限终点（AGENTS.md 铁律 7 原文照录）

> 7. **分支终点（2026-09-28 起）**：功能分支以"预注册任务完成或正式
> 判定不可完成"为终点——科学问题未解不等于分支不能结束；未竟问题
> 一律转 `docs/open-items.md` 跟踪（铁律 0），不得靠永续分支兜底。
> **worktree 回收与分支删除分两步**：worktree 回收看使命完成/工作树
> 干净/无进程依赖/数据分层处置；分支删除须 main 集成 + 完整测试 +
> 推送之后。本地功能分支及时推 origin 备份，避免单点丢失。

本任务的"预注册任务完成" = §4–§7 全部执行并按 §10 终态结案；
"正式判定不可完成" = 触发 §10 的阻断类终态并登记 OI。OPEN 是合法
终态，不是任务失败。

## 2. 证据基线与待决清单

### 2.1 仓内证据

| 证据 | 状态 | 用途 | 不允许推导 |
|---|---|---|---|
| 128/4096 页 `0x05/0x34` 正控（run `20260927T182613Z`） | VERIFIED | 事件方向性锚点 | knee 位置、L1 容量 <128 |
| P0″ 6300 条 PMU 观测 0 复用违约、0 编码异常 | VERIFIED | 复用探针内计数链 | 新事件必然有效 |
| `0x05` 128 页 288.08/1k、4096 页 1029.95/1k | VERIFIED | Q1 先导观察 | L1 entry 数；miss 概率 |
| `0x34` 128 页 0.0129/1k、4096 页 39.90/1k | VERIFIED | Q2 先导观察 | walk 次数/步数 |
| perf/simpleperf 与探针内计数同窗差分 | 未执行（OPEN） | 可选外部交叉验证 | 阻断本任务 |
| `0x2d/0x2f/0x8136/0x8128/0x8138/0x813a/0x813c/0x813e/0x8167` | 未实操 | Q2b/Q3/Q4 候选 | 未正控先用于结论 |
| THP backing 双端点审计 + 实际 backing 分组 | VERIFIED | Q4 进程级 cohort | 窗内逐时刻状态恒定、逐槽位归属 |
| 跨三日 512/1280 KiB 锚点复现 ≤1.2% | VERIFIED（经验观测） | 锚点判据参考 | 所有事件统一硬阈值 |
| ceiling drift 三次复发均 fail-closed | VERIFIED-NEGATIVE | 执行纪律 | 根因已知（OPEN） |

### 2.2 外部证据边界（三类来源，各管一段，互不越位）

| 来源 | 它回答什么 | 它不能回答什么 |
|---|---|---|
| **Arm Cortex-X4 TRM**（doc 102484；当前在线修订 `/102484/0003/` r0p3；本文逐字核对自 Issue 05 = `102484_0002_05_en` PDF，见 §3.1 出处注） | **目标核文档声称什么**：MMU 组件结构（L1 TLB / L2 TLB / MMUTC / translation table prefetcher）、miss→walk 路径、PMU event 文本 | 设备上的实际计数行为、THP backing、有效触达区间（须本机验证） |
| **Arm Cortex-X4 Core Software Optimization Guide**（PJDOC-1505342170-538636，Issue 3.0，r0p1，2023-05-26；全文 PDF 经 pdftotext 核对，见 §3.1 出处注） | **Arm 对软件访问模式与性能优化的指导**：用于审视随机依赖链、工作集扫描与结果解释是否遗漏微架构干扰（§6.6 核查清单）；其指令 latency/throughput 表是未来 core/pipeline 探针的资料 | **不是** TLB 容量/walk 成本数据源（全文无此类规格）；其建议**不成为**本机实测参数，也不据此事后改动已冻结矩阵 |
| **AArch64-Explore**（submodule，钉 `9e3d464`；README 自述对象为 **Apple M1 及后续 CPU**） | **哪些实验混淆值得排除、探针怎么设计**：访问模式、页内 offset 解耦、box 模式预取器检测、遍历变体、页尺寸变体（§6.5） | Apple 平台测得的 TLB 容量/延迟/计数编码**不能移植**为 X4 结论；其 README 定位是 toolbox 而非规格书 |
| **本机 run（本仓 records）** | **SM8650 CPU7 实际观测到什么** | 无——这是唯一的行为事实来源 |

## 3. 术语、事件表与结论权限

### 3.1 来源层级与事件定义表

**来源层级（首要 → 辅助 → 本机）**：

1. **Arm 原厂文档两份（并列首要，职责不同）**：
   - **Cortex-X4 Core TRM**（doc 102484）：事件与结构术语的**定义
     源**。*Memory management* 与 *Performance monitors events* 两
     节。修订元数据：本文逐字核对自 **Issue 05
     （`102484_0002_05_en`）PDF**；在线入口当前为 `/102484/0003/`
     （r0p3），**r0p3 与 Issue 05 的逐字差异核对列入 §11 待办**。
   - **Cortex-X4 Core Software Optimization Guide**
     （PJDOC-1505342170-538636，**Issue 3.0**，r0p1，2023-05-26，
     Non-Confidential；修订记录以 PDF 封面为准，非 URL 推断）：访
     问模式/性能优化指导的**混淆审查源**（§6.6）；其指令
     latency/throughput 表留作未来 core/pipeline 探针资料。
   **出处注（版权处置）**：Arm 文档站为 JS 渲染；两份 PDF 均经
   documentation-service/官方页面下载 + pdftotext 提取核对。两份
   PDF 封面均明示"may not be reproduced…without written
   permission"——**全文 PDF 与提取文本一律不入 git**，已移至仓
   外 `cpu-uarch-ref/arm-docs/`（只读）；仓内只保留引用元数据
   （文档号/修订/章节）与必要的短摘。
2. **ARM-software/data `pmu/cortex-x4.json`**：TRM 衍生的事件表可检
   索副本（其 refs 即引 TRM），counters=6；用作配置编码的固定索引
   （钉访问日期）。
3. **本机正控（本仓 runs + `configs/pmu-event-registry.json`）**：行
   为资格（S4）。三者不一致 → `SEMANTICS_UNVERIFIED`，不得择一方
   便解释。

**MMU 结构（TRM §6.1 + Table 6-1，Issue 05 逐字核对）——M6 更正
要点**：

```text
Cortex-X4 MMU 组件 = L1 instruction TLB + L1 data TLB（+ L1 TRBE TLB）
                   + L2 TLB（两级 TLB 结构的第二级）
                   + MMUTC（MMU Translation Cache，独立组件）
                   + translation table prefetcher
```

- **L1 data TLB**：**fully associative**，原生支持 4KB/16KB/64KB 页
  与 2MB/512MB block（TRM 原文）。
- **L2 TLB**：两级 TLB 结构的第二级；存全部页尺寸并按需为 L1 拆分
  （"stores all page sizes…breaking these down into smaller pages"）；
  miss 路径（TRM 原文）：**L1 miss → L2 TLB lookup → L2 miss →
  hardware translation table walk**。
- **MMUTC**：缓存 **translation table walk 中获得的中间 descriptor
  PA**（walk 缓存，不是 VA→PA TLB）；**8-way set associative，
  2048 entries**（TRM Table 6-1 明示参数）。**M6 更正：MMUTC ≠ L2
  TLB——二者是不同组件**（v2 的"同物两名"系错误，本版废止；外部
  评审此前的谨慎提醒（"偏强"）按 TRM 原文升级为确定性更正）。
- **translation table prefetcher**：检测连续页表访问并预取下一段，
  ECTLR 可禁。

**事件定义表**（TRM 文本列 = Issue 05 逐字核对状态）：

| code | 事件 | TRM 文本（出处行） | 本机资格（注册表） | 可支持的最强结论 |
|---|---|---|---|---|
| `0x05` | `L1D_TLB_REFILL` | ✅ 逐字一致："counts any refill of the data L1 TLB **from the L2 TLB**"，含翻译错误路径 | VERIFIED（run `20260927T182613Z`） | refill-like event density |
| `0x34` | `DTLB_WALK` | ✅ 逐字一致："data TLB access with at least one translation table walk；counts on any data access which **causes L2D_TLB_REFILL**" | VERIFIED（同上） | walk-like event density（= L2 TLB miss 触发） |
| `0x25` | `L1D_TLB` | L1 dTLB 查找（同拍 load+store 计 2 次） | 未注册 | （备选分母） |
| `0x2d` | `L2D_TLB_REFILL` | L2（统一）TLB refill（含指令侧） | 未注册 | unified refill-like（须正控） |
| `0x2f` | `L2D_TLB` | L2 TLB 访问（由 L1 refill 引起） | 未注册 | L2 access-like（须正控） |
| `0x8136` | `DTLB_STEP` | walk 的 step（步数） | 未注册 | 步数比（须与 `0x34` 口径配对验证） |
| `0x8128` | `DTLB_WALK_PERCYC` | 每周期在途 data walk 数（积分语义，非"walk 花多少周期"） | 未注册 | walker 活动量（须正控方向性） |
| `0x8138` | `DTLB_WALK_LARGE` | 大页 data walk | 未注册 | Q4 大页证据（须正控） |
| `0x813a` | `DTLB_WALK_SMALL` | 小页 data walk | 未注册 | Q4 小页证据（须正控） |
| `0x813c` | `DTLB_WALK_RW` | demand 访问导致的 walk | 未注册 | demand walk（升级候选） |
| `0x813e` | `DTLB_WALK_PRFM` | preload/prefetch 导致的 walk | 未注册 | prefetch walk（升级候选） |
| `0x8144` | `L1D_CACHE_MISS` | L1 data cache demand access miss | VERIFIED（P0″ runs） | data-miss 排歧对照 |
| `0x8167` | `STALL_BACKEND_TLB` | 后端 TLB stall 周期 | 未注册 | translation 受阻（升级候选） |

**措辞差异照录**：`0x02 L1I_TLB_REFILL` 的 TRM 文本写 refill 来源为
"from the MMU Translation Cache (MMUTC)"，而 `0x05` 写 "from the
L2 TLB"——同一份 TRM 内两种措辞；**照录不裁定**（不影响 `0x05`
的使用：其来源措辞为 L2 TLB，与 §6.1 的 miss 路径一致）。

**事件资格注册（S4）**：`configs/pmu-event-registry.json`（随本任务
TDD 建立）。每条注册：`{type, config, name, midr, source_doc,
source_revision, positive_control_run, outcome, review_ref,
validity_scope}`。分析器对未注册或作用域不匹配（MIDR/run 不符）的
事件自动降级 `SEMANTICS_UNVERIFIED`。

### 3.2 统一分母与密度定义

所有率默认：`R_e = 1000 × C_e / N_timed_dependent_loads`。
`R_0x05` = refill-like event density；`R_0x34` = walk-like event
density。

**`0x05` 在 4096 页达 1029.95/1k（>1000/1k）**：可直接推出的只是
**该事件总数大于探针报告的 timed dependent loads 数**。可能原因
（未鉴别，不预断）：计数窗覆盖 t0 前/t1 后代码（§5.3 量化）、被计
事件包含推测或重试路径（取决于目标核定义）、事件语义并非"每个完
成依赖 load 至多一次"。**分析器保留原值：不截断、不改写为 miss
概率**；原因待事件原文 + 窗口开销扫描 + 测量长度扫描共同核对
（§5.3）。TRM 对 `0x05` 的原文（"any refill of the data L1 TLB
from the L2 TLB"）已逐字核对——该文本本身不约束每 load 至多一
次，与观测不矛盾。

### 3.3 结论权限（逐级需证）

```text
观测事件变化（单 case）
→ 跨重复/seed/块稳定（协议级事实）
→ 显示 translation-related 转折（Q1/Q2a/Q2b 范围）
→ L2 TLB effective reach（Q2c 上限，须 Q2b + 稳定性 + 排他性）
→ translation 暴露成本估计（Q3 成本型上限，须 G3 排歧 + 可识别性）
```

默认层级：Q1/Q2a/Q2b 为**观测-协议级**；Q3 默认**关联型**。物理
entry 数、sets/ways（除 TRM 明示项）、`cycles/walk` 硬件延迟、
MMUTC reach、成本型因果值不在默认授权范围。

## 4. Gate 0：现有计数与执行契约复验（非重做基础设施）

正式采集前确认以下契约未退化（逐项有机器证据）：

1. 探针 artifact SHA-256 与 run manifest 一致、源码锚点在史；
2. **affinity 请求与执行位置证据分开记录**（M1）：raw 样本含
   `taskset 80` 命令行（= 请求）；执行位置以平台控制链与记录为证
   据。**当前探针无运行时 CPU 字段**——请求不等于测量期间未迁核；
   该证据缺口的处置见 §11（OI 登记，不阻断本任务，CPU7 为独占
   policy 域内唯一大核且实验以 taskset 绑定）；
3. 每事件 `time_running == time_enabled`（零复用）；
4. 事件 type/config 与 §3.1 表及注册表一致；
5. timed loads / warmup loads / ring passes 自洽（ring_passes 由
   `loads / slots` 自证）；
6. backing 双端点审计通过（或样本按契约 fail 入档）；
7. read-before-disable 计数路径未被改动；
8. controlled-baseline 环境事务有效且事后恢复 `walt`。

**阻断条件**：探针内事件恒零、编码倒挂、契约字段缺失或
read-before-disable 被破坏 → 停止正式结构推断，转入计数链调查。
外部 perf/simpleperf 对照为**可选交叉验证**，不是默认阻断项。

## 5. Gate 1：新增事件正控（按需求顺序，逐项过/降级）

### 5.1 正控顺序与内容

顺序：① `0x2d/0x2f`（Q2b）→ ② `0x8136/0x8128`（Q3）→ ③
`0x8138/0x813a`（Q4）→ ④ `0x813c/0x813e/0x8167`（仅主问题需要
时升级，不默认纳入）。

每项正控内容：floor/scale 锚点（128 页 vs 4096 页方向性）；适用时
base/mixed/thp 实际 backing 对照（`0x8138/0x813a` 必须）；10 个新
进程重复 + 短块；编码与 `running == enabled` 校验；**通过判据**：
方向与预期一致、跨进程稳定、无恒零 → 写入
`configs/pmu-event-registry.json`（含 run ID 与作用域）。**失败处
置**：`SEMANTICS_UNVERIFIED`，结论降级，原始数据不改写。**有限终
点**：不为找到期望曲线连续尝试新 raw event。

### 5.2 事件组（候选；最终以 running==enabled 为准；跨组不相减）

| 组 | 目标 | 事件 |
|---|---|---|
| G0 主曲线 | Q1/Q2a 基础 | cycles, mem_access_rd, `0x05`, `0x34` |
| G1 层级辨识 | Q2b 增强 | G0 + 注册后的 `0x2d/0x2f`（合计 ≤6） |
| G2 walk 活动 | Q3 主体 | cycles, `0x05`, `0x34` + 注册后的 `0x8136/0x8128`（合计 ≤6） |
| **G3 data-miss 排歧** | Q3 混杂对照 | cycles, mem_access_rd, `0x05`, `0x34`, `0x8144`（=5） |
| G4 页尺寸 | Q4 增强 | cycles, `0x05`, `0x34` + 注册后的 `0x8138/0x813a`（合计 ≤6） |

不同组是不同 run；**未验证锚点一致性前不得跨组逐项相减**；G3 未
执行时 Phase C 不得声称"已检验 data-miss 共线性"（M3）。

### 5.3 PMU 窗与墙钟窗的固定开销（逐事件判定，M2）

现有协议 `perf start → t0 → chase → t1 → read → disable`：PMU 覆盖
t0 前/t1 后少量探针代码；read-before-disable 是下游驱动约束，**不
改动**。量化方法（预注册）：

- 两点扫描：512 KiB（floor 区）与 16 MiB（walk-active 区）；
- 每点三个测量长度：**8 / 64 / 256 ring passes**（每长度 ≥1 个完整
  环；4 个 order_seed 同步检验斜率稳定性）；
- 对每个事件拟合 `C_e(N) = a_e + b_e·N`（N = timed loads）；
- **判定阈值（预注册）**：正式窗口采用的长度下，`|a_e| / C_e(N)`
  ≤ 5% 时该事件的边界开销可忽略并在报告标注；超过时该事件的绝对
  密度只报告为"含固定开销"，相关转折判定改用跨长度一致的斜率
  `b_e`。

## 6. 实验协议、预注册规则与统计

### 6.1 固定探针协议（照实现写，不虚构）

- 分配：guarded mmap（Linux）→ madvise（`-B`/`-T`）→ 建链触页（无
  独立 prefault）→ warmup 2 整环（精确 loads 入档）→ 端点审计 1 →
  PMU start → t0 → ×8 chase → t1 → read/disable → 端点审计 2 → 输
  出（含 before/after/endpoints_equal/seed/PMU 组）。
- 每 case：**10 个全新进程**（重复单位是进程；record 必带
  repetitions、median、分位数）。
- **训练量两个旋钮不混淆（M4）**：`warmup_passes`（默认 2 环，预热
  用）与 `loads_per_slot`（timed 训练量：短=8、长=512 ring
  passes）是不同参数；Phase A/B 的短/长训练指 `loads_per_slot`，
  warmup 保持 2 环不变。
- 布局变量：现有 `-S` 只控制访问顺序（**order_seed**）。本任务采
  用**路线 A**：4 个 order_seed + 10 个新进程布局观测（记录每进程
  VMA base），**不声称正交 layout_seed 实验**；若 Q1 对进程布局显
  著敏感，记 `LAYOUT_OBSERVATION_LIMITED` 并转 OI（路线 B 后置立
  项）。

### 6.2 analysis_rules v1（预注册冻结规则）

> **本节约定的全部数值与算法在首次 Phase A 正式采集前冻结**：以
> 文本块形式入本任务书，随任务书 commit 定版；其 SHA-256 与任务书
> 版本、源码 commit 一并写入每个 run 的评审记录。Phase B 配置只由
> §6.2.4 的确定性生成器从质量合格的 Phase A 数据产生；**不允许看
> 图后人工改点、改阈值或删 seed**。任何规则修订 = 新版本号 +
> CHANGELOG + 显式标记 exploratory 重测。

**6.2.1 粗扫页数（Phase A，buffer = pages × 4 KiB）**

```text
32, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 2048, 4096, 8192
```

**6.2.2 候选转折检测（Q1 knee）**

相邻页数点 (p_i, p_{i+1}) 满足全部三项即提名候选区间：

- `R_0x05(p_{i+1}) / R_0x05(p_i) ≥ 2.0`；
- `R_0x05(p_{i+1}) − R_0x05(p_i) ≥ 50 /1k`（绝对增量下限）；
- `cycles_load(p_{i+1}) / cycles_load(p_i) ≥ 1.15`。

多个候选分别列出；无候选 → Phase B 不生成，Q1 按
`RIGHT_CENSORED`（上界内未识别）或连续变化结案。

**6.2.3 walk-onset 检测（Q2a）**

首次满足以下全部条件的最小页数 p：

- `R_0x34(p) ≥ 1.0 /1k`；
- 该点 ≥8/10 样本 `R_0x34 > 0.5 /1k`（逐样本地板分离）；
- 下一个页数点同样满足前两项（持续性）。

8192 页仍未满足 → `RIGHT_CENSORED`（onset 下界报告）。

**6.2.4 Phase B 致密点生成器（确定性）**

对每个候选区间 [p_i, p_{i+1}]：插入四分位点
`p_i + k·(p_{i+1} − p_i)/4`（k=1,2,3）；若 `p_i/2 ≥ 32` 再插入
`p_i/2`。去重、升序。输入 = 通过质量门槛的 Phase A 数据；记录输入
run SHA-256、本规则块 SHA-256、输出配置 SHA-256。候选区间 >3 个
时按 `R_0x05` 相对增量取前 3。

**6.2.5 锚点判据（质量门槛）**

- 每个 Phase 配置的首尾各嵌一个锚点 case：**512 KiB base** 与
  **3072 KiB base**（G0 事件组、短训练、order_seed=42、10 进程）；
- 锚点有效：两锚点 median latency 与同制度历史组（short-base
  20260928T024022Z 的 512/3072 KiB 组）中位数偏差 ≤3%，且
  R_0x05/R_0x34 落在历史组 [p25, p75] 内；
- 锚点失真 → **当前块（= 该 run 目录）fail-closed**：块内数据不
  进入判定，查明原因后重跑该块。

**6.2.6 稳定条件（knee 成立）**

候选区间须：≥3/4 个 order_seed 的致密区间相互重叠；两种训练量
（8/512 ring passes）同制度（区间位置一致，幅度可变）；无块
fail。否则按 `ORDER_SENSITIVE` / `TRAINING_SENSITIVE` 结案。

**6.2.7 阶段 case 上限**

Phase A ≤ 28（13 点 × 2 seed + 2 锚点）；Phase B ≤ 48（≤3 区间 ×
≤4 插入点 × 4 seed × 1 训练量起步，含锚点）；Phase C ≤ 24；Phase
D ≤ 240 进程次（见 §7 Phase D 的 40/point·policy 上限）。**达到上
限即停，按已获数据结案。**

### 6.3 统计与数据分层

- **重复单位是进程**：每 case 10 个全新进程取 median（≥5 的纪律
  下限）；报 median [p25, p75]、各 seed 曲线、rejected 数。
- **"单次值禁止入库"的精确含义（S6）**：单次观测不得作为
  baseline/校准结论晋升；**逐样本原始记录（raw observations）是允
  许且必须归档的**——raw 本地保留 + SHA256 锚定，
  records/artifacts/manifest 按层入库；纪律违例数据进
  `data/quarantine/`（保留审计，禁止晋升与校准链）。
- 失败记录空 metrics + 结构化 failure；锚点失真 → 块 fail-closed
  （§6.2.5）。

### 6.4 块与锚点的机读证据（S3）

块 = 一个 run 目录（短块执行即一次 runner run）；锚点 case 作为
sweep 首尾条目**嵌入实验配置**（§6.2.5），与块内 case 共用同一
records.jsonl、同一环境事务与门禁快照——块-锚点关联由记录自证，
不依赖时间邻近推测。分析器以 `params.buffer_kb` 识别锚点 case 并
先做 §6.2.5 判定，再处理其余 case。

### 6.5 探针设计对照：AArch64-Explore 方法学（commit `9e3d464`）

> 来源：`third_party/AArch64-Explore`（submodule，钉
> `9e3d4646b296fc2948a3343c04bbc0a7835d4f79`）。以下结论均直接读
> 自 `AArch64-Explore/ProbeLatency.cpp` 与 `Probes.h` 的具体源码段
> 落（行号为该 commit 内容）；**其对象为 Apple M1+ CPU，此处只借
> 设计思想，不取任何数值结论**（§2.2 证据隔离）。

| 维度 | AArch64-Explore 的做法 | 本仓 `ptr_chase` 协议 | 对本任务的启示 |
|---|---|---|---|
| **TLB↔cache 解耦** | `kRandomTLBOffset` 族（:719/:738/:762）：页内加随机/线对齐/置换 offset——"test linear access of TLBs **without stressing cache associativity**"，遍历大面积（TLB 压力）而避免全部 load 落入同一 L1D set | 默认 `stride=64 B`，**每 4 KiB 页 64 slots 全遍历**——TLB 压力与数据 footprint 随页数**同增**（A4 混杂） | 我们的 X4 L1 dTLB 是 **fully associative**（TRM 明示），set 冲突在 L1 TLB 上不存在；但数据 cache 混杂仍在。Explore 的 offset 模式是"每页少量 slot"的替代设计——若 Q1 判定受 footprint 混杂支配，将其列为路线 B 候选（§11），本任务不携带 |
| **遍历变体** | `TLB Linear Increasing / Linear Decreasing / Full Random`（:1566-1583）：顺序/逆序/随机三向对照，区分预取与 replacement 效应 | 固定随机单环 × `order_seed`（只改顺序） | 逆序/顺序对照是廉价的机制排歧项：Phase A 可加 1 个 `kLinearIncreasing` 类对照点（经 runner 现有种子协议即可表达）——纳入 Phase A 可选增强，不扩 scope |
| **页尺寸变体** | `Node<sizeofPage8K64/16K/16K64>`（:1561 起）：8K/16K 多页尺寸节点 | 4 KiB base 为主；`-T` THP 仅 Q4 | 粒度变体对 Q4 有参考价值（`0x8138/0x813a` 大/小页 walk 事件正是为此设计） |
| **预取器检测** | box 模式（:371 注释）：页内集节点成"box"，同 box 相同随机 vs 不同随机，检测模式学习类预取器 | 用 PMU `L1D_CACHE_HWPRF (0x8154)` 直接测预取活动（P0″ 已测得 512→640 KiB 预取覆盖崩塌） | 两条路径互证：我们的事件法更直接，box 法可作为无事件时的后备；不必引入 |
| **缓存层级标记** | 测试缓冲档位标注覆盖域（:130-137：`2_MiB //covered by L1 TLB`、`16_MiB //covered by L2 TLB`、`48_MiB+ //covered by L2C TLB`） | 粗扫点按 §6.2.1（32..8192 页） | **档位标注思想采用**（粗扫点按候选结构区间成组提名）；**其数值（Apple 的 TLB 覆盖域）不采用** |
| **队列模拟** | `SimulateQ.nb`：TLB/L1 的队列模型仿真 | 无 | 若 Q3 需模型化解释，先读其模型假设再决定是否借鉴（§11 待办） |
| **TLB MLP** | `kTLB_NumSimultaneousLookups_Probe`（Probes.h:35） | 无（MLP=1 依赖链） | 本任务不涉及并发查找 |
| **计数/计时** | `m1cycles`（Apple KPC 私有计数框架） | Linux `perf_event_open`（read-before-disable） | 接口不同，纪律相同（原始计数 + enabled/running 审计） |

**引用方式**：正式报告中写"与 AArch64-Explore 的方法对照"时，必
须指到具体源码位置（commit permalink + 文件 + 行号），不得笼统背
书项目名；其 `Probes.h` 的 TestTraversal 模板与 warmup 处理**尚未
阅读**（§11 待办），本节结论以 `ProbeLatency.cpp` 已读段落为准。

### 6.6 原厂资料核查门禁（Optimization Guide 混淆清单）

> 门禁要求（预注册）：冻结 §3 事件语义与 §6 探针协议**之前**，已
> 核对两份原厂文档相关原文并记录文档号/PDF 实际修订/章节/页码
> （§3.1 出处注）。下表为 Optimization Guide 对本探针协议
> （`stride=64 B`、每 4 KiB 页 64 slots、同链展开 ×8、计时窗内纯
> load）的逐项判定；**不因指南建议事后改动已冻结矩阵**——需要的
> 新探针一律转 §11 open item。

| Guide 指导（章节） | 内容 | 对本协议的判定 |
|---|---|---|
| §4.4 Load/Store alignment | 跨 64B cache-line 边界的 load 与非 4B 对齐 quad load、跨 32B 边界的 store 有性能惩罚 | **已控制**：chase 每次访问为 64B stride 的 8B 指针 load，恒不跨线 |
| §4.5 Store to Load Forwarding | store→load 转发有对齐/数量限制 | **不适用**：计时窗内纯 load（建链 store 全在窗口外） |
| §4.3 Optimizing memory routines | 循环展开（每迭代多个 load/store）摊薄循环开销；但示例为独立 LDP/STP（引入 MLP） | **已控制（有意分歧）**：本探针同链展开 ×8——摊薄循环控制且**严格 MLP=1**（原理 §3 已论证；指南的并行化建议对被测量有反向作用，不采用） |
| §4.3 非临时 load（LDNPQ）/ DC ZVA | 针对 non-cacheable 流式例程 | **不适用**：本工作负载为 cacheable 匿名映射 |
| §4.13 Cache maintenance operations | cache 维护指令的性能注记 | **不适用**：本探针不使用 cache 维护指令 |
| 全文检索 | 无 TLB 容量/walk 成本/依赖链延迟探测内容 | **不适用**：不能作为 TLB 规格证据（与输入方的边界声明一致）；translation 性能结论一律以 TRM + 本机 run 为准 |

## 7. 分阶段矩阵与执行预算

### Phase A：base 粗扫（提名候选区）

- §6.2.1 的 13 个页数点 × 2 个 order_seed（42, 7）× 短训练
  （`loads_per_slot=8`，min_loads 地板不生效）× base（`-B`）× G0；
- 首尾锚点（§6.2.5）；Current HAL 温度与 cdev `cur_state` 采集；
- 产出：Q1/Q2a 候选区（按 §6.2.2/6.2.3 算法）；不产出结论。

### Phase B：候选区致密扫描（判定）

- §6.2.4 生成的致密点 × 4 个 order_seed（42, 7, 1337, 20260928）
  × 短训练起步；若候选成立，加跑长训练（512 ring passes）对照；
- G0/G1（G1 需 `0x2d/0x2f` 已注册）；
- **长训练热预算单列（M4）**：512 ring passes 下 warmup 量 =
  slots×512 loads/进程——8192 页（524,288 slots）单进程 warmup ≈
  2.68 亿 loads，为同点 timed 的 64 倍；长训练 case 成本由 warmup
  主导，**禁止**用 4.5 s/case 估计；按 `slots × 512 × 10 进程` 逐
  点核算，长/短训练分块并块间冷却，锚点漂移达 §6.2.5 阈值即停。

### Phase C：Q3 关联与条件升级

- 在 walk-floor / onset / active 三类区域选点（由 Phase A/B 数据
  按 §6.2.3 确定）；
- G2 先行；**G3（含 `0x8144`）为"检验 data-miss 混杂"的必备对
  照**——G3 未执行或跨组锚点不可比时，只发布关联曲线（默认层），
  终态 `MODEL_UNIDENTIFIABLE`，不输出任何成本值；
- 可识别性检查：walk density 与 `0x8144` density 的共线程度、事
  件口径配对性（`0x8136` vs `0x34`）、跨长度斜率一致性（§5.3）；
  **MMUTC 混杂声明**：walk 服务时间受 MMUTC（2048 项 walk 缓存）
  命中状态影响，成本型估计必须声明该混杂未分离；
- 全部通过才升级报告"暴露成本估计"（标 DERIVED + 竞争解释）。

### Phase D：Q4 THP cohort 对照（含停止预算，M5/S5）

选点（科学角色优先，≤3 点）：

1. **策略负控点**（预计 `-T` 仍为 base）：512 KiB——验证"仅请求
   THP"是否改变结果；
2. **映射机会点**（历史 mixed 区）：2304 KiB、3072 KiB；
3. **walk-active 点**：若与 2 冲突，以映射机会点优先（此时 walk-
   active 证据由 Phase B/C 承担）。

每点：`-B` 与 `-T` × 4 order_seed × 短训练 × G0（+G4 若注册）。
**停止预算（预注册）**：

- 每（buffer × policy）：**最多 40 个进程次**（4 seed × 10）；失
  败/被拒样本计入该额度；
- cohort 有效下限：每（buffer × backing cohort）≥ 3 个有效样本才
  成立该 cohort；
- 未达下限 → 该 cohort 终态 `INSUFFICIENT_COHORT`（只影响该
  cohort，不影响其他 cohort 结案）；
- 必报转化表：请求次数 → 实际 backing 构成 → 端点 drift 失败数
  → 进入分析样本数（选择偏差披露）；
- 指标各自预注册（A5）：latency 方向与最小可检测效应 ≥5%，
  R_0x05/R_0x34 方向与各自地板/规模段阈值（§6.2 口径）；报告三者
  方向一致性与各自不确定度；**不要求数值比例对应**。

### 执行预算（先测后写死）

- 经验单 case ≈ 4.5 s（短训练、含 10 reps 与 runner 开销）；
- 粗估（不含门禁/锚点/正控/重试/冷却/评审）：A ≈ 26 case（≈2
  min）→ B ≤ 48 case（短）+ 长训练按 §Phase B 单列核算 → C ≤ 24
  case → D ≤ 240 进程次（≈2–4 min）；
- 另计：Gate 1 正控（~10–20 case）、锚点、THP cohort 达成率（历史
  mixed 10–50%）、结构性失败重试、块间冷却；
- **纯执行时间不写成战役总耗时**；Phase A 完成后按实测修订预
  算。

## 8. 漂移、设备状态与重启

- 默认 Android baseline：**不关闭** thermal/perf 服务、不杀后台、
  不 drop caches、不 force-idle、不改飞行模式（"受控安静态"≠"纯
  净态"）；
- host mutation 一律 durable journal + 逆序恢复；
- 硬门禁：screen off / Dozing / camera idle / mi_thermald running /
  thermal status=0 / `max_cpu_temp_c=90.0`；
- drift 打法：短块 + 首尾锚点（§6.2.5/§6.4）+ `scaling_max_freq`
  画像值（2265600/2707200/2707200/2745600）+ Current HAL 温度
  （cached 禁用）；
- 重启四触发（基线污染/系统变更/长间隔首矩阵/绝不例行）；开机序
  列：boot_completed → 拔充或记录 → 静置 10–15 min → quiet-state
  门禁 → 5–10 min 限额稳定性观察 → 低成本锚点 → 开跑。

## 9. 实现与 TDD

### 9.1 配置（`configs/experiments/`，阶段化多文件，防叉积膨胀）

- `ptr-chase-sm8650-x4-tlb-ctrl.json`（Gate 1 正控）；
- `ptr-chase-sm8650-x4-tlb-coarse.json`（Phase A，含首尾锚点 case）；
- `ptr-chase-sm8650-x4-tlb-dense.json`（Phase B，由 §6.2.4 生成器
  产出，随附输入/规则/输出三 SHA-256）；
- `ptr-chase-sm8650-x4-tlb-thp.json`（Phase D）；
- 全部 protocol 1.2、`execution.controls: ["x4-prime"]`、
  `runner/tests/test_plan.py` protocol/case-count 守卫同步登记。

### 9.2 分析器与注册表

- `configs/pmu-event-registry.json`（§3.1/S4，随 TDD 建立）；
- `analysis/sm8650_tlb.py`：复用 `sm8650_x4_p0prime.py` 契约（编码
  /running/seed/sample_index/backing 校验、全失败 run 进 rejected、
  双峰标记），新增：
  - event density（R_0x05/R_0x34，>1000/1k 保留原值）；
  - §6.2.2/6.2.3 检测、§6.2.5 锚点判定、§6.2.6 稳定条件；
  - 事件资格状态（读注册表，未注册/作用域不符 →
    `SEMANTICS_UNVERIFIED`）；
  - Q3 可识别性检查输出（含 MMUTC 混杂声明检查）；
  - THP cohort 转化表与 `INSUFFICIENT_COHORT` 终态。

### 9.3 测试（`analysis/tests/test_sm8650_tlb.py` 等）

至少覆盖：①正控点不被误报为 knee；②`0x05`>1000/1k 不截断不改成
概率；③未注册事件不得进入 Q2c/Q3/Q4 结论；④mixed 不并入 thp；
⑤端点变化样本无数值 metrics；⑥running≠enabled 拒绝；⑦锚点失败
整块失效；⑧无膝点/双膝点/边界点（含左删失）；⑨order 敏感与训练
敏感；⑩模型不可识别时不输出成本值；⑪全失败 run 仍出 rejected；
⑫改判据/改历史数据必须留 revision history；⑬G3 缺失时不得声称
"已检验 data-miss 共线性"；⑭cohort 不足时输出
`INSUFFICIENT_COHORT` 且不追加尝试。

## 10. 报告纪律、终态与分支退役

### 10.1 报告分栏

- **直接实测**：ns/load、PMU cycles/load、event density（/1k
  loads）；
- **派生量**（标 DERIVED）：差值、比例、模型系数、暴露成本估计
  （若升级）；
- **微架构解释**：支持什么、哪些竞争解释未排除；**来源标注**——
  TRM 声称 / Explore 方法 / 本机观测，三段分标（§2.2）。

### 10.2 终态（每 Q 独立，不要求全有数值答案）

```text
INTERVAL_IDENTIFIED / WALK_ONSET_ONLY / LEFT_CENSORED / RIGHT_CENSORED /
ORDER_SENSITIVE / LAYOUT_OBSERVATION_LIMITED / TRAINING_SENSITIVE /
SEMANTICS_UNVERIFIED / BACKING_UNCONFIRMED / INSUFFICIENT_COHORT /
MODEL_UNIDENTIFIABLE / OPEN
```

- `LEFT_CENSORED`：首个扫描点（32 页）已处高位制度（按 §6.2 规则
  判定，如 R_0x05(32) ≥ 100/1k）——不得报告为 LOWER_BOUND；
- `RIGHT_CENSORED`：扫描上界（8192 页）内未出现目标转折/onset。

### 10.3 分支退役

严格按铁律 7：预注册任务完成或正式判定不可完成 → 未竟项转
`docs/open-items.md` → 正式评审 → FF 集成 main → main 全量复验
（CTest/单测/schema/哈希）→ 推送 origin → worktree 回收与分支删
除分别满足各自条件。OPEN 不阻碍退役。

## 11. 后置项登记（铁律 0；任务结束时落 `docs/open-items.md`）

1. **TRM r0p3 vs Issue 05 逐字差异核对**：本任务书的事件文本与
   MMU 结构描述逐字核自 `102484_0002_05_en`（Issue 05）PDF；Arm
   文档站（`/102484/0003/`，JS 渲染）当时无法抓取，r0p3 与 Issue
   05 的 §6.1 与 PMU events 两节差异未核对——下次可访问时补核，
   如有差异以 r0p3 为准并出修订。
2. **`Probes.h` TestTraversal 模板与 warmup 处理**（AArch64-
   Explore）：§6.5 结论以 `ProbeLatency.cpp` 已读段落为准；其遍历
   模板/warmup/计时细节未读，需引用时先读源码。
3. **Arm 文档物理位置登记**：两份原厂 PDF 与其 pdftotext 提取文
   本位于仓外 `cpu-uarch-ref/arm-docs/`（`x4trm.pdf` =
   `102484_0002_05_en`、`Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf`
   = PJDOC-1505342170-538636 Issue 3.0、各自 `.txt`）——Arm 版权
   禁止复制，永不入库（§3.1 出处注）。
3. **运行时 CPU 证据**（M1）：当前探针无 `sched_getcpu()`/运行时
   CPU 字段；如需"测量窗两端执行位置"字段（probe ABI 小改 + 契约
   测试 + 重新部署），另立小项评估，本任务不携带。
4. **路线 B（可控 VA 布局 / 页内 offset 变体）**：仅当 Q1 为
   `LAYOUT_OBSERVATION_LIMITED` 或受 footprint 混杂支配时立项
   （Explore 的 `kRandomTLBOffset` 族为参考实现）。
5. **perf/simpleperf 同窗差分**：外部交叉验证（CLI 窗 ≠ 探针内
   窗，需专门同窗机制），可选，不阻断。
6. **perf 二进制谱系**：设备上手工部署的静态 `perf` 未入 artifact
   manifest；使用前先 `sha256sum` 登记。
