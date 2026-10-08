# 遗留问题跟踪（open items）

> 本地快照（2026-09-23，tag `req-v0.3`）。仓库接入 GitHub 后同步为 Issues（标签 `open-item`）。每项注明：阻塞什么、如何回填、当前证据等级。

## OI-12 ROB 微架构深度分析项目（2026-09-30 登记，第二个部件探测项目）

- **交付物（v0.1 已入库）**：`docs/cpu-uarch-deep-analysis/rob-deep-analysis/`——报告 v0.1（采数前版本：估计量定义/混淆清单/判据预注册 J1–J8/协议三要素）、探针骨架 `probes/rob_window_probe.c`（mini-JIT，7 类别 × 2 锚点，本机编译冒烟 + 生成码 capstone 核验通过）、probes README；方法迁移矩阵相应升级 v0.3。
- **与 TLB 项目最大差异**：ROB 无 TRM 真值（已全文核验 TRM+优化指南零披露），走"估计量优先 + 第三方候选区间 + 交叉约束"（矩阵 C1 ✏️ 档）。
- **不做工程对接**（项目边界，2026-09-29 拍板）：不挂 runner/analysis/probes-CMake；采数数据按 B3 逐轮落盘但不进 runner 数据模型；数据分层/quarantine 纪律仍适用。
- **跟踪面**（逐项状态见报告附录待办表，此处登记归属与触发）：

| 项 | 内容 | 状态 |
|---|---|---|
| 采数前置 | Phase 0（0a 事件导出集 / 0b 锚点延迟标定 / 0c X4 核确认）→ §5.8 判据表冻结 | ⬜ 待办（触发：首次目标板采数） |
| E0 附带验证 | 6 项（MOV 消除 ×2、NOP/分支发射、拆分因子基线、fsqrt 标定）；**E0-3 是主协议最大单点风险**（NOP 若不占窗口则 stuffedcow 前提在 X4 不成立），预案已预注册 | ⬜ 待办 |
| 候选区间表扩充 | Geekerwan / Chips and Cheese / AnandTech 等第三方实测值渠道调研 | ⬜ 待办（采数前） |
| 探针 v2 | xbyak_aarch64 替代手写发射器评估；Microarchitecturometer（支持 Arm）/rob.rs 适配部件评估；E0 依赖链模式；混合类别；进程内扫描（免每点 chase 初始化）；黄金汇编回归 | ⬜ 待办（E0 之后） |
| CPUSUIT 代码复用范围 | 作者已确认为仓库所有者本人（Apache-2.0 头注，reference-materials.md 已更正）；当前保守策略 = 方法学借鉴不搬代码，**直接复用范围待所有者拍板** | ⏸ 待决策 |
| 判据闭环 | E1→E2→E3 后按 J1–J8 评定，允许/禁止归因命名；通过后报告升 v0.2（含实测），矩阵 ROB 列证据状态升级【目标机】 | ⬜ 待办 |

## OI-1 gem5 D9300 模型源码接入（2026-09-24：主体完成，剩余验证与梳理）

- **✅ 模型工作定位**：用户提供的 gem5-d9300-patch 增量树——`configs/example/arm/arm_multicore_d9300.py`（D9300 全系统配置）+ CoralNPU/NDP/Gemmini 资产 + `run_multicore.sh` 全流程（checkpoint/NPU 后端切换）。原始 drop 只读归档于 `../cpu-uarch-ref/gem5-d9300-patch/`（MANIFEST.sha256）。
- **✅ 集成落地（ADR-0004 修订：overlay 方案）**：`third_party/gem5` = 官方上游 submodule（钉 `ddd4ae35ad` = v25.0.0.1，增量树原生基线，ignore=dirty）；`third_party/gem5-d9300-patch/gem5` = 增量树（唯一事实源）；`apply_patchset.sh` 同步后构建（带基线断言与脏树检测）；脚本与文档路径已适配本仓布局。
- **✅ 最小集修剪（2026-09-24，blob 哈希普查）**：增量树真实基线定位为 **v25.0.0.1**（873/1008 逐字节吻合）；删除 873 个纯旧版携带文件（它们此前会把 v25.1 静默回退，属隐性风险），保留 **135 个有意 delta**（27 改 = O3/内存模型本体；108 新 = D9300 配置 + NPU 资产 + 流程脚本），1008 → 135 文件（次日失败 #3 修复后再减 1：`src/cpu/SConscript` 恢复上游，最终 **134 文件 = 26 改 + 108 新**）。普查方法与清单见 `docs/gem5-d9300-intake.md`。
- **✅ 改钉 v25.0.0.1（2026-09-25，ADR-0004 修订）**：修剪后钉 v25.1 的重建暴露结构性冲突（v25.1 O3 重构拆出 IQUnit，v25.0 基线增量无法适配——失败 #1 m5.internal 引用失效、失败 #2 IQUnit 模块缺失，详见 intake 文档）；裁定改钉增量原生基线 v25.0.0.1（零移植还原原项目已验证状态），`apply_patchset.sh` 新增基线断言与脏树检测（OI-8 overlay 加固两项落地）。v25.1 移植（746 行有意改动 + O3 重构适配）入 backlog。
- **✅ 验证门通过（2026-09-25，Xeon 干净重建）**：失败 #3（overlay 的 `src/cpu/SConscript` 注销 CheckerCPU 却保留 DummyChecker 注册——增量树自带的不自洽；该文件恢复上游即逐字节等同基线，按最小集原则从增量树移除，135 → 134 文件）修复后，`rm -rf build/ARM` 干净重建成功（gem5.opt 910M，0 error），SE 冒烟通过（`Exiting @ tick 46213000`，退出码 0）。**修剪 + 改钉的最终状态（v25.0.0.1 + 134 文件最小集）正式验证完毕**。
- **基线兼容性 ✅（2026-09-24 验证）**：Xeon 系统 scons 构建成功（`build/ARM/gem5.opt` 954MB）；ARM64 SE 冒烟仿真通过（交叉编译静态 hello → `Exiting @ tick`，退出码 0）。overlay 与 v25.1 基线兼容性正式确认。曾用 uv python 驱动构建导致 gem5py 崩溃（Error 134），改系统 scons 后通过；教训已记入 runbook 附2/附3 与 ADR-0007 修订。剩余：intake 梳理（O3/DDR 参数表、已有校准数据）、SE 模式精简配置（校准闭环用）、开源前 SPDX 检查点。
- **⏳ intake 梳理**：O3 参数表、DDR/内存配置、checkpoint 流程、NPU 后端、已有校准数据 → `docs/gem5-d9300-intake.md`。
- **⏳ 合规检查点（开源前）**：增量树逐文件 SPDX/权属复核（用户已确认无权属问题入库私有仓；delta 文件普遍缺许可证头）。
- **⏳ SE 模式精简配置**：现有配置为 full-system（需磁盘镜像 + 内核）；校准闭环需补 SE 模式配置让 ptr_chase 等微基准跑进 gem5（写配置时遵循 `third_party/gem5/configs/AGENTS.md`：优先 stdlib、窄配置、py_compile + 最小测试验证）。

## OI-8 runner 组合式重构与扩展性验收（Phase C，2026-09-24 评审衍生）

