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


2026-10-14实测补充：register-only实际1536 A8/Mpre0全门通过（3b888d4），before/after值一直留GPR并在两端SB防OOO跨边界，元数据/写回/ABI加载在区间外；仅程序顺序不能证明observer访存在区间外。同PCwarm替换observer words为NOP避免未验证MRS。dynamic plans必须由当前ownFD metadata、原native recipe与actual全部word共用绑定。

单位反例58b7128：NOP/zero/sink/live逻辑OP/DP都perISA+1，不能依据OP_RETIRED名称认证fusion后slot或执行资源；完整失败保留。微op数、issued-operation、有效在飞窗口、物理ROB entries分别命名。pureunit计时应另加workload完成边界，不能把afterMRS程序顺序当作所有老操作已完成；后续资源竞争需可观察最终checksum和对应供给反证。

## 最终热链与内核往返（2026-10-14 实测）

同VA warm-image不足以保证正式长JIT代码热：最后RW→RX之后要重新预热实际配方。v1供给门失败，v2 current-binding warm把refill降低但仍约2；v3把perf FD read和sched_getcpu移出4warm+1formal后，十个完整配置正式refill中位0（`docs/reviews/2026-10-14-rob-filler-resource-batch-results.md`）。warm0仍冷、后面为热，所有旧失败保留；这是观察器/内核往返干扰控制的实测证据，不自动认证ALU端口或ROB条目。

正确包络：一个GROUP+ID的真实绝对FD before/after包含5个独立direct ROI；每call都有当前own metadata、index/width/seqlock/offset/SIGILL检查，不能用外层binding替代内层。五者共享FD绝对值与enabled/running包络时间，direct delta每call独立算，所有before≤after均被绝对FD包围；原始trace和ordinal必须齐备。打印、代码权限/字修改及所有系统调用都在热链外。时间标签不得称每call独立FD时长。

首技术失败协议使v3在第11进程ROI-metadata-changed停止，10/16完整不能报16/16。下一版本可预注册小额技术invalid预算（仅明确metadata失效、不按指标筛选、固定ordinal/无retry/无补样、部分配对须显式覆盖）；这不能回救原批或把拒绝值填0。实现需在真实producer→raw→criterion对丢失/冲突/乱序进行反例，未完成前不启动admission长矩阵。

有限metadata新采样（`docs/reviews/2026-10-14-rob-filler-resource-bounded-results.md`）16fresh4096正式/16384warm、invalid0、原资源/供给门通过。旧首停失败不重新命名。固定ordinal只允许真实ROI-metadata-changed≤1/256，partial warm与rejected原字均保留；其它错误仍停；统计用共同有效trial≥31/32及真实trial标签，禁止数组重编号把near/far条件错接。新 `tools/diagnostic/owned_roi_packets.py` 在真实native计划身份上拒绝缺失/重复/冲突、接受记录置换不改变结果。

最老cold-head反例（`docs/reviews/2026-10-14-rob-cold-head-results.md`）：marker/供给/long excitation已正，但整个带标记窗口的L1D差不一定等于head数；near/out/metadata cache交互及fresh-process物理布局可以进入差分。采用同进程/sameVA-PFN-counter的hot/cold交错，state必须进入身份键；页内offset隔离是独立预注册控制，不能把总refill唯一归属某个PC。完整硬件positive与模型资格failure要分别命名，不能一个失败让另一事实变0。

同映射冷热state512实测（`docs/reviews/2026-10-14-rob-cold-head-interleaved-results.md`）：state进入schedule/warm/formal/invalid/rejected及统计身份键，真实load地址从map_base+offset共同出口生成，内容链和munmap必须用对应地址域。parser只允许注册256/512，duplicate/conflict/missing/state碰撞首停，旧v1原4096/16384失败保持。1024 cache/long/供给全通过仍不等于整批资格：near机会只有7/4<8时要保留失败，conditional far1不能消除不足。下一按真实wrong-direction事件联合检验机会，不把branch预测变动或稀少issue变成容量。

事件名必须从匹配TRM和原协议核对，不凭回忆：本轮报告曾把0x22误标BR_PRED（实际BR_PRED=0x12）；0x22实际BR_MIS_PRED_RETIRED。修订只改解释，不改raw编号。已有512issue窗的whole-ROI 0x22与extraLD/ST联合模式零反例；资格失败可以来自可观察错误方向机会不足，不能自动叫deadline/ROB限制。无0x22的cache palette不能被补成同样结论。固定PC复用历史的独立反证应记录actual per-packet code/branch PC；不同PC必须作为真实干预列出，不假装完全同代码VA。
