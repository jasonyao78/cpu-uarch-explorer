# Cache/内存层次延迟报告 — ptr-chase-cache-sweep

## 元信息（measurement-discipline §7 强制项）

| 项 | 值 |
|---|---|
| 目标 | xeon-8481c-01（sapphire-rapids-8481c，linux/x86_64） |
| 探针 | ptr_chase protocol=1.0 impl=portable |
| 探针谱系 | git `6847e895aa` dirty=False sha256=55f68bc53eb767d6… |
| 测量日期 | 2026-09-26T14:55:37.655501+00:00 |
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
| 32KiB | 1.321 |
| 64KiB | 4.216 |
| 128KiB | 4.223 |
| 256KiB | 4.227 |
| 512KiB | 4.695 |
| 1MiB | 5.389 |
| 2MiB | 15.372 |
| 4MiB | 37.435 |
| 8MiB | 38.474 |
| 16MiB | 40.349 |
| 32MiB | 41.625 |
| 64MiB | 44.394 |
| 128MiB | 70.038 |
| 256MiB | 100.941 |

## 层级台阶（推断，阈值：相邻档位比值 >1.5×）

**taskset=0**
- 32KB→64KB：1.32→4.22 ns（×3.2）
- 1024KB→2048KB：5.39→15.37 ns（×2.9）
- 2048KB→4096KB：15.37→37.44 ns（×2.4）
- 65536KB→131072KB：44.39→70.04 ns（×1.6）

## 置信度：MEDIUM

- **噪声来源**：无锁频——实测 powersave governor、800MHz~3.8GHz 浮动（2026-09-25 接入时采集），ns 绝对值受 DVFS 污染，跨档比较需谨慎；4K 默认页（TLB 遍历与 LLC 行为耦合）；单控制组，sibling 隔离未主动执行（口径见平台配置 notes）。
- **提升计划（MEDIUM→HIGH）**：锁频复测（governor=performance 或固定 scaling_setspeed，需 root）；hugepage 对照组；cycles 口径（perf 需 sudo，paranoid=4）；evict 工具对照 warm/cold。

---
数据来源：data/public/runs/20260926T145530Z-ptr-chase-cache-sweep/records.jsonl（raw 样本引用见各记录 raw_samples_ref）