- **✅ 最小纵向闭环（2026-09-24 落地）**：`runner/` 包实现 Plan → repeated execution → adapter → raw artifact → parser → statistics → atomic record 全链：`spec.py`（配置加载与结构校验）、`resolve.py`（ResolvedValue{value,source} 溯源 + 严格单位解析，未知单位硬报错）、`plan.py`（Plan/Run 分离、确定性 case 展开、repetitions 真实消费）、`adapters/ptr_chase.py`、`executor/local.py`（command_prefix 承载 QoS 控制）、`artifacts.py`（原始样本 + SHA256 manifest）、`records.py`（run-record v2 构建、JSONL 逐行 fsync、汇总文件 tmp→fsync→replace→父目录 fsync）、`engine.py`、`cli.py`（plan 预览 / run 执行、退出码阶梯 0/1/2）。22 项测试全绿（含真实二进制契约测试 `test_ptr_chase_contract.py`）。首份实机数据：M4 Pro P/E 双峰 cache sweep，28 case × 5 重复全 ok，28 条 run-record 与 141 条 artifact-manifest 全部通过 schema 校验（`data/public/runs/20260924T153722Z-ptr-chase-cache-sweep/`）。
- **剩余**：fake target / transport 契约测试；RISC-V compile-only preset 作为扩展性架构测试；gem5 overlay 同步加固（同步后 diff 摘要；基线断言与脏树检测已于 2026-09-25 落地）；跨 run 汇总与校准差异单（analysis/ 已落地单 run 报告，2026-09-25）。
- **⬆ 环境事务模型（2026-09-25 升级为主线任务）**：GB10 模式重新实现——host-wide lock、durable journal、inspect→validate→apply→verify→逆序 restore、中断恢复、未完成事务阻塞下次运行（OI-9 裁定"借模型"）。**第一个受控项 = Xeon 的 cpufreq governor（performance 锁频）**；macOS 无锁频能力（v0.3 §2.1 已知约束），对应路径是 capability-manifest 记 `unsupported` + 测量期 powermetrics 并发采样入档。原则：锁频是 host 级状态突变，必须走事务恢复，禁止用 command_prefix 实现。
- **先行低成本项（并入 Xeon 接入任务）**：频率只读快照——每 case 前后读 `scaling_cur_freq`（Linux）/ powermetrics 采样（macOS），写入 `environment.freq_snapshot`（schema 扩展字段，登记 runner/schema/README.md）；让每条记录能回答"当时频率多少"，不解决波动但提供不确定度证据。
- **传输层**：SSH/ADB Transport 与 gem5 Executor（SSH 随 Xeon 接入任务先行，见 `docs/tasks/2026-09-25-xeon-platform-onboarding.md`）。
- **验收标准（ADR-0006）**：新增 RISC-V 仅需 toolchain preset + ISA kernels + capability provider + target 配置；runner 主流程零修改、通用 schema 零修改、现有 contract tests 全绿。
- **前置**：ADR-0006 与 schema v2（2026-09-24 已落盘）。
- **状态更新（2026-09-26）**：环境事务已接线——平台声明式 `host_requirements`（默认拒绝、`--allow-mutation` 门槛）+ 启动前 `reconcile_unfinished` 中断自动恢复（任务书 2026-09-26 完成，测试含 SIGINT/SIGKILL 两路径）；Xeon 自动锁频的 sudo 边界已实证（结构化失败、系统不变），sudoers 配置属人工步骤（`docs/runbooks/xeon-governor-lock.md`）。组合式重构深化、RISC-V preset、gem5 overlay 加固仍待。

## OI-9 arm64-uarch-probe 借鉴迁移（2026-09-24 登记）

- **背景**：用户前作 `~/gb10-cpu-arch-probe`（GB10 = ARM64 Linux，X925+A725 双 cluster，在手且活跃；Phase 1-4 完成）。深度分析结论：其声明式配置、runner、契约测试、测量方法学领先本仓 1-2 个阶段，但绑定 ARM64/Linux 且有未完工子系统（环境事务）。
- **决策**：借鉴模式（用户拍板）——两仓独立；方法学迁移 + runner 蓝图参考；GB10 基线数据不入我方校准链。
- **方法学迁移**：`docs/methodology/measurement-discipline.md`（温度语义三档/页策略/统计/置信度/修正留痕/报告模板）。
- **ptr_chase 改进 backlog**：见 `probes/cache-mem/README.md`（MONOTONIC_RAW、hugepage+cold 参数化、evict 工具移植评估、chase_migrate 范式）。
- **runner 蓝图吸收清单**（Phase C / OI-8 的前置设计输入）：声明式 configs + 启动期引用完整性校验、Plan/Run 分离 + environment phase 分组、ProbeAdapter 4 方法 + 错误值返回、ResultStore 原子写 + case_definitions_signature、ResolvedValue{value,source} 参数溯源、exit code 阶梯、adapter↔二进制契约测试。**借分层、协议与测试方式，不借其当前 Runner 实现**（2026-09-24 外部评审实证：working-set 的 MiB/KiB 单位不被识别、静默降级为默认 1024KB；profile 声明的 samples 无消费点、sample_index 恒为 0；journal_tx_ids 从不追加；environment 硬编码 platform=unknown；CLI 以 coordinator=None 构造且调用缺 backend 参数）。fixture 的真实来源须由 capture manifest/命令证明（其历史 fixture 曾手写臆造，见该仓复盘文档），不能因文件存在就默认真实。
- **环境事务子系统：借模型、重新实现接线**（2026-09-24 评审纠偏，原"整体不吸收"裁定过头）：模型本身已实现 host-wide lock / durable journal / inspect→validate→apply→verify / 失败后逆序 restore / signal 中断恢复 / 未完成事务阻止新运行；coordinator=None 是 CLI/Runner 接线缺陷而非模型无价值。未来控制 Linux governor / hugepage / THP / perf 权限时此为核心模式（**2026-09-25 升级：第一个受控项定为 Xeon cpufreq governor，见 OI-8**）。**不吸收**：其 ARM64 硬编码假设。
- **GB10 平台**：未来接入按声明式平台 JSON 模式（v0.4 候选）；它是 hugepage/PMU/跨核方法学的最佳宿主，也是可扩展性的天然验收平台。**任务书已备（2026-09-25）：`docs/tasks/2026-09-25-gb10-platform-onboarding.md`——自驱模式：Mac↔GB10 无 SSH、GB10 可从 GitHub 只读 clone 但不能 push，故代码经 GitHub 下行、GB10 原生编译本地执行、数据经物理介质回传 Mac 侧按 quarantine 流程入库**（网络约束已核实并登记 hosts.md；规格摘要为 PUBLIC_SOURCE，拓扑以机上实测为准）。

## OI-2 红米设备信息回填（android-arm64）（2026-09-27 大更新：身份与拓扑全部实测，root 进行中）

- **已回填（MEASURED，2026-09-27，adb 未 root 状态）**：Redmi K70 Pro（23117RK66C/manet）；SM8650 = 1×X4(cpu7, midr 0x410fd821) + 5×A720(cpu2-6, 0x410fd811) + 2×A520(cpu0-1, 0x410fd801)；Android 15 / HyperOS 2.0.208.0.VNMCNXM；kernel 6.1.118-android14-11-ab13320413；BL 已解锁；governor=walt（可用 performance/powersave/schedutil）；cache size 属性高通内核不提供（manifest 记 None）；transport=adb 已接入（AdbExecutor + redmi-k70pro-01 平台配置 + 能力清单入库）。
- **✅ root 完成（2026-09-27，MEASURED）**：KernelSU LKM 成功——`su -c id` = uid=0(context=u:r:ksu:s0)，SELinux Enforcing，slot _b，boot_completed=1；仅刷 init_boot_b，boot/vendor_boot/vbmeta 未动。完整操作手册（含 OTA 重修补与回滚）：`docs/runbooks/redmi-manet-kernelsu-root.md`。镜像归档（不入库）：`~/Downloads/manet-rom/.../images/`（stock/KSU-patched/SHA256SUMS/device-info，校验 OK）。
- **✅ root 后能力实测（2026-09-27/28）**：`perf_event_paranoid=-1`，
  `armv8_pmuv3`、`cs_etm` 与 `llcc-pmu(type=9)` 节点已注册；用户态
  `config=0x1000` smoke 已确认可打开并对 CPU7 streaming-read 稳定响应，
  10 对 idle/load 完全分离（详见
  `docs/reviews/2026-09-27-sm8650-llcc-pmu-smoke.md`）。这仍不证明 occupancy、
  slice 归属或容量。walt→performance→walt sysfs 往返成功；thermal 16+
  冷却设备可读；midr root 通道确认 X4。
- **后续接线项（另行任务）**：runner 的 AdbExecutor 以 shell(uid 2000)
  运行。显式传 `type=8` 后，core PMU 可由 shell 正常计数；LLCC 有效事件
  `type=9/config=0x1000` 则在 `perf_event_open` 返回 EACCES，root 正控通过。
  因此 core PMU 应留在普通 probe 内，只有 LLCC sidecar 声明并审计 `su -c`
  特权边界；禁止把整个通用 probe 路径静默提权。环境事务的 Android
  controller 已有 su 通道。

## OI-3 x86 服务器信息回填与探测脚本评审（2026-09-24 更新：信息已回填，仅剩脚本评审）

- **已回填（MEASURED，2026-09-24）**：Ubuntu 24.04.4 LTS；kernel 7.0.0-30-generic；perf 7.0.12；`perf_event_paranoid=4`（非特权 perf 封锁，sudo 可用）；dmesg 确认 SPR 完整 PMU：Sapphire Rapids events、full-width counters、PEBS fmt4+-baseline、32-deep LBR、AnyThread deprecated；NMI watchdog 常驻占 1 个 hw-PMU 计数器；RAPL PMU（package/dram 功耗）。
- **方法学提示**：perf 采集一律走 sudo；全核计数时注意 NMI watchdog 占用的计数器缺口；PEBS/LBR 可用意味着 frontend/分支分析可做 precise 采样。
- **脚本评审（状态更新 2026-09-25）**：用户外部 x86 探测脚本始终未提供；linux-x86_64 平台已改经本仓 runner（ssh transport + taskset 控制）接入并产出首份 sweep（`data/public/runs/20260924T174644Z-ptr-chase-cache-sweep`）。外部脚本若日后提供仍可按三维度评审；平台接入项视为完成。

## OI-4 SM8550 历史数据溯源（2026-09-27 部分关闭）

