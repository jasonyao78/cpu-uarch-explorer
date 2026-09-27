# SM8650 cache 证据重审

**日期**：2026-09-27

**对象**：Redmi K70 Pro / SM8650 上的 `ptr_chase` 结果与仓库当前结论

**裁定原则**：硬件基线、测量事实和机理假设分层；保留原始记录，不以新解释改写历史数据。

## 1. 总结

当前仓库关于“X4 L2=1 MiB”“SM8650 无独立 CPU L3”“12 MiB 是
L3/SLC 合并级或 CPU 有效容量”“X4/A520 具有约 12/8 MiB 静态保护份额”
以及“LLCC PMU 无可用事件”的结论，均超出了现有实验的证明能力。

外部硬件描述给出更强的平台基线：X4 私有 L2 为 2 MiB、A720 每核 L2
为 512 KiB、每对 A520 共享 512 KiB L2、八核共享 12 MiB CPU L3，另有
独立 Qualcomm LLCC/system cache。仓库已有 SM8650 run 仍是有效的原始
延迟观察，但统一降级为“方法学受混杂的历史观察”，不得进入容量校准链。

核心混杂是固定 `warmup=200000`：stride=64 B 时最多覆盖 12,800,000 B，
约 12.2 MiB。小于该范围的 ring 在测量前完整遍历，大于该范围的 ring
没有完整遍历，因此 12 MiB 左右的形状可能由实验协议自身产生。4 KiB 页的
TLB/page-walk 与未知 PFN/color 分布又会影响大工作集；随机逻辑链只抑制
预取，不保证物理 cache set/bank 均匀。

## 2. 证据裁定表

| claim | previous status | direct evidence | confounder/contradiction | new status | next discriminator |
|---|---|---|---|---|---|
| X4 L2 为 2 MiB | 仓库写成 1 MiB | Cortex-X4 TRM 与 SM8650 CPU cache properties patch | 当前 sweep 只在 512 KiB 与 1 MiB 两档之间看到变化，不能反推容量恰为 1 MiB | `PLATFORM_BASELINE` | X4 512 KiB–3 MiB 细扫 + L2 refill + DTLB，比较 4 KiB/实际 THP |
| A720 L2 512 KiB/核；A520 L2 512 KiB/双核共享 | 部分由曲线推断 | SM8650 CPU cache properties patch | 本仓尚未用 PMU 独立校验有效边界 | `PLATFORM_BASELINE` | 分核型细扫与 core PMU |
| 八核共享 CPU L3 12 MiB，另有 LLCC | 曾写成“无 per-cluster L3，末级=LLCC/SLC 单级” | SM8650 device tree 同时描述 CPU L3 与 LLCC；cache properties patch 给出 12 MiB L3 | 单核 latency 无法仅凭相近延迟分离两个外层结构 | `PLATFORM_BASELINE` | 修复协议后做 L3 dense sweep，联合 core/LLCC PMU |
| 12 MiB 曲线边界独立证明 cache 容量 | 曾定案或称较有把握 | X4 dense sweep 在 12 MiB 后逐渐变慢 | 固定 warmup 的覆盖量约 12.2 MiB，与目标边界同量级 | `REJECTED` | `warmup_passes` 等覆盖率重测 |
| X4 约 12 MiB、A520 约 8 MiB 是静态保护份额 | 曾写成干扰实验“实证” | 一次并发重流下若干点的延迟差异 | 非事务化；页映射、调度、温度和背景负载未形成配对分布；单一 latency 不能命名分配机制 | `HYPOTHESIS` | PMU 后的随机交错干扰实验，逐条件至少 20 次 |
| A520 32 MiB 慢路径来自互连/QoS 或 outstanding-miss 能力 | 曾给出 QoS 候选解释 | dense runs 中约 255/302/147 ns，说明现象不稳定 | `ptr_chase` 为 MLP=1，outstanding-miss 能力不是首要解释；内存侧 DVFS、页遍历和映射均未控制 | `OPEN` | 先完成 L2/L3 校准；记录 DTLB、LL-cache、DRAM/LLCC 事件 |
| 相机抢占 LLCC/SLC 份额 | 曾作为拟验证机理 | 一次亮屏/相机/灭屏手测给出相互矛盾数值 | 仓库无可接纳的“+51%”配对 run；相机 active client 未形成前后证据链 | `REJECTED` | A/B/A/B 或随机交错；前后解析 `Active Camera Clients`；双峰区每条件至少 20 次 |
| `llcc-pmu` 没有事件/不可用 | 曾由 `0x00..0x27` 全部 `ENOENT` 定案 | sysfs 注册 `llcc-pmu`，实测 type=9 | Qualcomm downstream driver 接受的事件编码是 `config=0x1000`，旧扫描未覆盖 | `OPEN` | 用户态 `perf_event_open(type=9, config=0x1000)` smoke test |
| `scaling_cur_freq` 证明负载实际频率固定 | 曾用于把 ns 确定换算为 cycles | 块前后 cpufreq 值稳定，L1 换算接近整数周期 | Linux CPUFreq 文档不保证该值等于测量区间真实硬件时钟；整数外观不是独立证明 | `REJECTED` | 保留 ns；cycles 标 `DERIVED`；用 PMU/AMU cycles 建立闭环 |
| 随机单环消除了物理布局/冲突影响 | 曾用于驳回物理页解释 | Fisher–Yates 让逻辑访问顺序均匀、难预取 | X4 L2 为 PIPT；4 KiB 页下 PFN/color、set/bank 映射仍可能改变冲突 | `REJECTED` | 多次新分配；权限允许时记录 `/proc/pagemap` PFN/color 摘要 |

