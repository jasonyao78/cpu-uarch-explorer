# TLB 层次与自有 counter 窗口工作流

## 本次任务的目的（给人类看）

复用本轮有效判别方法，避免文档规格、proxy、实际容量混成一个数。结果落点 `docs/reviews/2026-10-13-sm8650-tlb-hierarchy-findings.md` 和 `docs/reviews/2026-10-13-pmu-bounded-counter-results.md`。

1. 先核对target MIDR和参考修订，分别列L1 i/d、unified L2；查主表与debugRAM交叉证据，冲突保留。规格2048/256×8不能强制leaf reach=2048或给hash命名。
2. 小型测量也要同时看L1 refill、walk和cache/branch，不只看周期。小N32同offset已经cache refill≈1，是实测反例；每page轮换cacheline、同PFN aliases/order及相同ISA形状控制后才读容量转折。
3. 粗扫描定位，另预注册相邻页新binary和N32资格，不重新给旧raw套fine阈值。i49约7%refill低于旧.10但远高于floor，因此新below.001/above.005需事先冻结，旧ambiguous不回填。报每epoch/alias/offset全部曲线与混合状态。
4. 直读PMU用自己FD当前mmap的cap/index/width/offset/even sequence，不把root/open/cap=true作为许可，不复用上次index。index0不MRS；64bit offset/raw总值及delta模回绕、GROUP+ID绝对包含比对、knownwork正控都过，才说读数路径可用。
5. metadata变动是该窗口失效，不是未发射或0次。若固定窗口预算允许loss，先注册最多invalid/每role覆盖/完整trace，不看metric选择、不补采、不救旧batch。实际v1失败保留，v2本次72/72且0invalid，不是通过放宽metric门获得结果。
6. 所有临时profile只动已登记sysctl，private write-ahead、finally restore/readback、restore-failed也保存；每新board批检查runner及自有perf两类journal终态，固定单操作者。无global PMCR/PMUSERENR/counter值写入。
7. 长8192 knownwork不等于8marker短ROI精度，4event不等于6event能力；下一短ROI先自己的metadata和marker阴阳控制，再filler/单位/供给/生命周期。组件资格不代替ROB容量；旧384图示或g+chain proxy不晋升。

每批source/build/launch/raw SHA分列、actual生成word/IR/producer→consumer→criterion连通、原失败/被拒trace保留。复核直接用原JSONL第二算术，公开只匿名计数，不把PFN/offset/kernel地址/serial入Git。局部loop同时比较native plan和实际ELF decode，宏变体保留默认合同。全回归必须给真实范围/测试数；新加probe不能蹭此前708通过。