- **已解决**：`sm8650-x4.txt` / `sm8650-a510.txt` 溯源 = **`redmi-k70pro-01`（本机）**——该文件用 `taskset 80`（CPU7）测量，与 2026-09-27 实测拓扑 CPU7=X4 prime 精确吻合，SoC 型号 SM8650 一致。证据等级 DERIVED（推断，三证据链一致）；数据文件保持原标注。
- **仍待**：`sm8550-cacheline.txt` 来源仍 UNKNOWN（本机为 SM8650，8550 数据来自他机）——保持 UNKNOWN 标注，不用于校准。
- **同时确认**：`sm8650-x4.txt` / `sm8650-a510.txt` 对应哪台设备、测试日期与系统状态。

## OI-5 M4 Pro PMU 能力实测（2026-09-24 关闭：计时器与 QoS 分流已实测；PMC 转为环境决策）

- **计时器（MEASURED，`probes/platform/timer_resolution`）**：timebase 125/3 → 1 tick = 41.67ns；相邻调用 74.8% 零间隔；有效分辨率 41.67ns；调用开销 4.06ns。含义：单次计时区间下限 ~42ns，L1 级测量须 ≥10^5 loads/区间（现有探针远超，量化噪声可平均掉）。
- **QoS 分流（MEASURED，`probes/platform/qos_steering`）**：延迟链吞吐双峰——USER_INTERACTIVE 1.59 ns/iter、DEFAULT 1.61、BACKGROUND 6.07（比值 3.8×），重复设置可复现 → QoS→P/E 分流可靠生效。BACKGROUND 可作为 E-core 测量的调度手段（macOS 无精确绑核的替代）。注意：绝对值含 volatile-store 转发开销，本探针证明的是分流双峰性，非核间 IPC。
- **残余（非阻塞，环境决策）**：xctrace/Instruments 未安装（xcrun 确认无 Xcode）。per-thread KPC 计数器（IPC/分支等）非计时法微基准的刚需；如分支 probe 或 throughput 校准需要，安装 Xcode 后验证。powermetrics 作 cluster 级采样补充。

## OI-6 D9300 实机信息回填

- **阻塞**：§2.5 画像、严格校准实验设计。
- **回填**：机型（vivo X100 / iQOO Neo9 Pro / OPPO Find X7 / 其他）、root 状态、adb 可达性、kernel 版本。
- **方法学提醒**：全大核无小核兜底，thermal 压力大于大小核机型，校准实验需预留温控与间歇。

## OI-7 外部参考材料处置（新增，2026-09-23；2026-09-23 二次更新：已迁至仓库外）

- **位置**：`../cpu-uarch-ref/`（workspace 级，仓库外，已加只读约束）。含两个子目录：`cpu-cache-demo-code/`（历史 demo）与 `cpu微架构材料/`。
- **内容**：CPUSUIT 探针工程（含 xbyak_aarch64 第三方库）+ Michael 自己的 gem5 DDR 时延分析 + DDR 时序分析 + 未知作者 PPTX。
- **初步评估**（详见 req-v0.3 置信度注记）：CPUSUIT 覆盖度（ROB 探测、port 分析等）对 probes/ 规划有 HIGH 参考价值；gem5 DDR 分析为本人作品，可评估后移入 `docs/`（注意其绑定 gem5 commit 3dc9dcc）。
- **处置待决策**：逐文件确认作者与许可证 → 决定 移入 docs / 登记为方法学参考 / 忽略。
- **状态更新（2026-09-30，ROB 项目源码通读）**：CPUSUIT 作者身份确认 = **仓库所有者本人**（`include/probe_type.h` 等头文件署名 Copyright(c) Michael Yao + Apache-2.0 头注；src 多数文件无头注、根目录无 LICENSE）——reference-materials.md 已更正。ROB 深析项目已按方法学借鉴执行（报告 §0 + probes README 借鉴登记）；代码复用范围待所有者拍板。PPTX 作者仍未知，维持原处置。

## OI-10 改进项登记（2026-09-26，源自 ptr-chase-pipeline-analysis §7.2）

> 任务书"非目标"节的排除项必须有 OI 落点——排除不等于丢弃。以下五项各有归属主题，触发条件满足时转为任务书。
> **状态（2026-09-26）**：五项均 ⬜ 待办，触发条件未满足；与 `ptr-chase-pipeline-analysis.md` §7.2 状态列联动（该表为信息展示，本表为跟踪面）。§7.2 的 #1（M4 清单）/#2（事务接线）已完成，闭环记录见 CHANGELOG 与 run `20260926T145530Z`，不入本表。

| 项 | 内容 | 归属/触发条件 | 状态（2026-09-26） |
|---|---|---|---|
| 适配器注册表 | `engine.py` 的 `_ADAPTERS` 硬编码 ptr_chase，加探针要改引擎 | 触发：core/branch/TLB 任一**新探针任务**立项时并入 | ⬜ 待办 |
| SSH 会话复用 | `ssh.py` 每条命令一个 TCP+认证会话 | 触发：单 run 命令数显著放大（多核型 sweep/更多重复）或 adb 通道接入时 | ⬜ 待办 |
| 测量期频率多次采样 | freq_snapshot 目前是 case 前后瞬时值；powermetrics 并发采样（macOS）未做 | 触发：锁频后数据仍漂移、或 T1 ±1 cycle 校准启动时 | ⬜ 待办（锁频已落地，主问题缓解；多次采样仍待） |
| 跨 run 汇总报告 | analysis/ 只支持单 run | 触发：同一实验第二次复测入库后（漂移分析需求自然出现） | ⬜ 待办 |
| p95/p99 尾部统计 | n=5 时无意义（插值≈max） | 触发：repetitions ≥20 的实验出现时 | ⬜ 待办 |

## OI-11 LLCC 深度探测与 ptr_chase 升级（2026-09-27 登记，源自 SM8650 SLC 方法学讨论）

> **2026-09-27 证据重审**：旧“12 MiB CPU 有效容量”“X4/A520 静态保护
> 份额”“LLCC PMU 零事件”均重新开放，详见
> `docs/reviews/2026-09-27-sm8650-cache-evidence-reassessment.md`。固定
> `warmup=200000` 在 64 B stride 下只覆盖约 12.2 MiB，恰与原结论同量级；
> 本机无 hugetlb pool 但支持 THP，不能把 4 KiB/TLB 混杂写成永久状态。
> 新门禁为：测量协议修复 → X4 2 MiB 私有 L2 校准 → core/LLCC PMU →
> L3/LLCC 与干扰实验。在私有 L2 可识别前停止外层 cache 容量定案。
>
> **2026-09-28 复审**："校准 + 正向控制 + 细扫"链路中的容量裁定被外部
> 评审驳回（预注册门禁事后改写、排他性机制表述、L2 几何论证错误），
> 两份评审文档顶部已加更正块。**X4 私有 L2 门禁重新打开，外层
> L3/LLCC 容量定案维持封锁**；数据与工程链路保留为实验档案。该门禁
> 不扩散到正交主题：分支预测、TLB、前端、执行端口、MLP、跨核迁移等
> 不依赖精确 L2 容量的探测可继续。cache 相关实验若把 L2 容量仅作为
> 区间/潜变量，也可在明确依赖和禁止唯一命名容量 knee 的前提下继续。

