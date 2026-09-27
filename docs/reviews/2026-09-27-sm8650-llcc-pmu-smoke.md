# SM8650 LLCC PMU userspace smoke 裁定

**实施日期**：2026-09-28
**目标**：`redmi-k70pro-01` / SM8650 / CPU7 Cortex-X4
**范围**：只读 `perf_event_open` 能力与响应性；不做 cache 容量定案

## 1. 裁定

`llcc-pmu` 的 `type=9/config=0x1000` **可由 root userspace 打开、调度和
读取，并对 CPU7 上的 streaming-read 产生稳定、可重复、远高于 idle floor
的计数响应**。旧的“扫描 `0x00..0x27` 均 `ENOENT`，所以 LLCC PMU 没有
事件”结论不成立；`0x27` 在同一工具中仍作为负控返回 `ENOENT`。

本次只把状态从 `OPEN` 提升为“event responsive”。它不证明该计数器在本机
精确等于某一 slice 的 read miss，不证明 CPU 独占份额、occupancy 或 LLCC
容量，也不替代 core PMU 与同一次 `ptr_chase` case 的同步采样。

## 2. 实现与可复现边界

- source commit：`d31ba55`；
- AArch64 static artifact SHA-256：
  `ca0a64df4412023a9a20d30f8606e8b8a0f7571649ac46f1e138f47d00cf3377`；
- 工具：`probes/platform/linux/pmu_counter_smoke.cpp`；
- kernel：`6.1.118-android14-11-ga3b9c44908dd-ab13320413`；
- PMU sysfs：`armv8_pmuv3/type=8`，`llcc-pmu/type=9`；LLCC 节点没有
  `format/`、`events/` 或 `cpumask`；
- 安全上下文：正式 10 对 smoke 经 KernelSU `su -c`，
  `uid=0 context=u:r:ksu:s0`；普通 adb shell 与 LLCC 的细分权限验证见 §5；
- CPU/control：`taskset 80` + 工具内 `sched_setaffinity(cpu7)`；governor
  保持 `walt`，没有为 capability smoke 做 host mutation；
- 工作负载：每个条件独立新进程，64 MiB buffer 在计数前分配并逐 cache line
  预触页；计数窗口 100 ms；stream 每 64 B 读取 8 B；10 对条件按
  idle→load / load→idle 交替；
- 环境 pre/post：screen off + Dozing、camera active clients `[]`、
  `mi_thermald=running`、force-idle=false；最高 CPU 温度 38.0→39.2°C；
  cpufreq max caps 未漂移。

工具先在 enable 后立即读取 baseline，再执行 workload，在 disable **之前**
读取 final，报告 `final-baseline`。读序不是风格选择：Qualcomm 下游驱动仅在
私有 hw state 未标记 stopped 时把累计值写回 `event->count`。最初提交
`4281cb3` 采用常规 disable→read，在该驱动上复现同一 event 内 delta=0；
`d31ba55` 改为 read→disable 后，core PMU 与 LLCC PMU 均闭环。驱动维护累计
总数，因此工具从不假设 `PERF_EVENT_IOC_RESET` 会把驱动私有累计值清零。

依据：

