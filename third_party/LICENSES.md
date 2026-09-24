# SPDX / 许可证清单

> 新增或更新第三方依赖时同步维护本表（ADR-0004）。主仓自身代码许可证：Apache-2.0（见根目录 LICENSE）。

| 包 | 引入路径 | 来源 | 版本/commit | 许可证 | 补丁 |
|---|---|---|---|---|---|
| gem5 | `third_party/gem5`（正式 submodule） | https://github.com/gem5/gem5.git | stable @ `f5c5a6e390`（v25.1.0.1 线） | BSD-3-Clause（见 third_party/gem5/LICENSE） | 无（上游纯净；本地增量走 overlay，见下一行） |
| gem5-d9300-patch（本地增量树） | `third_party/gem5-d9300-patch/gem5` | 用户提供内部 delta；原始 drop 只读归档于 `../cpu-uarch-ref/gem5-d9300-patch/`（含 SHA256 清单） | 2026-09-24 入库快照 | **逐文件 SPDX 待补**（用户已确认无权属问题；开源前检查点，OI-1） | 覆盖上游 867 文件 + 新增 50 文件 |

## 本地未入库的参考材料（明确**不是**本仓依赖）

| 目录 | 内容 | 许可证状态 | 处置 |
|---|---|---|---|
| `../cpu-uarch-ref/cpu-cache-demo-code/`（仓库外） | 历史内存延迟 demo（lmbench 衍生，GPLv2） | 不随本仓分发 | 存档参考（ADR-0002） |
| `../cpu-uarch-ref/cpu微架构材料/`（仓库外） | 第三方 CPUSUIT 探针工程 + 个人 gem5 DDR 分析 + 未知作者材料 | 无 LICENSE / 部分本人作品 | 评审中（OI-7）；CPUSUIT 仅方法学借鉴、禁搬代码 |
