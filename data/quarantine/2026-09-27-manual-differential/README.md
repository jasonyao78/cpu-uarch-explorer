# 检疫归档：2026-09-27 手工差分实验两个 run（非证据，禁止校准使用）

> 本目录是 `data/quarantine/`（审计保留区，measurement-discipline 开篇
> 规则）的归档。内容**不是证据**：禁止晋升 candidate/baseline，禁止
> 进入校准链，禁止据其数字作任何容量/层级裁定。

## 归档对象

| run 目录 | 实验 | 记录数 | 谱系 |
|---|---|---|---|
| `20260927T094438Z-ptr-chase-cache-sweep/` | `ptr-chase-cache-sweep`（protocol 1.0） | 28（全 ok） | redmi-k70pro-01；probe 构建于 `06e7786` 且 `dirty: True`；artifact sha256 `058db618…` |
| `20260927T094617Z-ptr-chase-slc-dense/` | `ptr-chase-slc-dense`（protocol 1.0） | 20（全 ok） | 同上 |

## 为什么进检疫区（三条缺陷，与证据重审一致）

1. **固定 `warmup=200000`**：64 B stride 下只覆盖约 12.2 MiB，与旧
  "12 MiB 有效容量"结论同量级——
  `docs/reviews/2026-09-27-sm8650-cache-evidence-reassessment.md`
  点名的首要缺陷。
2. **无实际页 backing 审计**：protocol 1.0 记录无 observations、无
  PMU、无 `page_policy_actual`——请求与实态不可分。
3. **脏树构建 + 旧协议**：artifact 由 `dirty: True` 工作树产出，
  谱系等级不足以支撑校准。

## 正式排除裁定（原文照录，不修改）

`docs/reviews/2026-09-27-sm8650-cache-evidence-reassessment.md` §3：

> 工作树中未跟踪的 `20260927T094438Z-ptr-chase-cache-sweep` 与
> `20260927T094617Z-ptr-chase-slc-dense` 不属于本次版本化证据，
> 既不修改，也不据其数字作裁定。

同时段 changelog/open-items 背景：`06e7786`（2026-09-27 P0
zero-code results——no hugetlb pool，manual differential rejected）、
`79b0792`（OI-11：manual differential too noisy）。

## 处置说明（2026-09-28，经仓库所有者授权的单次操作）

- 两目录自 `data/public/runs/` **原样移入**本检疫区（含 `raw/`，
  SHA256 manifest 锚定保持有效）；证据文件一律不改写。
- 注意：两目录内 `run-manifest.json` 的 `records` 字段记录的仍是
  移动前的绝对路径（`data/public/runs/...`），已随移动失效，属已
  知且不改写的谱系事实。
- 同 morning 的四个同类缺陷 run（`060512Z/075007Z/082635Z/083827Z`）
  仍在 `data/public/runs/`（历史已跟踪状态），其可用范围与禁止用
  途以证据重审 §3 表格为准；本归档不改变它们的处置。
