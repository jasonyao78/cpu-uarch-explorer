# third_party — 外部依赖统一管理

政策（ADR-0004）：**所有 submodule 统一置于本目录**，不允许出现在仓库其他位置；新增依赖必须先登记 `LICENSES.md` 再引入。

## 计划引入

| 依赖 | 路径 | 许可证 | 状态 |
|---|---|---|---|
| gem5 | `third_party/gem5`（submodule） | BSD-3-Clause（上游） | 官方上游 submodule，钉 `ddd4ae35ad`（v25.0.0.1，增量树原生基线，ADR-0004 修订）；工作树经 apply_patchset.sh 同步增量后构建（带基线断言） |
| gem5-d9300-patch | `third_party/gem5-d9300-patch/gem5` | 待逐文件 SPDX（开源前检查点，OI-1） | D9300/CoralNPU/NDP/Gemmini 增量树（本地 gem5 修改的唯一事实源，见其 README 与 AGENTS.md） |

## 登记要求

每个依赖记录：名称、来源 URL、引入 commit/tag、上游许可证、是否打过补丁、补丁清单位置。
