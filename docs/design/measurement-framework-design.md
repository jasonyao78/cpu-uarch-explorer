# 测量框架详细设计 —— cpu-uarch-explorer 全栈

> 读者对象：有初级微架构知识背景的工程师（知道 cache 有层级、知道 CPU 有核，不需要知道 ROB/IQ 是什么）。
> 内容基准：2026-09-24 的实现（commit `92cc1e5`）。本文描述**已实现的现状**；规划性内容集中在最后两节并明确标注。
> 关联文档：需求基线 `docs/requirements/v0.3.md`、决策记录 `docs/adr/`、测量纪律 `docs/methodology/measurement-discipline.md`、注释纪律 `docs/methodology/comment-discipline.md`。

## 0. 这个框架是干什么的（30 秒版）

我们想回答一个问题：**一颗 CPU 的微架构参数到底是多少？**——cache 每层多大、多快？内存延迟多少？分支预测器多准？流水线多深？

做法是用一组极小的测量程序（**probe，探针**）做定向实验：比如用指针追逐测内存层级延迟，把"工作集大小 → 延迟"画成曲线，台阶的位置和高度就暴露了 cache 层次结构。

这个框架负责把这类测量**工程化**：同一份探针源码、同一份实验定义、同一份数据格式，在 Apple M4 Pro、x86 服务器、Android 手机、gem5 模拟器上跑出**可直接对比**的结果；每个数字都能回答"什么时候、在哪台机器、哪版代码、什么参数下测的"；实机数据与仿真数据的系统性偏差最终用于**校准 gem5 模型**。

## 1. 背景概念扫盲

### 1.1 指针追逐（pointer chase）——目前唯一的测量探针

要测"一次内存访问的真实延迟"，不能顺序读一片数组——CPU 的硬件预取器会猜到你下一步读哪并提前取好，测出来的不是真实延迟。

`ptr_chase` 的做法：缓冲区按 64 字节切格，每格存下一格的地址，**随机打乱后首尾相接成环链**。沿链走时每一步的地址都依赖上一步读出的值，CPU 无法并行、无法预测——测到的就是"一次串行依赖 load 的真实延迟"。实现细节与踩坑记录（多链并行会把延迟摊薄 4 倍、L1 曾因此测出荒谬的 0.42ns）写在 `probes/cache-mem/ptr_chase.cpp` 头部"技术原理"节——那是本仓注释密度的范本。

### 1.2 P 核与 E 核、QoS 分流

Apple M4 Pro 有 10 个性能核（P-core）+ 4 个能效核（E-core），cache 层次和频率都不同。macOS **不允许**把线程精确钉在某核上，但有 QoS（服务质量等级）机制：进程设为 BACKGROUND 等级，调度器就把它放上 E 核。我们用 `taskpolicy -b <命令>` 实现分流（已实测验证：同一探针在默认 QoS 与 BACKGROUND 下延迟呈稳定双峰，OI-5）。这是"平台能力不同 → 控制手段不同"的第一个实例——Linux 上对应手段是 `taskset` 绑核。

### 1.3 为什么重复 5 次取中位数

单次测量会被中断、频率漂移、其他进程干扰。计时器有效分辨率实测为 41.67ns，单次测 L1 延迟（约 1ns）根本不靠谱——所以探针每次跑数百万次访问取平均（量化噪声被平均掉），框架再把实验**重复 5 次取中位数**，并记录 min/max/p25/p75。详见 `docs/methodology/measurement-discipline.md`。

### 1.4 gem5 与校准

gem5 是一个学术级计算机体系结构模拟器：用软件模拟一颗 CPU 的微架构（流水线、cache、分支预测器），跑得慢但内部完全可见。我们的目标之一是建一个联发科 Dimensity 9300 的 gem5 模型。**校准** = 用实机实测数据（MEASURED）对比仿真数据（SIMULATED），差异超阈值就调整模型参数——铁律：microbenchmark 用于校准（允许调参），Geekbench/SPEC 只用于验证（不许回头调参），否则验证集失去意义（v0.3 §9）。

