# 遗留问题跟踪（open items）

> 本地快照（2026-09-23，tag `req-v0.3`）。仓库接入 GitHub 后同步为 Issues（标签 `open-item`）。每项注明：阻塞什么、如何回填、当前证据等级。

## OI-1 gem5 D9300 模型源码接入（2026-09-24：主体完成，剩余验证与梳理）

- **✅ 模型工作定位**：用户提供的 gem5-d9300-patch 增量树——`configs/example/arm/arm_multicore_d9300.py`（D9300 全系统配置）+ CoralNPU/NDP/Gemmini 资产 + `run_multicore.sh` 全流程（checkpoint/NPU 后端切换）。原始 drop 只读归档于 `../cpu-uarch-ref/gem5-d9300-patch/`（MANIFEST.sha256）。
- **✅ 集成落地（ADR-0004 修订：overlay 方案）**：`third_party/gem5` = 官方上游 submodule（钉 `f5c5a6e390`，v25.1.0.1，ignore=dirty）；`third_party/gem5-d9300-patch/gem5` = 增量树（唯一事实源）；`apply_patchset.sh` 同步后构建；脚本与文档路径已适配本仓布局。
- **⏳ 基线兼容性验证（构建中）**：delta 覆盖 867 个修改文件（+22841/−54427；删除量提示增量基于不同版本的上游开发）+ 50 个新文件；scons `build/ARM/gem5.opt` 后台构建中（日志 `third_party/gem5/build-macos-arm64.log`）。首次失败原因：conda Python 3.13 未过 gem5 链接检查，已改用 Homebrew Python 3.12。
- **⏳ intake 梳理**：O3 参数表、DDR/内存配置、checkpoint 流程、NPU 后端、已有校准数据 → `docs/gem5-d9300-intake.md`。
- **⏳ 合规检查点（开源前）**：增量树逐文件 SPDX/权属复核（用户已确认无权属问题入库私有仓；delta 文件普遍缺许可证头）。
- **⏳ SE 模式精简配置**：现有配置为 full-system（需磁盘镜像 + 内核）；校准闭环需补 SE 模式配置让 ptr_chase 等微基准跑进 gem5（写配置时遵循 `third_party/gem5/configs/AGENTS.md`：优先 stdlib、窄配置、py_compile + 最小测试验证）。

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