| 项 | 内容 | 归属/触发条件 | 状态 |
|---|---|---|---|
| P0 warmup/页策略正确性 | `warmup_passes` 完整遍历；THP 请求与 smaps 实际 backing 分开记录 | 所有新 SM8650 容量实验的前置门禁 | ✅ 完成（`a8a6ac6`、`1532274`） |
| P0 受控安静态 v2 | 显式 profile；逐 policy 精确恢复；Android 状态 before/after；前后门禁 fail-closed | 新 SM8650 校准实验前置；临时 control-path smoke 只验控制链，不产容量数据 | ✅ 完成（`a1f52b6`–`0895270`、`d405460`；验收见 runbook §7） |
| P0 X4 私有 L2 校准 | 512 KiB–3 MiB 细扫，4 KiB/实际 THP 对照，≥10 次新分配，联合 L2 refill/DTLB | 协议修复后第一项实机实验；失败则停止外层解读 | ✅ 已执行（`9f7441b`，run `20260927T175218Z/175405Z`）；裁定 **OPEN/INCONCLUSIVE**（后续闭环尝试被评审驳回，维持开放） |
| P0' PMU 事件语义正向控制 | L1D/L2D access/refill + L3 refill + DTLB walk 的地板/规模双向验证 | 校准裁定遗留（事件语义未证不可排因）；细扫前置门禁 | ⚠️ 数据保留（`219bcbb`）：计数相干性成立；**容量推断门禁 FAILED 维持**（预注册 8 MiB 预期未达，事后改写已撤销，见评审更正块） |
| P0″ demand/prefetch 专用事件复测 | `L1D/L2D_CACHE_MISS/HWPRF` + `MEM_ACCESS_RD` 同窗；≥4 seed × 短/长训练 × base/THP 正交；探针加可记录 seed；分析器入库 | P0' 门禁失败后唯一认可的容量推断路径；512→640 机制（预取崩塌 vs 置换共振）判别 | ✅ base 矩阵完成（`7c00d6d`/`32207d2`/`867d9b1`/`5c15287`/`6ac1da5`，评审 `docs/reviews/2026-09-28-sm8650-x4-p0prime.md`）：**512→640 跳变与 L1 预取活动/覆盖代理崩塌稳定伴生**（高置信，4 seed × 双训练一致；上游原因未鉴定）；**容量信号不容许（跨 seed/训练不稳）→ 维持 OPEN/INCONCLUSIVE**；2 MiB（DTS 平台描述）未证实未否决 |
| 动态 cpufreq ceiling drift 与恢复门禁（P0″-THP 收尾，规则 4c） | 2304/3072 KiB 短/长 × 4 seed，THP 请求按实际 backing 分组；短块执行、short/long 分开、条件交错，块前后各放 base 锚点，同步采集 Current HAL 温度与 cooling-device 状态 | 触发条件：后续实验必须依赖 >2 MiB backing 对照，且四 policy 回画像值并稳定 ≥5 分钟（2026-09-28 三次 drift；**根因 OPEN**——不得写成已定案 NSP/thermal，`dumpsys` cached 温度不可当实时值，cdev state 与有效限额非时刻同步，以 `scaling_max_freq` 为唯一有效门禁）；drift 复发则当前块 fail-closed，此前数据由块前后锚点决定去留；只完善 >2MiB 页策略叙述，不改变容量 OPEN 状态 | ⏸ **无限期推迟**（本轮选择 c；run `20260928T122738Z` 归档）：不阻塞正交微架构主题；若触发条件成立，可改选 (a) 新建较低稳定画像或 (b) OEM 策略根因专项调查；LLCC/外层 cache 容量定案仍封锁 |
| P1 PMU 采样通道 | armv8 PMU 与 chase 同步；LLCC `type=9/config=0x1000` 响应性与权限边界已独立验证 | X4 L2 用 shell core PMU 同窗采样；外层 cache 再接最小 root LLCC sidecar；root userspace 路径已通，不触发 LKM | ✅ core 同窗已验证（`04f99b4`；两轮校准 + 正向控制共 35 case 全部 running==enabled）；LLCC sidecar 后置外层阶段（**评审后维持封锁**） |
| P1 细粒度私有 L2 扫描 | 448–800 KiB @ 32/64 KiB + 896–1408 KiB @ 64 KiB；6 cache 事件同窗（计数器预算内） | 正向控制通过（已满足）；目标：L1 崩塌成像 + l2ref 起始沿定位 | ⚠️ 数据保留（`687d09e`，run `20260927T184203Z`）；**裁定驳回**（排他性机制表述、起始沿与逐样本矛盾、几何论证错误——见评审更正块）：512→640 改为"预取覆盖率崩塌强证据（待 P0″ 正式裁定）"；起始沿未成立；2 MiB 未否决、1 MiB 待检 |
| P1 多链带宽模式 | ptr_chase `--chains N`：吞吐 cliff 作为独立物理量（Probe ABI 变更） | latency + PMU 仍不能区分外层结构时单独立项 | ⬜ 待办 |
| P2 逐 rep 双峰检测 | statistics.py 分位数/双峰标记（median-of-5 掩盖双峰，Xeon 有前科） | 触发：P1 多链模式立项时并入 | ⬜ 待办 |
| P2 干扰编排进 spec | cross-core/相机/GPU 条件采用配对或随机交错；相机前后验证 active client | L2/L3/PMU 基线通过后；禁止一次性手跑归因 | ⬜ 待办 |
| LKM-M1 只读 dump | ioremap 0x25000000 读 ATTR/HW_INFO/LB_CNT + kprobe 导 drv_data（不依赖 llcc 符号；kprobe 已注册实证） | 用户态 `config=0x1000` 与 core PMU 均不足后；另需源码/Module.symvers/签名取证 | ⬜ 条件后置 |
| LKM-M2 perfmon 直读 | ioremap 0x24095000 lagg-base 直接读计数器 | 同 LKM-M1 前置；M2 依赖 M1 加载通路验证 | ⬜ 条件后置 |
| LKM-M3 slice 受控实验 | 读写 slice/驱逐实验 | **红线**：仅开发环境，量产机禁写；M1/M2 全通后单独立项 | ⬜ 搁置 |

## OI-12 SM8650 测量 regime 跨日基线移动（2026-09-30 登记，TLB 战役方差表征衍生）

- **背景**：TLB 战役 Phase A 期间，3072 KiB latency 当夜六连测逐 run median ∈ [7.865, 8.561] ns（C=8.014），较昨日 short-base 参照（7.73815 ns，run `20260928T024022Z`）高 +3.6%；512 KiB 同日差 ≤2%。v4.4 锚点判据已改方差表征池宽带（任务书 §6.2.5）吸收该移动，但移动本身**未归因**（候选：3.5h 限额 drift episode 残态、物理页布局日际差、内核状态）——任务书裁定"不重锚、不解释"。footprint 越大跨日摆动越大（512 稳定、3072 移 3.6%、32 MiB 跨块 +58%），任何跨日参照类门禁都须以此摆动量级为校准前提。
- **触发条件（何时回填/升级）**：①后续 Phase 块若再现跨日/跨 session 基线移动 >3%（锚点池带连续触发、或 main 数据跨日断档），升级为 regime 根因调查（候选路径：ftrace `cpu_frequency_limits` 确认限额、THP 状态审计、short-base 同点复测）；②任何新实验任务书拟设跨日参照门时，必须先引用本条方差数据校准，禁止直接照搬 ≤1.2%/≤3% 级经验阈值。
- **证据**：方差表征 6 run（`20260929T235909Z`–`235957Z`，`beb63ef`）；两块 fail-closed 留档（`f93b319`）；任务书 v4.4 §6.2.5；分析器池参照现算（`af3455b`）。
- **状态**：⬜ 观察中（不阻塞 TLB 战役；Phase A 块 3 起按 v4.4 池带执行）。

## OI-13 分析器对非 G0 metric 集主体 run 的适用性扩展（2026-09-30 登记，TLB 战役 Phase C 执行衍生）

- **背景**：`analyze_records` 要求精确 G0 metric 集合（latency + cycles + mem_access_rd + `0x05` + `0x34`），而任务书 §5.2 冻结的 G2 组（不含 mem_access_rd）与 G3 组（含额外 `0x8144`）均不满足——`validate_anchors` 在 ANCHORS_OK 路径上无条件对主体 run 调 `analyze_records`，导致 Phase C 这类非 G0 主体块的锚点判定无法走入库函数路径（Phase C 实际以 §6.2.5 同一规则直接提取复刻执行，见 `docs/reviews/2026-09-30-sm8650-tlb-phase-c.md` §3）。同样受限的还有 `adjudicate_q3` 的 G3 数据消费（其 evidence `data_miss_collinearity_checked` 设计为恒 False）。
- **扩展方向（立项时评审，不在 TLB 战役内改判据/改分析器）**：①`analyze_records` 对超集 metric 集（多出 PMU 指标）放行并派生对应字段（required ⊆ present）；②`validate_anchors` 增加"主体非 G0 时 main_result 跳过或降级"的显式模式（锚点判定与主体分析解耦）；③G2 类缺失 mem_access_rd 的集合是另一层问题（契约有意缺失，不应简单放行——分析器对缺失每一项都要有命名的降级语义）。
- **触发条件**：下一个需要非 G0 事件组做正式块级判定的实验任务立项时（如 LLCC/cache 阶段的异构事件组），必须先关闭本项，禁止再用"直接提取复刻"绕行。
- **状态**：⬜ 待办（不阻塞 TLB 战役：Phase C 已按披露的方法学结案）。

## OI-14 SM8650 TLB 战役后置项（2026-09-30 登记，任务书 §11 落位 + 战役衍生）

> 战役终审：`docs/reviews/2026-09-28-sm8650-tlb-hierarchy.md`。分支
> `codex/sm8650-tlb-hierarchy` 退役后本表为唯一跟踪面。

