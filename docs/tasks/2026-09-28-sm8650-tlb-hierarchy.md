# 任务书：SM8650 Cortex-X4 TLB 层级探测（2026-09-28）

> **版本**：v1（依据第二版评审大纲落地）。
> **前置阅读**：仓库根 `AGENTS.md`（铁律 0–7）、
> `docs/methodology/measurement-discipline.md`、
> `docs/reviews/2026-09-28-sm8650-x4-p0prime.md`（P0″ 裁定与残差）、
> `docs/runbooks/redmi-manet-freq-control-chain.md`（频率控制链排障）。
> **本任务与"科学问题未解"解耦**：容量类结论达不到证据门槛时，按
> 预注册终态（OPEN/限定结论）如实结案，不为得到数值而追加实验。

## 1. 任务契约与有限终点

### 1.1 任务对象

- 设备：`redmi-k70pro-01`（SM8650，HyperOS 2.0.208，
  kernel 6.1.118-android14-11-ga3b9c44908dd-ab13320413，KernelSU root）。
- 固定核：**CPU7 / Cortex-X4**（midr `0x410fd821`，toybox `taskset 80`）。
- 探针：现有 `ptr_chase`（`stride=64 B` 随机依赖单环、同链展开 ×8、
  warmup 默认 2 完整环、PMU 同窗计数、backing 双端点审计、`-S` 记录
  种子）。artifact 以 run manifest 的 SHA-256 锚定，源码锚点随记录。
- 主实验映射：**4 KiB base（`-B`）**；`-B`/`-T` 实际 backing cohort
  仅用于 Q4。
- 分支：`codex/sm8650-tlb-hierarchy`（worktree
  `.worktrees/sm8650-tlb-hierarchy`）。

### 1.2 四个科学问题

- **Q1**：`0x05`（`l1d_tlb_refill`）事件密度的**第一稳定转折区间**，
  及其对访问顺序 seed、进程布局观测、训练量的稳健性 → 报告协议限定
  的 **L1 translation effective reach**。
- **Q2**：`0x34`（`dtlb_walk`）的 **walk-onset 区间**（从近零地板进
  入稳定上升的位置）；仅当 L2 相关新事件正控通过且事件定义允许联合
  解释时，才进一步估计 **L2 TLB（MMUTC）有效触达范围**，否则终态
  `WALK_ONSET_ONLY`。
- **Q3**：translation/walk activity 的**暴露成本是否可识别**——先验
  证候选事件资格与模型可识别性，再决定是否给出成本估计；失败则只发
  布事件密度与 cycles/load 联合曲线。
- **Q4**：mixed-THP 降延迟观察（校准 run）是否具有**一致的
  translation 事件证据链**——进程级实际 backing cohort 对照；不估算
  TLB 对总收益的精确贡献比例。

### 1.3 非目标

- 不反推 cache/LLCC 容量（X4 私有 L2 保持 OPEN/INCONCLUSIVE，
  OI-11；本任务不触碰）。
- 不反推 TLB 物理 entry 数、sets/ways、replacement 策略。
- 不把 `cycles/walk` 命名为实测 page-walk 硬件延迟。
- 不把 `0x05/loads`、`0x34/loads` 改写为"miss 概率"（见 §3.2：
  event density 可 >1000/1k，不静默截断）。
- 不做 mixed cohort 内逐槽位 THP 归属推断。
- 不把 `l1d_tlb_refill` 与 `dtlb_walk` 逐项相减当作 L2 TLB hit rate。
- 不把 mixed-THP 同步变化按比例分摊为 TLB 收益占比。
- 不扩展 v0.4、LLCC、PFN 着色、多链、RISC-V 等工作（各有归属）。

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

