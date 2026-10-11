# cpu-uarch-explorer

**r2 当前进展（2026-10-11）**：当前 Agent 独占设备，持续端到端推进 TLB/ROB；m0b 已完成集成使命。TLB 固定地址集的工作集转折 (8,9]、W9 单 victim 响应跨 victim/历史/方向复制；物理 ways 与硬件索引未认证。地址几何对照五mapping/77760窗已完成：target7在W8即复制，100/200在W9才复制，三跨度一致；通用8页边界被反例推翻，局部转折五新mapping/69120窗确认target7=(7,8]、100=(8,9]，两跨度/双order十曲线一致，C2至W10无转折。下一项转Q-A分布及Q-D有效在飞占用。ROB 零值对照已完成 64 进程/192 窗，有限主门 12/12 通过：MOVZ #0/#1 同码形下 rename 响应显著不同，说明资源和值域敏感；不换算 ROB/PRF 项数。同值锚点依赖48进程/144窗完成：带锚点Rn改变伴随周期及rename改变，但NONE负控波动使主门失败，按not-qualified归档。长 load 路线因模型资格不足停止，NOP 细扫仍只报告有效窗口区间。旧正式 A1、旧 frozen 与旧不完整 L1 不拼接。来源、构建、启动和 raw SHA 逐批核验；正式 runner 接入及窗内 clock 后置项保留于 `docs/open-items.md`。

最新证据：[TLB 地址族局部转折](docs/reviews/2026-10-11-tlb-local-turn-results.md)、[ROB 同值依赖](docs/reviews/2026-10-11-rob-dependency-results.md)、[TLB 地址几何反例](docs/reviews/2026-10-11-tlb-address-geometry-results.md)、[TLB victim/历史对照](docs/reviews/2026-10-11-tlb-victim-history-results.md)、[ROB 零值对照](docs/reviews/2026-10-11-rob-zero-value-results.md)、[ROB 操作事件资格](docs/reviews/2026-10-11-rob-event-results.md)。历次反例和全部原始窗口按各报告路径保留，结果不晋升为物理容量结论。

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

Q-D有效在飞占用有限结果：[`2026-10-11-tlb-walk-parallel-results.md`](docs/reviews/2026-10-11-tlb-walk-parallel-results.md)，495窗、240/240长窗门；固定总8192页K1→8 A/C=.553→3.039，不认证walker数量，短窗235/240部分不合格原样保留。
