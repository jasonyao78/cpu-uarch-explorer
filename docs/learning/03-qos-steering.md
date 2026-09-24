# 03 · QoS 分流：macOS 不让绑核，怎么测 E 核

> 费曼段：一句话——**不能点名坐哪，就穿上"我不着急"的衣服，调度器自然把你安排到角落的节能核。**

## 概念

### 问题

Apple M4 Pro 有 10 个 P-core（性能核）+ 4 个 E-core（能效核），微架构不同、频率不同、cache 层次不同——做探测当然想分开测。Linux 上这事简单：`taskset -c 3` 把进程钉在 3 号核。但 **macOS 不提供精确的绑核接口**：`THREAD_AFFINITY_POLICY` 只是个 hint，调度器可以不理。

### 解法：QoS 等级分流

macOS 的 QoS（服务质量等级）是调度器的核心输入：进程声明自己多"着急"，调度器据此分配核型。**BACKGROUND 等级的线程会被放上 E-core**——这是 macOS 公开支持的路径。我们用 `taskpolicy -b <命令>` 让探针以 BACKGROUND QoS 运行。

### 怎么知道它真的生效了（实测证据）

OI-5（2026-09-24）：同一延迟链探针，USER_INTERACTIVE/DEFAULT ≈ 1.6 ns/iter，BACKGROUND ≈ 5.2~6.1 ns/iter，**双峰结构三个会话稳定复现**。注意纪律细节：P/E 比值 2.6~3.9× 随频率状态漂移，**比值不作为常量引用**——我们只断言"双峰存在且可复现"，断言强度不超过证据强度。

### 在框架里怎么落地

平台配置的 `controls` 列表把分流声明化：`qos-background` 控制组带 `command_prefix: ["/usr/sbin/taskpolicy", "-b"]`，执行器把它拼到探针命令前。请求值（QoS=background）进 `environment.control`，实际命令进 `raw_command`——requested/actual 双记录。

## 测量

首份 P/E 双峰 sweep（2026-09-24）：32KiB 档 default 0.77ns vs background 1.4~2.3ns；256MiB 档 123ns vs 184~190ns。E-core 的层次台阶位置与 P-core 明显不同（E 核 L2 更大、DRAM 更远）。

## 费曼自测

1. 为什么 QoS 分流可信但不是精确绑核？（调度器在 QoS 档内仍可迁移线程；我们测的是"档"不是"核"）
2. 为什么比值不能当常量？（DVFS 频率漂移，双核型频率缩放不同步）
3. 如果 macOS 未来开放精确绑核，框架要改哪里？（只改 platform 配置的 controls 列表，主流程不动——这正是 controls 抽象的意义）

## 锚点

- `probes/platform/macos-arm64/qos_steering.cpp`（能力探针）
- `configs/platforms/macbook-m4pro-01.json`（controls 声明）
- OI-5（`docs/open-items.md`，已关闭）
