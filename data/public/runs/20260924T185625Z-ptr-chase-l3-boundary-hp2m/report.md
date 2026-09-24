# Cache/内存层次延迟报告 — ptr-chase-l3-boundary-hp2m

## 元信息（measurement-discipline §7 强制项）

| 项 | 值 |
|---|---|
| 目标 | xeon-8481c-01（sapphire-rapids-8481c，linux/x86_64） |
| 探针 | ptr_chase protocol=1.0 impl=portable |
| 探针谱系 | git `e8d4c85a0e` dirty=False sha256=55f68bc53eb767d6… |
| 测量日期 | 2026-09-24T18:56:34.891918+00:00 |
| 温度口径 | warm（显式预热 + 多趟 median，§1 主口径） |
| 页策略 | 默认 4K 页（未启用 hugepage；TLB 效应与 cache 效应在小步长区间耦合，见 probes/cache-mem/README 已知局限） |
| 重复次数 | 每 case 5 次，统计量 median（min/p25/p75/max 见 records.jsonl） |
| 证据等级 | MEASURED |
| 控制口径 | 按 environment.control 分组（Linux taskset 绑核到指定物理核（SMT sibling 空闲纪律见平台配置 notes）） |

## 延迟曲线

![latency curve](latency.svg)

## 数据表（median，ns）

| buffer | taskset=0 |
|---|---|
| 64MiB | 36.892 |
| 68MiB | 37.123 |
| 72MiB | 38.091 |
| 76MiB | 40.030 |
| 80MiB | 40.078 |
| 84MiB | 41.181 |
| 88MiB | 45.488 |
| 92MiB | 48.039 |
| 96MiB | 48.927 |
| 100MiB | 52.304 |
| 104MiB | 53.930 |
| 108MiB | 55.827 |
| 112MiB | 59.377 |
| 116MiB | 60.138 |
| 120MiB | 61.811 |
| 124MiB | 63.704 |
| 128MiB | 65.374 |

## 层级台阶（推断，阈值：相邻档位比值 >1.5×）

**taskset=0**
- 未检测到明显台阶

## 置信度：MEDIUM

- **噪声来源**：无锁频——实测 powersave governor、800MHz~3.8GHz 浮动（2026-09-25 接入时采集），ns 绝对值受 DVFS 污染，跨档比较需谨慎；4K 默认页（TLB 遍历与 LLC 行为耦合）；单控制组，sibling 隔离未主动执行（口径见平台配置 notes）。
- **提升计划（MEDIUM→HIGH）**：锁频复测（governor=performance 或固定 scaling_setspeed，需 root）；hugepage 对照组；cycles 口径（perf 需 sudo，paranoid=4）；evict 工具对照 warm/cold。

---
数据来源：data/public/runs/20260924T185625Z-ptr-chase-l3-boundary-hp2m/records.jsonl（raw 样本引用见各记录 raw_samples_ref）
