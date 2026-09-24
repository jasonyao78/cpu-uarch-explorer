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