| 证据 | 状态 | 用途 | 不允许推导 |
|---|---|---|---|
| 128/4096 页 `0x05/0x34` 正控（run `20260927T182613Z`） | VERIFIED | 事件方向性锚点 | knee 位置、L1 容量 <128 |
| P0″ 6300 条 PMU 观测 0 复用违约、0 编码异常 | VERIFIED | 复用探针内计数链 | 新事件必然有效 |
| `0x05` 128 页 288.08/1k、4096 页 1029.95/1k | VERIFIED | Q1 先导观察 | L1 entry 数 |
| `0x34` 128 页 0.0129/1k、4096 页 39.90/1k | VERIFIED | Q2 先导观察 | walk 次数/步数 |
| perf/simpleperf 与探针内计数同窗差分 | 未执行（OPEN） | 可选外部交叉验证 | 阻断本任务（CLI 计数窗 ≠ 探针内计数窗，非同窗） |
| `0x2d/0x2f/0x8136/0x8128/0x8138/0x813a/0x813c/0x813e/0x8167` | 未实操 | Q2/Q3/Q4 候选 | 未正控先用于结论 |
| THP backing 双端点审计 + 实际 backing 分组 | VERIFIED | Q4 进程级 cohort | 窗内逐时刻状态恒定、逐槽位归属 |
| 跨三日 512/1280 KiB 锚点复现 ≤1.2% | VERIFIED（经验观测） | 锚点判据的参考 | 所有事件的统一硬阈值（近零地板处相对误差无意义，见 §6.2） |
| ceiling drift 三次复发均 fail-closed | VERIFIED-NEGATIVE | 执行纪律 | 根因已知（OPEN） |

## 3. 术语、事件表与结论权限

### 3.1 事件定义表

出处：ARM-software/data `pmu/cortex-x4.json`（Cortex-X4 TRM 衍生，
armv9.2-a，PMUv3，counters=6）；通用架构编码与 Arm 官方 PMU 博客、
windowsperf 别名表三方一致。正式定稿前钉住源 URL 与访问日期；设备
内核 PMU = `armv8_pmuv3`（type 8）。

| code | 事件 | 语义（官方描述摘要） | 正控状态 | 可支持的最强结论 |
|---|---|---|---|---|
| `0x05` | `L1D_TLB_REFILL` | L1 data TLB 自 L2 TLB（MMUTC）的 refill，含翻译错误路径 | ✅ VERIFIED | refill-like event density |
| `0x34` | `DTLB_WALK` | 导致 ≥1 次页表 walk 的 data TLB 访问（= 导致 `L2D_TLB_REFILL` 的访问） | ✅ VERIFIED | walk-like event density |
| `0x25` | `L1D_TLB` | 每次 load/store 的 L1 dTLB 查找 | 未实操 | （备选分母） |
| `0x2d` | `L2D_TLB_REFILL` | L2（统一）TLB refill（含指令侧贡献） | 未实操 | L2 refill-like（须正控） |
| `0x2f` | `L2D_TLB` | L2 TLB 访问（由 L1 refill 引起） | 未实操 | L2 access-like（须正控） |
| `0x8136` | `DTLB_STEP` | 数据页表 walk 的 step（步数） | 未实操 | 步数比（须与 `0x34` 口径配对验证） |
| `0x8128` | `DTLB_WALK_PERCYC` | 每周期在途 data walk 数（积分语义，非"walk 花多少周期"） | 未实操 | walker 活动量（须正控方向性） |
| `0x8138` | `DTLB_WALK_LARGE` | 大页 data walk | 未实操 | Q4 大页证据（须正控） |
| `0x813a` | `DTLB_WALK_SMALL` | 小页 data walk | 未实操 | Q4 小页证据（须正控） |
| `0x813c` | `DTLB_WALK_RW` | demand 访问导致的 walk | 未实操 | demand walk（升级候选） |
| `0x813e` | `DTLB_WALK_PRFM` | preload/prefetch 导致的 walk | 未实操 | prefetch walk（升级候选） |
| `0x8167` | `STALL_BACKEND_TLB` | 后端 TLB stall 周期 | 未实操 | translation 受阻（升级候选） |

**MMUTC ≡ L2 TLB**：`0x05` 描述写 "from the L2 TLB"，`0x02` 描述写
"from the MMU Translation Cache (MMUTC)"——同物两名，本文统一写
**L2 TLB（MMUTC）**。名称可引用（目标核事件文档）；其物理容量/组织
不在本任务授权范围。

### 3.2 统一分母与密度定义

所有率默认：

```
R_e = 1000 × C_e / N_timed_dependent_loads
```

`R_0x05` = refill-like event density；`R_0x34` = walk-like event
density。**`0x05` 在 4096 页达 1029.95/1k（>1000/1k）**：说明该事件
每次逻辑 load 可计超过一次，不得改写为"miss 概率"或截断到 100%；
>1000/1k 的情形进入事件 sanity 解释项。

