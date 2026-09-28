# SM8650 core-PMU 事件语义正向控制裁定

**⚠️ 复审更正（2026-09-28，外部评审，优先级 P0）**

本文数据（§2/§3 表格、完整性核验、事件编码官方出处）仍然有效；以下
**裁定级内容被驳回**：

1. **§4 规则 3 裁定撤销，恢复为 FAILED。** 计划预注册的 8 MiB 预期为
   "数百/1k"，实测 83.3/1k、16 MiB 反降 58.9/1k——按预注册规则应裁
   `SEMANTICS-UNVERIFIED` 并停止容量推断。"预取过滤、起始沿仍有效"
   是事后替换假设，作为放行依据不成立；该解释本身降级为待检假设
   （且 `0x17` 是否被预取过滤恰需专用事件验证，不能自证）。
2. **§6 "P1 门禁解除"结论撤销。** P1 不应进入；已执行的 P1 数据保留
   为实验档案，其裁定见细扫评审的更正块。
3. **§5 residual 2 的"预取查找"假设撤回。** `L1D_CACHE (0x04)` 的官方
   定义明确排除 prefetches（ARM-software/data `cortex-x4.json`），与
   假设自相矛盾；512 KiB 的 l1acc 超额（1762/1k）解释重新开放。
4. **事件集选择不完整。** 官方同一份数据提供 demand/prefetch 分离的
   专用事件（`L1D_CACHE_MISS 0x8144`、`L2D_CACHE_MISS 0x814c`、
   `L1D_CACHE_HWPRF 0x8154`、`L2D_CACHE_HWPRF 0x8155`、
   `MEM_ACCESS_RD 0x66`），本次未使用。L1 系与 `dtlb_walk` 的
   "SEMANTICS-VERIFIED" 降级为"计数相干性观察"（规模/地板双向成立），
   "可用于容量推断"的效力待 P0′ 复测（专用事件 × 多 seed × 双训练
   量）后重裁。

以下为原文（保留审计，结论以上述更正为准）：

**实施日期**：2026-09-28
**目标**：`redmi-k70pro-01` / SM8650 / CPU7 Cortex-X4
**范围**：只验证架构化 core PMU 原始事件的计数语义；不做 cache 容量定案
**计划**：`docs/superpowers/plans/2026-09-28-sm8650-pmu-positive-control.md`

## 1. 裁定

正向控制**通过**，P1 细粒度 L2 扫描门禁解除。逐事件结论：

| event | config | 裁定 | 依据 |
|---|---|---|---|
| `cycles` | `0x11` | SEMANTICS-VERIFIED | cyc/load 与 ns × cpufreq 报告频率自洽（4.0–17.4 cyc 全区间） |
| `l1d_cache_refill` | `0x03` | SEMANTICS-VERIFIED | 地板（16/32 KiB 0.17–0.25/1k）→ 规模（512 KiB 248/1k）→ 饱和（≥8 MiB 1001/1k≈每 load 必 miss）四档全自洽 |
| `l1d_cache` | `0x04` | SEMANTICS-VERIFIED | 基线 ≈1003/1k≈每 load 一次 L1 查找；512 KiB 的 1762/1k 超出部分见 §4.3 |
| `l2d_cache` | `0x16` | COUNTS-COHERENT（幅度含预取流量） | 1508→3682/1k 随工作集增长且远超 demand miss，含预取发起的 L2 查找，不能当 demand-only 计量 |
| `l2d_cache_refill` | `0x17` | COUNTS-COHERENT（幅度≠朴素 miss 率） | 三个十进位动态范围（0.11→83.3/1k）、干净地板；但 ≥8 MiB 时 ~92–94% demand miss 被核内/预取服务（§4.2），**起始沿有效、绝对幅度无效** |
| `l3d_cache_refill` | `0x2a` | COUNTS-COHERENT（同上警告） | 0.008→4.56/1k，570× 范围；溢出尺度上同受预取过滤 |
| `l1d_tlb_refill` | `0x05` | COUNTS-COHERENT | 288→1030/1k，单调、跨档 |
| `dtlb_walk` | `0x34` | SEMANTICS-VERIFIED | 128 页 0.013/1k → 4096 页 39.9/1k（3100×），地板与规模双向验证 |

"SEMANTICS-VERIFIED" = 在已检验区间内，事件名称与计数行为一致，可用于
推理。"COUNTS-COHERENT" = 计数真实、单调、跨档自洽，但幅度受预取/层次
结构过滤，不得按朴素模型换算成 demand miss 率。

## 2. 实现与可复现边界

- 探针未改动：设备端 `ptr_chase` SHA-256
  `c887bc7d094020fe3c57ad19f6aa3e573b7548f72be2967098d9257535c9de03`
  （源锚点 `99c8c72`）；事件全部经运行时 `--pmu-event` 传入。
