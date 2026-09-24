# 11 · 跨平台抽象：正交分解与"换配置不改代码"

> 费曼段：一句话——**"在哪测"拆成五个独立维度，每个维度单独取值，平台差异就收进了一份 JSON。**

## 概念

### backend 单字符串的组合爆炸（ADR-0006 的由来）

早期设计用一个字符串标识目标：`macos-arm64`。看着简单，但它把 OS、ISA、设备、执行环境揉在一个键里。评审指出：扩展到 Android、x86、gem5、RISC-V 时，schema 枚举、目录、CMake、Runner、解析**五处要联动改**，组合爆炸。

现在的 target 是五个正交字段，各自独立取值：

| 字段 | 取值 | 含义 |
|---|---|---|
| `os` | darwin/linux/android | 操作系统 |
| `isa` | aarch64/x86_64/riscv64 | 指令集 |
| `target_id` | macbook-m4pro-01 等 | 匿名设备编号 |
| `execution_kind` | native/simulator | 真机还是模拟器 |
| `executor`/`transport` | native/gem5-…；local/ssh/adb | 怎么执行、怎么到达 |

`backend` 字符串降级为**派生展示名**，不再作权威键。

### controls：平台差异的唯一收敛点

平台间的本质差异只有一个：**怎么控制"在哪跑、什么状态跑"**。macOS 用 `taskpolicy -b`（QoS→E 核），Linux 用 `taskset -c`（绑核），Android 走 adb shell。框架把它声明化成平台配置的 `controls` 列表，执行器把 `command_prefix` 拼到探针命令前。**换平台 = 换一份 JSON，主流程零修改**——这是 ADR-0006 §5 的验收标准（新增 RISC-V 只允许动 toolchain preset、ISA kernels、capability provider、平台配置四处）。

### 三机管线（GB10 任务的形态）

Mac（驱动 runner）→ Xeon（交叉编译 aarch64 静态二进制）→ GB10（deploy + 执行）。组合式蓝图里 BuildProfile / Transport / Executor 的分离就是为"编译机 ≠ 驱动机 ≠ 目标机"准备的。

### capability discovery：先体检再上跑道

每个平台接入先跑能力探针（计时器分辨率、绑核手段、PMU 可用性），结果按 capability-manifest 落档。禁止假定任何平台有完整硬件控制权——macOS 连 sudo 都给不了你锁频和 PMU（v0.3 §2.1）。

## 费曼自测

1. 为什么 `backend` 不能保留为权威键？（组合爆炸；且"backend"里藏的维度变化无法独立演化）
2. 新增 gem5 执行通道时动主流程吗？（不动——executor 字段选择执行器实现，选择逻辑集中一处）
3. "同一份实验"跨平台的锚点是什么？（ExperimentSpec 的 protocol_version + 指标定义，不是文件名或代码行）

## 锚点

- `docs/adr/ADR-0006`（正交分解与扩展验收标准）
- `configs/platforms/macbook-m4pro-01.json`（controls 实例）
- `docs/tasks/2026-09-25-gb10-platform-onboarding.md`（三机管线）
