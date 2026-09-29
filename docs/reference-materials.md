# 外部参考材料索引（reference materials index）

> 本文件**受 git 跟踪**，是参考材料登记簿。第三方材料本体默认位于
> **仓库外** `../cpu-uarch-ref/`（workspace 级，已加只读约束
> `chmod -R a-w`），永不入库；下节列出的仓库所有者授权作品是明确例外。
>
> **例外（用户决策 2026-09-28）**：由仓库所有者主导并有权授权、可能含
> 用户团队或 AI/并行代理协作的调查文档，可按原文归档入仓，存放于
> `docs/reference-materials/`；不以“单一自然人独立创作”作为授权依据。
> 下表登记此类副本；第三方材料维持仓外只读、永不入库。

## 入库归档（docs/reference-materials/）

| 材料 | 原件位置 | 内容摘要 | 许可证状态 | 处置 |
|---|---|---|---|---|
| Android灭屏最高频锁定实验与证据链（v1.1） | `../cpu-uarch-ref/Android灭屏最高频锁定实验与证据链.md` | SM8650 频率三层状态、唤醒 boost ftrace、已证无效路径、Perf 资源静态模型、0x1091 实验设计 | 仓库所有者主导并授权 Apache-2.0；可能含团队/代理协作 | ✅ 已归档（2026-09-28，逐字节一致）；本仓 runbook `redmi-manet-freq-control-chain.md` 的证据来源之一 |
| Qualcomm Perf2 Resource Apply Failure - Root Cause Investigation | `../cpu-uarch-ref/Qualcomm Perf2 Resource Apply Failure - Root Cause Investigation.md` | Perf2 正 handle≠生效的 syscall 实证、根因候选与 P0–P3 实验计划 | 同上 | ✅ 已归档（2026-09-28，逐字节一致）；同上 |
| Qualcomm Perf2 HAL 资源不生效根因分析与手工调试完整手册 | `../cpu-uarch-ref/Qualcomm Perf2 HAL 资源不生效根因分析与手工调试完整手册.md` | Perf2 调查完整操作手册：取证命令库、状态标记体系（VERIFIED/TODO 等）、受控状态迁移（亮灭屏/WiFi/飞行模式）、UID 差分、strace/ftrace/simpleperf/uprobe 配方 | 同上 | ✅ 已归档（2026-09-28，逐字节一致）；本仓 runbook §5 调试手段章节的命令来源 |

## 仓外登记清单（永不入库）