### 3.3 结论权限（逐级需证）

```text
观测事件变化（单 case）
→ 跨重复/seed/块稳定（协议级事实）
→ 显示 translation-related 转折（Q1/Q2 范围）
→ 在新事件正控支持下讨论 L2 TLB（MMUTC）有效触达（Q2 上限）
→ walk activity 暴露成本的模型估计（Q3 上限，须可识别性检查）
```

物理 entry 数、sets/ways、`cycles/walk` 硬件延迟不在授权范围。

## 4. Gate 0：现有计数与执行契约复验（非重做基础设施）

正式采集前确认以下契约未退化（逐项有机器证据）：

1. 探针 artifact SHA-256 与 run manifest 一致、源码锚点在史；
2. `taskset 80` 实际运行于 CPU7（raw 样本含命令行）；
3. 每事件 `time_running == time_enabled`（零复用）；
4. 事件 type/config 与 §3.1 表一致；
5. timed loads / warmup loads / ring passes 自洽（ring_passes 由
   `loads / slots` 自证）；
6. backing 双端点审计通过（或样本按契约 fail 入档）；
7. read-before-disable 计数路径未被改动；
8. controlled-baseline 环境事务有效且事后恢复 `walt`。

**阻断条件**：探针内事件恒零、编码倒挂、契约字段缺失或
`read-before-disable` 被破坏 → 停止正式结构推断，转入计数链调查。
外部 perf/simpleperf 对照为**可选交叉验证**，不是默认阻断项。

## 5. Gate 1：新增事件正控（按需求顺序，逐项过/降级）

顺序：① `0x2d/0x2f`（Q2 层级辨识）→ ② `0x8136/0x8128`（Q3）→
③ `0x8138/0x813a`（Q4）→ ④ `0x813c/0x813e/0x8167`（仅主问题需
要时升级，不默认纳入）。

每项正控内容：

- **floor/scale 锚点**：128 页（`0x05` 显著、`0x34` 近零）与 4096
  页（`0x34` 显著）两点方向性；
- 适用时做 base/mixed/thp 实际 backing 对照（`0x8138/0x813a` 必
  须）；
- 10 个新进程重复 + 短块；
- 编码（type/config）与 `running == enabled` 校验；
- **通过判据**：方向与预期一致、跨进程稳定、无恒零；
- **失败处置**：该事件 `SEMANTICS_UNVERIFIED`，对应结论降级（如 Q3
  只发联合曲线），原始数据不改写；
- **有限终点**：不为找到期望曲线而连续尝试新 raw event。

事件组（候选，最终仍以 `running == enabled` 为准；不同组是不同
run，**未验证锚点一致性前不得跨组逐项相减**）：

| 组 | 目标 | 事件 |
|---|---|---|
| G0 主曲线 | Q1/Q2 基础 | cycles, mem_access_rd, `0x05`, `0x34` |
| G1 层级辨识 | Q2 增强 | G0 + 正控后的 `0x2d/0x2f`（合计 ≤6） |
| G2 成本/页尺寸 | Q3/Q4 | cycles, `0x05`, `0x34` + 正控后的 `0x8136/0x8128` 或 `0x8138/0x813a`（合计 ≤6） |

**PMU 窗与墙钟窗边界**（现有协议）：`perf start → t0 → chase → t1 →
read → disable`——PMU 覆盖 t0 前/t1 后的少量探针代码。
read-before-disable 是下游驱动约束，**不改动**；改为做固定开销
sanity：按 `-n` 扫至少 3 个测量长度，拟合"固定截距 + 每 load 斜
率"，检验 event density 随测量长度是否稳定；若截距显著则在报告中
标注，不暗改窗口。

## 6. 实验协议与预注册判定

### 6.1 固定探针协议（照实现写，不虚构）

- 分配：guarded mmap（Linux）→ madvise（`-B`/`-T`）→ 建链触页（无
  独立 prefault）→ warmup 2 整环（精确 loads 入档）→ 端点审计 1 →
  PMU start → t0 → ×8 chase → t1 → read/disable → 端点审计 2 →
  输出（含 before/after/endpoints_equal/seed/PMU 组）。
- 每 case：**10 个全新进程**（重复单位是进程；record 必带
  repetitions、median、分位数）。
