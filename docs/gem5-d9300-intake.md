# gem5 D9300 模型接入调查记录（intake survey）

> 状态：进行中（OI-1）。本文件随接入进展更新；重大决策进 ADR。

## 2026-09-24 首次核实

### 收到的源码

| 项 | 值 |
|---|---|
| 路径 | `third_party/gem5`（本地克隆，当前 .gitignore 排除） |
| 远程 | `git@github.com:gem5/gem5.git`（上游） |
| 分支 | `stable` |
| HEAD | `f5c5a6e390`（"misc: add remaining labels to labeler.yml (#3494)"） |
| 版本线 | v25.1.0.1（hotfix 线，2025 年第二个大版本） |
| 许可证 | BSD-3-Clause（上游 LICENSE） |
| 体积 | 374 MB（含 .git） |

### 关键发现：无 D9300 内容

- 全分支检索（`git log --all --grep`）与全树检索（文件名 + 内容，大小写不敏感）：**无任何 d9300 / dimensity / mediatek 资产**（仅 .mailmap 出现 mtk 域名）。
- 工作树干净，无本地未提交修改，无 stash。

### 旁证

- 用户的 gem5 DDR 时延分析报告基于 commit `3dc9dcc`，该 commit **不在当前克隆历史中** → 真实的 D9300 模型工作存在于另一个仓库/历史中，尚未提供。

### v25.1 中与 D9300 建模相关的现成资产（若走自建路线）

- **Neoverse V2 核心模型配置**（v25.1 新增）：分布式 IQ（8 个 scheduler × 22 项）、真实 FU 延迟、FDIP 取指预取——是目前 gem5 官方库中最接近现代 Arm 大核（X 系列/A720 级）的 O3 参数化模板。
- gshare 分支预测器新增（#2303）——可配置选项增加。

### 待办

1. **定位 D9300 模型工作**（用户侧）：其他机器 / 内部 git 仓 / 压缩包？重点找：Python 配置（`configs/` 下 mtk/d9300 相关）、C++ 修改（`src/cpu/o3`、`src/mem` 等 diff）、O3 参数表、已有校准数据。
2. **若确认无现成模型**：决策自建路线（以 Neoverse V2 配置为模板做 D9300 参数化），单独写计划。
3. **fork → submodule**（ADR-0004）：将（含 D9300 工作的）仓库推送到本人 GitHub，`git submodule add` 钉 commit，移除对应 gitignore 条目。
4. 按 v0.3 §2.4 清单梳理：基线 commit / Python 配置修改 / C++ 核心修改 / O3 参数 / FU latency / ROB/IQ/LQ/SQ / 分支预测 / Cache-TLB / 预取 / 内存模型 / 参数证据来源 / 已有校准数据及误差。

## 2026-09-24 二次更新：模型定位与集成

### 模型工作本体（用户提供的 gem5-d9300-patch）

- **形态**：gem5 增量文件树（overlay），非完整仓库；1014 文件 / 32MB，按上游目录结构镜像存放新增/修改文件。
- **核心资产**：
  - `configs/example/arm/arm_multicore_d9300.py`（31.7KB）——D9300 全系统配置本体；
  - `configs/coralnpu/`、`src/ndp*/`、`configs/gemmini/`、`scripts/build_kernel_with_gemmini_ko.sh`——Coral NPU + NDP + Gemmini（超出 D9300 范畴，对应 NPU 探索方向）；
  - `run_multicore.sh`——ARM Linux 全系统流程：scons 编译、checkpoint 管理（8 条失效规则）、NPU 后端切换（stage-a / verilated-coral）、磁盘镜像与内核注入；
  - `apply_patchset.sh` + README + AGENTS.md——overlay 工作流（submodule 保持纯上游，增量树为唯一事实源）。
- **自带治理规则**（其 AGENTS.md）：内存映射 / NPUDevice 参数 / checkpoint 行为变更需同步文档与兼容性说明；D9200/D9300 或 NPU 变更至少提供 Stage-A MMIO / Verilated Coral DMA / Driver / MobileNet 之一 PASS，附完整命令与 guest 输出。

### 集成现状

- `third_party/gem5`：官方上游 submodule（v25.1.0.1 @ `f5c5a6e390`，ignore=dirty）。
- `third_party/gem5-d9300-patch/gem5`：增量树入库（唯一事实源），路径已适配本仓；原始 drop 只读归档 `../cpu-uarch-ref/gem5-d9300-patch/`（SHA256 清单 1015 项）。
- overlay 同步后 footprint：**867 个已跟踪文件被修改（+22841 / −54427）+ 50 个新文件**。

### 风险与验证（进行中）

- **基线版本差异**：−54427 行删除表明增量基于与 v25.1.0.1 不同的上游版本开发；scons `build/ARM/gem5.opt` 构建验证中，失败则按报错回退基线 commit 或修增量。
- **构建环境备忘**：gem5 v25.1 + conda Python 3.13 链接检查失败（"Can't find a working Python installation"）；改用 Homebrew Python 3.12（`/opt/homebrew/opt/python@3.12/libexec/bin` 前置 PATH）+ brew protobuf 29.3 + scons 4.10.1（`~/.local/bin`）。
- `3dc9dcc`（DDR 报告引用的 commit）不在上游 v25.1 历史中；增量覆盖的 867 个修改文件的 diff 形态可用于溯源真实开发基线（构建通过后做）。
