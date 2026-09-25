# 任务说明书：GB10（DGX Spark，linux-aarch64）平台接入——自驱模式（git 下行 / 物理回传）

> 类型：agent 可执行任务书（自包含，无需对话上下文）
> 创建：2026-09-25｜修订：2026-09-25（网络约束确认后改为自驱模式）｜状态：待执行
> 预估规模：2~4 个 commit（Mac 侧）；GB10 侧只做构建与执行，不提交
> 必读先行：`AGENTS.md`、`docs/design/measurement-framework-design.md`、`docs/open-items.md` OI-9（GB10 定位与借鉴边界）

## 1. 背景与网络约束（决定形态）

本仓是跨 ISA/OS 的 CPU 微架构测量框架，已有 macos-arm64（M4 Pro）闭环，Xeon（linux-x86_64）接入由另一任务书负责。GB10（NVIDIA DGX Spark）是第三平台：ARM64 Linux、X925+A725 双核型、统一内存。

**已确认的网络约束（2026-09-25）**：
- Mac 与 GB10 **不在同一局域网，无任何 SSH 通道**（双向皆无）；
- GB10 **能访问 GitHub（clone/pull），但不能 push 或上传**；
- Mac → GB10 只能**单向传输源码或二进制**。

因此 GB10 采用**自驱模式**：代码经 GitHub 下行，GB10 原生编译、本地执行，数据经物理介质回传、Mac 侧收口入库。SSH executor / deploy 步骤 / 交叉编译管线**均不在本任务范围**（交叉编译管线留作 Android 接入的预演课题）。

```text
Mac（本机）              GitHub（私有仓，下行中继）          GB10（自驱目标）
───────────             ──────────────────────            ─────────────────
开发+push ─────────▶  main 分支 ──────────────────▶  gh clone（只读）
                                                         原生编译（cmake preset）
                                                         runner 本地跑 sweep
                        （无 push 通道）
run 目录入库 ◀──── USB-C 物理拷贝（或其他确认的上行通道） ◀── run 目录打包
```

## 2. 平台事实（公开资料口径，PUBLIC_SOURCE，**一律以机上实测为准**）

用户提供的规格摘要（2026-09-25，未经本仓实测）：

- SoC：NVIDIA GB10 Grace Blackwell；CPU 20 核 = 10× Cortex-X925 + 10× Cortex-A725（无 SMT 记载，需实测确认）；
- 内存：128GB LPDDR5x 统一内存（CPU/GPU 共享，NVLink-C2C 一致性互连）；标称带宽 273 GB/s @ 8533 MT/s；
- OS：DGX OS（Ubuntu LTS 深度定制）；I/O：4× USB-C（40Gbps，物理回传介质）、10GbE；
- 形态：桌面机，240W。

参考仓拓扑假设（`~/gb10-cpu-arch-probe/configs/platforms/gb10.json`，**假设起点，必须机上验证**）：cluster c0 = cpu 0-9，c1 = cpu 10-19；核型分组 a725 = {0-4, 10-14}，x925 = {5-9, 15-19}。GB10 侧已有用户前作（OI-9）：**只参考配置思路，不复制代码（许可证矛盾未解），其基线数据不入本仓校准链**。

## 3. 目标（验收标准）

