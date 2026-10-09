# cpu-uarch-explorer

**r2 当前进展（2026-10-09）**：当前Agent独占设备，已获授权常规端到端持续推进TLB/ROB。新增target100五mapping/4000窗：38/40双差正，但存在负epoch及W8全walk反例；精确ways仍OPEN。ROB细扫114进程/342窗，NOP+fsqrt k8/k16在预注册1-cycle规则下分别响应于每gap N∈(672,704]/(640,672]；无锚点/对齐/ADD/FADD对照已交付，物理ROB仍未识别。当前协议/驱动`7a249e3`、分析`afe6d26`，复用探针`217e5e3`；均在r2，m0b不恢复开发，旧正式A1/frozen不拼接。见[局部确认报告](docs/reviews/2026-10-09-local-confirmation-results.md)；后续继续替换历史与资源归因对照。

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
