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
- **剩余**：fake target / transport 契约测试；RISC-V compile-only preset 作为扩展性架构测试；gem5 overlay 同步加固（同步后 diff 摘要；基线断言与脏树检测已于 2026-09-25 落地）；SSH/ADB Transport 与 gem5 Executor；跨 run 汇总与校准差异单（analysis/ 已落地单 run 报告，2026-09-25）。
- **验收标准（ADR-0006）**：新增 RISC-V 仅需 toolchain preset + ISA kernels + capability provider + target 配置；runner 主流程零修改、通用 schema 零修改、现有 contract tests 全绿。
- **前置**：ADR-0006 与 schema v2（2026-09-24 已落盘）。

## OI-9 arm64-uarch-probe 借鉴迁移（2026-09-24 登记）

- **背景**：用户前作 `~/gb10-cpu-arch-probe`（GB10 = ARM64 Linux，X925+A725 双 cluster，在手且活跃；Phase 1-4 完成）。深度分析结论：其声明式配置、runner、契约测试、测量方法学领先本仓 1-2 个阶段，但绑定 ARM64/Linux 且有未完工子系统（环境事务）。
- **决策**：借鉴模式（用户拍板）——两仓独立；方法学迁移 + runner 蓝图参考；GB10 基线数据不入我方校准链。
- **方法学迁移**：`docs/methodology/measurement-discipline.md`（温度语义三档/页策略/统计/置信度/修正留痕/报告模板）。
- **ptr_chase 改进 backlog**：见 `probes/cache-mem/README.md`（MONOTONIC_RAW、hugepage+cold 参数化、evict 工具移植评估、chase_migrate 范式）。
- **runner 蓝图吸收清单**（Phase C / OI-8 的前置设计输入）：声明式 configs + 启动期引用完整性校验、Plan/Run 分离 + environment phase 分组、ProbeAdapter 4 方法 + 错误值返回、ResultStore 原子写 + case_definitions_signature、ResolvedValue{value,source} 参数溯源、exit code 阶梯、adapter↔二进制契约测试。**借分层、协议与测试方式，不借其当前 Runner 实现**（2026-09-24 外部评审实证：working-set 的 MiB/KiB 单位不被识别、静默降级为默认 1024KB；profile 声明的 samples 无消费点、sample_index 恒为 0；journal_tx_ids 从不追加；environment 硬编码 platform=unknown；CLI 以 coordinator=None 构造且调用缺 backend 参数）。fixture 的真实来源须由 capture manifest/命令证明（其历史 fixture 曾手写臆造，见该仓复盘文档），不能因文件存在就默认真实。
- **环境事务子系统：借模型、重新实现接线**（2026-09-24 评审纠偏，原"整体不吸收"裁定过头）：模型本身已实现 host-wide lock / durable journal / inspect→validate→apply→verify / 失败后逆序 restore / signal 中断恢复 / 未完成事务阻止新运行；coordinator=None 是 CLI/Runner 接线缺陷而非模型无价值。未来控制 Linux governor / hugepage / THP / perf 权限时此为核心模式。**不吸收**：其 ARM64 硬编码假设。
- **GB10 平台**：未来接入按声明式平台 JSON 模式（v0.4 候选）；它是 hugepage/PMU/跨核方法学的最佳宿主，也是可扩展性的天然验收平台。

## OI-2 红米设备信息回填（`android-arm64`）

- **阻塞**：§2.3 画像补全、Android target 适配、capability discovery 基线。
- **回填命令**（adb）：
  ```bash
  adb shell getprop ro.product.model ro.product.name ro.board.platform \
    ro.build.version.release ro.build.version.security_patch
  adb shell 'cat /proc/version'
  adb shell 'cat /proc/sys/kernel/perf_event_paranoid'   # PMU 权限，-1/0 最佳
  adb shell 'ls /sys/bus/event_source/devices/'          # PMU 设备节点
  adb shell 'cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors scaling_cur_governor'
  adb shell 'ls /sys/class/thermal/'
  adb shell 'id'                                          # 确认 root
  ```
- **备注**：demo 历史数据含 SM8550 与 SM8650 两份（见 OI-4），当前设备大概率为其一。

## OI-3 x86 服务器信息回填与探测脚本评审（2026-09-24 更新：信息已回填，仅剩脚本评审）

- **已回填（MEASURED，2026-09-24）**：Ubuntu 24.04.4 LTS；kernel 7.0.0-30-generic；perf 7.0.12；`perf_event_paranoid=4`（非特权 perf 封锁，sudo 可用）；dmesg 确认 SPR 完整 PMU：Sapphire Rapids events、full-width counters、PEBS fmt4+-baseline、32-deep LBR、AnyThread deprecated；NMI watchdog 常驻占 1 个 hw-PMU 计数器；RAPL PMU（package/dram 功耗）。
- **方法学提示**：perf 采集一律走 sudo；全核计数时注意 NMI watchdog 占用的计数器缺口；PEBS/LBR 可用意味着 frontend/分支分析可做 precise 采样。
- **脚本评审（状态更新 2026-09-25）**：用户外部 x86 探测脚本始终未提供；linux-x86_64 平台已改经本仓 runner（ssh transport + taskset 控制）接入并产出首份 sweep（`data/public/runs/20260924T174644Z-ptr-chase-cache-sweep`）。外部脚本若日后提供仍可按三维度评审；平台接入项视为完成。

## OI-4 SM8550 历史数据溯源

- **阻塞**：无（已决定不进校准决策），仅影响历史档案的标注。
- **现状**：`data/public/legacy/sm8550-cacheline.txt` 证据等级 UNKNOWN（连机主都不记得来源设备）。若溯源失败，保持 UNKNOWN 标注即可。
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
