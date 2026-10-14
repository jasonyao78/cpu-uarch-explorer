# cpu-uarch-explorer

**当前 SM8650 TLB/ROB 状态（2026-10-14，r2）**：primary独占设备，m0b已集成结束使命。

| 目标 | 当前依据 |
|---|---|
| L1 iTLB | 4KiB实测 **48→49** 相邻转折，六缓存/分支控制曲线复制；官方128/48冲突保留 |
| L1 dTLB | 4KiB实测 **96→97**，六缓存控制曲线复制，支持官方96 |
| 共享L2 TLB | 匹配r0p1官方 **2048 entries、256 sets × 8 ways**；有效leaf容量与精确set selector独立黑盒尚OPEN |
| ROB | 物理entries尚OPEN；旧g+chain窗口代理/第三方384未晋升。register-only短ROI **1536/1536资格通过**，A8/Mpre0、far|near1；单位对照OP/DP不能区分NOP/zero/sink分配，物理ROB仍OPEN，所有profile恢复0 |

[层次/容量结论与2700窗证据](docs/reviews/2026-10-13-sm8650-tlb-hierarchy-findings.md)、[目标账本](docs/reviews/2026-10-11-tlb-rob-goal-ledger.md)、[资料核验](docs/reviews/2026-10-13-x4-r0p1-source-audit.md)、[L2 descriptor dose反例](docs/reviews/2026-10-13-tlb-descriptor-dose-results.md)、[寄存器发射资格](docs/reviews/2026-10-14-rob-register-fenced-results.md)、[单位反例](docs/reviews/2026-10-14-rob-sink-unit-results.md)。有限实验完成不等于全部物理机制已识别；main/remote未动作，后置项在 `docs/open-items.md`。完整diagnostic727/727（623.629s）覆盖至有限metadata/admission v1.3；cold-head后加2项局部测试通过，正式runner/analysis/CTest本轮未改未重跑。resource v1/v2均完整但供给门未过；有限metadata契约已实现；新资源复核16/4096正式+16384warm全过，invalid0，供给门/周期资源差复制。admission探索84/21504正式+86016warm完整、invalid0，两epoch/两链复制三filler响应差，strict供给3点失败保留；cold-head4096正式/16384warm完整，long/marker/供给正控通过，但带标记L1D差模型不合格；同映射冷热/offset8192正式+32768warm完整，1024 cache/long/供给通过，但near7/4低于原8门，资格失败；branch-sites6144正式/24576warm完整、invalid0，packet两epoch/head1-2全部32/32错方向/near/far和原门通过；packet cache2048/8192完整、marker32/32/long过，但head1三格L1D剂量超原门；下一head-only ROI独立剂量后gap/packing/PRF。旧失败批不晋升。formal paths未改未重跑。

跨 ISA、跨 OS 的 CPU 微架构探索平台：真实设备微架构探测 → 统一实验协议与数据模型 → gem5 O3 建模与实机校准 → 综合 Benchmark 验证 → ARM / x86 / RISC-V 对比。

当前状态：需求基线 **v0.3**（tag `req-v0.3`）。M4 Pro 最小闭环、Xeon
平台接入和 gem5 D9300 增量树重建已完成；SM8650 的旧 cache 容量结论经
证据重审后重新开放。2026-09-28 SM8650 测量链定论：core PMU 与 `ptr_chase`
同窗采样链路可信（计数相干性、完整性核验、环境门禁 fail-closed 均成立）；
P0″ 正式复测（demand/prefetch 专用事件 × 4 seed × 双训练量 × 定圈，探针
`-S seed` 与逐样本分析器已入库）裁定 **512→640 KiB 跳变与 L1 预取活动/
覆盖代理量崩塌稳定伴生（近端解释，高置信；上游原因未鉴定）**；**私有
L2 容量信号按预注册规则判定不容许**（跨 seed/训练量不稳），容量维持
**OPEN/INCONCLUSIVE**——SM8650 DTS 的 2 MiB 为平台描述证据，未证实未否
决，几何/着色/预取残差见 `docs/reviews/2026-09-28-sm8650-x4-p0prime.md`。
THP 对照段因动态 ceiling drift 推迟（根因 OPEN，恢复门禁见 OI-11）；外
层 L3/LLCC 的容量定案在私有 L2 可识别前继续封锁，但该局部门禁不阻塞
分支预测、TLB、前端、执行端口、MLP、跨核迁移等正交微架构探索。**2026-
09-30 SM8650 TLB 层级探测战役完成**（任务书 v4.4，分支
`codex/sm8650-tlb-hierarchy`）：Q1 L1 dTLB refill 第一有效转折
**INTERVAL_IDENTIFIED [120, 1024] 页**（480 KiB–4 MiB 宽饱和区，4
seed × 双训练量一致）、Q2a walk-onset **INTERVAL_IDENTIFIED [2560,
3072] 页**（10–12 MiB，下沿在 MMUTC 2048 项之上）、Q3 walk 暴露成本
**MODEL_UNIDENTIFIABLE**（实测 walk 与延迟反相关，单调性不成立）、
Q4 mixed-THP 机制方向一致（受限比较级，3072 KiB mixed lat -12.4% /
R_0x05 -82%）+ 两处 INSUFFICIENT_COHORT；新增 4 事件 QUALIFIED
（`0x2d`/`0x8136`/`0x8128`/`0x813a`）、2 事件 SEMANTICS_UNVERIFIED
（`0x2f`/`0x8138`）。终审 `docs/reviews/2026-09-28-sm8650-tlb-hierarchy.md`；
TLB 的 Q1/Q2a 区间不主张 TLB 物理项数，L2 容量门禁与 TLB 判定相互独
立。gem5 微架构建模继续后置到探针校准闭环和 D9300 实机就位之后（见
OI-1/OI-6）。