| 项 | 内容 | 归属/触发条件 | 状态 |
|---|---|---|---|
| TRM r0p3 vs Issue 05 逐字核对 | 任务书事件文本/MMU 结构逐字核自 Issue 05 PDF（`102484_0002_05_en`）；在线 r0p3 未核对——有差异以 r0p3 为准出修订 | 触发：下次可访问 Arm 文档站时；新引用 X4 事件文本前 | ⬜ 待办 |
| Explore 遍历模板细节 | `Probes.h` TestTraversal 模板与 warmup 处理未读；§6.5 对照仅以 `ProbeLatency.cpp` 已读段落为准 | 触发：需引用其遍历/warmup 细节时先读源码 | ⬜ 待办 |
| Arm PDF 物理位置 | `x4trm.pdf`（Issue 05）与 Software Optimization Guide（Issue 3.0）+ 提取文本在仓外 `cpu-uarch-ref/arm-docs/`；Arm 版权禁止复制 | 永久不迁移入库；引用只写文档号/修订/章节 | ✅ 已落位（持续遵守） |
| 运行时 CPU 证据 | 探针无 `sched_getcpu()` 字段；affinity 请求 ≠ 测量期执行位置（Gate 0 契约 #2 的登记缺口） | 触发：需要执行位置证据时另立小项（probe ABI 小改 + 契约测试 + 重新部署） | ⬜ 待办 |
| 路线 B（可控 VA 布局） | Q1 宽饱和区的布局排歧（PFN 着色 vs 渐进饱和）；Explore `kRandomTLBOffset` 族为参考实现 | 触发：Q1 区间解释需要布局排歧时立项（probe + schema + 契约测试全链） | ⬜ 条件后置 |
| 线性/逆序遍历建链 | 随机环结果的顺序依赖嫌疑排查手段；probe ABI 变更 | 触发：出现顺序依赖嫌疑时立项 | ⬜ 条件后置 |
| perf/simpleperf 同窗差分 | CLI 窗 ≠ 探针内窗，需专门同窗机制；可选交叉验证 | 触发：探针内计数链出现可疑证据时 | ⬜ 可选 |
| perf 二进制谱系 | 设备手工部署的静态 perf 未入 artifact manifest | 触发：使用前先 `sha256sum` 登记 | ⬜ 使用时执行 |
| Q2b 可选增强 | `0x2d`（QUALIFIED）在 onset 区间 [2560,3072] 的 unified refill 曲线未采（Phase C 只用了 G2/G3） | 触发：Q2c 授权议程重启时（任务书 §3.3 门槛满足后） | ⬜ 条件后置 |
| 固定开销标签 | cycles 与 dtlb_walk 的绝对密度"含固定开销"（§5.3 判定：512K 冷启动 ≈8 walks/窗、cycles ≈55k cycles/窗） | 触发：任何复用本战役密度数据的分析须先读 Gate 1 评审 §4；转折判定用跨长度斜率 | ✅ 持续约束（Gate 1 评审已载） |
| Q4 达成率方法学 | mixed 达成率 2304=12.5%、3072=37.5%（16 MiB=87.5% 覆盖）；比较级证据需预设更大尝试预算或更强达成手段 | 触发：未来 THP 类对照设计时引用为预期达成率 | ✅ 已登记（本行即参照） |
| 最小点 R_0x34 反常 | Phase A/B 粗扫/致密的最小页数点（32/48 页）R_0x34 反常高于 64–1024 页段（0.45–0.82 vs 0.05–0.31/1k）；onset 算法按地板处理，判读不受其影响 | 触发：未来以 walk 地板绝对水平为证据时先解释该最小点抬升（候选：冷启动摊薄、小 footprint 下每页重复访问频率）；当前仅登记观察，不影响 Q2a 终态 | ⬜ 观察项 |

## REV-TLB-R2-M0-20260930 批次复审遗留（M0-1/2）

- **归属**：SM8650 TLB r2 的 M0-1/M0-2；评审 [M0 批次复审](reviews/2026-09-30-sm8650-tlb-r2-m0-review.md)，输入提交 adaac4d。
- **状态**：3e539c6 已修原目标编译、判据/锚点/Markdown 异常；本会话 2026-10-01 已复核。group 内契约分组已修，二次聚合/图表语义仍有遗留，见下方 REV-M0-BATCH。M0-6 可接受；OI-13 保持未关闭，不构成双独立评审通过。
- **关闭前置**：C1 Android/Linux 两处 PageBackingClass 类型限定与正常目标构建；C2 指标 coverage/联合样本集合；C3 knee floor 与 walk_samples 完整入口守卫；C4 锚点必要事件守卫；C5 Markdown/main 图表 nullable 兼容（组合现有图表测试 18 通过、1 error）。修复后以缺项/超集/部分覆盖的集成回归及旧 runs 差分重放验收。
- **交付口径**：C6 extra 事件在原始 record 与 AnalysisResult 的保留范围、OI-13 状态/docstring；M0-1 当前仅页策略提取子项，RAII/合法地址池/timer/CPU 身份仍按任务书跟踪。
- **正式测量前冻结**：C7 B1/B2 选择规则及 pilot 隔离、offset 节点地址实现与 realized geometry；分别归属 Phase B 与 M0-4/Phase A。
- **首轮快照证据（adaac4d，最新结果见下方收口复核）**：macOS build、analysis 140、runner 154、CTest 18 通过；NDK 目标语法检查失败；49 runs/291 records 重放中 42 原可处理 runs 不变，7 非 G0 为预期接纳扩展；完整数据四图不变，缺指标图表路径失败。Linux/Android 运行、raw 哈希重验和 main 合并未执行。
- **触发条件**：下一次 M0-1/M0-2 子项验收前关闭 C1–C6；Phase A/B 正式采样前冻结 C7；科学问题终态不代替工程缺陷关闭。

## REV-M0-BATCH-20260930 两层复审遗留（2026-10-01 更新）

- **归属**：r2 数据管道 M0-3/4 + main 图表；[原两层评审](reviews/2026-10-01-m0-two-layer-review.md)、[46b1daa 收口复核](reviews/2026-10-01-m0-closure-review.md)。最新代码基线 m0b 2d48704、main 798f774；作者回执 r2 46b1daa（上板清单提交后 HEAD ae8532d）。
- **已关闭**：MB-01 GROUP read 实际字节长度；MB-02 失败项名称/spec 映射；MB-04 cohort/图表非 legacy identity 命名拒绝；MB-08 v1.3 B1→B2 三条件合格门口径满足（阈值/证据仍在正式矩阵前冻结）。
- **P1 未关闭**：MB-03 case.params 中 chains 等请求虽留存，adapter/kernel 未消费，同 buffer/control 的 K=1/2 argv 相同；新形状仍先读 buffer_kb/stride，通用 ID 又拒绝 PMU 列表；未知 swept 参数仍可进 ID 后消失。MB-07 缺点审计与空系列诊断已修，但报告沿用固定终态却宣称按剩余点重判，删除 onset 区间仍输出原 INTERVAL_IDENTIFIED。
- **P2/后置**：MB-05 FD 不可复制及 move 所有权已验证，snapshot/window 差分与有效性待交付；MB-06 descriptor requested→canonical→执行→realized→identity/类型/schema 的最小契约待交付。适用触发为首个依赖该契约的 Phase A/K 链/Phase B 实验，不能统一推到 Phase B。MB-02 旧头注释及任务书的事件 ID 口径仍需与位置映射实现对齐。
- **最新证据**：m0b analysis 149、runner 158、preset build/CTest 19；main analysis 167；main/r2 图表 overlay 21/21；NDK 两源码目标语法检查通过。生产 PerfWindow 头文件 syscall 注入通过读长/错误拒绝/映射/move 检查，无内核执行。m0b 对3e539c6：49 runs/291 records 的规范化分析输出与 cohort 结果一致；r2 对a104dbf：42原可处理 runs 不变、7预期接纳扩展；完整旧数据四图+报告为5/5文件字节一致。
- **出口裁定**：当前代码侧未通过；原回执保留，复核文档列出最小修复与集成验证。MB-03/07清零后再做两层合并/main组合验证；M0-3/4仅组件/扩展缝子项不能代替完整能力验收。
- **处置更新（2026-10-01 作者）**：MB-03/07 收口修复已交付——m0b `ee736ed`（消费契约 + 通用 ID 解耦）、main `9093f4a`（缺点报告标注不支持区间）；回执 `docs/reviews/2026-10-01-m0-closure-response.md`（含评审反例复现与验收场景端到端证据）。待评审复核清零；清零后执行两层合并/main 组合验证。MB-05（首个短窗 pilot 前）/MB-06（首个依赖新条件的 Phase A/K 链采样前）时点维持 §11 登记。
- **时序决策（2026-10-07 用户拍板）**：评审复核（MB-03/07 清零）**延后**，与 M0-5 pilot 上板采数并行；m0b→r2 两层集成/main 组合验证仍按评审明令排在清零之后（顺序不变，只把评审从关键路径上挪开）。**风险登记**：若评审对 MB-03 消费契约打回，M0-4b 的 tlb_set deriver/adapter（建于该契约通道）与三份 pilot 配置在波及面上——pilot 数据判读前必须先对评审结论做一次波及评估；概率低（修复按评审反例逐条处置并附复现证据）但不为零。触发：评审结论到达时第一步执行。
- **MB-06/OI-13 关闭包（2026-10-07 交付）**：MB-06 descriptor 最小契约已关闭（类型规范身份 + requested→realized 一致性，m0b `0b8c8b1`）；OI-13 分析侧关闭，余 merge 时 main 图表测试口径更新（§11-9 预登记）；Phase A 矩阵冻结（任务书 §5.5）。送审包 `docs/reviews/2026-10-07-mb06-oi13-phase-a-package.md`——**Phase A 配置写就的等待前置 = 该包判据确认 + MB-03/07 清零 + 两层集成**。
- **完整 M0 前置**：Linux/SM8650执行证据、短窗能力/窗口有效性、M0-5 pilot→独立校准冻结→锚点池。OI-13仍部分关闭；所有新条件在正式采样前完成最小证据契约。