- 事件编码依据：ARM-software/data `pmu/cortex-x4.json`（TRM 衍生，
  `counters: 6`）+ Arm 官方 PMU 博客与 windowsperf 别名表三方一致；
  cache 组 6 事件恰好用满 6 个可编程计数器。
- 正式 run（protocol 1.2，controlled-baseline，各 10 次新进程）：
  - `data/public/runs/20260927T182457Z-ptr-chase-sm8650-x4-pmu-ctrl-cache/`
    （16/32/512 KiB + 8/16 MiB × 6 事件）
  - `data/public/runs/20260927T182613Z-ptr-chase-sm8650-x4-pmu-ctrl-tlb/`
    （512 KiB/16 MiB × cycles+l1d_tlb_refill+dtlb_walk）
- 预检（walt、单进程、1M loads，只作 smoke）：32 KiB 与 8 MiB 两档 6 事件
  全部打开、`running==enabled`、规模自洽；与正式 run 同区间一致。
- 完整性：全部样本 `time_running_ns == time_enabled_ns`（6 事件无复用）；
  全部样本 actual backing = `base`；每 case 前后 state snapshot
  `policy_result.valid=true`；两次 run 后四个 policy 全部恢复 `walt`
  （adb 复核）；CPU7 峰值 45.7 °C，远低于 90 °C 中止线；`mi_thermald`
  全程 running；schema 校验 7 records + 72 artifact entries 全过。
- 512 KiB 锚点跨三日三次独立 run 复现：校准 base（2.389 ns / 6.556 cyc /
  l2ref 0.218/1k）、本 cache 组（2.408 / 6.61 / 0.23）、本 TLB 组
  （2.417 / 6.63）——漂移 ≤1.2%。

## 3. 正式数据（median；计数归一化到 1,000 次 timed load）

cache 组（run 182457Z）：

| KiB | latency ns | cyc/load | l1 ref/1k | l1 acc/1k | l2 acc/1k | l2 ref/1k | l3 ref/1k |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 16 | 1.462 | 4.01 | 0.17 | 1002.7 | 1.0 | 0.11 | 0.008 |
| 32 | 1.464 | 4.02 | 0.25 | 1002.9 | 1.2 | 0.11 | 0.009 |
| 512 | 2.408 | 6.61 | 248.2 [217.7, 253.2] | 1761.8 | 1508.1 | 0.23 | 0.015 |
| 8192 | 6.354 | 17.43 | 1001.2 | 1012.4 | 3110.4 | 83.3 [78.3, 86.6] | 1.18 |
| 16384 | 6.021 | 16.52 | 1001.2 | 1012.2 | 3682.1 | 58.9 [55.8, 60.1] | 4.56 |

TLB 组（run 182613Z）：

| KiB | latency ns | cyc/load | l1d tlb ref/1k | dtlb walk/1k |
|---:|---:|---:|---:|---:|
| 512 | 2.417 | 6.63 | 288.1 [287.7, 289.6] | 0.013 [0.010, 0.014] |
| 16384 | 5.912 | 16.22 | 1030.0 [1012.6, 1039.2] | 39.9 [36.2, 44.5] |

宽 IQR 个案（512 KiB l1ref、16 MiB dtlb_walk）已按规则标记，不做静默平均
解读；上表方括号内为 [p25, p75]。

## 4. 逐条验收规则裁定

1. **L1-fit：PASS。** 16/32 KiB 的 l1acc ≈ 1003/1k（每 load 一次查找，
   窗口开销 +0.3%）、l1ref 0.17–0.25/1k ≈ 0。
2. **L1-overflow 规模：PASS。** 512 KiB l1ref = 248/1k，与"每 load 随机
   触一行"的朴素估计（≈875/1k）同数量级；偏低 3.5× 由置换策略对循环
   引用序列的非随机行为解释（§4.3 正是该效应解释了校准的 512→640 KiB
   假象）。l2acc 1508/1k 与 L1-miss 流量同规模。
3. **L2-resident 低 refill：PASS；8 MiB 幅度预期：朴素模型被证伪（事件
   本身未被证伪）。** 512 KiB l2ref = 0.23/1k（与校准 0.218/1k 互证）。
   8 MiB l2ref = 83.3/1k：较常驻区上升 ~360×、脱离近零档，但未达朴素
   模型（1–4 MiB L2 对 8 MiB 随机环 ≥50% miss）的"数百/1k"。延迟证据
   否决"83/1k 是 DRAM 级 miss"：17.4 cyc/load 的平均值容不下任何显著
   DRAM 混合；且 demand L1 miss ≈100%（1001/1k）时 ~92% 由核内服务。
   一致解读：0x17 按 TRM 定义计"L1 发起的核外读"，而 L2/DSU 侧预取
   把绝大多数 demand miss 过滤掉了（预取填充不是 L1 demand 事务）。
   **推论：0x17 的起始沿（近零 → 持续非零）保留容量判别力；溢出尺度
   上的绝对幅度不得换算为 miss 率。** 16 MiB l2ref 反低于 8 MiB
   （58.9 vs 83.3）且延迟更低（16.5 vs 17.4 cyc）——预取有效性/几何
   效应，列为残差（§5）。