### 1.5 证据等级

仓里每个数字标注来源等级：`MEASURED`（实测）/ `DERIVED`（换算）/ `SIMULATED`（仿真）/ `PUBLIC_SOURCE` / `ASSUMED` / `UNKNOWN`。这是实机与仿真数据混库时的防混淆机制，也是"这个数字能不能信"的速查标签。

## 2. 总体架构：四层全景

```text
┌──────────────────┐  ┌──────────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Probe 层         │  │  Runner 层            │  │  数据层          │  │  校准层（进行中） │
│  C++17 探针       │─▶│  Python 编排          │─▶│  JSONL + 清单    │─▶│  gem5 对比校准   │
│  ptr_chase /      │  │  plan→run→parse→统计  │  │  证据等级        │  │  差异单驱动      │
│  平台能力探针      │  │  重复执行 / QoS 控制   │  │  raw 样本留本地   │  │  overlay 增量树  │
└──────────────────┘  └──────────────────────┘  └─────────────────┘  └─────────────────┘
        ▲                        │
        └──── 报告层（analysis/，规划中）◀── records.jsonl
```

贯穿四层的设计思想（来自 ADR-0003/0006 与三轮外部评审）：

1. **"测什么"与"怎么跑"分离**：实验语义在 ExperimentSpec（JSON），平台差异在 platform 配置（JSON），Runner 主流程零平台特判。
2. **Plan/Run 分离**：plan 把实验展开成确定性 case 集合（可预览、可审计、无副作用），run 只执行。参数错误在 plan 期爆掉。
3. **每个数字都可溯源**：参数来源、二进制版本（SHA256 + git commit）、原始输出、环境控制——全部落盘。历史教训：前人留下的 SM8550 数据无日期无机型无代码版本，现已彻底不可考（ADR-0003 背景）。
4. **绝不编造数据**：探针报错/解析失败时产出"failed 记录 + 结构化原因"，不是编出来的数字。
5. **能力先探测后使用**：每个平台接入时先跑能力探针（capability discovery），不假定任何平台有完整硬件控制权（macOS 尤其如此）。

## 3. Probe 层设计（`probes/`）

### 3.1 探针的分类哲学

| 类别 | 例子 | 移植性 |
|---|---|---|
| **"测什么"类（portable）** | ptr_chase（内存延迟） | 同一份 C++ 源码跨所有平台编译 |
| **ISA 内核类（isa-kernel）** | 指令延迟、执行端口、分支序列（规划中） | 天然依赖指令集，按 `kernels/<isa>/` 组织，一致性由 ExperimentSpec 锚定（ADR-0006 §2） |
| **平台能力探针** | timer_resolution、qos_steering | 按 backend 组织（`probes/platform/macos-arm64/`），用于 capability discovery，**不产出校准数据** |

五域规划（v0.3 §5）：`core/`（指令延迟/吞吐）、`cache-mem/`（✅ ptr_chase 已实现）、`branch/`、`tlb/`、`sync/`——后四域目前只有 README。

### 3.2 ptr_chase 解剖（176 行 C++ 的教科书级结构）

- **防预取**：Fisher–Yates 洗牌 + 固定种子（可复现）——顺序链会被 stride 预取器跟踪；
- **防并行**：严格单链；同链展开 8 次只为摊薄循环控制开销，不引入访存并行度；
- **防优化**：mmap 真实内存 + 真实数据依赖 + volatile sink 物化结果；
- **计时口径**：计时区间装 ≥10⁵ 次 load，把 41.67ns 的计时量化噪声平均到 10⁻⁴ 以下（与能力探针实测结论联动）；
- **输入校验**：非法输入一律非零退出，绝不静默产出记录。

### 3.3 Probe ABI——探针与框架的唯一接口

任何新探针必须满足三条契约（ADR-0006 §3）：

