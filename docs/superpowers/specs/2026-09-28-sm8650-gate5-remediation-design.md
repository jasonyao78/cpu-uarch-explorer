# SM8650 Gate 5 修复与主线解阻设计

**状态**：用户已授权直接修复（2026-09-28）

**目标**：修复正式评审中的证据、术语、THP 观测窗与来源授权问题；同时把
私有 L2 容量的不确定性从“全局阻塞”收敛为有触发条件的局部遗留，使独立的
微架构探索可以继续。

## 1. 方案比较与选择

### A. 只修文档，THP 与容量全部延期

改动最少，但下一次 THP 实验仍可能把测量前 backing 当成测量窗事实，已知的
证据缺口继续存在。不采用。

### B. 修证据链 + THP 双快照 fail-closed + 有界欠账（采用）

保留既有 `page_policy_actual`/`anon_huge_kb` 兼容字段；在 warmup 完成后、
计数器启动前记录 before 快照，在计时和 PMU 窗结束后记录 after 快照。
两端观测失败或 backing/AnonHugePages 变化时退出 1，不输出有效 metrics；
稳定样本追加 before/after/stable 审计字段。旧捕获仍可解析，新字段采用
schema v2 的可扩展字段机制登记。

L2 容量保持 `OPEN/INCONCLUSIVE`，但只阻塞依赖该容量解释的实验，不阻塞
分支预测、TLB、前端、执行端口、访存并行度、跨核延迟等正交主题。

### C. 先彻查 OEM 频率/THP/L2 根因，再开展其他主题

科学纯度最高，但把平台专有且可能长期不可控的问题变成全仓关键路径，无法
形成可结束的研究迭代。不采用。

## 2. THP 观测契约

Linux 普通匿名映射的实际 backing 是测量窗属性，不是 `madvise` 返回值或
单一时刻属性。新成功输出必须满足：

1. warmup 已结束；
2. before `/proc/self/smaps` 读取成功；
3. timed loop 与 PMU 计数结束；
4. after `/proc/self/smaps` 读取成功；
5. before/after 的实际类别和 `AnonHugePages` 完全一致。

稳定时，兼容字段等于两端共同值，并输出：

- `page_policy_actual_before/after`
- `anon_huge_kb_before/after`
- `page_backing_stable=1`

不稳定时只在 stderr 报告两端值并以退出码 1 结束，Runner 按既有 Probe ABI
生成空 metrics 的结构化失败记录。快照在 timed/PMU 窗之外，不污染时延或
事件计数。显式 hugetlb 和非 Linux `platform-default` 由映射机制保证本次
执行内不发生 THP promotion/demotion，仍输出成对字段。

这是一项对 protocol 1.2 既有“逐样本实际 backing”承诺的符合性修复，不
重解释历史记录、不批量改旧 ExperimentSpec；新读者兼容旧输出。

## 3. 证据和措辞修复

- P0″ 报告与生成报告纳入第六个全失败 run，账目统一为 6 runs、156
  records、115 ok、41 failed、1166 artifacts、三次 ceiling drift。
- “热钳位”一律改为观测事实“动态 cpufreq ceiling drift”；根因继续 OPEN。
- 512→640 KiB 只表述为“与 L1 硬件预取活动/覆盖代理崩塌稳定伴生”，不把
  PMU 相关性升级为已识别的上游因果。
- 参考材料明确为仓库所有者主导、可能含并行代理协作的作品；Apache-2.0
  授权依据是已登记的所有者决定，不再声称三份均由单一自然人独立完成。
- 逐字节归档保留原始 Markdown 行尾空格；仅对明确列出的归档文件配置
  `git diff --check` whitespace 例外，不扩大到普通源码/文档。

## 4. 主线继续门槛

采用“依赖切片”而非“一个问题阻塞全部问题”：

- **继续**：实验的问题陈述、指标和结论不依赖精确 L2 容量，且沿用
  environment/probe/schema fail-closed 门禁。
- **条件继续**：需要 cache 层级解释但能把 L2 容量作为区间/潜变量，并用
  PMU 或差分对照隔离。
- **停止**：结论必须把某个 knee 唯一命名为 L2/L3/LLCC 容量，或使用
  不稳定 backing/频率样本作为有效数值。

未竟的 L2 容量、THP 补跑、ceiling drift 根因继续由 `docs/open-items.md`
追踪；触发条件到达时再恢复，不靠永续分支兜底。

## 5. 验证与交付

本机执行 Release、UBSan、runner、analysis、schema/hash/引用完整性检查；
远端 Xeon 用仓库规定的 `rsync -a --delete` 同步到隔离目录，执行 Linux
native 构建、CTest 和真实 `-B` backing 审计。修复以小步提交推送到当前
功能分支，`main` 不动；通过第二次正式评审后再集成。