- [Qualcomm downstream qcom_llcc_pmu.c](https://android.googlesource.com/kernel/msm.git/+/90651f2c1e5de4d9359d216a41f94e6a24847404/drivers/perf/qcom_llcc_pmu.c)
  定义 `LLCC_RD_EV=0x1000`、per-CPU monitor 和累计读取逻辑；
- [Linux perf_event_open(2)](https://man7.org/linux/man-pages/man2/perf_event_open.2.html)
  定义 per-CPU `pid=-1,cpu>=0`、counting read format、ioctl 和 errno 语义。

## 3. 正控与负控

同一最终 artifact 的 core PMU 正控：

```text
pmu=armv8_pmuv3 type=8 config=0x11 scope=thread cpu=7
count_delta=274530422 time_enabled_ns=100128854
time_running_ns=100128854 bytes_read=520093696
```

LLCC 负控：`type=9/config=0x27` 在 `perf_event_open` 返回
`errno=2 (ENOENT)`、exit 2。它证明工具没有把任意 config 伪装成成功。

## 4. 十对交替样本

所有样本 `time_running_ns == time_enabled_ns > 0`，未见 multiplex。表内是
工具已经扣除各进程 immediate baseline 后的 `count_delta`：

| pair | order | idle | stream-read |
|---:|---|---:|---:|
| 1 | idle→load | 8,648 | 53,982,224 |
| 2 | load→idle | 10,768 | 53,963,936 |
| 3 | idle→load | 11,120 | 53,995,728 |
| 4 | load→idle | 10,952 | 54,149,680 |
| 5 | idle→load | 8,240 | 53,975,848 |
| 6 | load→idle | 12,256 | 54,107,064 |
| 7 | idle→load | 7,248 | 54,098,184 |
| 8 | load→idle | 7,264 | 54,030,120 |
| 9 | idle→load | 7,440 | 53,960,104 |
| 10 | load→idle | 7,248 | 53,897,672 |

汇总：

| condition | n | min | median | max |
|---|---:|---:|---:|---:|
| idle | 10 | 7,248 | 8,444 | 12,256 |
| stream-read | 10 | 53,897,672 | 53,988,976 | 54,149,680 |

最保守的 `min(load) / max(idle) = 4397.66×`，两组完全分离；load 极差相对
中位数约 0.47%。这些比值只支撑“对该负载有稳定响应”，不赋予事件更具体的
微架构语义。

## 5. 剩余不确定性与下一门禁

1. sysfs 没有导出事件名/format；虽然公开下游驱动把 `0x1000` 命名为 LLCC
   read event/read miss，尚未取得这台量产内核的精确源码与配置哈希，因此
   事件语义保持“downstream-driver convention + measured responsiveness”。
2. 计数可能是 CPU monitor、bank 汇总或更广系统流量；本 smoke 没有区分。
3. LLCC 计数需要 root，而正式 `ptr_chase` 当前是 adb shell。Runner 集成
   必须单独设计最小特权 sidecar，并把上下文、artifact 与计数窗口写进记录；
   禁止把整个通用 probe 路径静默提升为 root。
4. 下一步先实现 core PMU（L2 refill、L3 refill、DTLB walk、cycles）与 LLCC
   companion 的同窗采样、逐 repetition 记录和 4 KiB/THP 可审计分组；之后
   才执行 X4 512 KiB–3 MiB L2 校准矩阵。
5. 用户态 LLCC 路径已经可用，不满足 LKM-M1/M2 的触发条件；量产机继续
   禁止写 LLCC 控制寄存器。

临时 raw、远端构建树和设备端二进制已在记录验收证据后删除（本机产物移入
废纸篓）；本 smoke 不进入 `data/public/`，上表是完整接纳样本集。

## 6. 权限边界复核

为区分“shell 无权读取 sysfs type”与“shell 无权调用 perf event”，后续提交
`95ae11e` 为工具增加了与 `--pmu` 互斥的显式 `--type`。干净提交静态产物
SHA-256 为
`9c50ebd43147ceab30c2c4598d80a96bbc7eac18dbb9f441e554248fb8892ac7`。
同一产物、CPU7、100 ms、64 MiB 的对照结果为：

| caller | event | result |
|---|---|---|
| adb shell `uid=2000 context=u:r:shell:s0` | core `type=8/config=0x11`, thread | 成功；`count_delta=277415731`，无 multiplex |
| adb shell | LLCC `type=9/config=0x27`, per-CPU | `ENOENT` / exit 2（无效事件负控） |
| adb shell | LLCC `type=9/config=0x1000`, per-CPU | `EACCES` / exit 2 |
| KernelSU root `uid=0 context=u:r:ksu:s0` | LLCC `type=9/config=0x1000`, per-CPU | 成功；`count_delta=53068336`，无 multiplex |

据此，root 不是所有 PMU 的必要条件：core PMU 应直接集成到普通 shell probe；
只有 LLCC event open 需要最小特权 sidecar。显式 type 来自受审计的平台能力
清单，记录必须同时保留 type 数值与来源，避免绕过 sysfs 后失去可追溯性。
