# 无系统调用插入的热ROI对照 v3.0

## 本次任务的目的（给人类看）

v2最终RX后预热确实把大程序warm0的I-refill从约15降到后续约2，但正式窗仍越过≤1原供给门；不复评分。warm与正式之间每次perf FD读取会进入内核。本版独立检验观察器干扰：同一个绝对FD GROUP/ID读包围4warm+1正式，内层每call仅用户态当前metadata/JIT硬件计数，**无read syscall、无权限/代码变更、无打印**。该改动不改payload、16配置/4096正式+16384warm、事件或任何统计门；沿用 docs/design/2026-10-14-rob-filler-resource.md。

producer probes/diagnostic/rob_filler_resource_batch.c；consumer tools/diagnostic/rob_filler_resource_batch_analysis.py；controller tools/diagnostic/run_sm8650_rob_filler_resource_batch.py。每call前后全部own metadata仍验证，index不得从外层继承跳过核验。FD绝对before必须≤全部5组direct before≤after≤共同FD绝对after，五组共用同一个实际ID对齐FD delta，所有direct delta分别重算且≤这个外包络；enabled/running是包络时间，不能称每call独立时长。任意metadata变化/包络失败即技术失败，不以其他call替补。

64无PMU的原warm-image训练后最终RX、FD before、4当前绑定warm、1当前绑定正式、FD after，最后输出完整warm/正式原始trace。私有raw保留每call锁/offset/index/hardware及共同绝对FD值，供消费者交叉核对包络相同和按ordinal完整。0→1→0的write-ahead/finally恢复不变，frequency/governor不动。旧v1/v2失败保留。若仍有refill，继续报告供给未合格；若减少且资源差不变，仅取得资源响应控制，不直接认证ROB。