## SMOKE-20261001 冒烟执行衍生（2026-10-01 登记，runbook §6）

- **背景**：上板前清单首板执行完毕（环境 1.1–1.9 全过，S1–S5 全过，S6 跳过；细节见 `docs/runbooks/2026-10-01-sm8650-tlb-r2-preboard.md` §6）。门控定型：预注册 S1 判据满足，**0x2f 批准升级三事件版**（0x05+0x2d+0x2f 同窗）。

| 项 | 内容 | 归属/触发条件 | 状态 |
|---|---|---|---|
| android-arm64-cross CMake preset 缺失 | r2 `CMakePresets.json` 无 android 项，证据管道探针（主线纪律）无标准构建路径；冒烟已绕开 cmake 直编 | 触发：Phase A 正式采数前（建 preset，或拍板长期直编 + runbook 登记） | ⬜ 待办 |
| 0x2d 判据口径（总竞争条目数） | 冒烟实测 0x2d 跳变点提前至 w=8（filler 512 下总竞争条目 ≠ w）；naive "w≤≈0 才跳" 预期不成立，Q-B 判据须按总竞争条目数口径写 | 触发：M0-5 pilot 判据冻结前（与 MB-08 阈值冻结联动） | ⬜ 待办 |
| PerfWindow 真机 GROUP read 首验 | S6 按 runbook 跳过；生产 PerfWindow 的 nr/ena/run/values 布局真机复核未做 | 触发：M0-3/4 代码侧出口验收证据（评审方闭环清单） | ⬜ 待办 |
| runbook §2 与现状不符 | ① .c 须用 clang（clang++ 触发 -Werror=deprecated）；② android-arm64 preset 不存在 | — | ✅ 已关闭（runbook 本次修订） |

## REV-MB06-PHASE-A-20261007 送审包复核遗留

- **归属/输入**：SM8650 TLB r2；r2 `d086173`、m0b `0b8c8b1`、main `9093f4a`；[正式复核](reviews/2026-10-07-mb06-oi13-phase-a-review.md)。本段为评审方更新，历史作者回执保留；最新出口裁定以本段为准。
- **可关闭**：MB-03 原消费/通用 ID 缺陷、MB-07 原缺点报告误称重判缺陷。本轮针对性路径 4/4、main+m0b 图表 24/24；缺口反例受控披露，完整历史四图+报告 5/5 字节一致。
- **P1 / Phase A 正式采样前关闭**：PA-01 完整残差身份导出及二次聚合守卫；PA-02 请求模式核验、关键参数/事件与 realized descriptor 持久化；PA-03 实际跨区域取样与 active-domain 审计；PA-04 A1 冲突分区可识别性证明、隔离/全域配对及扫描矩阵；PA-05 A3 估计量重订、N-set 实现与阈值两侧覆盖，收紧“结构验证通过”命名。
- **P2/口径及触发**：PA-06 OI-13 保持部分关闭，extras 派生/消费在首个正式新事件组使用前完成或正式拆分跟踪；旧“图表 1 failure”叙述移除。PA-07 递归 typed canonical identity 在结构化 descriptor 正式使用前完成。PA-08 ProbeAdapter 第三参 Protocol 在新 ROB/ALU/FPU adapter 接入前同步。PA-09 3/轮的重复汇总/边际/删失/种子计数规则在正式矩阵前冻结。
- **出口裁定**：本包不通过，Phase A 不冻结；MB-03/07 清零不代替本轮新 P1 清零。两层集成可用于修复和软件组合验证，不能视为正式矩阵放行。MB-04 对旧显式身份的既有关闭保留，但新增残差身份已使守卫范围不足（PA-01）。
- **新证据边界**：m0b runner182/analysis153/CTest19、main analysis170；旧战役51 runs/295 records规范化分析与cohort一致（完整AnalysisResult新增identity，不能无条件称逐字相同）；生产选址函数16/16合成布局只访问region0；pilot结构化记录0/14含set_domain。NDK仅目标语法检查，无adb/手机执行；上板验证由其他Agent负责。本次仅提交评审产物，不代修生产代码。

## REV-PA-RESPONSE-20261007 v1.6 修复回执复核

- **输入/归属**：SM8650 TLB r2 `dbd9831`、m0b `4655dd3`、main `9093f4a`；[最新复核](reviews/2026-10-07-pa01-05-rereview.md)。旧回执保留，本段为当前出口裁定。
- **已修子项**：H身份出口及cohort/图表命名拒绝；请求形状/seed漂移/缺事件拒绝；单目标16/16四区域配额；PA-07递归规范形；PA-08Protocol同步。MB-03/07历史关闭维持，OI-13仍部分关闭。
- **P1 / 正式采样前关闭**：RPA-01 A3超过256的N不可生成、filler不可实现、每轮仅W访问导致目标工作集未测；RPA-02按region ID累加N-set/T2审计并按实际访问核对；RPA-03逐进程realized持久化/混域处理/ParseError守卫；RPA-04完整残差身份出口及二次聚合；RPA-05A1 scope特定门、target/seed真实矩阵、实际高字段预测分区和量化判据。
- **行动链**：先修估计量/链长与审计→runner每样本闭环→完整身份→实际配置plan与预注册→双层/main整树回归→重送审→上板Agent做NDK完整构建/部署/新几何pilot→独立正式矩阵。可连续推进；正式后置项须保留本表触发条件。
- **证据**：187/155/19、NDK语法检查、main组合24/24、51runs/295records规范化统计与cohort一致；合成N=96/256仅访问160节点，审计误报384/1024区域；三样本后两次fallback仍ok且record标签取首样本。无adb/手机验证。详细日志与脚本见评审。
- **出口**：当前代码侧不通过，Phase A v1.6不冻结；不能将单目标配额/H专有身份的关闭扩展成五项全关闭。


## REV-RPA-V2-20261007 v1.7 收口复核

- **输入/归属**：r2 `30341d6` 回执、任务书 v1.7、m0b `95fa2a9`；[复核裁定](reviews/2026-10-07-rpa01-05-v2-review.md)。**当前不通过，Phase A 正式冻结未完成。**
- **已关闭子项**：两文件检查确认生产共享头为权威且无重复实现；RPA-02 region ID 累加/N-set/T2/隔离/scatter 的合成软件审计；RPA-03 runner 逐次 realized 保存、混域标注及结构化失败。A1 消费端仍见下项。
- **P1 / 正式矩阵前关闭**：RV2-01 有效预热条件身份与下游一致性（真实 plan 同测量 loads、异 warmup_passes 可生成，当前 cohort/图表仍合并）；RV2-02 独立 CALIBRATION/阈值确定与冻结合同、有限网格/删失/L3 语义、A1 实际 VA/混域/purity 门消费金样；RV2-03 作者提交未提交的 CTest 金样注册并重跑干净新快照。具体关闭条件见复核，评审不代修生产代码或代提交他人修改。
- **正式后置 A3——整体 translation reach / 全链遍历探针模式**：接受本批次不做 A3；触发 = A1 判出 H* 后单独立项。交付 = 全链遍历模式设计、地址访问/filler 预算/计数分母可执行性推演、每点 plan、实际访问追踪金样。N≤256 保留协议不构成 reach 完成。原送审树未有专门条目，本次评审在此补登记，非追认 `30341d6` 已登记。
- **P2 / 同批口径修正**：golden 跨界场景的“64MiB 区域必不跨256MiB”注释与 purity 契约矛盾；补实际输出→消费边界金样。回执未附所称20万随机基址脚本，确定性跨界反例足以支持保守 purity 门。
- **证据/边界**：runner192/analysis158、main图表组合24/24；51runs/295records统计/cohort规范化一致（identity元数据除外），旧 warmup_passes 全2；干净95fa快照CTest19/19，新 golden 单独编译运行通过，20/20注册在他人未提交diff；NDK三源码syntax-only通过，无adb/手机执行。Android完整构建/部署/新几何标定归上板Agent。
- **行动链**：预热身份与消费者→标定合同/A1门金样→作者提交CTest注册并锁新基线→全量软件与两层/main集成复核→上板Agent独立标定/冻结→正式矩阵；A3保持条件后置。


## REV-RPA-ROUND3-20261008 v1.8 收口复核

