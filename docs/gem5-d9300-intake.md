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

### 构建验证结果（macOS，2026-09-24）

configure 通过（Homebrew Python 3.12 + brew protobuf 29.3 + scons 4.10.1）；**922 个对象编译成功**，含 delta 自带文件（`coral_backend.o`、`coral_stagea_backend.o`、`npu_device.o`、`NPUDevice.py.o`）。唯一硬错误：

```
src/dev/npu/coral_verilated_backend.cc:8:10: fatal error: 'elf.h' file not found
```

`<elf.h>` 为 glibc 专属头文件，macOS 不提供；且 verilated NPU 后端依赖 Verilator + NPU RTL，属 Linux 流程。**结论：overlay 与 v25.1 基线兼容性良好；正式构建平台定为 Xeon 服务器**（runbook：`docs/runbooks/build-gem5-xeon.md`）。macOS 本地构建非 verilated 变体的备选方案：delta 中对 verilated 后端加 `__APPLE__` 守卫（backlog）。首次失败记录：conda Python 3.13 未过 gem5 链接检查（"Can't find a working Python installation"）。

### SE 冒烟仿真（2026-09-24 通过）

- 交叉编译 ARM64 静态 hello（服务器已有 `/usr/bin/aarch64-linux-gnu-gcc`）→ `configs/deprecated/example/se.py --cmd /tmp/hello-arm64` → **`Exiting @ tick 46213000 because exiting with last active thread context`，退出码 0**。
- 注意：ARM-only 构建（`build/ARM/`）跑 x86 二进制会报 `ValueError: No SE workload is compatible`（v25 Workload 兼容性检查），属预期，非故障。
- 结论：**构建 → 二进制可运行 → ARM SE 仿真执行** 全链路验证完毕；gem5 D9300 模型基础设施功能就绪。

### delta 树清理（2026-09-24）

- **已删 `util/`（6 文件）**：`orchestrator-request.py`（纯新增，原项目的分布式编排管道）+ `transmitter.py`、`gem5-resources-manager/requirements.txt`、`dockerfiles/gpu-fs/{Dockerfile,README.md}`、`docker-bake.hcl`（5 个上游文件的改写，均不在 scons 构建路径上，删除后恢复上游原版）。submodule 工作树已同步恢复（`git checkout -- util/`）。
- **保留，待 Xeon 构建通过后定夺**：`ext/pybind11/`（185 文件，旧版 vendored 副本——与 `src/python` 绑定的 API 兼容性未知，删错了编译就挂）、`ext/testlib/terminal.py`（2 行改动）、`configs/example/gem5_library/x86-parsec-benchmarks.py` 与 `riscv-fs.py`、`tests/gem5/example_configs/multisim/`（测试引用关系不确定）。
- **判定保留（项目相关）**：D9300/X4/A720/A510 等 ARM core 模型、`arm_multicore_*` 配置、coralnpu/ndp/gemmini 资产、`src/dev/npu/`、`src/cpu/o3/tdm.*`、`tlm_chi.py`、riscv 配置（v0.3 方向）、`run_multicore.sh`、`scripts/`、`tests/test-progs/{gemmini-apps,ndp}/`。
- 原始档案 `../cpu-uarch-ref/gem5-d9300-patch/`（含 MANIFEST.sha256）保留全部原文件，任何删除可恢复。

## 2026-09-24 三次更新：基线定位与最小集修剪（blob 哈希普查）

### 方法

上一轮清理靠目录语义判断，留有"删错编译就挂"的不确定区。本轮用确定性方法：对增量树全部 1008 个文件计算 blob 哈希，与上游各 release tag 逐路径比对（`git rev-parse <tag>:<path>`），统计吻合数。

### 普查结果

| 上游版本 | 吻合 | 不同 | 基线中不存在 |
|---|---:|---:|---:|
| v25.1.0.1（当前钉住） | 0 | 863 | 145 |
| **v25.0.0.1（=真实基线）** | **873** | **27** | **108** |
| v24.1.0.3 | 659 | 228 | 121 |

- **基线确认：v25.0.0.1**（873/1008 完全吻合，次优 v25.0.0.0 为 865）。OI-1 此前记录的"867 改/50 新"是相对原项目基线的口径，相对 v25.1 的真实效果是"864 个文件被替换成旧版 + 144 个新增"。
- **抽样实证**：`src/arch/arm/isa.cc` 的 diff 为回退 v25.1 变更（copyright 2025→2024、删 `snsBankedIndex64`）——大量"修改"是旧版携带（carryover），非有意改动。

### 修剪执行（最小集 = 有意 delta）

- **删除 873 个纯携带文件**（与基线 v25.0.0.1 逐字节相同）：删除后 sync 不再覆盖，v25.1 原版文件自然保留——顺带消除了"overlay 静默回退上游"的隐性风险。
- **保留 135 个文件**：
  - 相对基线有改动 27 个 = **D9300 模型本体**：`src/cpu/o3/`（commit/cpu/decode/fetch/fu_pool/iew/inst_queue/lsq/rename + SConscript）、`src/mem/DRAMInterface.py`、`cfi_mem.cc`、`coherent_xbar.cc`、`src/python/gem5/components/memory/dram_interfaces/lpddr5.py`、`src/dev/arm/RealView.py`、`configs/common/FSConfig.py`、`configs/example/arm/devices.py`、SConscript 胶水；
  - 基线中不存在 108 个 = **新增资产**：`arm_multicore_{d9200,d9300,heng}.py`、`starter_fs_x{2,3,4}.py`、`configs/{coralnpu,ndp,gemmini}/`、`src/{ndp,ndp_dev_a,gemmini_dev_a}/`、`tests/test-progs/`、`run_multicore.sh`、`apply_patchset.sh`、AGENTS/README 适配版。
- 增量树：1008 → **135 文件**（32MB → 14MB，其中大部分是 tests/test-progs 二进制与 NPU 资产）。
- 上一节"待 Xeon 构建通过后定夺"的 pybind11 问题被普查裁决：182 个文件为纯携带（已删），但 **7 个基线中不存在的 pybind11 文件保留**——若 Xeon 构建报 pybind11 相关错误，第一嫌疑就是它们。

### 验证门（未通过前不算完成）

修剪改变 sync 结果，本地 macOS 无法构建 gem5（elf.h 阻塞），**验证门 = Xeon 重建 + SE 冒烟**，操作命令见 runbook `docs/runbooks/build-gem5-xeon.md` §修剪后回归验证。回滚路径：`git checkout <修剪前 commit> -- third_party/gem5-d9300-patch` + submodule 重置 + 重同步 + 重建。原始 drop 档案（`../cpu-uarch-ref/`，MANIFEST.sha256）为最终兜底。

**若重建失败的最可能根因**：27 个有意改动文件按 v25.0 API 编写，与 v25.1 核心头文件不兼容（如 `inst_queue.hh` 周边 API 在 v25.1 有变更）——届时两条路：从 git 历史恢复携带文件回到全量 overlay（保底），或把 27 个文件 port 到 v25.1 API（正确但工作量大的根治，迟早要做，因为上游更新路线依赖它）。
