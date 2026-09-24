# 任务说明书：GB10（DGX Spark，linux-aarch64）平台接入——交叉编译 + 部署 + 首跑

> 类型：agent 可执行任务书（自包含，无需对话上下文）
> 创建：2026-09-25｜状态：待执行｜**前置依赖：Xeon 接入任务完成**（`docs/tasks/2026-09-25-xeon-platform-onboarding.md`，其中的 SshExecutor 与频率快照钩子被本任务直接复用）
> 预估规模：3~5 个 commit；新增/修改约 8~12 个文件
> 必读先行：`AGENTS.md`、`docs/design/measurement-framework-design.md`、`docs/tasks/2026-09-25-xeon-platform-onboarding.md`（先看它怎么做的）、`docs/open-items.md` OI-9（GB10 定位与借鉴边界）

## 1. 背景

本仓是跨 ISA/OS 的 CPU 微架构测量框架，已有 macos-arm64（M4 Pro）闭环与 linux-x86_64（Xeon，前置任务）接入。GB10（NVIDIA DGX Spark）是第三平台：**ARM64 Linux、X925+A725 双核型、统一内存**——它是验证框架 ARM64-Linux 路径与"三机管线"（Mac 驱动 → Xeon 交叉编译 → GB10 执行）的载体，也是 Android 接入的唯一形态（交叉编译+拷贝+远程执行）的预演。

GB10 侧已有用户前作 `~/gb10-cpu-arch-probe`（OI-9）：**只允许参考其平台配置思路，其基线数据不入本仓校准链**；其许可证状态（根 LICENSE BSD-3-Clause vs pyproject Proprietary）统一前不复制其代码。

## 2. 平台事实（公开资料口径，PUBLIC_SOURCE，**一律以机上实测为准**）

用户提供的规格摘要（2026-09-25，未经本仓实测）：

- SoC：NVIDIA GB10 Grace Blackwell；CPU 20 核 = 10× Cortex-X925 + 10× Cortex-A725（无 SMT 记载，需实测确认）；
- 内存：128GB LPDDR5x 统一内存（CPU/GPU 共享，NVLink-C2C 一致性互连）；标称带宽 273 GB/s @ 8533 MT/s（最高 301 GB/s）；
- OS：DGX OS（Ubuntu LTS 深度定制）；网络：10GbE RJ-45（SSH 通道）、ConnectX-7（本期不用）；
- 形态：桌面机，240W，无特殊机房要求。

参考仓拓扑假设（`~/gb10-cpu-arch-probe/configs/platforms/gb10.json`，**假设起点，必须机上验证**）：cluster c0 = cpu 0-9，c1 = cpu 10-19；核型分组 a725 = {0-4, 10-14}，x925 = {5-9, 15-19}（即每 cluster 内 5 A725 + 5 X925 混排）。

## 3. 目标（验收标准）

1. **能力发现先行**：在 GB10 上实测并回填平台画像——`lscpu -e` 拓扑（核型/cluster 映射）、`/sys/devices/system/cpu/cpu*/topology/`、cpufreq 可用性（`scaling_available_governors`、`scaling_cur_freq`）、hugepage 能力（`/proc/sys/vm/nr_hugepages`）、计时器（clock_getres MONOTONIC/MONOTONIC_RAW）。结果按 capability-manifest schema 落 `configs/platforms/gb10-spark-01.capability.json`，证据等级 MEASURED；与 §2 公开资料冲突处以实测为准并在报告中注明；
2. `configs/platforms/gb10-spark-01.json` 入库：target 五要素 + ssh host（扩展字段，登记 `runner/schema/README.md`）+ probes 映射（GB10 侧部署路径）+ **至少两个控制组**（X925 核 / A725 核各一，taskset 绑核，cpu 编号以实测拓扑为准）；
3. **交叉编译链**：`CMakePresets.json` 新增 `linux-aarch64-release` preset + `cmake/toolchain-linux-aarch64.cmake` toolchain 文件；在 Xeon 上用 `aarch64-linux-gnu-gcc`（已装）交叉编译 ptr_chase，**静态链接**（`-static`，消除 GB10 侧 glibc 依赖）；
4. **deploy 步骤**：runner 新增部署环节——run 前把二进制 scp/rsync 到 GB10 约定路径并**校验 SHA256**（与 artifact-manifest 对齐）；deploy 失败要产生结构化 failure 而非含糊的 ssh 报错；
5. **首跑数据**：ptr-chase-cache-sweep 在 GB10 完成（14 档 buffer × 5 重复 × 2 控制组），run 目录入库（records/manifests/report.md/latency.svg；raw/ 不入库）；全部 records 过 run-record.v2 schema 校验；频率快照按 Xeon 任务同款钩子入档；
6. **数据合理性**：X925 与 A725 两组曲线应呈可区分的延迟档（双核型差异）；DRAM 区延迟与 LPDDR5x 统一内存特性一致。**异常不得强行解释**，如实记录、标注置信度、可疑现象进报告"失败与异常"节；
7. 本机全部测试绿色（CTest 5 + runner 22+新增 + analysis 7）；deploy/交叉编译逻辑有 fake 级单测（不依赖 GB10 在线）；
8. 文档同步：CHANGELOG、设计文档 §11/§12、OI-9 的 GB10 条目更新为"已接入"。