- 布局变量：现有 `-S` 只控制访问顺序（**order_seed**）。本任务采用
  **路线 A**：4 个 order_seed + 10 个新进程布局观测（记录每进程
  VMA base），**不声称正交 layout_seed 实验**；若 Q1 对进程布局显著
  敏感，记 `LAYOUT_OBSERVATION_LIMITED` 并转 OI（路线 B 后置立
  项）。

### 6.2 预注册 knee 方法（看正式矩阵前写定）

- 粗扫如何提名候选区（R_0x05/R_0x34 的相邻点比值 + cycles/load 联
  合）；
- 致密点如何生成（候选区 ± 相邻档内插）；
- 最小效应大小（密度与 cycles/load 双指标）；
- 稳定条件：≥3 个 order_seed 同区间、两种训练量同制度、无块内锚
  点失真；
- 容差：分**绝对地板阈值**（近零计数处，如 <0.5/1k 的绝对差）与
  **规模段相对容差**（上量处参考 ≤1.2% 经验锚点，不机械套用）；
- 边界点 → `LOWER_BOUND_ONLY`；多拐点 → 分别报告；无拐点 →
  `OPEN`；
- **禁止**看图后改阈值或删 seed。

### 6.3 统计与数据分层

- 稳态重复 ≥5 次取 median（本任务沿用 10 进程）；单次值禁止入库；
- 报 median [p25, p75]、各 seed 曲线、rejected 数；
- 失败记录空 metrics + 结构化 failure；纪律违例进
  `data/quarantine/`；锚点失真 → 块 fail-closed；
- raw 本地保留 + SHA256 manifest；records/artifacts/manifest 入库。

## 7. 分阶段矩阵与执行预算

### Phase A：base 粗扫（提名候选区）

- 页数：32..8192 页预注册档位（约 12 档；对应 buffer 128 KiB..32
  MiB，stride 64B）；
- 2 个 order_seed × 1 个训练量（短训练，loads_per_slot=8）×
  base（`-B`）× G0 事件组；
- 短块 + 块前后 base 锚点（512 KiB/3072 KiB）+ Current HAL 温度与
  cdev `cur_state` 采集；
- 产出：Q1/Q2 候选区；不产出结论。

### Phase B：候选区致密扫描（判定）

- 候选区 ± 相邻档致密点；
- 4 个 order_seed × 短/长两训练量（8 与 512 ring passes；
  min_loads 地板不生效）；
- G0/G1（若 `0x2d/0x2f` 正控通过）；
- 产出：Q1 `INTERVAL_IDENTIFIED | LOWER_BOUND_ONLY | ORDER_SENSITIVE
  | LAYOUT_OBSERVATION_LIMITED | TRAINING_SENSITIVE | OPEN`；Q2
  `WALK_ONSET_ONLY | … | OPEN`。

### Phase C：Q3 成本判定

- 在 walk-floor / onset / active 三类区域选点；
- G2（若 `0x8136/0x8128` 正控通过）；
- 先做可识别性检查（walk 与 data miss 共线程度、事件口径配对性）；
- 通过 → 报告"暴露成本"模型系数（标 DERIVED 与竞争解释）；失败
  → `MODEL_UNIDENTIFIABLE`，只发联合曲线。

### Phase D：Q4 THP cohort 对照

- 代表 buffer 点（第一转折前 / 转折附近 / walk-active 区，≤3 点）；
- `-B` vs `-T`，各 4 order_seed × 短训练 × G0（+`0x8138/0x813a` 若
  正控通过）；
- 按实际 backing 分 base/mixed/thp cohort 独立报告；mixed 不并入
  thp；
- **必报转化表**：请求次数 → 实际 backing 构成 → 端点 drift 失败
  数 → 进入分析样本数（选择偏差披露）；
- 判读：latency 下降与 R_0x05/R_0x34 下降是否同向同规模 →
  translation 证据链一致/不一致；不估算收益占比。

### 执行预算（先测后写死）

- 经验单 case ≈ 4.5 s（含 10 reps 与 runner 开销；实测：56 case ≈
  202 s）；
- 粗估：A ≈ 12 档 × 2 seed ≈ 24 case（≈2 min）+ 锚点/门禁；B ≈
  8–16 case × 2 训练 ≈ 16–32 case；D ≈ 3 点 × 2 策略 × 4 seed = 24
  case；
