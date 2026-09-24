# 遗留问题跟踪（open items）

> 本地快照（2026-09-23，tag `req-v0.3`）。仓库接入 GitHub 后同步为 Issues（标签 `open-item`）。每项注明：阻塞什么、如何回填、当前证据等级。

## OI-1 gem5 D9300 模型源码接入（2026-09-24 更新：基线就位，D9300 工作未随附）

- **已就位**：`third_party/gem5` = 上游 gem5/gem5 `stable` @ `f5c5a6e390`（v25.1.0.1 线，2026-09-24 核实），远程为上游 GitHub，工作树干净，BSD-3-Clause。
- **关键发现**：该克隆中**未发现任何 D9300/Dimensity/MediaTek 相关修改**（全分支检索 + 全树文件名与内容检索）。它是基线，不是模型。
- **下一步（二选一或并行）**：
  - (a) **定位真实 D9300 模型工作**：是否在其他机器/内部仓/压缩包中？v0.3 §2.4 预期的"Python 配置修改、C++ 修改、O3 参数、已有校准数据"均不在此克隆内；
  - (b) **决策在基线上自建**：v25.1 自带 **Neoverse V2 核心模型配置**（分布式 IQ、真实 FU 延迟、FDIP），是 D9300（X4+A720）O3 参数化的最佳起点；自建路线需另行计划。
- **接入 checklist 状态**：基线 commit ✅ 已知；D9300 配置/C++ 修改/校准数据 ❌ 未随附；fork→submodule 待用户将此克隆推送到本人 GitHub 后钉版（当前 .gitignore 排除，ADR-0004）。
- **调查记录**：`docs/gem5-d9300-intake.md`。
- **关联**：`../cpu-uarch-ref/cpu微架构材料/gem5-DDR访问通路时延细节全流程分析.md`（Michael 自己的分析，基于 gem5 commit `3dc9dcc`）——`3dc9dcc` 不在当前克隆历史中，进一步佐证 D9300 模型工作在其他仓库/历史里，接入时需一并定位。

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
- **脚本评审（仍待）**：用户已有一份 x86 探测脚本（待提供）。评审维度：① 覆盖度（core latency/throughput、branch、TLB、带宽 vs 仅 mem）；② 方法学（绑核、sibling 隔离、预热、稳态判定、统计口径；8481C 为 Sapphire Rapids，警惕硬编码事件名）；③ 可移植性与许可证。

## OI-4 SM8550 历史数据溯源

- **阻塞**：无（已决定不进校准决策），仅影响历史档案的标注。
- **现状**：`data/public/legacy/sm8550-cacheline.txt` 证据等级 UNKNOWN（连机主都不记得来源设备）。若溯源失败，保持 UNKNOWN 标注即可。
- **同时确认**：`sm8650-x4.txt` / `sm8650-a510.txt` 对应哪台设备、测试日期与系统状态。

## OI-5 M4 Pro PMU 能力实测（2026-09-24 更新：拓扑与 powermetrics 已实测）

- **已实测（MEASURED，2026-09-24）**：sysctl 拓扑——2 perflevels，Performance 10 核 + Efficiency 4 核，`hw.cpufamily=399882554`，品牌串 "Apple M4 Pro"；powermetrics——采样器含 cpu_power/gpu_power/ane_power/thermal/sfi/tasks/interrupts 等，支持 text 与 plist（NUL 分隔）输出，`--show-cpu-qos`/`--show-hwp-capability`/`--show-plimits`/`--show-pstates` 开关可用，毫秒级采样率与 SIGINFO 即时采样。详见 v0.3 §2.1。
- **仍待验证**：Instruments/xctrace per-thread KPC 计数器可用性（需在 M4 Pro 上实际跑一次 CPU Counters 验证）；QoS→P/E 分流可靠性 probe（属 runner/targets capability discovery 的实现内容）；`mach_absolute_time` 实际精度与开销。

## OI-6 D9300 实机信息回填

- **阻塞**：§2.5 画像、严格校准实验设计。
- **回填**：机型（vivo X100 / iQOO Neo9 Pro / OPPO Find X7 / 其他）、root 状态、adb 可达性、kernel 版本。
- **方法学提醒**：全大核无小核兜底，thermal 压力大于大小核机型，校准实验需预留温控与间歇。

## OI-7 外部参考材料处置（新增，2026-09-23；2026-09-23 二次更新：已迁至仓库外）

- **位置**：`../cpu-uarch-ref/`（workspace 级，仓库外，已加只读约束）。含两个子目录：`cpu-cache-demo-code/`（历史 demo）与 `cpu微架构材料/`。
- **内容**：第三方 CPUSUIT Benchmark 探针工程（无 LICENSE，含 xbyak_aarch64 第三方库）+ Michael 自己的 gem5 DDR 时延分析 + DDR 时序分析 + 未知作者 PPTX。
- **初步评估**（详见 req-v0.3 置信度注记）：CPUSUIT 覆盖度（ROB 探测、port 分析等）对 probes/ 规划有 HIGH 参考价值，但**无 LICENSE 不可搬代码**，仅限方法学借鉴；gem5 DDR 分析为本人作品，可评估后移入 `docs/`（注意其绑定 gem5 commit 3dc9dcc）。
- **处置待决策**：逐文件确认作者与许可证 → 决定 移入 docs / 登记为方法学参考 / 忽略。
