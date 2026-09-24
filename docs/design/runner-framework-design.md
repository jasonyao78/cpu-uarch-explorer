# 测试框架详细设计 —— cpu-uarch-explorer runner

> 读者对象：有初级微架构知识背景的工程师（知道 cache 有层级、知道 CPU 有核，不需要知道 ROB/IQ 是什么）。
> 内容基准：2026-09-24 的代码实现（commit `92cc1e5`）。本文描述的是**已实现的现状**，不是规划；规划性内容集中在最后一节，并明确标注。
> 关联文档：需求基线 `docs/requirements/v0.3.md`、决策记录 `docs/adr/`（ADR-0003/0006/0008 为主）、测量纪律 `docs/methodology/measurement-discipline.md`。

## 0. 这个框架是干什么的（30 秒版）

我们想回答一个问题：**一颗 CPU 的 cache/内存层级到底有多快？**（未来还会问：分支预测器多准、流水线多深……）

做法是用一个极小的测量程序（叫 **probe，探针**）去访问不同大小的内存区域，测每次访问花多少纳秒。访问 32KB 很快（在 L1 cache 里），访问 256MB 很慢（要去 DRAM）。把"区域大小 → 延迟"画成一条曲线，台阶的位置和高度就暴露了这颗芯片的 cache 层次结构。

这个框架负责把这件事**工程化**：同一份探针源码、同一份实验定义、同一份数据格式，在 Apple M4 Pro、x86 服务器、Android 手机、gem5 模拟器上跑出**可以直接对比**的结果，并且每个数字都能回答"什么时候、在哪台机器、哪版代码、什么参数下测的"。

## 1. 背景概念扫盲

### 1.1 指针追逐（pointer chase）——我们唯一的探针（目前）

要测"一次内存访问的真实延迟"，不能连续读一片数组——CPU 的硬件预取器（prefetcher）会猜到你下一步读哪，提前帮你取好，测出来的就不是真实延迟了。

`ptr_chase` 的做法：把一块缓冲区切成 64 字节一格，每格里存下一格的地址，**随机打乱后首尾相接成一条环链**。沿链走，每一步的地址都依赖上一步读出来的值，CPU 无法并行、无法预测——测到的就是"一次串行依赖 load 的真实延迟"。实现细节与踩坑记录（比如多链并行会把延迟摊薄 4 倍导致 L1 测出荒谬的 0.42ns）写在 `probes/cache-mem/ptr_chase.cpp` 头部的"技术原理"节，那是本仓注释密度的范本。

### 1.2 P 核与 E 核、QoS 分流

Apple M4 Pro 有 10 个性能核（P-core）和 4 个能效核（E-core），两者的 cache 层次和频率都不同。macOS **不允许**精确把线程钉在某个核上，但提供 QoS（Quality of Service，服务质量等级）机制：把进程设为 BACKGROUND 等级，调度器就会把它放到 E 核上跑。我们用 `taskpolicy -b <命令>` 实现这个分流（已实测验证：同一探针在默认 QoS 和 BACKGROUND QoS 下延迟呈稳定双峰，见 OI-5）。

### 1.3 为什么要重复 5 次取中位数

单次测量会被系统中断、频率漂移、其他进程干扰。我们的计时器有效分辨率是 41.67ns（实测），单次测 L1 延迟（约 1ns）根本不靠谱——所以探针每次跑几百万次访问取平均（量化噪声被平均掉），框架再把这个实验**重复 5 次取中位数**，并记录 min/max/p25/p75 分位数。详细纪律见 `docs/methodology/measurement-discipline.md`。

### 1.4 证据等级

仓里每个数字都标来源等级：`MEASURED`（实测）/ `DERIVED`（换算）/ `SIMULATED`（仿真）/ `PUBLIC_SOURCE` / `ASSUMED` / `UNKNOWN`。这是未来把实机数据和 gem5 仿真数据放在一起校准时的防混淆机制。

## 2. 总体架构

```text
┌─────────────┐   ┌──────────────────────────────┐   ┌──────────────────┐
│  Probe 层    │   │  Runner 层（本框架主体）       │   │  数据层           │
│  C++17 探针  │──▶│  plan → run → parse → 统计    │──▶│  JSONL 记录 +     │
│  (ptr_chase) │   │  重复执行 / QoS 控制 / 落盘    │   │  原始样本 + 清单   │
└─────────────┘   └──────────────────────────────┘   └──────────────────┘
       ▲                                                     │
       └────────────── 报告层（analysis/，规划中，未实现）◀─────┘
```