1. stdout 输出 `key=value` 行（机器可解析）；
2. 退出码：0 成功 / 1 输入或环境错误 / 2 能力不支持；
3. **非法输入必须非零退出**——带 nan/inf 正常退出是最坏的数据污染形式。

CTest 边界测试（`tests/`）守住第 3 条：合法输入断言产出数值、非法输入断言非零退出。

### 3.4 平台能力探针

接入新平台时先回答"这台机器能怎么测"：计时器分辨率多少？有没有绑核手段？PMU 可用吗？`probes/platform/macos-arm64/` 的两个探针回答了 macOS 的前两问（41.67ns 分辨率；QoS 分流双峰 2.6~3.9×）。结论写入需求文档平台画像，能力快照按 `capability-manifest` schema 记录。

## 4. 平台层（`configs/platforms/`）

### 4.1 为什么 target 要正交分解（ADR-0006 §1）

早期设计用一个 `backend` 字符串（如 `macos-arm64`）标识目标。评审指出这会把 OS、ISA、设备、执行环境混在一个键里：扩展到 6 个后端时，schema 枚举、目录、CMake、Runner、解析五处要联动修改，组合爆炸。

现在的 target 是五个正交字段：`os`（darwin/linux/android）、`isa`（aarch64/x86_64/riscv64）、`target_id`（匿名库存编号）、`execution_kind`（native/simulator）、`executor` + `transport`（local/ssh/adb）。`backend` 字符串降级为派生展示名。新增平台只需一份 JSON 配置。

### 4.2 controls：平台差异的收敛点

平台间的本质差异只有一个：**怎么控制"在哪跑、什么状态跑"**。平台配置的 `controls` 列表把这件事声明化：

```json
{ "id": "qos-background",
  "control": { "mechanism": "qos", "value": "background" },
  "command_prefix": ["/usr/sbin/taskpolicy", "-b"] }
```

执行器把 `command_prefix` 拼到探针命令前即可。macOS 用 taskpolicy，未来 Linux 用 `taskset -c`、Android 用 adb shell 内的绑核——**主流程不变，只换配置**。`environment.control`（请求的机制与值）与 `raw_command`（实际执行的命令）双双入档，对应"requested/actual 双记录"原则（GB10 教训：探针打印请求值 hugepage=1，实际已静默回退 4K 页）。

## 5. Runner 层（`runner/` 包）

按数据流顺序的模块导读（每个模块头部 docstring 有完整设计锚点）：

| 模块 | 职责 | 关键设计决策 |
|---|---|---|
| `errors.py` | 错误类型与退出码阶梯 | CLI 退出码：0 全成功 / 1 配置错误 / 2 有 case 失败。`ParseError` 专用于解析失败 |
| `resolve.py` | 参数解析与溯源 | `ResolvedValue{value, source}` 记录参数来自哪层（CLI > 实验 > 平台 > 规格默认）；**单位解析严格化**：认识 `KiB/MiB/GiB/KB/MB/GB/B`（1024 进制），不认识的单位直接报错——GB10 实证教训：`64MiB` 被静默当成 1024KB，DRAM 实验实际跑在 1MB 工作集上且无告警 |
| `spec.py` | 配置加载与结构校验 | 只做运行必需轻校验；完整 schema 校验是开发期动作，运行时 stdlib 零依赖 |
| `plan.py` | 确定性 case 展开 | controls × sweep 笛卡尔积；派生参数（loads）plan 期算好；**repetitions 落到每个 case**（GB10 教训：samples=7 声明了却从不执行） |
| `adapters/base.py` | 适配器协议 | 适配器只做两件事：参数→argv、stdout→metrics；`require_finite_number` 拒绝 nan/inf |
| `adapters/ptr_chase.py` | ptr_chase 适配 | 对应 Probe ABI：`-b KB -s stride -n loads -w warmup` |
| `executor/local.py` | 本地执行器 | subprocess + command_prefix 注入控制；**永不抛异常**，超时/启动失败也收敛为结果对象，语义归上层 |
| `engine.py` | Run 引擎 | 串起全链：逐 case 重复执行 → 原始输出落盘 → 解析 → 统计 → 写记录；退出码映射 0/1/2 → ok/failed/unsupported。模块头部有"反模式对照表"，逐条对应 GB10 实证缺陷 |
| `artifacts.py` | 原始样本与清单 | 每 sample 的 stdout/stderr 原样落盘 + SHA256；probe 二进制也登记（SHA256 + git commit/dirty） |
| `statistics.py` | 统计量 | median/p25/p75/min/max（inclusive 插值）；空样本抛错——没有样本就没有数字 |
| `records.py` | 记录构建与落盘 | JSONL 逐行写 + 每行 fsync（崩溃最多丢当前行）；汇总文件 `tmp → fsync → replace → 父目录 fsync` 原子写 |
| `cli.py` | 命令行入口 | `plan` 预览（无副作用）/ `run` 执行 |

