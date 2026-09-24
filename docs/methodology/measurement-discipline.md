# 测量方法学纪律（measurement discipline）

> 来源与地位：迁移自 arm64-uarch-probe（作者 Michael Yao；根 LICENSE 为 BSD-3-Clause、包元数据仍标 Proprietary，统一前仅借鉴方法不复制代码）并经本仓裁剪（OI-9；2026-09-24 外部评审纠偏）。
> 所有探针开发、实验执行、报告撰写必须遵守。**违反本纪律的数据可落入 `data/quarantine/`（保留审计线索），但禁止晋升为 candidate/baseline，禁止进入校准链。**

## 1. 温度语义（cache/memory 测量强制）

| 模式 | 定义 | 适用 |
|---|---|---|
| warm | 显式预热 + 多趟 + median，稳态驻留延迟 | 层级延迟基准（主口径） |
| cold-dbl-evict | 先驱逐（evict 工具）再测 | 准确名称是 eviction-conditioned first traversal：驱逐动作本身不证明目标数据已离开系统级缓存，"真 cold" 须由工作集曲线 / 对照组 / PMU 佐证 |
| cold-warm0 | 不预热但**不等于 cold** | 禁止误标；使用必须打 `[COLD-L3residue]` 类标签 |

- 驱逐指令按 ISA 分别表述，不跨 ISA 合并：ARM `DC CIVAC` 清到一致性点（PoC，DSU 上通常即 L3/SLC 边界），**不保证清出 SLC**；x86 `clflush`/`clflushopt` 语义不同源。任何驱逐声称必须标注所用指令与可达边界。
- 铁律：**禁止跨温度模式合并数据**；每个数字必须能回答"warm 还是 cold、什么页策略、median 几次"。

## 2. 页策略与 TLB 纪律

- **Linux 目标**：正式测量用 hugepage（`MAP_HUGETLB`）**减少并重塑** TLB/page-walk 开销（不是"消除 TLB 噪声"）；页大小按平台 capability 记录（如 GB10 为 2MiB——平台配置，非 Linux 通用常量）；分配向上对齐；池不足时 fallback 必须显式标注实际页策略（requested/actual 双记录），strict 模式直接失败。4K 页数据只作对照，并标注预期 TLB 开销量级。
- **macOS**：无 hugepage/clflush 对应能力——capability manifest 标注 `unsupported`，证据等级按 ADR-0005/0006 降级路径处理，不得硬测硬报。

## 3. 重复与统计

- 稳态测量 ≥5 次取 median（GB10 用 median-of-7）；cold 单趟噪声大，**单次值禁止入库**。median-of-N 只是默认采样策略，不构成置信度证明——还需样本独立性、热漂移监控、异常值处理与终止条件（分级见 §4）。
- run-record 必须带 `repetitions`、median、分位数；原始样本按 `artifact-manifest` 引用（schema v2）。
- 探针保持单次测量纯粹性；重复/取中位/错误归 runner 层职责。

## 4. 置信度分级

- `HIGH / MEDIUM / LOW / UNKNOWN` 四档；每档注明**噪声来源**与**提升计划**（MEDIUM→HIGH 的具体补测项）。
- 与 `evidence.provenance` 配合：置信度评价测量过程，证据等级标注数据来源，两者不互相替代。

## 5. 频率感知

- ns 与 cycles 成对记录；跨核型/跨平台比较禁止只比 ns。
- cycles 必须区分来源：PMU/硬件计数器实测 cycles 与由频率换算的 derived cycles 分开标注，后者证据等级按 DERIVED 处理。
- 环境快照必须含核频（Linux `scaling_cur_freq` / macOS powermetrics 采样），但快照不代表测量区间的精确频率，禁止据此把 derived cycles 当作实测值。

## 6. 数据修正留痕

- **禁止静默改数**：旧值 → 新值 → 原因必须写入 revision history（参考 SUPERSEDED_PARTIAL 模式）。
- 修正后旧数据保持可溯（git 历史 + revision 表）。

## 7. 报告模板（每个测量数字必须携带）

温度模式 / 页策略 / 重复次数与统计量 / 置信度 / 核型与频率 / 证据等级 / 测量日期。