## 3. 历史 run 的可用范围

下列已跟踪 run 保持原文件、hash 和 run-record 不变：

| run | 允许继续使用 | 禁止用途 |
|---|---|---|
| `20260927T060512Z-ptr-chase-cache-sweep` | root 前设备/Runner 冒烟、原始延迟观察 | cache 容量、层级命名、跨核型周期比较 |
| `20260927T075007Z-ptr-chase-cache-sweep` | governor 事务与频率快照链路、原始曲线 | X4 L2=1 MiB、L3/LLCC 容量或合并级定案 |
| `20260927T082635Z-ptr-chase-slc-dense` | dense sweep 执行成功、历史延迟分布 | 12 MiB 容量、A520/X4 保护份额或 QoS 机理 |
| `20260927T083827Z-ptr-chase-slc-dense` | thermal controller 事务闭环、历史延迟分布 | 同上；且不能由一次 run 排除双峰与内存侧 DVFS |

工作树中未跟踪的 `20260927T094438Z-ptr-chase-cache-sweep` 与
`20260927T094617Z-ptr-chase-slc-dense` 不属于本次版本化证据，既不修改，
也不据其数字作裁定。

## 4. 重新开放后的实验门禁

1. 修复完整 ring pass warmup，并把请求页策略与实际 backing 分开记录；
2. 建立可逆、可审计的 Android 受控安静态，而不是宣称“纯净态”；
3. 先校准已知 2 MiB 的 X4 私有 L2；校准失败则停止解释外层 cache；
4. 接入 core PMU，并验证 LLCC PMU `config=0x1000`；
5. 再做 8–16 MiB L3 dense sweep、跨核型和相机/干扰实验；
6. 多链/MLP 作为最后的独立物理量，不用于补救前序协议错误。

在第 1–3 步通过前不采集新的 SM8650 容量数据。

## 5. 主要依据

- [Arm Cortex-X4 Technical Reference Manual](https://documentation-service.arm.com/static/6473ef18bae17b773b05d1e8)
- [SM8650 CPU cache properties patch](https://patchew.org/linux/20260615-topic-sm8650-upstream-cpu-props-v3-0-eeb6e9fa7581@linaro.org/20260615-topic-sm8650-upstream-cpu-props-v3-2-eeb6e9fa7581@linaro.org/)
- [SM8650 device tree](https://android.googlesource.com/kernel/common/+/cf1ca1f66d301a55ab8e79188ddf347a8d011e35/arch/arm64/boot/dts/qcom/sm8650.dtsi)
- [Linux CPUFreq documentation](https://cdn.kernel.org/doc/html/latest/admin-guide/pm/cpufreq.html)
- [Qualcomm downstream LLCC PMU driver](https://android.googlesource.com/kernel/msm.git/+/90651f2c1e5de4d9359d216a41f94e6a24847404/drivers/perf/qcom_llcc_pmu.c)
- [SM8650 LLCC configuration](https://android.googlesource.com/kernel/common/+/14d0e1a09fe97a7524ff36baa695900cb0c10c23/drivers/soc/qcom/llcc-qcom.c)
