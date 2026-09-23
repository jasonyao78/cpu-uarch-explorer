# ADR-0004: 全部 submodule 统一置于 third_party/

- 状态：已接受（2026-09-23）

## 背景

仓库将引入多个外部依赖的源码级集成（首要为 gem5 D9300 O3 模型 fork，还包括可能的第三方探针库）。根目录散落 submodule 不利于许可证扫描与结构 clarity。

## 决策

- 所有 submodule 统一放 `third_party/<name>/`，gem5 即 `third_party/gem5`；不允许根目录或其他位置出现 submodule。
- SPDX/许可证清单集中在 `third_party/LICENSES.md`，新增依赖必须先登记后引入。
- gem5 接入时（待用户提供源码，见 open-items OI-1）：fork 到个人账号 → submodule 钉 commit → 在本 ADR 追加基线 commit 与补丁清单。

## 后果

- 根目录干净；许可证审计范围确定；构建脚本统一引用 `third_party/` 路径。
- 代价：文档/命令中的路径稍长，可忽略。
