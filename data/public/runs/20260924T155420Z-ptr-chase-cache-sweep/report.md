# Cache/内存层次延迟报告 — ptr-chase-cache-sweep

## 元信息（measurement-discipline §7 强制项）

| 项 | 值 |
|---|---|
| 目标 | macbook-m4pro-01（apple-m4-pro，darwin/aarch64） |
| 探针 | ptr_chase protocol=1.0 impl=portable |
| 探针谱系 | git `9a742a12d8` dirty=True sha256=1211e935a67e8cb2… |
| 测量日期 | 2026-09-24T15:54:20.363887+00:00 |
| 温度口径 | warm（显式预热 + 多趟 median，§1 主口径） |
| 页策略 | 默认 4K 页（未启用 hugepage；TLB 效应与 cache 效应在小步长区间耦合，见 probes/cache-mem/README 已知局限） |
| 重复次数 | 每 case 5 次，统计量 median（min/p25/p75/max 见 records.jsonl） |
| 证据等级 | MEASURED |
| 核型识别 | 按 environment.control 分组（macOS QoS 分流，OI-5 实测双峰；default≈P-core 档，background=E-core） |

## 延迟曲线

![latency curve](latency.svg)

## 数据表（median，ns）

| buffer | qos=background | qos=default |
|---|---|---|
| 32KiB | 2.270 | 0.773 |
| 64KiB | 2.710 | 0.790 |
| 128KiB | 8.310 | 0.785 |
| 256KiB | 8.984 | 6.786 |
| 512KiB | 11.112 | 6.977 |
| 1MiB | 12.098 | 7.075 |
| 2MiB | 27.314 | 7.163 |
| 4MiB | 81.557 | 9.062 |
| 8MiB | 143.491 | 12.953 |
| 16MiB | 163.573 | 52.770 |
| 32MiB | 182.148 | 89.874 |
| 64MiB | 185.563 | 106.559 |
| 128MiB | 186.685 | 117.747 |
| 256MiB | 177.988 | 122.645 |

### 双峰比值（qos=default / qos=background，随频率漂移，不作常量引用）

- 32KB：×0.34
- 64KB：×0.29
- 128KB：×0.09
- 256KB：×0.76
- 512KB：×0.63
- 1024KB：×0.58
- 2048KB：×0.26
- 4096KB：×0.11
- 8192KB：×0.09
- 16384KB：×0.32
- 32768KB：×0.49
- 65536KB：×0.57
- 131072KB：×0.63
- 262144KB：×0.69

## 层级台阶（推断，阈值：相邻档位比值 >1.5×）

**qos=background**
- 64KB→128KB：2.71→8.31 ns（×3.1）
- 1024KB→2048KB：12.10→27.31 ns（×2.3）
- 2048KB→4096KB：27.31→81.56 ns（×3.0）
- 4096KB→8192KB：81.56→143.49 ns（×1.8）

**qos=default**
- 128KB→256KB：0.79→6.79 ns（×8.6）
- 8192KB→16384KB：12.95→52.77 ns（×4.1）
- 16384KB→32768KB：52.77→89.87 ns（×1.7）

## 置信度：MEDIUM

- **噪声来源**：无锁频（DVFS 漂移，QoS 比值 2.6~3.9× 区间漂移即其表现）；QoS 分流是调度 hint 而非严格绑核，同 QoS 内可能迁移；页策略为 4K 默认页。
- **提升计划（MEDIUM→HIGH）**：测量期 powermetrics 并发采样核频入档；hugepage 对照组；重复次数提升至 7+ 并监控热漂移。

---
数据来源：data/public/runs/20260924T155420Z-ptr-chase-cache-sweep/records.jsonl（raw 样本引用见各记录 raw_samples_ref）