- **输入/归属**：r2回执 `1b47948`、任务书v1.8、m0b `5ccb841`、main `2fa8d5d`；[第三轮复核](reviews/2026-10-08-rpa-round3-review.md)。本段为最新裁定，前轮记录保留作历史。
- **已关闭**：RV2-01真实plan预热2/4差异在cohort/main图表命名拒绝，51runs统计/cohort与实际四图+报告兼容；RV2-03金样CTest注册已提交，干净5ccb841快照20/20。既有RPA-02收集器、RPA-03runner逐样本闭环关闭维持。
- **未关闭 / P1（RV2-02，Phase A正式矩阵前）**：R3-A收集假设C/硬件模型T混淆，使C=T=H3/H4的单set真值被预测为四set；R3-B平台检查恒不拒绝、左/右删失与单点被升格sharp；R3-C隔离跨高字段仍放行、审计/覆盖门和records→完整H*路径未闭合（空L3也consistent）；R3-D数值选择仍为“复核并冻结”，缺具体决策程序。逐项关闭条件和可复现反例见复核，不要求评审方代给阈值。
- **P2/触发**：`_residual_digest`旧digest恒None的陈旧docstring与金样“64MiB必不跨256MiB”注释随本批修正；main整曲线首次承载非legacy条件之前，验证跨buffer的条件标签/分系列，不能把旧名单兼容扩展为任意新实验图表已合格。
- **证据**：m0b192/169、main171、main/m0b图表组合25/25、干净CTest20/20、NDK三源码syntax-only；51runs/295records规范化统计/cohort一致，实际B/T与4SVG+report内容一致。生产头整数VA金样独立验证4×4索引模型；所有曲线反例为合成输入，不是手机测量。
- **后置与出口**：A3条件后置沿用REV-RPA-V2的专门登记；当前本包不通过，v1.8正式冻结不确认。先修A1数学/分类→组合必经门与矩阵覆盖→固定标定决策合同→新基线软件及整树集成复核→上板Agent独立标定/冻结→正式矩阵。无adb或设备执行，本评审不代修/代提交生产代码。


## REV-RV2-02-ROUND4-20261008 v1.8.1 复核

- **输入/归属**：r2回执 `24a919c`、任务书声明v1.8.1、m0b `fa663f5`、main `2fa8d5d`；[第四轮复核](reviews/2026-10-08-rv2-02-round4-review.md)。**当前不通过，RV2-02未关闭，正式冻结未确认。** 先前评审保留作历史，本段为最新裁定。
- **关闭/接受**：R3-A双假设C/M预测，生产共享头16对关系与匹配H3/H4正例通过；R3-B弱平台/右删失子项；R3-C全scope purity拒绝与空L3拒绝子项；R3-D具体网格/STOP决策函数已交付。RV2-01/03保持关闭。
- **P1 / Phase A正式矩阵前关闭**：R4-B无低侧曲线仍sharp onset=6并进入supported；R4-C缺scope1仍supported、L3只有一个target仍consistent、审计维数/总和/实际高字段与records→L1/L2/L3→H*必经路径未闭合；R4-D冻结值2.0未被正式分类器消费（仍读3.0），冻结配置/锚定与任务书正文未同步。逐项关闭条件见复核，均延续上轮合同。
- **P2/触发**：随行动方下轮修复调整A1测试入口位置（直接模块14项、loader16项）与回执旧169计数；平台点过滤低于on造成选择偏差，随分类契约修订、最迟扩展W网格前明确；上轮残余注释/首次非legacy整曲线标签事项继续原触发条件，不丢弃。
- **证据/边界**：analysis174/174、A1 loader16/16、C/M整数VA16/16、旧51runs/295records规范化统计/cohort一致、main图表组合25/25；本轮未重跑runner/CTest/NDK/完整旧图渲染，生产差分仅两个A1 Python文件。全部新增反例为合成软件验证，无adb/手机执行。
- **行动链**：左删失传播→完整record入口/矩阵覆盖→冻结配置贯穿与正文同步→新基线整树软件验证/重送审→上板Agent独立标定冻结→正式矩阵。Android完整交叉构建/部署及设备验证归上板Agent；A3继续按已登记条件后置。本轮只提交自有评审文档、脚本、证据与本段台账。


## REV-RPA-R5-20261008 第五轮复核

- **输入/归属**：r2回执 `ecbfefc`、复核时r2 `ac7ffc7`（仅追加术语）、m0b `1e5e99d`、main `2fa8d5d`；[第五轮复核](reviews/2026-10-08-r5-review.md)。**本包不通过，RV2-02未清零，正式冻结不确认。**
- **关闭/接受**：R4-B左删失及其supported传播已修；缺scope1、L3空/单target数量不足、STOP未冻结拒跑的helper子项通过；分类器直接on参数有效。RV2-01/03、R3-A保持关闭。
- **P1 / Phase A正式矩阵前关闭**：R5-T顶层只读取/回报on=2.0，却未传入adjudicate_h/classify_onset（实际默认3.0）；R5-C键仅H/scope/W，seed/target记录最后写覆盖，完整128条输入交换L1/L2顺序会从全suspect变全supported，L3调用0次，L2未比较；覆盖/有效样本/请求-realized审计剩余合同继续R3-C；R5-D§5.5与冻结配置/代码/标定数据锚定仍未同步。逐项关闭条件见复核。
- **过程口径更正**：覆盖强制和全链入口已在第三轮 `b3ace66` R3-C明确要求，前一轮v1.7也已要求实际A1消费者；本轮不接受“第四轮才新增要求”的分类。第六条接缝门方向接受，但需真正运行成功的全链正例、冲突seed/target、缺层及置换不变性负样本。
- **P2/触发**：随下一次送审修正回执A1金样22→21；测试入口位置、平台点过滤选择偏差、旧注释与首次非legacy整曲线标签事项保留原触发条件。
- **证据/边界**：analysis179/179、A1 loader21/21；真实三层plan48/48/32经fake runner生成128条ok records、1280个合成观测，未运行手机进程；原阈值接线/三层组合反例稳定复现。生产差分仅A1 Python两文件，本轮未重复runner/CTest/NDK/旧图渲染，无adb/设备验证。
- **行动链**：冻结配置逐层传递→完整条件身份与L1/L2/L3判定→fake runner端到端正负与输入置换测试→正文/冻结审计产物→新基线回归重送审→整树集成→上板Agent独立标定/正式矩阵；A3保持既有条件后置。本评审只提交自有复核产物与本段台账。


## REV-RPA-R6-20261008 第六轮复核

- **输入/归属**：r2 `6a45a93`、任务书声明v1.8.2、m0b `3c4b507`、main `2fa8d5d`；[第六轮复核](reviews/2026-10-08-r6-review.md)。**不通过，RV2-02未清零，正式冻结不确认。**
- **关闭/接受**：R5-T阈值逐层参数流转已修，on2/3及调用kwargs核验通过；R5-D入口段更新接受，冻结产物/旧段仍待对齐；历史分类更正接受。RV2-01/03、R3-A、R4-B保持关闭。
- **P1 / Phase A正式矩阵前关闭**：R6-A按set_target字段存在性分层，真实三份计划全有该字段，128条adapter/engine ok记录的L1/L2全域点被送L3，入口missing scopes[-1]；L1/L3有8个完全相同params的case，需明确层角色/来源和重叠/重复策略。R6-B缺L3仍unique、四target全suspect也unique，W8/12不可能满足完整onset平台条件，需预注册两点比较量/容差并强制准确覆盖。R6-C整份classes含platform_median被逐字比较，同sharp/onset8、平台差0.1即reproducible=False，不符两seed onset一致合同。
- **继承关闭条件**：R3-C/R5-C的W/有效样本/请求-realized审计及每case实际hi责任继续跟踪；R5-D的冻结配置/代码/数据锚定及§5.5数值选择合同未完成。随完整消费者修订一起收口，不改写历史已关闭项。
- **P2/触发**：本轮置换金样实际24条/H1/无L3，回执128条逐字节声明须据真实正例修正；字典相等不等于未排序JSON字节相等，序列化口径随下一次送审固定。正文复制段/版本前缀、测试入口位置、平台点选择偏差和既有后置项保留原触发条件。
- **证据/边界**：本轮analysis182/182、A1 loader24/24；真实48/48/32计划经fake runner生成128条/1280合成观测，原序/乱序均稳定复现路由错误；阈值组件通过、L3与L2反例已复现。runner192为作者报告，本轮未复跑无改动runner/CTest/NDK/旧图表。无adb、手机进程或perf执行。
- **行动链**：明确层来源/重叠身份→真实128条record成功正例→L3两点合同与L2统计比较→缺层/缺点/冲突/置换负例→正文/冻结审计产物→新基线重送审→整树集成→上板Agent独立标定/正式矩阵；A3沿既有条件后置。本次仅提交自有复核产物和本段台账。


## REV-RPA-R7-20261008 第七轮复核

