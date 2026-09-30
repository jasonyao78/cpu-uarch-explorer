# 遗留问题跟踪（open items）

> 本地快照（2026-09-23，tag `req-v0.3`）。仓库接入 GitHub 后同步为 Issues（标签 `open-item`）。每项注明：阻塞什么、如何回填、当前证据等级。

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
- **内容**：第三方 CPUSUIT Benchmark 探针工程（无 LICENSE，含 xbyak_aarch64 第三方库）+ Michael 自己的 gem5 DDR 时延分析 + DDR 时序分析 + 未知作者 PPTX。
- **初步评估**（详见 req-v0.3 置信度注记）：CPUSUIT 覆盖度（ROB 探测、port 分析等）对 probes/ 规划有 HIGH 参考价值，但**无 LICENSE 不可搬代码**，仅限方法学借鉴；gem5 DDR 分析为本人作品，可评估后移入 `docs/`（注意其绑定 gem5 commit 3dc9dcc）。
- **处置待决策**：逐文件确认作者与许可证 → 决定 移入 docs / 登记为方法学参考 / 忽略。

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