关键设计思想（来自 ADR-0006 与三轮评审）：

1. **"测什么"与"怎么跑"分离**：实验语义写在 ExperimentSpec（JSON 配置）里，平台差异写在 platform 配置里，Runner 主流程不含任何平台特判。
2. **Plan/Run 分离**：`plan` 阶段把实验展开成一组确定性的 case（可预览、可审计、无副作用），`run` 阶段只做执行。参数解析错误在 plan 期就爆掉，不会跑到一半才失败。
3. **每个数字都可溯源**：参数从哪来（实验定义还是平台默认）、二进制是哪版代码编的、原始输出是什么——全部落盘。
4. **绝不编造数据**：解析失败、探针报错时，产出的是"failed 记录 + 结构化失败原因"，而不是一个编出来的数字。

## 3. 核心概念与数据模型

四个概念构成一次实验的完整描述（schema 定义在 `runner/schema/`，JSON Schema 2020-12）：

| 概念 | 文件 | 类比 | 说明 |
|---|---|---|---|
| **ExperimentSpec** | `configs/experiments/*.json` | 实验方案书 | 测什么、扫哪些参数、指标定义。例：`ptr-chase-cache-sweep.json` 定义 buffer 从 32KiB 扫到 256MiB 共 14 档 |
| **Platform 配置** | `configs/platforms/*.json` | 设备档案 | 目标机的正交属性（OS/ISA/执行方式）、探针二进制路径、控制手段（QoS）、默认参数 |
| **run-record** | `runner/schema/run-record.v2.schema.json` | 实验记录单 | 一个 case 的结果：状态、指标值、统计量、环境、参数及来源、原始样本引用 |
| **artifact-manifest** | `runner/schema/artifact-manifest.schema.json` | 物证清单 | 二进制、原始样本的 SHA256 与谱系 |

数据流中的派生概念（纯内存对象，定义在 `runner/plan.py`）：

- **Control**：一次调度控制设置，如"BACKGROUND QoS"。对应 run-record 的 `environment.control`。
- **Case**：一个确定性执行单元 = 一组参数 × 一个 Control × 重复 N 次。例：`ptr-chase-cache-sweep:qos-background:b4096K-s64B`。
- **Sample**：case 的单次执行。5 个 sample 汇总成 1 条 run-record。

**run-record v2 的两条硬约束**（schema 强制，2026-09-24 评审修订）：

- `status=ok` → `metrics` 必须至少有一项数值指标；
- `status=failed/skipped/unsupported` → `metrics` 允许为空，但**必须**带结构化 `failure{reason, detail}`（机器可读原因码，如 `probe-exit-1`、`capability-unsupported`）。

## 4. 逐模块详解（`runner/` 包）

按数据流顺序。每个模块的头部 docstring 都写了设计锚点，此处是导读版。

