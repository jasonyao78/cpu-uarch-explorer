# ADR-0006: 目标正交分解、ExperimentSpec 与 Probe ABI

- 状态：已接受（2026-09-24，源自外部评审的技术裁定；验证证据见当日提交记录）

## 背景

评审指出三类结构性问题，经逐条实测验证全部成立（如 `-n 1` 输出 `latency_ns=inf` 退出码 0；UBSan 对 stride=9 报 misaligned store；`ctest` 无测试；x86_64 交叉构建产物落在 `macos-arm64` 目录；qos 比值三次会话 2.6~3.9× 漂移）：

1. `backend` 单字符串混合 OS / ISA / 设备 / 执行环境 / 模拟器 / SoC，扩展会组合爆炸（schema 枚举、目录、CMake、Runner、解析五处联动修改）；
2. 「同一份 probe 源码」对指令 latency/端口/分支序列等天然依赖 ISA 的实验不成立；
3. 数据模型 v1 缺陷：required 与 ADR-0003 声明不一致；`additionalProperties:false` 与"新增字段不破坏旧读者"冲突；无 schema/protocol 版本、无运行状态、无统计量与原始样本引用、证据来源与访问分类混在一个枚举。

## 决策

### 1. 目标正交分解（schema v2 `target` 对象）

权威字段：`os`（darwin/linux/android）、`isa`（aarch64/x86_64/riscv64）、`abi`、`target_id`（库存编号）、`cpu_profile`（SoC 画像）、`execution_kind`（native/simulator）、`executor`（native/gem5-arm64-d9300/…）、`transport`（local/ssh/adb）。
`backend` 字符串降级为**派生展示名**，不作权威键。Runner 主流程只依赖能力接口，不依赖组合字符串。

### 2. ExperimentSpec 与实现分层

- **ExperimentSpec**（versioned）：测什么、参数、前置条件、指标定义——这是跨 ISA 一致性的锚点；
- **portable harness**：计时、预热、统计、输出（同一实现跨平台复用）；
- **ISA kernels**：`kernels/<isa>/` 存放 ISA 专用实现（指令 latency、端口、分支序列、fence/原子、PMU 访问、RISC-V 自定义指令）。
- 每次运行记录 `protocol_version` 与 `implementation_id`（portable 或 kernel:<isa>），跨 ISA 可比性由协议版本保证而非文件名。

### 3. Probe ABI

- 输出：stdout `key=value` 行，含 `schema_version`；
- 退出码：0=成功；1=输入/环境错误；2=能力不支持（允许以 `status=unsupported` 降级证据等级，禁止静默无效输出）；
- 非法输入必须非零退出（ptr_chase 已按此修复，首批 CTest 守住）。

### 4. schema v2（`runner/schema/`，v1 归档保留）

四类记录：`experiment`（ExperimentSpec）、`capability-manifest`（目标能力快照）、`run-record`（运行记录）、`artifact-manifest`（二进制/镜像/checkpoint/原始样本的 SHA256 清单）。
run-record 新增：`status`（ok/failed/skipped/unsupported）、`statistics`（repetitions/min/median/分位数/`raw_samples_ref`）、结构化 `environment.control`、`git.dirty`、`artifact.sha256`；`evidence.provenance`（来源）与 `access_class`（访问分类）分离；`additionalProperties=true`（扩展字段可演进）。

### 5. RISC-V 扩展验收标准（扩展性架构测试）

新增 RISC-V 仅允许改动：toolchain preset + ISA kernels + capability provider + target 配置。
**Runner 主流程零修改、通用 schema 零修改、现有 contract tests 全绿。** RISC-V compile-only preset 先行，作为架构验收。

## 后果

- 目录将随 runner 里程碑演进为 `schemas/`、`probes/{runtime,experiments,kernels}`、runner 组合式（BuildProfile/Transport/Executor/PlatformControl/Collector/Parser）——**本轮不搬家**，随实现落地；
- `probes/platform/` 能力探针代码留在 Probe 层，Runner 只调用与解释（修正了此前"升级为 runner 模块"的表述）；
- gem5 overlay 加固（基线断言、同步后 diff 摘要、预存脏树检测）随首个校准里程碑落地；disposable worktree / patch series 推迟，overlay 方案维持（ADR-0004 修订）；
- 统计口径（重复次数、中位数、原始样本、DVFS/thermal 状态）从 capability 探针开始强制执行；无频率控制的平台上 ±1 cycle 类目标按 ADR-0005 允许降级证据等级。