## 4. 非目标

- GPU/Blackwell/NVLink-C2C 相关的一切（本期纯 CPU 微架构）；
- NPU/CoralNPU 资产、gem5 一切；
- hugepage 正式测量（本期只探测能力并记录；正式 hugepage 实验属后续任务）；
- governor 锁频（环境事务主线任务，OI-8；本期只读快照）；
- 在 GB10 上原生编译（可作为 fallback 记录，但交付物是交叉编译管线——它是 Android 的预演形态）。

## 5. 约束与坑

1. Xeon 任务说明书 §5 的全部约束在此适用（rsync `--delete`、单位解析、不编造数字、注释纪律、gem5 目录勿碰、提交只在本机）；
2. **GB10 接入信息在 `data/private/hosts.md`**（任务开始时执行代理应先补登记 GB10 的 host；真实地址不入库）；
3. 参考仓 `~/gb10-cpu-arch-probe` 只读，**不得复制其代码**（许可证矛盾未解）；其 gb10.json 拓扑仅作假设起点；
4. DGX OS 是定制 Ubuntu：内核/驱动可能被 NVIDIA 改过，cpufreq/thermal 行为与标准 Ubuntu 可能有差异——以 sysfs 实测为准，不要假定；
5. 统一内存架构下，CPU 与 GPU 共享内存控制器：若 GPU 侧有负载会干扰内存测量——run 前后记录 GPU 利用率快照（`nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader`，只读）入 `environment` 扩展字段并登记；
6. SSH 断线重试：deploy 与执行要容忍一次重试，二次失败才记 failed（网络抖动不动玷污数据档案）。

## 6. 建议实施步骤

1. 通读必读文件；确认 Xeon 任务产物（SshExecutor、freq 快照钩子）已入库；
2. 登记 GB10 host 到 `data/private/hosts.md`，验证 `ssh <gb10>` 免密可达；
3. 机上能力发现（§3.1 全部命令），产 capability JSON + 回填 §2 的实测版拓扑；
4. toolchain 文件 + preset；Xeon 上交叉编译，本地（Mac）`file` 命令确认产物为 `ELF 64-bit aarch64 static`；
5. deploy 环节实现（含 SHA256 校验与重试）+ fake 测试；
6. 平台配置（控制组按实测拓扑）→ 本机 plan 预览确认展开；
7. 首跑 → 报告 → schema 校验 → 数据合理性检查（§3.6）；
8. 测试、文档、提交（粒度：工具链+deploy / 平台配置 / 数据 / 文档）。

## 7. 交付物清单

- `cmake/toolchain-linux-aarch64.cmake` + preset；deploy 模块与测试；
- `configs/platforms/gb10-spark-01.json` + `gb10-spark-01.capability.json`；
- `data/public/runs/<时间戳>-ptr-chase-cache-sweep/`（GB10 首份数据，含报告）；
- `data/private/hosts.md` 更新；文档更新（§3.8）；commit 粒度按 §6.8。

## 8. 升级路径（停下来问人）

- GB10 实测拓扑与 §2 假设完全不同（如核型映射相反、有 SMT）；
- cpufreq sysfs 不存在或被 DGX OS 定制为只读异常；
- 交叉编译产物在 GB10 上无法运行（先排除静态链接问题再上报）；
- 需要 sudo 或需要修改 GB10 系统配置才能完成本期目标；
- sweep 数据出现无法解释的异常（如延迟倒挂、双峰消失）。
