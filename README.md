# cpu-uarch-explorer

跨 ISA、跨 OS 的 CPU 微架构探索平台：真实设备微架构探测 → 统一实验协议与数据模型 → gem5 O3 建模与实机校准 → 综合 Benchmark 验证 → ARM / x86 / RISC-V 对比。

当前状态：需求基线 **v0.3**（tag `req-v0.3`）。**M4 Pro 最小骨架已闭环**（2026-09-25：probe → 统一 JSON 数据 → 自动报告三段打通，两份 P/E 双峰 sweep 实测入库，gem5 D9300 增量树修剪至 134 文件并在 Xeon 上重建+冒烟验证通过）。当前主线：探针域扩展（core/branch/TLB）与 Xeon 平台接入；gem5 微架构建模后置（校准闭环需探针套件与 D9300 实机就位，见 OI-1/OI-6）。

## 平台矩阵

| Backend | ISA | OS/环境 | Host | Target |
|---|---|---|---:|---:|
| `macos-arm64` | ARM64 | macOS | 是 | 是 |
| `linux-x86_64` | x86-64 | Linux | 是 | 是 |
| `android-arm64` | ARM64 | Android（root 高通，型号待补） | 否 | 是 |
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
- `docs/reviews/` — 外部评审归档
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

- 主仓许可证：Apache-2.0（见 `LICENSE`；决策背景见 `docs/adr/ADR-0002-license-apache2.md`，含历史 demo 代码来源审计）。
- 仓库未来转公开时 git 历史全量可见：从第一个 commit 起即执行设备匿名化与 secret 扫描，请勿提交设备序列号、NDA 资料。
- 个人参考材料已移至**仓库外** `../cpu-uarch-ref/`（只读约束），受跟踪索引见 `docs/reference-materials.md`；开源发布前删除该目录即可，与 git 历史无任何关联。
