# TLB 探针骨架（对应《TLB微架构深度分析报告》§5）

目标平台：Android Linux arm64 / 高通 SM8650（仅测 Cortex-X4 核，报告 §5.2）。

| 文件 | 对应章节 | 用途 |
|---|---|---|
| `tlb_capacity_probe.c` | §5.3 / §5.4 / §3.3(M4) | 改进版指针追逐容量扫描（预热 volatile 化、PMU 失败明确 n/a + mux 检测、真集合四分布、地址/逐轮数据落盘、**-K 独立链并行 walk 探针** + 时延百分位） |
| `l2_set_probe.c` | §5.5 | L2 同 set 地址生成器（H1~H4 假设 + **最终 VA 校验** + 分桶取样）+ **prime+probe** 稳态 way 跳变实验（filler 驱逐 + 分阶段 PMU + 首轮剔除 + 对照组 + run 模式地址落盘） |

**版本**：两文件头部均有完整版本记录（v1.0 → v2.1）。v2.0 为外部评审1 修订（真集合、prime+probe、最终 VA、-K 链）；v2.1 为外部评审2 修订（预热消除修复、perf fd<0 伪报 0 修复、mux 检测、slow 分子修正、绑核失败终止、--rawlog、run 模式地址落盘）。**TODO**：§5.6 的 iTLB 短跳板探针尚无源码（设计见报告），后续迭代补齐。

**v2 变更要点（外部评审1）**：
- `-d` 分布改为**真集合**：0 连续 / 1 大步距（修 v1 越界 bug）/ 2 随机集合 / 3 随机序（仅对照）；
- L2 run 模式改 **prime+probe**：v1 直接重访 w≤16 页，全部驻留 L1 dTLB，稳态**测不到 L2**；
- 哈希与校验统一用**最终虚拟地址**；新增 `-K` 独立链测并行 walk 深度（串行链单 outstanding miss，旧 fast/slow 协议无效，`-m` 降为辅助观察）。

## 编译

**macOS 主机（M4 Pro）→ Android arm64 交叉编译（推荐，源码零修改）：**

```bash
# NDK r26/r27/r28 的 macOS 工具链仍为 x86_64（prebuilt/darwin-x86_64），M 系 Mac 走 Rosetta 2
NDK=~/Library/Android/sdk/ndk/27.0.12077973
CC=$NDK/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android34-clang
$CC -O2 -Wall -Wextra -static -o tlb_capacity_probe tlb_capacity_probe.c
$CC -O2 -Wall -Wextra -static -o l2_set_probe l2_set_probe.c
```

**纯 Linux 主机本机编译**（流程验证用）：`gcc -O2 -Wall -Wextra -Werror ...`（同参数）。
macOS 本机 `cc` 编译仅用于语法/流程验证（产物为 Mach-O，不能在 Android 运行）。
替代方案：手机 Termux 内 `pkg install clang` 原生编译，免交叉。

**部署与运行（需 root）**：

```bash
adb push tlb_capacity_probe l2_set_probe /data/local/tmp/
adb shell -> su -> cd /data/local/tmp
taskset 80 ./tlb_capacity_probe -N 96 -R 200 -d 2 -e 0x0005 -e 0x002D
# taskset 80 = 绑 CPU7（X4 prime，toybox 十六进制掩码语法；无 -c 选项）
# 先用 /proc/cpuinfo 的 part 号（X4=0xd82）确认 X4 是哪颗核
```

## 容量扫描（地面真值：L1 dTLB 96 条 / L2 2048 条，X4 TRM Table 5-1）

```bash
# 细粒度扫描 N=80..112，验证 L1 拐点=96；每配置独立进程=独立重复
for n in $(seq 80 112); do
  taskset 80 ./tlb_capacity_probe -N $n -R 200 -d 2 \
      -e 0x0005 -e 0x002D --addrlog addr_N$n.log
done
# 真集合三分布对比（§5.4-2 全相联判据； -d 3 随机序仅作对照）
for d in 0 1 2; do taskset 80 ./tlb_capacity_probe -N 96 -R 200 -d $d -s 256; done
```

## M4：K 独立链并行 walk 深度（报告 §3.3，v2 重构）

```bash
# 每链工作集须 > 2048 页（持续 L2 miss → walk）；K 递增找饱和
for k in 1 2 4 8 16; do
  taskset 80 ./tlb_capacity_probe -N 4096 -R 20 -d 2 -K $k -e 0x8128 -e 0x0034
done
# 判读：DTLB_WALK_PERCYC(0x8128) 均值随 K 上升至平台 = 并行 walk 深度；
#       饱和后时延/负载线性增长。K 链逐拍交错（宏轮内 for step { for k {...} }）。
```

输出 `p50/p90/p99/max`（ns/宏轮）。注意：macOS 部分宿主 CLOCK_MONOTONIC
粒度约 1 µs，百分位需在 Android 目标板验证；必要时改 `CLOCK_MONOTONIC_RAW`。

## L2 way 跳变 + 索引假设检验（sets=256 × ways=8 已确认，目标只剩哈希函数）

```bash
for h in 1 2 3 4; do
  for w in $(seq 1 16); do
    taskset 80 ./l2_set_probe run -H $h -T 7 -w $w -R 20 -P 65536 -T2 100 \
        --addrlog run_h${h}_t7_w${w}.txt
  done
done
# 协议门控：probe 段 L1D_TLB_REFILL(ev0x5)≈w 且 L2D_TLB(ev0x2f)≈w，否则 filler 不足；
# 判据：w≤8 → L2D_TLB_REFILL(ev0x2d)≈0；w≥9 → 跳变（round 0 已剔除，计数为分阶段增量）；
# -T2 对照 set：跳变应为目标 set 特异。gen/run 均落盘最终 VA + 重算 set 供审计。
# 事件由探针内嵌 perf_event_open 采集（无需外层 perf）；simpleperf 等价：
#   simpleperf stat -e r5,r2d,r2f -- taskset 80 ./l2_set_probe run ...
```

## Android（SM8650）执行要点（报告 §5.2）

- 用 **simpleperf** 代替 perf：`simpleperf stat -e r5,r2d -- taskset 80 ./tlb_capacity_probe ...`
- 需 root 与 `perf_event_paranoid` 放宽；先用 `simpleperf list` 核对内核导出的事件集
- X4 为 prime 大核（通常 CPU7，掩码 0x80）；用 `/proc/cpuinfo` 的 part 号（0xd82）确认
- 锁核 + 记录频率轨迹防 DVFS 漂移

## 骨架性质声明

- 这是**可编译、流程完整**的基础版：错误处理、统计检验（置信区间）、DVFS 记录、
  IRQ 屏蔽等正式实验要求见报告 §5.8，由外层脚本与后续迭代补齐。
- 已知编译陷阱（开发中实测）：追逐循环若结果未使用会被 clang -O2 整体消除，
  代码中已用编译屏障 + sink 防护，修改测量循环时勿移除。