- 另计：Gate 1 正控（~10–20 case）、锚点、THP cohort 达成率（混合
  率历史 10–50%）、结构性失败重试、块间冷却；
- **纯执行时间不写成战役总耗时**；正式预算在 Phase A 完成后按实
  测修订。

## 8. 漂移、设备状态与重启

- 默认 Android baseline：**不关闭** thermal/perf 服务、不杀后台、不
  drop caches、不 force-idle、不改飞行模式（§6 测量纪律；"受控安静
  态"≠"纯净态"）；
- host mutation 一律 durable journal + 逆序恢复（runner 环境事务）；
- 硬门禁：screen off / Dozing / camera idle / mi_thermald running /
  thermal status=0 / `max_cpu_temp_c=90.0`；
- drift 打法：短块 + 块前后锚点 + `scaling_max_freq` 画像值
  （2265600/2707200/2707200/2745600）+ Current HAL 温度（cached 禁
  用）；
- 重启四触发（基线污染/系统变更/长间隔首矩阵/绝不例行）；开机序
  列：boot_completed → 拔充或记录 → 静置 10–15 min → quiet-state
  门禁 → 5–10 min 限额稳定性观察 → 低成本锚点 → 开跑。

## 9. 实现与 TDD

### 9.1 配置（`configs/experiments/`，阶段化多文件，防叉积膨胀）

- `ptr-chase-sm8650-x4-tlb-ctrl.json`（Gate 1 正控）；
- `ptr-chase-sm8650-x4-tlb-coarse.json`（Phase A）；
- `ptr-chase-sm8650-x4-tlb-dense.json`（Phase B，候选区确定后再生
  成）；
- `ptr-chase-sm8650-x4-tlb-thp.json`（Phase D）；
- 全部 protocol 1.2、`execution.controls: ["x4-prime"]`、
  `runner/tests/test_plan.py` protocol/case-count 守卫同步登记。

### 9.2 分析器（`analysis/sm8650_tlb.py` + 测试）

复用 `sm8650_x4_p0prime.py` 的契约（schema v2 observations、编码/
running/seed/sample_index/backing 校验、全失败 run 进 rejected、双
峰标记），新增：

- event density（R_0x05/R_0x34，>1000/1k 不截断）；
- 第一转折与 walk-onset 判定（§6.2 预注册规则的实现）；
- 块前后锚点一致性判定与块 fail 标记；
- 事件资格状态（§3.1 表驱动）；
- Q3 可识别性检查输出；
- THP cohort 转化表（请求→实际→失败→有效）。

### 9.3 测试（`analysis/tests/test_sm8650_tlb.py` 等）

至少覆盖：①正控点不被误报为 knee；②`0x05`>1000/1k 不截断不改成
概率；③未正控事件不得进入 Q3/Q4 结论；④mixed 不并入 thp；⑤端点
变化样本无数值 metrics；⑥running≠enabled 拒绝；⑦锚点失败整块失
效；⑧无膝点/双膝点/边界点；⑨order 敏感与训练敏感；⑩模型不可识
别时不输出成本值；⑪全失败 run 仍出 rejected；⑫改判据/改历史数
据必须留 revision history。

## 10. 报告纪律、终态与分支退役

### 10.1 报告分栏

- **直接实测**：ns/load、PMU cycles/load、event density（/1k
  loads）；
- **派生量**（标 DERIVED）：差值、比例、模型系数；
- **微架构解释**：支持什么、哪些竞争解释未排除。

### 10.2 终态（每 Q 独立，不要求全有数值答案）

```text
INTERVAL_IDENTIFIED / WALK_ONSET_ONLY / LOWER_BOUND_ONLY /
ORDER_SENSITIVE / LAYOUT_OBSERVATION_LIMITED / TRAINING_SENSITIVE /
SEMANTICS_UNVERIFIED / BACKING_UNCONFIRMED / MODEL_UNIDENTIFIABLE / OPEN
```

### 10.3 分支退役

严格按铁律 7：预注册任务完成或正式判定不可完成 → 未竟项转
`docs/open-items.md` → 正式评审 → FF 集成 main → main 全量复验
（CTest/单测/schema/哈希）→ 推送 origin → worktree 回收与分支删
除分别满足各自条件。OPEN 不阻碍退役。