- **输入/归属**：r2 `69e39f7`、任务书仍 v1.8.2、m0b `6756d00`、main `2fa8d5d`；[第七轮复核](reviews/2026-10-08-r7-review.md)。**不通过，RV2-02未清零，Phase A正式冻结不确认。**
- **关闭/接受**：R6-C的L2平台噪声误杀关闭，同onset/平台差0.1通过、onset差2拒绝；R6-B缺L3与全退化L3误放行子项关闭。RV2-01/03、R3-A、R4-B、R5-T维持关闭。
- **P1 / 正式矩阵前关闭**：R7-A新入口读record.experiment_id，但真实runner只写manifest，loader不注入；实际三配置run_plan→写盘→load_run的128条/1280合成观测，record该字段0/128，入口unknown layer。R7-B正式L3每target仅W8/12，消费者强制sharp，但其低侧/onset/两个平台点至少需4点，L3门永不可达；必须预注册两点比较规则或正式扩展网格，不得只扩测试。
- **证据更正/触发**：回执所称128条全量正例实际为40条手工/H1夹具，手工插入experiment_id且L3有6/8/10/12四点；同夹具仅收回正式L3网格即不能判H*。下一次送审必须更正声明，补真实配置保存/加载→消费者正例与置换/覆盖负例。
- **继承合同**：R3-C/R5-C完整W/有效样本/实际hi/请求-realized审计与重复策略，R5-D正文/冻结配置-代码-标定数据锚定继续原关闭条件；任务书本轮未修订。本轮未重测旧防御反例，既有A3及P2后置项沿原触发条件保留。
- **证据/边界**：本轮独立analysis185/185、A1 loader27/27；使用真实planner/runner/adapter/writer/loader，仅外部执行/二进制登记/Git来源替换为mock。全部新增数值为合成软件诊断，无adb/手机/perf执行；不声称本轮runner/CTest/NDK/旧runs重放。
- **行动链**：贯通权威manifest层来源→选择并注册可识别L3合同→真实计划写盘/读盘端到端正负及置换→正文/冻结产物/证据更正→新基线复核→整树集成→上板Agent独立标定及正式矩阵。本次仅提交自有评审产物与本段台账，远程分支不处理。


## REV-RPA-R8-20261008 第八轮复核

- **输入/归属**：r2 `e02cc3d`、任务书仍v1.8.2、m0b `0840b6e`、main `2fa8d5d`；[第八轮复核](reviews/2026-10-08-r8-review.md)。**不通过，RV2-02未关闭，Phase A正式冻结不确认。**
- **已修子项**：R7-B两点L3不可达性关闭，限附加形态一致性；诊断性补manifest来源后真实128条可得H*=1，全部below/单target冲突拒绝、缺target命名报错。既有RV2-01/03、R3-A、R4-B、R5-T、R6-C关闭维持。
- **P1延续 / 正式矩阵前关闭**：R7-A没有进入提交——0840b6e仅两个analysis文件，真实runner仍只向manifest写experiment_id；实际128条/1280合成观测0条含record级ID，入口unknown layer。R3-C/R6-B准确覆盖仍未修：合法协议的target201替换200、W100/200替换8/12均获H*=1；分别由邻接错误plan经真实runner/adapter生产，不能以数量/任意两点代替预注册合同。
- **证据口径**：新增测试128个planner case数量属实；但record仍手工构造且读回补ID，spy显示run_plan/_run_case均0调用，88条realized节点总和不符请求W，不能称实际producer链通过。纯函数合成曲线保留；record级端到端须用真实producer，仅mock外部执行。
- **继承与触发**：R5-D正文/冻结配置-代码-标定数据锚定，R3-C/R5-C有效样本/实际hi/最终审计/重复处理继续原合同；任务书未同步两点规则，入口docstring仍写sharp/onset规则。高→低误标签为both-below为P2（保守拒绝），随两点规则正文同步修订。既有A3/P2后置触发不变。
- **证据边界**：独立analysis187/187、runner192/192、A1 loader29/29；正式128条生产/读盘诊断与两个邻接错误plan全部fake外部执行，无adb/手机二进制/perf。未复跑CTest/NDK/历史runs。本次仅提交自有评审文档、脚本、证据与本段台账。
- **分支终点与行动链**：真实来源接线→真实producer正负例及精确覆盖→正文/冻结审计合同→新基线验收→m0b合入codex/sm8650-tlb-hierarchy-r2、main相关变更核对及整树回归→结束m0b开发、设备工作由r2/上板Agent承接。worktree按干净/无依赖/数据处置回收；分支删除须main集成+完整测试+推送，用户暂不处理远程期间保留引用，不因此延长开发使命。本轮没有执行集成/回收/删除。


## REV-RPA-R9-20261008 第九轮复核

- **输入/归属**：r2回执 `51d34fc`（复核读取HEAD `9ec80cc`，追加分支生命周期/索引文档）、m0b `b0f287f`、main `2fa8d5d`；[第九轮复核](reviews/2026-10-08-r9-review.md)。**不通过，RV2-02未关闭，正式冻结/软件出口不确认。**
- **本轮关闭**：L3准确target/W覆盖——两个邻接错误plan经真实runner/adapter生成合法record，201替200、W100/200替8/12均命名TlbError；诊断性补层来源后的正式128条H*=1且完整结果/canonical JSON置换相等。§5.5对应集合/两点规则文字同步接受。既有RV2-01/03、R3-A、R4-B、R5-T、R6-C及其他已关闭L3子项维持关闭。
- **P1延续 / 正式矩阵前关闭**：R7-A仍未交付——b0f287f实际仍只有两个analysis文件，无engine/schema README修改；真实三配置128条ok/1280合成观测，0条含record级ID，入口unknown layer。新增TestR9虽调用run_plan1次、_run_case32次、FakeExec320次，产物却ok0/failed32；ID断言循环0次仍通过，不能作为生产接线正证据。
- **验收证据修复 / 同一关闭条件**：Fake输出需匹配每case请求H/target/W/节点及全部PMU事件；先断言summary.ok=32/failed=0、len(ok_records)=32、失败集合为空，再逐条核ID。缺接线时测试必须失败，实际engine修复后通过；之后用真实三配置128条成功记录完成正式入口与置换。回执“真实探针调用/部署走查”改为fake执行证据，deploy_if_needed当前被mock，不能当设备证据。
- **继承合同**：R5-D冻结配置/代码/标定数据锚定、R3-C/R5-C其他有效样本/实际hi/最终审计/重复策略及旧docstring/重复段等沿原台账；不扩大关闭范围，也不重开本轮已修准确集合。A3和既有P2后置触发不变。
- **证据边界**：独立analysis190/190、runner192/192、A1 loader32/32全绿，同时捕获新测试32条parse-error（缺cycles/l1d_tlb_refill/l2d_tlb、目标descriptor不符）。所有新诊断均fake外部执行，无adb/手机二进制/perf；未复跑CTest/NDK/旧战役runs。main他人文档差异保留，本次只提交自有评审产物与本段台账。
- **行动链**：在明确m0b目录提交实际engine/schema接线→使run_plan测试产生非空成功记录并反证缺接线必失败→真实128条保存/加载/A1正负与置换→新基线验收→m0b合入r2、main相关变更核对与集成回归→结束m0b开发、设备工作由r2/上板Agent承接。回收/删分支按已确认铁律7分步；本轮不执行集成、删除或推送。


## FIX-A1-PRODUCER-TAKEOVER-20261008 接手修复

- **授权/归属**：用户要求直接接手本轮软件修复；m0b `b0f287f`→`0a27eba1a185618855a4081cd27dc21245e97e35`；[修复与验收对账](reviews/2026-10-08-a1-producer-takeover-fix.md)。旧 R9 报告保留为旧快照事实。
- **本轮关闭**：R7-A 实际 engine 在所有 record 写盘前持久化 plan.experiment_id，schema README 登记；R9 非空成功集合缺口关闭。新测试在缺接线的旧 engine 上明确失败，修复后真实三配置→runner/adapter→writer→load_run→A1 的 128 条记录全部成功、ID128/128，完整结果及 canonical JSON 置换不变。失败记录同样保存 ID。准确 target/W 关闭保留。
- **验收边界**：自身修复0a27eba上analysis191/191、runner195/195、A1模块33/33；另一Agent并行6f433e3上补跑analysis191/191、runner197/197及生产链诊断通过，未代写代提交其改动；1280次合成传输调用，不是手机进程。外部执行/二进制登记为 mock；无 adb/手机/perf/NDK/CTest/旧runs重放/main集成。源/证据哈希及复现脚本在对账文档；他人设备run目录未改未提交，远程未处理。
- **剩余 P1 / 归属 A1 软件收口，触发 = 正式矩阵前**：R3-C/R5-C 完整W/层角色/条件身份、有效样本、请求-realized最终审计、每case实际hi与重复处理；R5-D配置/代码/专用标定数据锚定、隔离核验和§5.5正文对齐继续原关闭条件。不能将这些软件余项交给设备Agent代替实现。
- **当前出口**：本轮两项通过；RV2-02整体与Phase A正式冻结仍不通过。先闭合既有软件合同→m0b/r2/main相关变化核对与集成回归→上板Agent独立标定/正式矩阵。既有关闭和A3/P2后置触发不变；本次未合并、回收或删除分支。