1. **能力发现先行**：GB10 上实测并回填平台画像——`lscpu -e` 拓扑（核型/cluster 映射）、`/sys/devices/system/cpu/cpu*/topology/`、cpufreq 可用性（`scaling_available_governors`、`scaling_cur_freq`）、hugepage 能力（`/proc/sys/vm/nr_hugepages`）、计时器（`clock_getres` MONOTONIC/MONOTONIC_RAW）。结果按 capability-manifest schema 落 `configs/platforms/gb10-spark-01.capability.json`，证据等级 MEASURED；
2. `configs/platforms/gb10-spark-01.json` 入库：target 五要素（`transport: local`——GB10 上 runner 本地执行）+ probes 映射（GB10 侧构建路径 `build/linux-aarch64/release/probes/cache-mem/ptr_chase`）+ **至少两个控制组**（X925 核 / A725 核各一，`taskset` 绑核，cpu 编号以实测拓扑为准）；
3. **原生构建链**：`CMakePresets.json` 新增 `linux-aarch64-release` preset（通用 Linux ARM64，非交叉——同一份 preset 将来也能用于其他 ARM64 Linux 目标）；GB10 上 `cmake --preset linux-aarch64-release && cmake --build --preset linux-aarch64-release` 通过；
4. **首跑数据**：GB10 上 `runner.cli run` 完成 ptr-chase-cache-sweep（14 档 buffer × 5 重复 × 2 控制组）→ `analysis.cli report` 生成报告；run 目录经物理介质回传 Mac，**由 Mac 侧入库**（records/manifests/report.md/latency.svg；raw/ 按策略不入库但**保留在 GB10 本地备查**，不回传）；
5. 全部 records 通过 run-record.v2 schema 校验（在 Mac 侧执行校验）；
6. **数据合理性**：X925 与 A725 两组曲线应呈可区分的延迟档；DRAM 区延迟与 LPDDR5x 统一内存特性一致。**异常不得强行解释**，如实记录、标注置信度；
7. 本机（Mac）全部测试保持绿色；若 runner 有任何改动以适配 `transport: local` 的 GB10 场景，必须主流程零平台特判且带测试；
8. 文档同步：CHANGELOG、设计文档 §11/§12、OI-9 GB10 条目更新为"已接入（自驱模式）"。

## 4. 非目标

- SSH executor / deploy 步骤 / 交叉编译管线（留作 Android 预演课题）；
- GPU/Blackwell/NVLink-C2C、NPU 资产、gem5 一切；
- hugepage 正式测量（本期只探测能力并记录）、governor 锁频（OI-8 环境事务主线）；
- GB10 侧的 git commit/push（无通道；且提交统一在 Mac 收口，保持单点写入）。

## 5. 约束与坑

1. Xeon 任务说明书 §5 的全部通用约束在此适用（单位解析、不编造数字、注释纪律、提交粒度等）；
2. **GB10 接入信息登记在 `data/private/hosts.md`**（真实地址不入库；网络约束同步注明，防止后续任务书再假设 SSH）；
3. 参考仓 `~/gb10-cpu-arch-probe` 只读，不得复制其代码；其拓扑仅作假设起点；
4. DGX OS 是定制 Ubuntu：cpufreq/thermal 行为可能与标准 Ubuntu 有差异——以 sysfs 实测为准；CPU/GPU 共享内存控制器，run 前后只读取 GPU 利用率快照（`nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader`）入 `environment` 扩展字段并登记 `runner/schema/README.md`；
5. **回传介质与打包**：run 目录（不含 raw/）打包为一个 tar.gz 经 USB-C 拷回；Mac 侧解包后先入 `data/quarantine/` 校验（schema + 样本数 + manifest 一致性），通过再移入 `data/public/runs/` 并提交——**回传数据按 quarantine 流程走，不直接进 public**；
6. GB10 上的 `uv`/`cmake`/`gcc` 若缺失，按 DGX OS 常规方式安装并记入 runbook；不改动系统级配置（不需 sudo 完成的任务不做 sudo）。

## 6. 建议实施步骤

1. 通读必读文件；在 `data/private/hosts.md` 登记 GB10 与网络约束；
2. Mac 侧：新增 `linux-aarch64-release` preset → push；GB10 侧：`gh auth login` → clone → preset 构建；
3. 机上能力发现（§3.1 全部命令）→ capability JSON 与实测拓扑；
4. 平台配置（控制组按实测拓扑）→ GB10 上 plan 预览确认展开；
5. GB10 上 run + report → 本地目检数据合理性（§3.6）→ 打包回传；
6. Mac 侧：quarantine 校验 → 入 public → schema 校验 → 提交；
7. 文档与提交（粒度：preset+配置 / 数据 / 文档）。

## 7. 交付物清单

- `CMakePresets.json` 新增 preset；`configs/platforms/gb10-spark-01.json` + capability JSON；
- `data/public/runs/<时间戳>-ptr-chase-cache-sweep/`（GB10 首份数据，Mac 侧入库，含报告）；
- `data/private/hosts.md` 更新；runbook 增补 GB10 自驱流程（clone/构建/执行/回传）；文档更新（§3.8）。

## 8. 升级路径（停下来问人）

- GB10 实测拓扑与 §2 假设完全不同；
- DGX OS 缺少构建工具且安装需要超常规手段；
- 回传介质不可用（需用户另行确认上行通道）；
- sweep 数据出现无法解释的异常（延迟倒挂、双峰消失、GPU 干扰显著）。

