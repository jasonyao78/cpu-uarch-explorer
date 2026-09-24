# third_party — 外部依赖统一管理

政策（ADR-0004）：**所有 submodule 统一置于本目录**，不允许出现在仓库其他位置；新增依赖必须先登记 `LICENSES.md` 再引入。

## 计划引入

| 依赖 | 路径 | 许可证 | 状态 |
|---|---|---|---|
| gem5 | `third_party/gem5` | BSD-3-Clause（上游） | 基线已就位：上游 stable v25.1.0.1 @ `f5c5a6e390`（2026-09-24 核实）；**未发现 D9300 修改**；fork→submodule 待办（OI-1，见 `docs/gem5-d9300-intake.md`） |

## 登记要求

每个依赖记录：名称、来源 URL、引入 commit/tag、上游许可证、是否打过补丁、补丁清单位置。