## 6. 数据层（`runner/schema/` + `data/`）

### 6.1 为什么 JSONL 先行（ADR-0003）

原始层唯一事实源是 JSONL：每行一条记录、追加写、流式可读、schema 可演进、C++/Python 双端零依赖。SQLite 汇总层推迟到首次跨 run 分析需求出现时再引入（YAGNI），schema 已按可无损迁移设计。

### 6.2 四类记录与 v1→v2 演进

| 记录 | 类比 | 说明 |
|---|---|---|
| ExperimentSpec | 实验方案书 | 测什么/参数/指标定义（`configs/experiments/`） |
| capability-manifest | 体检报告 | 平台能力快照（计时器/绑核/PMU） |
| run-record | 实验记录单 | 一次 case 的结果、统计、环境、参数溯源 |
| artifact-manifest | 物证清单 | 二进制与原始样本的 SHA256 谱系 |

v2 相对 v1 的改进全部来自评审实证：状态字段（ok/failed/skipped/unsupported）、统计量与原始样本引用、证据来源与访问分类拆成两个正交轴、`additionalProperties=true`（新增字段不破坏旧读者）。2026-09-24 第三轮评审又修订一条硬约束：**metrics 强制随 status 条件化**——ok 必须有数值指标；failed/skipped/unsupported 允许空 metrics 但必须带结构化 `failure{reason, detail}`（此前的 schema 下，一条失败的记录根本无法合法表达，只能编造数字）。

### 6.3 归档策略（2026-09-24 数据策略，v0.3 §7）

一次 run 的产出：

```
records.jsonl       # run-record——入库（数据层本体）
artifacts.jsonl     # artifact-manifest——入库
run-manifest.json   # run 汇总——入库
raw/                # 原始 stdout/stderr——不入库（可再生，占 83% 体量）
```

raw 样本的完整性由 manifest 的 SHA256 锚定，需要时按记录参数重跑再生；晋升 baseline 的数据如需长期留存原始样本，压缩后进 `data/private/` 或 HDD 冷存储。违反测量纪律的数据走 `data/quarantine/`（保留审计线索、禁止晋升 baseline，该目录文档先行、随首份隔离数据建立）。

## 7. 构建与质量保障

### 7.1 构建（ADR-0008）

CMake + `CMakePresets.json` 单一入口，产物按 `<目标平台>/<profile>` 分层（`build/macos-arm64/release` 等）。构建配置谱系入库可审计；`build/` 一行 gitignore 全覆盖。现有 preset：`macos-arm64-release` / `macos-arm64-ubsan` / `darwin-x86_64-release`。新增平台 = 新增 preset，不动 CMakeLists。

### 7.2 三层测试体系

