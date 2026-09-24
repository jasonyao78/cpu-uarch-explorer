# 10 · 频率管理与环境事务：动系统设置的人要负责还原

> 费曼段：一句话——**进别人厨房做饭可以，用完得把灶台恢复原样；有些厨房（macOS）根本不让你动火。**

## 概念

### 频率为什么重要

同一个 load 在 3GHz 下是 3 个周期、在 2GHz 下是 2 个周期——**ns 值随频率漂移**，cycles 才是微架构的固有属性。所以跨平台比较只比 ns 是没意义的（measurement-discipline §5：ns 与 cycles 成对记录，cycles 还须区分 PMU 实测与频率换算——换算出来的按 DERIVED 降级）。

### 能力分级：锁频不是所有平台都能做

| 平台 | 锁频能力 | 对策 |
|---|---|---|
| Linux（Xeon/Android root） | ✅ cpufreq governor=performance | **环境事务**：改前存原值 → 测量 → 测完恢复 |
| macOS（M4 Pro） | ❌ 无用户态锁频（v0.3 §2.1 硬约束） | **测量期 powermetrics 并发采样入档**，频率波动转成不确定度证据 |

设计原则：**"锁频"不写进通用协议，它是平台能力**。capability discovery 先回答"这台机器能不能锁"，能锁走事务，不能锁走采样，两条路径都落 requested/actual 双记录。

### 环境事务模型（OI-8 主线，待实现）

改 governor 是 **host 级状态突变**——和 `taskset`（只影响子进程）有本质区别，所以**禁止用 command_prefix 实现**。正确形态借自 GB10 的事务协调器（评审已核实其模型完整实现，只是接线没闭环）：

- host-wide lock（同一时刻只有一个实验能改环境）；
- durable journal（改了什么、原值是什么，落盘）；
- inspect → validate → apply → verify 四步；
- 失败**逆序 restore**；进程被信号杀死也要能恢复；
- 未完成事务**阻止**下一次运行（上次没还原干净，不许再开新的）。

### 先行低成本项：频率只读快照

事务模型落地前，先做只读的：每个 case 前后读一次 `scaling_cur_freq` 写进 `environment.freq_snapshot`。不改系统、不需 sudo，让每条记录能回答"当时频率多少"。已并入 Xeon 接入任务书。

### "锁最大频率"的边界

锁频减少的是核心频率抖动，不是全部噪声：turbo 预算、热耗散仍会让实际频率漂移（D9300 全大核的热压力 v0.3 §2.5 专门提醒过）。标准做法是 governor=performance + 记录实际达成频率，而不是宣称"频率已固定"。

## 费曼自测

1. 为什么 governor 不能走 command_prefix？（prefix 只影响子进程；governor 是全局状态，改完必须恢复）
2. macOS 路径怎么处理频率不确定性？（powermetrics 并发采样入档 → 置信度评级的依据）
3. 未完成事务为什么要阻止下次运行？（环境处于未知的中间态，继续测会产生无法解释的数据）

## 锚点

- `docs/methodology/measurement-discipline.md` §5（频率感知纪律）
- OI-8（事务模型主线任务）、OI-9（借模型裁定）
- `docs/tasks/2026-09-25-xeon-platform-onboarding.md` §2.6（快照验收项）