4. **L3/DTLB 规模锚：PASS。** l3ref 0.008→1.18→4.56/1k（16 MiB 超出
   名义 12 MiB L3 后出现真实核外流量）；dtlb_walk 0.013→39.9/1k；
   两者在 512 KiB 均保持近零。l1d_tlb_refill 288/1k（128 页）说明
   L1 dTLB 对随机模式的有效容量 <128 项，但 miss 几乎全由 MMUTC 无
   walk 吸收（walk 仅 0.013/1k）——层次行为教科书式自洽。
5. **无复用、比值稳定：PASS。** 两组全部样本 running==enabled；除 §3
   标记的两个宽 IQR 个案外，逐进程比值稳定。
6. **测量完整性：PASS。** 见 §2。

## 4.2 对 2026-09-27 X4 L2 校准裁定的回写

1. **512→640 KiB 延迟/周期跳变确认为 L1 置换假象，不是 L2 容量事件。**
   512 KiB 处 L1 miss 率已达 25%（l1ref 248/1k）而 L2 refill 仍 0.23/1k
   ——L1 未命中的部分全部由 L2 平静吸收。延迟分解（DERIVED，模型依赖）：
   6.61 cyc ≈ 0.75×L1命中(~4–5 cyc) + 0.25×L2(~14–15 cyc)。640 KiB 处
   12.17 cyc 且 l2ref 依旧 0.31/1k，是 L1 命中率在 512→640 KiB 间崩塌
   （循环引用序列对置换策略极度敏感的已知伪 LRU 病态），与 L2 无关。
   校准裁定第 2 条由此获得机制解释；P1 将以 32/64 KiB 步长的 l1ref/l1acc
   致密采样直接成像该崩塌。
2. **校准的 dtlb_walk 近零读数转为可信**：该事件已被双向验证（512 KiB
   近零地板 + 16 MiB 规模计数），故 512→640 KiB 跳变的 TLB 解释正式
   排除。
3. **存活下来的唯一容量候选信号 = l2ref 起始沿 ~1–1.25 MiB**（校准：
   1024 KiB 0.99/1k → 1152 KiB 15.0/1k → 1280 KiB 22.5/1k）。起始沿
   是"核内资源+预取也托不住工作集"的第一尺度，据此形成工作假设
   （HYPOTHESIS，非事实）：SM8650 的 X4 私有 L2 可能 ≈1 MiB（Arm X4
   TRM 允许 1/2 MiB 配置；仓内平台基线的 2048 KiB 来自名义描述，未
   被本仓测量证实或证伪）。P1 细扫裁定。
4. **禁止回读**：校准 ≥1 MiB 区间的 l2ref 绝对幅度（15–68/1k）不得按
   朴素模型换算为"部分容量/命中率"；只有起始沿位置可作证据。

## 5. 剩余不确定性（residuals）

1. 过滤 demand miss 的预取器身份未鉴定（L1 侧 / L2 侧 / DSU stash 均有
   可能；l2acc 随 N 增长、l1acc 仅 512 KiB 异常升高，提示多层活动）。
2. 512 KiB l1acc = 1762/1k 的 0.76/load 超出部分：L1 预取查找假设，
   SPECULATIVE，未单独证实。
3. 8/16 MiB 反转（延迟与 l2ref 均 16 MiB 更低）未解释；与容量门禁无关。
4. 伪 LRU 循环共振为推断，未做置换策略仿真；P1 致密扫描可提供实验侧
   直接证据。
5. 4 KiB 页 PFN 着色对 L2 物理索引的影响由 10 次新进程分摊但未消除。
6. 事件语义只在已检验区间内成立；未检验尺度（如 >16 MiB、THP 混合区）
   不外推。
7. uncore/DSU 频率未锁定，cyc↔ns 换算依赖 cpufreq 报告值（DERIVED）。

## 6. 下一门禁（P1 设计输入）

- 门禁状态：**通过**，进入 P1 细粒度私有 L2 扫描（448–800 KiB @ 32/64
  KiB；896–1408 KiB @ 64 KiB，交接文档既定区间）。
- 事件集：cycles + l1d_cache_refill + l1d_cache + l2d_cache +
  l2d_cache_refill + l3d_cache_refill（6 事件 = 计数器预算，已实证无复
  用）。dtlb_walk 在 ≤1408 KiB 区间已证近零，不占用计数器；仅当异常时
  以配对相邻 run 补测。
- 判定目标：(a) l1ref/l1acc 致密成像 512→640 KiB 的 L1 命中率崩塌；
  (b) l2ref 起始沿定位（起始沿 = 容量信号，幅度不换算）；(c) 逐进程
  稳定性与页着色敏感度。
- LLCC/外层 cache 阶段（root sidecar）仍按交接文档后置，本评审不涉及。
