# probes/cache-mem — Cache 与内存层次探测

当前探针：

- `ptr_chase` — 指针追逐内存延迟（clean-room 实现，替代历史 lmbench 衍生 demo，见 docs/adr/ADR-0002-license-apache2.md）。

方法学：在按 stride 切分的缓冲区内构建**随机单环链**（Fisher–Yates 洗牌），沿严格依赖的指针链追逐 N 次，单调钟计时求平均延迟。随机顺序使硬件预取器难以跟踪；每迭代对**同一条链**展开 8 次摊薄循环控制开销——展开不引入额外访存级并行（MLP），这是测量正确性的关键（2026-09-23 冒烟测试曾用 4 条独立链，L1 测量值被 MLP 摊薄近 4 倍而失真，已修正）。

输出：`key=value` 机器可解析行（buffer_kb / stride / loads / elapsed_ns /
latency_ns / warmup / 页策略），由 Runner 层包装为 `record.schema.json` 记录。

已知局限（v1）：

- 循环控制开销残余 <1 cycle/load，L1 级测量略偏悲观方向，解读 L1 数值时留意（v0.3 §9 校准需交叉方法验证）。
- 随机置换只随机化逻辑访问顺序，未控制 4 KiB 物理页的 PFN/color；TLB、
  page walk、PIPT cache set/bank 冲突仍可能与 cache 效应耦合。

## 后续迭代方向（backlog，方法学迁移 OI-9）

- ~~hugetlb 开关~~ ✅ 2026-09-25 已实现：`-h`（缺页池回退并显式标注）/
  `-H`（严格，退出 2）。~~THP 实际 backing~~ ✅ 2026-09-27 已实现：
  `-T` 请求 `MADV_HUGEPAGE`，warmup 后/测量前与 timed/PMU 窗结束后各
  解析一次 `/proc/self/smaps`，分别输出
  `page_policy_requested`、`page_policy_actual=base|thp|mixed` 与
  `anon_huge_kb`，并保存 before/after 与
  `page_backing_endpoints_equal=1`。两端实际类别或 `AnonHugePages` 不同
  时退出 1、不产有效 metrics；端点相同不能排除窗内瞬态变化。不能由“无
  hugetlb pool”推出“无 hugepage”，也不能把 madvise 成功当作实际 THP。
  Linux 普通匿名映射在目标区间两侧保留
  `PROT_NONE` guard page，使 `/proc/self/smaps` 的 VMA 级
  `AnonHugePages` 可保守、精确地归属于被测 buffer；guard page 不参与访问，
  也不改变中间区间的 default/THP 策略。
- `CLOCK_MONOTONIC_RAW` 替代 `CLOCK_MONOTONIC`（减小时钟调整抖动）。
- cold 模式参数化（驱逐后冷测 + 输出温度标签）——遵守 `docs/methodology/measurement-discipline.md`。
- `evict_slc` 类驱逐工具的移植评估（独立小进程，BSD-3 同源，引用需登记来源）。
- 跨核迁移延迟探针（chase_migrate 范式：绑核建链 → warm → 迁核确认 → 测同链，penalty = dst − src）。
- **多链带宽模式（--chains N）**——2026-09-27 LLCC 方法学讨论定级 P1：MLP=1 延迟轴对容量/替换策略不敏感（SM8650 实证 14-32M 缓坡无膝点），吞吐 cliff 是独立第二物理量；触及 Probe ABI，单独评审后动。
- 逐 rep 分布 + 双峰检测（statistics.py，定级 P2，runner 侧，独立于 probe）。

### runner 侧配套 backlog（2026-09-27 LLCC 方法学讨论）

- **SUPERSEDED（2026-09-27 证据重审）**：旧 P0 的单次相机/亮屏差分已
  因互相矛盾而否决，不能验证 6 MiB 共享或 camera slice 竞争；重测必须
  配对/随机交错并保存 active camera client 前后状态。
- P1：先修完整 ring pass warmup 与 THP 实际 backing，再做 X4 2 MiB L2
  校准；私有 L2 不能识别时停止外层 cache **容量定案**，不扩散阻塞到
  分支预测、TLB、前端、执行端口、MLP、跨核迁移等正交主题。
- P1：armv8 core PMU 事件（L2/L3 refill、DTLB walk）与 chase 同步采；
  LLCC PMU 先走用户态 `perf_event_open(type=9, config=0x1000)`。此前
  `0x00..0x27` 的 `ENOENT` 未覆盖该事件，不能定案为“零事件”。
- P2：cross-core 干扰编排进 experiment spec（probe 保持单一职责，并发在 runner 层）。
