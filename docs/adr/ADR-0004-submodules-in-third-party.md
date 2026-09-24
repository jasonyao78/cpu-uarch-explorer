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

## 修订（2026-09-24）：Overlay 方案取代 Fork 优先

收到 D9300 模型增量后发现其自带 overlay 设计（其 README/AGENTS 明确声明：submodule 保持纯上游，增量树为唯一事实源）。经用户确认采用 overlay：

- `third_party/gem5`：官方上游 submodule，钉 `f5c5a6e390`（v25.1.0.1），不直接提交修改；（**钉住的基线已被 2026-09-25 修订取代为 v25.0.0.1**，见下节）
- `third_party/gem5-d9300-patch/gem5`：增量树（本地 gem5 修改的唯一事实源），`apply_patchset.sh` 编译前同步进 submodule 工作树；
- 上游更新 = submodule 快进 + 重同步 + 重建；fork 方案保留为"未来必须修改 submodule 本体"时的备选。

后果：增量在我们仓内可 review/diff、随仓演进；submodule 保持可复现；代价是构建前多一步同步，且同步后 submodule 工作树处于 dirty 状态（已用 `ignore = dirty` 隔离）。

## 修订（2026-09-25）：钉住基线改为 v25.0.0.1 + 同步断言

blob 哈希普查（`docs/gem5-d9300-intake.md`）证明增量树的真实开发基线是 **v25.0.0.1**（873/1008 逐字节吻合）；钉 v25.1 会产生"静默版本混合"（曾致 `m5.internal`、`IQUnit` 类引用失效的构建错误）。决定：

- submodule 改钉 **v25.0.0.1**（`ddd4ae35ad`）；增量树经最小集修剪（135 有意 delta 文件）同步后与上游原版完全一致——无端口工作量；
- `apply_patchset.sh` 新增**基线断言 + 预存脏树检测**（钉错基线或工作树有残留时拒绝同步；`GEM5_SKIP_BASELINE_CHECK=1` 可跳过）——OI-8 的 overlay 加固两项由此落地；
- 移植到 v25.1 列为独立里程碑（backlog）：746 行有意改动中约半数为统计插装，v25.0→v25.1 的 O3 重构（IQUnit 拆分等）需逐文件三方 diff 移植。