## 平台矩阵

| Backend | ISA | OS/环境 | Host | Target |
|---|---|---|---:|---:|
| `macos-arm64` | ARM64 | macOS | 是 | 是 |
| `linux-x86_64` | x86-64 | Linux | 是 | 是 |
| `android-arm64` | ARM64 | Android（Redmi K70 Pro / SM8650，KernelSU root） | 否 | 是 |
| `android-arm64-d9300-phys` | ARM64 | Android（D9300 实机在手，型号/root 待补，校准后置启用） | 否 | 是 |
| `gem5-arm64-d9300` | ARM64 | gem5 O3（v25.0.0.1 + 134 文件增量，Xeon 构建与 SE 冒烟已验证） | 由 Host 驱动 | 是 |
| `linux-riscv64` | RISC-V64 | Linux | 未来可选 | 未来支持 |

## 仓库导航

- `docs/requirements/v0.3.md` — 需求基线（平台画像、架构、校准误差目标）
- `docs/requirements/CHANGELOG.md` — 基线修订记录
- `docs/adr/` — 架构决策记录（许可证、数据模型、分支策略等）
- `docs/methodology/` — 测量纪律与[注释纪律](docs/methodology/comment-discipline.md)（新代码强制遵守）
- `docs/open-items.md` — 遗留问题跟踪（设备信息回填、gem5 intake 梳理等）
- `docs/design/` — 框架详细设计文档（面向初级微架构背景读者）
- `docs/README.md` — 文档地图（各目录职责 + 战役结论入口索引）
- `docs/reviews/` — 评审与裁定归档（外部评审 + 本仓自评判定：Gate/Phase/战役终审）
- `docs/reports/` — 面向读者的传播报告（同事版/对外版）
- `docs/learning/` — 个人学习笔记（费曼工作流，开源时可整目录移除）
- `probes/` — P0 微基准源码（C++17 + CMake；构建走 `CMakePresets.json`，`build/<target-triple>/<profile>` 分层，ADR-0008）
- `runner/` — Python 编排（`schema/` 为统一数据模型；v2 含 experiment / capability / run-record / artifact 四类记录，ADR-0006）
- `configs/` — 声明式配置：`experiments/` 实验规格实例、`platforms/` 平台画像与 probe 二进制映射（ADR-0008）
- `pyproject.toml` / `uv.lock` / `.python-version` — Python 工具链，uv 管理（ADR-0007）
- `workloads/` — Geekbench / SPEC / CoreMark 适配层（只含 Runner 与解析器，不含商业内容）
- `analysis/` — 报告生成与校准对比（单 run 报告已实现：`python -m analysis.cli report --run <run目录>`）
- `third_party/` — 全部 submodule（gem5 已接入并验证）与 SPDX 许可证清单
- `data/public/` — 可入库的参考数据；`data/private/`、`data/restricted/` 永不入库

## 许可与合规

- **在本仓工作的代理与新成员**：先读 `AGENTS.md`（构建/实验命令与铁律速查；操作规程的唯一家园，本文件不重复）。
- 主仓许可证：Apache-2.0（见 `LICENSE`；决策背景见 `docs/adr/ADR-0002-license-apache2.md`，含历史 demo 代码来源审计）。
- 仓库未来转公开时 git 历史全量可见：从第一个 commit 起即执行设备匿名化与 secret 扫描，请勿提交设备序列号、NDA 资料。
- 第三方参考材料位于**仓库外** `../cpu-uarch-ref/`（只读约束），受跟踪索引见 `docs/reference-materials.md`；仅仓库所有者明确授权的三份调查文档按原文归档在 `docs/reference-materials/`，其来源与协作属性在目录 README 单独披露。


2026-10-13剂量实验更新：固定1536leaf、27fresh/64,896初始观察/324窗完整，简单leaf+PT→2048预算预测未复制，技术与几何阴性门通过；报告 `docs/reviews/2026-10-13-tlb-descriptor-dose-results.md`。官方L2规格仍2048/256×8，实测sethash／条目分配与ROB物理容量仍OPEN。完整674diagnostic通过，下一固定映射PT关联／in-page offset与ROB自己的PMU元数据接口，原始失败与counterexamples保留。
