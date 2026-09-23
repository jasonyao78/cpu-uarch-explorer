# ADR-0002: 主仓许可证 Apache-2.0 与历史 demo 代码来源审计

- 状态：已接受（2026-09-23）

## 背景

仓库未来开源。候选许可证：MIT / BSD-3 / Apache-2.0，均为宽松许可证，核心差别在专利条款（Apache-2.0 含明确专利授予与反诉条款）。硬件/微架构方向项目未来可能有企业层面使用者，专利条款对贡献者与使用者均为实质保护；与 gem5 的 BSD-3 兼容。据此选定 Apache-2.0。

阻塞问题：历史 demo `cpu-cache-demo-code/mem-lat.c` 与 lmbench（GPLv2）的 `lat_mem_rd.c` 结构高度相似，若构成衍生则 Apache-2.0 不可适用于该代码。

## 审计结论（2026-09-23）

**判定：衍生。** 依据（证据等级：DERIVED，人工逐段比对）：

1. `ONE/FIVE/TEN/FIFTY/HUNDRED` 宏阶梯（`#define ONE p = (char **)*p;` 及其倍数展开）是 lmbench `lat_mem_rd.c` 的标志性写法，逐字一致；
2. 指针追逐计时循环的总体结构（mmap 缓冲区 → 按 stride 建链 → 宏展开追逐 → gettimeofday 计时）与 lmbench 同构；
3. demo README 中 `line_test`/`words_initialize` 的中文逐行走读对应 lmbench `line.c` 的内部结构，佐证该工程接触过 lmbench 源码。

该文件并非逐字拷贝（参数处理、随机洗牌建链、计时细节为改写），但核心基准循环与宏阶梯属于复制的传承谱系，按保守原则判为衍生。lmbench 为 GPLv2，与 Apache-2.0 不兼容。

## 决策

1. 主仓许可证：Apache-2.0（`LICENSE` 全文入仓）。
2. **不迁移** `mem-lat.c` 原件；`cpu-cache-demo-code/` 整体 gitignore，仅作本地历史存档。
3. 以 clean-room 方式在 `probes/cache-mem/ptr_chase.cpp` 重写指针追逐延迟探针：仅沿用公开的测量方法学（随机环链 + 依赖载追逐 + 单调钟计时），不沿用 lmbench 的任何代码结构、宏写法与初始化流程；实现为独立设计（Fisher–Yates 洗牌、4 条不相交环链摊薄循环开销、`clock_gettime(CLOCK_MONOTONIC)`）。
4. 历史数据文件（sm8650/sm8550 结果文本）以副本存 `data/public/legacy/`，标注来源与证据等级（sm8550 为 UNKNOWN，不进任何校准决策）。

## 后果

- 仓库自第一个 commit 起许可证纯净；原 demo 保留在磁盘但不入库、不受 Apache-2.0 覆盖。
- 重写版探针的方法学正确性由后续 M4 Pro 实测验证（对已知缓存层次拐点做 sanity check）。
- 教训写入 `docs/learning/`：引入任何外部代码前先做来源审计。
