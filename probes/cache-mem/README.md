# probes/cache-mem — Cache 与内存层次探测

当前探针：

- `ptr_chase` — 指针追逐内存延迟（clean-room 实现，替代历史 lmbench 衍生 demo，见 docs/adr/ADR-0002-license-apache2.md）。

方法学：在按 stride 切分的缓冲区内构建**随机单环链**（Fisher–Yates 洗牌），沿严格依赖的指针链追逐 N 次，单调钟计时求平均延迟。随机顺序使硬件预取器难以跟踪；每迭代对**同一条链**展开 8 次摊薄循环控制开销——展开不引入额外访存级并行（MLP），这是测量正确性的关键（2026-09-23 冒烟测试曾用 4 条独立链，L1 测量值被 MLP 摊薄近 4 倍而失真，已修正）。

输出：`key=value` 机器可解析行（buffer_kb / stride / loads / elapsed_ns / latency_ns），由 Runner 层包装为 `record.schema.json` 记录。

已知局限（v1）：

- 循环控制开销残余 <1 cycle/load，L1 级测量略偏悲观方向，解读 L1 数值时留意（v0.3 §9 校准需交叉方法验证）。
- 未做页着色/大页控制；TLB 效应与 cache 效应在小步长区间耦合，解读时注意。

## 后续迭代方向（backlog，方法学迁移 OI-9）

- `CLOCK_MONOTONIC_RAW` 替代 `CLOCK_MONOTONIC`（减小时钟调整抖动）。
- hugepage 开关（fallback/strict 两级）+ cold 模式参数化（驱逐后冷测 + 输出温度标签）——遵守 `docs/methodology/measurement-discipline.md`。
- `evict_slc` 类驱逐工具的移植评估（独立小进程，BSD-3 同源，引用需登记来源）。
- 跨核迁移延迟探针（chase_migrate 范式：绑核建链 → warm → 迁核确认 → 测同链，penalty = dst − src）。