| 层 | 位置 | 守什么 |
|---|---|---|
| C++ 边界测试 | `tests/`（CTest，release 5 项 / ubsan 6 项） | Probe ABI：合法输入产出数值、非法输入非零退出 |
| Python 单测 | `runner/tests/`（19 项） | 单位解析、plan 展开、参数溯源、统计、原子写、样本不互相覆盖（回归锚点：`with_suffix` 曾把 `.s0` 当后缀导致重复样本互相覆盖） |
| 真实二进制契约测试 | `runner/tests/test_ptr_chase_contract.py`（3 项） | adapter argv → 真实编译的 ptr_chase → 真实 stdout → parser 全链。fixture 必须真实捕获（GB10 教训：手写 fixture 与真实输出漂移，parser 上线即崩） |

### 7.3 注释纪律

`docs/methodology/comment-discipline.md`（2026-09-24 起强制）：模块头部写职责 + 设计锚点；公开函数写契约；非显然决策留"为什么"及出处；反模式防线旁标注教训来源；中文注释英文标识符；`ptr_chase.cpp` 头部为密度基准；改代码不改注释视为缺陷。

## 8. 校准层：gem5 集成（基建已验证，建模后置）

### 8.1 overlay 集成方案（ADR-0004 修订）

- `third_party/gem5`：官方上游 submodule，钉 `ddd4ae35ad`（**v25.0.0.1**，增量树原生基线），**保持纯净**，不直接提交修改；
- `third_party/gem5-d9300-patch/gem5`：D9300 增量树，**唯一事实源**；
- `apply_patchset.sh`：构建前把增量同步进 submodule 工作树，带基线断言与脏树检测；上游更新 = submodule 快进 + 重同步 + 重建。

### 8.2 最小集修剪（2026-09-24/25，blob 哈希普查）

增量树真实基线经 blob 哈希普查定位为 **v25.0.0.1**（873/1008 文件逐字节吻合）。原树中 873 个文件是旧基线的纯携带——它们在 sync 时会**静默回退**上游新版的对应文件（隐性风险，已消除）。修剪后保留 **134 个有意 delta**：26 个改动（O3 流水线 commit/fetch/iew/inst_queue/lsq/rename 等 + DRAMInterface/lpddr5 内存模型）+ 108 个新增（D9300/D9200 配置、CoralNPU/NDP/Gemmini 资产、`run_multicore.sh`）。普查与清单详见 `docs/gem5-d9300-intake.md`。

### 8.3 当前状态与验证门

- **已通过（2026-09-25，最终状态）**：v25.0.0.1 + 134 文件最小集，Xeon 干净重建成功（gem5.opt 910M，0 error），SE 冒烟通过。过程中修掉三个增量树缺陷（m5.internal 引用、IQUnit 结构性冲突、CheckerCPU 注销链断裂），全部留痕于 intake 文档；
- 未做：D9300 的 SE 模式精简配置（现有配置是全系统级，需磁盘镜像+内核）；**建模/校准整体后置**——启动条件为探针套件齐备（core+cache+branch）且 D9300 实机入册（OI-6），此前 gem5 侧只做 intake 参数谱系梳理。

## 9. 常用操作手册

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

# 3. 开发期 schema 完整校验
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

## 10. 扩展指南

- **加实验（不改代码）**：`configs/experiments/` 写新 ExperimentSpec JSON，plan 预览后 run；
- **加平台（不改主流程）**：`configs/platforms/` 写平台配置（target 五要素 + probes 映射 + controls 列表）；
- **加探针（三步）**：C++ 实现遵守 Probe ABI + CTest 边界测试 → `runner/adapters/` 写适配器注册进 `engine.py` → 加真实二进制契约测试；
- **加 ISA（架构验收，OI-8）**：只允许动四处——toolchain preset、ISA kernels、capability provider、platform 配置；Runner 主流程与通用 schema 零修改是验收标准（ADR-0006 §5）。

## 11. 当前状态与已知限制

