# 遗留问题跟踪（open items）

> 本地快照（2026-09-23，tag `req-v0.3`）。仓库接入 GitHub 后同步为 Issues（标签 `open-item`）。每项注明：阻塞什么、如何回填、当前证据等级。

## OI-1 gem5 D9300 模型源码接入

- **阻塞**：§2.4 全部细节、gem5 校准闭环、ADR-0004 的 submodule 落地。
- **来源**：用户手头已有带 git 仓的代码，稍后提供。
- **接入时 checklist**：fork → `third_party/gem5` 钉 commit → 梳理基线 commit / Python 配置 / C++ 修改 / O3 参数 / 已有校准数据及误差 → ADR-0004 追加记录。
- **关联**：仓库外参考目录中的 `cpu微架构材料/gem5-DDR访问通路时延细节全流程分析.md`（Michael 自己的分析，基于 gem5 commit `3dc9dcc`）——接入时确认该 commit 与 D9300 模型的关系。

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

## OI-3 x86 服务器信息回填与探测脚本评审

- **阻塞**：§2.2 画像补全（发行版/kernel/perf 权限）、`linux-x86_64` target 适配。
- **回填命令**：
  ```bash
  cat /etc/os-release | head -3; uname -r
  cat /proc/sys/kernel/perf_event_paranoid
  ls /sys/bus/event_source/devices/ | head
  sudo dmesg | grep -i -m5 PMU
  perf --version 2>/dev/null || echo "perf not installed"
  ```
- **脚本评审**：用户已有一份 x86 探测脚本（待提供）。评审维度：① 覆盖度（core latency/throughput、branch、TLB、带宽 vs 仅 mem）；② 方法学（绑核、sibling 隔离、预热、稳态判定、统计口径；8481C 为 Sapphire Rapids，警惕硬编码事件名）；③ 可移植性与许可证。

## OI-4 SM8550 历史数据溯源

- **阻塞**：无（已决定不进校准决策），仅影响历史档案的标注。
- **现状**：`data/public/legacy/sm8550-cacheline.txt` 证据等级 UNKNOWN（连机主都不记得来源设备）。若溯源失败，保持 UNKNOWN 标注即可。
- **同时确认**：`sm8650-x4.txt` / `sm8650-a510.txt` 对应哪台设备、测试日期与系统状态。

## OI-5 M4 Pro PMU 能力实测

- **阻塞**：macOS target 的 capability discovery 细粒度定义（v0.3 §2.1 已有定性判断，证据等级 PUBLIC_SOURCE）。
- **回填**：授权后在 M4 Pro 本机执行只读命令：`sysctl hw.nperflevels hw.perflevel0.name hw.perflevel0.physicalcpu hw.perflevel1.name hw.perflevel1.physicalcpu hw.cpufamily machdep.cpu.brand_string`；`sudo powermetrics --help` 采样项确认；Instruments/xctrace 计数器可用性验证。

## OI-6 D9300 实机信息回填

- **阻塞**：§2.5 画像、严格校准实验设计。
- **回填**：机型（vivo X100 / iQOO Neo9 Pro / OPPO Find X7 / 其他）、root 状态、adb 可达性、kernel 版本。
- **方法学提醒**：全大核无小核兜底，thermal 压力大于大小核机型，校准实验需预留温控与间歇。

## OI-7 外部参考材料处置（新增，2026-09-23；2026-09-23 二次更新：已迁至仓库外）

- **位置**：`../cpu-uarch-ref/`（workspace 级，仓库外，已加只读约束）。含两个子目录：`cpu-cache-demo-code/`（历史 demo）与 `cpu微架构材料/`。
- **内容**：第三方 CPUSUIT Benchmark 探针工程（无 LICENSE，含 xbyak_aarch64 第三方库）+ Michael 自己的 gem5 DDR 时延分析 + DDR 时序分析 + 未知作者 PPTX。
- **初步评估**（详见 req-v0.3 置信度注记）：CPUSUIT 覆盖度（ROB 探测、port 分析等）对 probes/ 规划有 HIGH 参考价值，但**无 LICENSE 不可搬代码**，仅限方法学借鉴；gem5 DDR 分析为本人作品，可评估后移入 `docs/`（注意其绑定 gem5 commit 3dc9dcc）。
- **处置待决策**：逐文件确认作者与许可证 → 决定 移入 docs / 登记为方法学参考 / 忽略。