| 模块 | 职责 | 关键设计决策 |
|---|---|---|
| `errors.py` | 错误类型与退出码阶梯 | CLI 退出码：0 全成功 / 1 配置错误 / 2 有 case 失败。`ParseError` 专用于解析失败 |
| `resolve.py` | 参数解析与溯源 | `ResolvedValue{value, source}` 记录每个参数来自哪一层（CLI > 实验 > 平台默认 > 规格默认）；**单位解析严格化**：认识 `KiB/MiB/GiB/KB/MB/GB/B`（一律 1024 进制），不认识的单位直接报错——这是评审实证过的教训（GB10 项目把 `64MiB` 静默当成 1024KB，DRAM 实验实际跑在 1MB 工作集上，且无任何告警） |
| `spec.py` | 配置加载与结构校验 | 只做运行必需的轻校验；完整 schema 校验是开发期动作（`uv run --with jsonschema`），运行时保持 stdlib 零依赖 |
| `plan.py` | 确定性 case 展开 | `build_plan()` 做 controls × sweep 笛卡尔积，计算派生参数（loads = max(min_loads, 每槽位 8 次)，对齐 8 次展开因子）；**repetitions 在 plan 期就落到每个 case 上**（GB10 的另一个教训：配置里写了 samples=7 但执行器从不读它） |
| `adapters/base.py` | 探针适配器协议 | 适配器只做两件事：参数→argv、stdout→metrics。`require_finite_number` 拒绝 nan/inf |
| `adapters/ptr_chase.py` | ptr_chase 适配器 | 对应 Probe ABI：`-b KB -s stride -n loads -w warmup`；stdout `key=value` 行 |
| `executor/local.py` | 本地执行器 | subprocess 同步执行；控制手段通过 command_prefix 注入（`taskpolicy -b`）；**永不抛异常**——超时/启动失败也收敛为结果对象，语义判断交给上层 |
| `engine.py` | Run 引擎 | 把上面所有环节串起来：逐 case 重复执行 → 原始输出落盘 → 解析 → 统计 → 写记录。退出码映射：0→ok、1→failed、2→unsupported（Probe ABI，ADR-0006 §3）。模块头部有一张"反模式对照表"，逐条对应 GB10 的实证缺陷 |
| `artifacts.py` | 原始样本与清单 | 每个 sample 的 stdout/stderr 原样落盘 + SHA256 登记；probe 二进制也登记（SHA256 + git commit/dirty）——回答"这数字是哪版二进制测的" |
| `statistics.py` | 统计量 | median/p25/p75/min/max（inclusive 线性插值）；空样本列表抛错——没有样本就没有数字 |
| `records.py` | 记录构建与落盘 | `build_run_record()` 组装 v2 记录；JSONL 逐行写且每行 fsync（崩溃最多丢当前行）；汇总文件走 `tmp → fsync → replace → 父目录 fsync` 原子写（读者永远看到完整文件或不存在） |
| `cli.py` | 命令行入口 | `python -m runner.cli plan ...` 预览；`python -m runner.cli run ...` 执行 |

### 探针二进制与仓库的接口（Probe ABI）

探针（C++）与 Runner（Python）之间的契约只有三条，任何新探针都必须满足：

1. stdout 输出 `key=value` 行（机器可解析）；
2. 退出码：0 成功 / 1 输入或环境错误 / 2 能力不支持；
3. **非法输入必须非零退出**，绝不允许带着 nan/inf 正常退出（静默无效数据是最坏的数据）。

## 5. 构建系统（ADR-0008）

CMake + `CMakePresets.json` 单一入口，构建产物按 `<目标平台>/<profile>` 分层：

```bash
cmake --preset macos-arm64-release      # 配置到 build/macos-arm64/release
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release      # 5 项 CTest（ubsan preset 为 6 项，多一项 UBSan 探针测试）
```

现有 preset：`macos-arm64-release`（默认）、`macos-arm64-ubsan`（UBSan 内存错误检查变体）、`darwin-x86_64-release`（x86_64 交叉，验证可移植性）。新增平台 = 新增 preset，不动 CMakeLists。整个 `build/` 被 gitignore 一行覆盖。

## 6. 测试体系（三层）

| 层 | 位置 | 守什么 |
|---|---|---|
| C++ 边界测试 | `tests/`（CTest，release preset 5 项 / ubsan preset 6 项） | 探针输入校验：合法输入必须产出数值、非法输入必须非零退出（WILL_FAIL）——守住 Probe ABI 第 3 条 |
| Python 单测 | `runner/tests/`（unittest，19 项） | 单位解析、plan 展开、参数溯源、统计正确性、原子写、样本不互相覆盖（有回归测试：曾经 `with_suffix` 误把 `.s0` 当后缀导致 5 趟样本互相覆盖） |
| 真实二进制契约测试 | `runner/tests/test_ptr_chase_contract.py` | adapter 生成的 argv 被**真实编译的 ptr_chase** 执行、真实 stdout 能被 parser 解析。fixture 必须来自真实二进制而非手写（GB10 教训：手写 fixture 与真实输出漂移，parser 上线即崩） |

运行方式：`python -m unittest discover -s runner/tests -t .`（用 `.venv/bin/python`）。

## 7. 数据管理与归档策略

一次 run 的产出（`data/public/runs/<时间戳>-<实验名>/`）：

```
records.jsonl       # 28 条 run-record（每 case 一条）——入库
artifacts.jsonl     # 141 条 artifact-manifest（二进制 + 140 个样本）——入库
run-manifest.json   # run 汇总——入库
raw/                # 280 个原始 stdout/stderr——不入库（可再生，占 83% 体量）
```