**已打通**（2026-09-25）：M4 Pro 单平台 "probe → 统一 JSON 数据 → 自动报告" 全链（v0.3 里程碑闭环）；两份实机 sweep 均已生成报告（`report.md` + `latency.svg` 随 run 目录入库）；gem5 增量树修剪至 134 文件最小集并改钉原生基线 v25.0.0.1。

**已知限制**：

- ~~只有 local 执行器~~ ✅ 2026-09-25：SSH 通道已实现（SshExecutor + transport 工厂按 ADR-0006 选择，主流程零特判），Xeon（linux-x86_64）平台接入并产出首份跨平台数据；ADB/gem5 通道未实现；
- 只有 ptr_chase 一个测量探针；core/branch/tlb/sync 四域只有 README；
- 报告层仅支持单 run 报告；跨 run 汇总与校准差异单未做；
- 环境事务（改 governor/hugepage 需"改完恢复"）只有设计结论（借 GB10 模型重新实现），无代码；频率管理按能力分级：**能锁的平台走事务锁+恢复（Xeon governor=performance 为第一受控项），不能锁的平台（macOS 无锁频能力）走测量期并发采样入档**，频率只读快照作为先行项并入 Xeon 接入（OI-8）；
- gem5 基建已验证（v25.0.0.1 + 134 文件最小集，Xeon 重建与 SE 冒烟通过）；D9300 SE 精简配置与建模后置（启动条件：探针套件齐备 + D9300 实机入册）。

**Xeon 首测解读（2026-09-25，修订版 v2 —— 修正留痕，measurement-discipline §6）**：

- **v1 结论（同日早些时候）**：台阶位置与硬件画像一致（L1d 48KB 边界在 64K 档、L2 2MB 边界在 2M 档）；LLC 平台期未观测到，原因未锁定，候选 DVFS/TLB/THP。
- **v2 根因（freq_snapshot + L3 细扫 + 重复内分布三重证据锁定）**：
  1. **内存敏感负载下 HWP 不升频**——指针追逐全程实测 800MHz（`freq_snapshot` 入档），而 ALU 密集负载可达 2.0GHz：ns 绝对值被放大 2~4 倍，但同 case 内比值/台阶位置不受影响（频率在同一 case 内约去）；
  2. **4K 页 TLB 压力把平台期拉成斜坡**——4M→64M 的缓慢单调爬升（82→94 cycles@0.8GHz）与页数增长（1K→16K 页，L2 STLB 2048 项溢出）吻合；
  3. **物理页分配布局决定 L3 观测形态**——96MiB 档 5 次重复内双峰（3 次 ~60ns / 2 次 108~141ns，同二进制同尺寸仅 mmap 布局不同）：坏布局下 L3 set 冲突使命中看起来像 DRAM。真实 L3 命中延迟的证据存在于 2M 档（33cy）与 96M 好运气样本（48cy），与 SPR 文献值 ~40-50cy 吻合。
- **判定**：sysfs 容量真值（48K/2M/105M）与台阶位置**全部一致**；"缺失的 L3 平台期"不是硬件矛盾，而是 **4K 页 + 内存碎片布局 + 未锁频** 的合成伪影——正是 measurement-discipline"hugepage 为 Linux 正式测量前提"条款的又一实证。
- **复测前置（按优先级）**：① ptr_chase hugepage 支持（backlog 项，消除 TLB 项 + 大幅降低 set 冲突敏感度）；② 锁频（sudo governor=performance，需用户授权；走未来环境事务）；③ evict 工具 warm/cold 对照。

## 12. 下一步（规划，未实现）

1. ~~analysis/ 报告层~~（✅ 2026-09-25 落地：单 run Markdown + SVG）→ 后续：跨 run 汇总对比、校准差异单（MEASURED vs SIMULATED）；
2. fake transport/target 契约测试（SSH fake 单测已落地 2026-09-25；target 契约随 ADB/gem5 通道补充）；
3. 环境事务模型落地（Linux governor/hugepage 控制的前置）；
4. gem5 SE 模式精简配置（ptr_chase 进模拟器，校准闭环起点）。