| 材料 | 位置（相对仓库根） | 内容摘要 | 许可证状态 | 允许使用范围 | 处置 |
|---|---|---|---|---|---|
| 历史 demo | `../cpu-uarch-ref/cpu-cache-demo-code/` | lmbench 衍生内存延迟探针 + SM8650/SM8550 历史数据 | lmbench 谱系，GPLv2 风险 | 仅存档查阅；代码不迁移（已由 ptr_chase 替代，ADR-0002） | 数据副本已在 `data/public/legacy/` |
| CPUSUIT Benchmark | `../cpu-uarch-ref/cpu微架构材料/`（根目录及 src/include/script/thirdparty） | 微架构探针工程（ROB/BTB/TLB/RAS 容量探针 + 部件延迟/吞吐表征 + 取指带宽/cache 时延），基于 xbyak_aarch64 运行时生成指令流 | **作者 = 仓库所有者本人**（2026-09-30 源码头核实：`include/probe_type.h` 等署名 Copyright(c) Michael Yao 且带 Apache-2.0 头注；src 多数文件无头注、根目录无 LICENSE 文件；**此前登记的"第三方/无 LICENSE"有误， hereby 更正**）；内嵌 xbyak_aarch64 为 Apache-2.0 | 本人作品：ROB 项目按方法学借鉴执行（借鉴登记见 rob-deep-analysis/probes/README.md 与报告 §0）；**代码复用范围待所有者拍板**（当前保守：不搬代码）；已知瑕疵：fdiv 缺测、`StartCycleCounter` 失败路径不检查 | 已更正（2026-09-30）；作者确认完成，复用范围待决策 |
| 知乎《初评 Arm Cortex X4、A720、A520》 | `../cpu-uarch-ref/docs/初评Arm Cortex X4、A720、A520 - 知乎.md`（图片在同目录 `{pageTitle}/`） | JamesAslan 的 X4/A720/A520 微架构分析（ROB 非传统/条目打包/early deallocation 声称；X3 dispatch 实测声称） | 第三方文章（知乎 p/633012156；与 ROB 任务书所引 p/4577094382 链接不同，视为同作者系列文，出处以实际文件为准） | 仅个人阅读与方法学参考；声称一律预注册为待验假设（报告必读 4） | 已登记（2026-09-30） |
| Cardyak《Cortex-X4 Microarchitecture Block Diagram》 | `../cpu-uarch-ref/docs/2023 - Cortex-X4.jpg` | X4 微架构框图（ROB 384 / 调度器 80+80+42 / LB 96 / SB 72 等） | 第三方示意图 | 仅作候选区间（最低权重），不进判据（报告 §3.2） | 已登记（2026-09-30） |
| Arm Cortex-X4 官方文档 PDF（TRM 102484_0003_06_en / SW Optimization Guide Issue 3.0） | `../cpu-uarch-ref/docs/Arm_Cortex_X4_Core_TRM_102484_0003_06_en.pdf`、`Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf` | Arm 官方非机密文档（TLB 真值表在第 5 章；ROB 零披露已全文核验；dispatch 宽度在优化指南 §4.1） | Arm 官方 Non-Confidential（可再分发） | 权威依据（报告/TRM 事件语义均逐字核验） | 已登记（2026-09-30） |
| gem5 DDR 时延分析 | `../cpu-uarch-ref/cpu微架构材料/gem5-DDR访问通路时延细节全流程分析.md/.html` | Michael 自己的报告：gem5 DDR 读通路时延分解（trace + 源码 commit `3dc9dcc`） | 本人作品 | 可评估后移入 `docs/`（接入 gem5 时，OI-1） | 待 gem5 源码接入时处置 |
| DDR 时序参数分析 | `../cpu-uarch-ref/cpu微架构材料/DDR关键时序参数分析.md` | DDR 关键时序参数讲解 | 作者待确认 | 确认作者前仅个人阅读 | 待确认 |
| CPU MicroArchitecture Analysis.pptx | `../cpu-uarch-ref/cpu微架构材料/` | 微架构分析幻灯片 | **作者未知** | 确认作者与来源前不引用、不传播 | 待确认 |
| gem5-d9300-patch 原始 drop | `../cpu-uarch-ref/gem5-d9300-patch/` | gem5 增量树原始档案 + MANIFEST.sha256（1015 项） | 同左（工作副本已入 `third_party/gem5-d9300-patch/`） | 只读存档；一切变更以 third_party/ 增量树为准 | 已归档（2026-09-24） |
| arm64-uarch-probe（GB10 项目） | `~/gb10-cpu-arch-probe`（原地保留，活跃项目） | 本人前作：GB10（ARM64 Linux，X925+A725 双 cluster）微架构探测框架，Phase 1-4 完成；声明式配置/runner/契约测试/测量方法学 | 根 LICENSE 为 BSD-3-Clause（Copyright Michael Yao 2026）；包元数据仍标 Proprietary，待参考仓统一后再复制代码，当前仅借鉴设计和方法 | **借鉴模式**（用户决策 2026-09-24）：模式与方法学迁移、runner 蓝图参考（借分层/协议/测试方式，不借当前 Runner 实现）；代码引用须登记来源；GB10 基线数据不入我方校准链 | 已登记，迁移跟踪见 OI-9 |

## 借鉴工作流（防"被参考实现带偏"）

借的是**思路不是代码**。每借一处方法学，在对应 probe 的 README（或本文件）登记三要素：

1. **来源**：具体文件/章节；
2. **借了什么**：方法学一句话；
3. **差异点**：我们的实现与参考实现的具体差异（强制填写——这是防止参考实现悄悄限制设计空间的对冲机制）。

## 纪律

- 不修改参考目录内任何文件（只读约束已施加；如需解锁，`chmod -R u+w <目录>`）。
- 不把**第三方**参考目录内容复制进仓库；仓库所有者有权授权作品的入库例外见顶部说明（`docs/reference-materials/` 归档区）。
- 新增个人参考材料时先登记本表，再放至 `../cpu-uarch-ref/`。
