# SPDX / 许可证清单

> 新增或更新第三方依赖时同步维护本表（ADR-0004）。主仓自身代码许可证：Apache-2.0（见根目录 LICENSE）。

| 包 | 引入路径 | 来源 | 版本/commit | 许可证 | 补丁 |
|---|---|---|---|---|---|
| gem5 | `third_party/gem5`（正式 submodule） | https://github.com/gem5/gem5.git | stable @ `ddd4ae35ad`（**v25.0.0.1**，2026-09-25 由 v25.1 改钉：增量树真实基线，ADR-0004 修订） | BSD-3-Clause（见 third_party/gem5/LICENSE） | 无（上游纯净；本地增量走 overlay，见下一行） |
| gem5-d9300-patch（本地增量树） | `third_party/gem5-d9300-patch/gem5` | 用户提供内部 delta；原始 drop 只读归档于 `../cpu-uarch-ref/gem5-d9300-patch/`（含 SHA256 清单） | 2026-09-25 修剪后最小集：**134 文件**（基线 v25.0.0.1 上有意 delta：26 改 + 108 新；普查见 `docs/gem5-d9300-intake.md`） | **逐文件 SPDX 待补**（用户已确认无权属问题；开源前检查点，OI-1） | overlay 同步进 submodule 工作树（apply_patchset.sh） |
| AArch64-Explore | `third_party/AArch64-Explore`（正式 submodule） | https://github.com/name99-org/AArch64-Explore.git | main @ `9e3d4646b296fc2948a3343c04bbc0a7835d4f79`（2026-09-28 引入即上游最新 tip） | **无 LICENSE（保留所有权利 / all rights reserved）**——见下方专项说明 | 无（上游纯净；只读参考，禁止复制/修改其内容入本仓） |

### AArch64-Explore 专项说明（无 LICENSE 依赖的处置约定，2026-09-28 用户决策）

- **性质**：Apple Silicon（M1–M4）微架构探测文档与探针代码，是本仓
  M4 Pro 工作的**权威参考资料**（用户裁定"重要资料入库"）。
- **合规口径**：上游无 LICENSE = 保留所有权利。git submodule 机制
  只在仓内保存**提交指针 + URL**（clone 时从上游 GitHub 拉取），本
  仓不分发其代码 blob；`docs/`、`probes/` 等本仓目录**禁止**复制其
  文件内容（需要其方法时按"方法学借鉴、自己实现"处理，同 CPUSUIT
  纪律）。
- **上游风险**：作者变更许可/提出异议/删库时，按既定移除预案执
  行——`git submodule deinit -f third_party/AArch64-Explore &&
  git rm third_party/AArch64-Explore`（单提交摘除指针，无需改写历
  史；历史中仅存的只是 URL 与 commit 号）。
- **钉版纪律**：pinned commit 的变更只能经"评审 + 更新本表"的提
  交完成，禁止在 submodule 工作树内本地修改（保持上游纯净，同
  gem5 的 ignore=dirty 约定精神）。

## 本地未入库的参考材料（明确**不是**本仓依赖）

| 目录 | 内容 | 许可证状态 | 处置 |
|---|---|---|---|
| `../cpu-uarch-ref/cpu-cache-demo-code/`（仓库外） | 历史内存延迟 demo（lmbench 衍生，GPLv2） | 不随本仓分发 | 存档参考（ADR-0002） |
| `../cpu-uarch-ref/cpu微架构材料/`（仓库外） | 第三方 CPUSUIT 探针工程 + 个人 gem5 DDR 分析 + 未知作者材料 | 无 LICENSE / 部分本人作品 | 评审中（OI-7）；CPUSUIT 仅方法学借鉴、禁搬代码 |