**只有记录和清单入库，原始样本留在本地**（2026-09-24 数据策略，v0.3 §7）。raw 的完整性由 manifest 里的 SHA256 锚定；需要时按记录参数重跑再生。晋升 baseline 的数据如需长期保存原始样本，压缩后进 `data/private/` 或 HDD 冷存储。

违反测量纪律的数据走 `data/quarantine/`（保留审计线索，禁止晋升 baseline）——该目录目前"文档先行"，首份隔离数据出现时再建。

## 8. 常用操作手册

```bash
# 0. 一次性准备
uv sync                                        # Python 环境
cmake --preset macos-arm64-release && cmake --build --preset macos-arm64-release

# 1. 预览实验（无副作用，先看再跑）
.venv/bin/python -m runner.cli plan \
  --experiment configs/experiments/ptr-chase-cache-sweep.json \
  --platform configs/platforms/macbook-m4pro-01.json

# 2. 执行（约 2 分钟：28 case × 5 重复）
.venv/bin/python -m runner.cli run \
  --experiment configs/experiments/ptr-chase-cache-sweep.json \
  --platform configs/platforms/macbook-m4pro-01.json

# 3. 开发期校验产出（schema 完整校验）
uv run --with jsonschema python3 -c "
import json, jsonschema
schema = json.load(open('runner/schema/run-record.v2.schema.json'))
for line in open('data/public/runs/<run目录>/records.jsonl'):
    jsonschema.validate(json.loads(line), schema)
print('all valid')"

# 4. 全部测试
ctest --preset macos-arm64-release
.venv/bin/python -m unittest discover -s runner/tests -t .
```

## 9. 扩展指南

### 加一个新实验（不改代码）

在 `configs/experiments/` 写一份新的 ExperimentSpec JSON（复制 `ptr-chase-cache-sweep.json` 改 sweep 范围/重复次数），`plan` 预览确认后 `run`。

### 加一个新平台（不改主流程）

在 `configs/platforms/` 写平台配置：target 五要素 + probe 二进制路径 + controls 列表。例：x86 服务器的控制手段会从 `taskpolicy` 换成 `taskset` 绑核——只改配置里的 `command_prefix`。

### 加一个新探针（加一个适配器）

1. C++ 侧：实现探针，遵守 Probe ABI（§4 末三条），在 `tests/` 加 CTest 边界测试；
2. Python 侧：在 `runner/adapters/` 写一个适配器（两个方法），注册进 `engine.py` 的 `_ADAPTERS`；
3. 在 `runner/tests/` 加真实二进制契约测试。

### 加新 ISA（架构验收测试，OI-8）

按 ADR-0006 §5：新增 RISC-V 只允许动四处——toolchain preset、ISA kernels、capability provider、platform 配置。**Runner 主流程和通用 schema 零修改**是验收标准。

## 10. 当前状态与已知限制

**已打通**（2026-09-24）：M4 Pro 单平台 "probe → 统一 JSON 数据" 全链；首份实机数据（P/E 双峰 cache sweep，28 case 全 ok，schema 校验通过）。

**已知限制**：

- 只有 local 执行器；SSH/ADB/gem5 执行通道未实现（platform 配置的 `transport` 字段已预留）；
- 只有 ptr_chase 一个探针；core/branch/tlb/sync 四域只有 README；
- 报告层（`analysis/`）未实现——records.jsonl 目前还没有消费者；
- 环境事务（改 governor/hugepage 这类需要"改完恢复"的操作）只有设计结论（借 GB10 模型重新实现），无代码；
- gem5 侧：增量树已修剪至 135 文件最小集，Xeon 重建验证进行中（OI-1）。

## 11. 下一步（规划，未实现）

1. **analysis/ 报告层**：消费 records.jsonl，生成带 P/E 对比与延迟曲线的报告——v0.3 里程碑"probe → JSON → 自动报告"的最后一段；
2. fake transport/target 契约测试（不依赖真机的 Runner 回归）；
3. 环境事务模型落地（Linux governor/hugepage 控制的前置）；
4. gem5 SE 模式精简配置（让 ptr_chase 跑进模拟器，校准闭环的起点）。
