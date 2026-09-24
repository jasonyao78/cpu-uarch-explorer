# ADR-0008: 构建目录单一入口与仓库布局修订

- 状态：已接受（2026-09-24 提案；当日用户拍板后按 §清理清单 执行完毕）
- 关联：ADR-0004（third_party 集中）、ADR-0006 §后果（目录随实现落地）、v0.3 §5（目录结构）

## 背景

第三轮评审（`docs/reviews/2026-09-24-gb10-borrow-review.md`）处置完毕后，对仓库做整体结构复审，发现以下问题（均已现场核实）：

1. **构建目录平铺且无谱系**：`build/`（macos-arm64 Release）、`build-ubsan/`（ENABLE_UBSAN=ON）、`build-x86/`（`CMAKE_OSX_ARCHITECTURES=x86_64`）三个平级目录各自手工配置，无任何文件记录配置参数；且 `.gitignore` 只覆盖 `build/`，其余两个长期以 untracked 状态污染 `git status`——在"私有转公开、git 历史全量可见"（v0.3 §7）约束下，误 `git add -A` 把构建产物送入历史是不可接受的事故类型。平台矩阵还将扩展（android-arm64 交叉、riscv64 compile-only、Debug/ASan profile），平铺 `build-*` 命名会组合爆炸（正是 ADR-0006 批评的模式）。
2. **评审工作文件残留**：`review-ref/` 含参考仓源码副本 11 个文件，其许可证矛盾未决（根 LICENSE BSD-3-Clause vs pyproject Proprietary，见 `docs/reference-materials.md`），**绝不可入库**；`review-1826c74.txt` 评审原文已驱动四个文档与一个 schema 的修改，按本仓决策可追溯文化应归档而非删除。
3. **gem5 本机死构建残留**：`third_party/gem5/build/` 约 1.5G，是 macOS 构建尝试的残骸（922 对象编译成功、elf.h 阻塞，commit `ccf1daf`），无 `gem5.opt`，macOS 构建已判定不可行、正式构建走 Xeon（`docs/runbooks/build-gem5-xeon.md`），残留永远不会被续用。
4. **文档落后于实现**：`configs/`（experiments/platforms，声明式配置）已随 runner 最小闭环落地（commit `f260867`）但未入 v0.3 §5；测试按语言分家（`tests/` CTest、`runner/tests/` unittest）符合 ADR-0006"随实现落地"，需正式确认；`data/quarantine/` 被 methodology 引用但尚不存在（文档先行状态，记录即可）。

## 决策

### 1. 构建目录单一入口，按 `<target-triple>/<profile>` 分层

```
build/                              # 唯一入口，.gitignore 一行覆盖
├── macos-arm64/release/            # 默认本机构建（现 build/）
├── macos-arm64/ubsan/              # UBSan 变体（现 build-ubsan/）
└── darwin-x86_64/release/          # x86_64 交叉（现 build-x86/，CMAKE_OSX_ARCHITECTURES=x86_64）
```

- 驱动机制：**CMakePresets.json**（本机 cmake 4.3.2、Xeon Ubuntu 24.04 自带 cmake 3.28，均远超 presets v3 所需的 3.21；声明式、参数谱系入库、IDE 友好）。`scripts/build.sh` 作为不引入新文件的备选方案，不采用。
- 每个 configurePreset 显式声明 `binaryDir` 与 `cacheVariables`——构建配置谱系从此入库可审计。
- CMakeLists.txt 本体不改（`ENABLE_UBSAN` option 保留，preset 传 `-DENABLE_UBSAN=ON`）。

### 2. `.gitignore` 收敛

构建忽略收敛为 `build/` 一行（分层后全覆盖），消除"未跟踪但未忽略"状态。

### 3. 评审文件处置

- `review-ref/`：删除。裁定已全部落入 commit `b0a67bf`/`0b2d70e`；原始出处 `~/gb10-cpu-arch-probe` 钉 `f0b4013`，可随时复查；许可证矛盾未决前其源码副本不得进入本仓 git 历史。
- `review-1826c74.txt`：归档为 `docs/reviews/2026-09-24-gb10-borrow-review.md`（纯文本评审意见，无许可证问题），CHANGELOG 第三轮条目补指向。

### 4. gem5 侧

- 删除 `third_party/gem5/build/`（约 1.5G 死残留；已被 gitignore，删除零风险）。
- `third_party/gem5-d9300-patch` **维持现名与 overlay 方案**（ADR-0004 修订不变）：改名 `gem5-d9300-overlay` 虽更名副其实，但牵连 OI-1 / LICENSES.md / runbook 一串引用，churn 大于收益。存量工作（SPDX 逐文件复核、同步加固）仍按 OI-1/OI-8 执行。

### 5. 布局确认与文档补登记

- `configs/` 正式入册 v0.3 §5：`configs/experiments/`（ExperimentSpec 实例）+ `configs/platforms/`（平台画像/控制/二进制映射）。
- 测试维持按语言分家：`tests/` = C++ CTest（probe 边界/契约），`runner/tests/` = Python unittest（随包）。不物理搬家，写入本 ADR 与 README。
- `data/quarantine/` 保持文档先行：首份隔离数据出现时再建目录。

## 清理清单（拍板后按序执行）

1. `mkdir docs/reviews`，`review-1826c74.txt` → `docs/reviews/2026-09-24-gb10-borrow-review.md`（入库）
2. 删除 `review-ref/`（11 个参考仓副本，不入库）
3. 删除 `third_party/gem5/build/`（约 1.5G）
4. 新增 `CMakePresets.json`（三个 preset：`macos-arm64-release` / `macos-arm64-ubsan` / `darwin-x86_64-release`，binaryDir 指向上文分层路径）
5. `.gitignore` 构建忽略收敛为 `build/`
6. 用 presets 重新配置三个构建目录并全量重建；`ctest` 与 `runner` 22 项测试回归
7. 更新 `configs/platforms/macbook-m4pro-01.json` 的 probe 路径（`build/probes/...` → `build/macos-arm64/release/probes/...`）
8. 删除旧 `build-ubsan/`、`build-x86/`（`build/` 在分层重建后已被新树取代）
9. 文档同步：v0.3 §5 补 `configs/`、README 仓库导航、CHANGELOG、runbook 中构建命令改 preset 形式
10. 重跑一次 ptr-chase-cache-sweep（新路径）验证闭环不回退

## 后果

- 构建配置从"手工记忆"变为"入库可审计的 preset"，与数据层 provenance 原则对齐。
- `git status` 永久干净；误入库构建产物的风险消除。
- 迁移成本：三个构建目录内容全部重新生成（无增量迁移价值，CMake 缓存不可搬运）；runner 配置路径一处修改。
- 代价：`cmake --preset` 比 `cmake -B build` 命令略长；可接受。
