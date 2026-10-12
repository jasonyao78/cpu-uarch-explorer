# TLB同VA集合的物理邻接干预（预注册v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-tlb-full-pointer-representation-results.md` 的495真机窗显示：全位指针编码确实改变低地址投影，几何差仍存在；dense物理页又有大量PFN邻接。下一检验相邻物理页是否为低walk/reach的必要条件，而非再重跑不同VA布局。采用同VA集合、同物理需求轨迹，改变VA→PFN关联；不能把这种干预阳性唯一归因HPA，也不能把阴性当全部聚合机制被排除。

Arm官方本地 `../cpu-uarch-ref/docs/Arm_Cortex_X4_Core_TRM_102484_0003_06_en.pdf` §5.1/§5.2以及ECTLR HPA_DIS/HPA_L1_DIS说明MMUTC同时承载I/D和intermediate descriptor、支持硬件页聚合；目标r0p1而参考r0p3，未读取实际ECTLR/PTE_CONT。常规连续PA范围聚合要求一致的VA→PA连续关系，这是本实验约束的模型；不预设所有硬件压缩必须使用该形式。

## 配对与实际激励

新 `probes/diagnostic/tlb_pfn_association.cpp` 和 `probes/diagnostic/tlb_pfn_association_layout.h`。4096页memfd与canonical映射；一个2MiB对齐、16MiB的自有VA arena全页base-backed/预fault，remap仅在自有映射内。每个N使用canonical节点0..N−1，两个assignment:

- natural：VA位置j→物理节点j。
- no-adjacent：VA位置j→节点π[j]，π为全排列、π[j]%64=j%64；每一对相邻active VA页实际PFN差不为±1。只重排前N映射；其余映射不删除，不能宣称物理PTE页地址不变（未观测）。

物理节点i始终offset=64*(i%64)，因此π保留余数同时保持**完全相同的VA页/line集合、offset分布、物理页/line集合与物理访问顺序**。相同seed137物理节点闭环与反向order，stored pointer均全位XOR 0x9e3779b97f4a7c15；复用相同四ISA decode body并独立审计真正调用点。π改变虚拟访问顺序，这是无法同时消除的残余，阳性只能称VA→PFN关联敏感（可能包含replacement/VA预取/descriptor时序），不唯一称HPA。

布局器按实际canonical PFN计算：从identity起，取最低位置bad邻接边(a,a+1)，令b=a+1；枚举同b%64的其它位置c，选择最小c，使交换b/c后涉及b−1,b,c−1,c的所有合法边都非邻接；交换，重复直到0bad。每次至少移除一bad且不引入新bad，因此有限停止。唯一PFN的±1关系度数≤2；b两邻居最多排除4个候选节点，原b节点与c邻居的关系最多排除4个候选位置，另排除b自己；每bin≥16，至少一个候选存在。实现仍须独立验证全排列/余数/实际PFN0bad，找不到候选为硬错误，不能fallback或挑seed。PFN重复、零/不可见/swapped、迁移或canonical/alias不一致都拒绝。

## 固定有限矩阵和测量门

N={1024,1280,1536,1792,2048,2304,2560,3072}，assignment×两order×8N=32+1floor；3窗/cell×3fresh epochs=**297窗**。epoch1反向cell顺序；warm与每窗load=(1048576/N)*N，头必须回到闭环起点。CPU7/4096、GROUP+ID/pinned/user-only/noRESET/noMUX，events=[0x11,0x08,0x05,0x34,0x8154,0x8155]。15秒进程间隔；baseline walt且仅只读环境，任何运行冲突/环境违规即停留证。

hard门：真实plan/code/graph、每cell前后canonical和alias raw pagemap以及smaps4KiB/nohuge一致、no-adjacent实际0邻接、IR=4*loads±max(1000,1%)、typed IDs/counts、noMUX/完整覆盖。背景门保持前批：floor cycles≤当前cycles1%，floor L1 dTLB refill/walk≤.001*loads；每窗refill/load∈[.75,1.25]。tap背景单独≤.001*loads，辅助失败不得洗掉主结果。raw地址/PFN/实际words留private，public只导出审计计数/所有PMU值和带符号差。

## 主判据与局部reach（观察名称，不是物理容量）

每N六epoch/order配对，以3窗总walk/总loads计算Δ=no-adjacent−natural。全部同号且|Δ|≥.10→该N复制关联敏感；任一N满足且主门全过→ASSOCIATION_SENSITIVE。所有N全部六差|Δ|<.10→ASSOCIATION_NOT_CHANGED_AT_DETECTION_SCALE；其它→INCONCLUSIVE。floor/技术/背景未过→命名不可算，保留全部数据，不删窗改门。

负结论额外区分激励：natural在至少两个N≥1792，三个epoch都实际ascending PFN邻接比例≥.10，才称CONTIGUITY_CONTROL_EXCITED；否则NOT_EXCITED，不能说“移除聚合没有影响”。即使激励通过，尚未直接观察聚合实际启用；若无邻接下低walk/相同转折仍保留，连续PA聚合不是该新协议行为的必要解释，不能回填旧UNKNOWN。

逐assignment/order/epoch八点曲线独立分类，walk/load≤.05为below、≥.20为above、其间ambiguous；不可算/非单调先命名，不把均值变锐。首次above两侧都有below/above，且至少两个连续above高侧点→操作区间(last below, first above]；全部below→right-censored、首点above→left-censored、仅末点above→right-censored、ambiguous→ambiguous。六曲线区间逐字相同才复制；其它heterogeneous。导出完整signed curves，不报MMUTC physical entries/ways。这个阈值只是有限reach定位规则，不是硬件pagewalk容量方程。

## 软件出口与谱系

consumer `tools/diagnostic/tlb_association_analysis.py`、driver `tools/diagnostic/run_sm8650_tlb_association.py`、tests `tools/diagnostic/tests/test_tlb_association*.py`、公开evidence `docs/reviews/evidence/2026-10-12-tlb-pfn-association/`。先pure布局RED/GREEN与恶意PFN/余数/边验证、真实host共享FD remap图、plan→driver→写盘→raw审计及重哈希反例；双NDK/实际机器码/IR，source/build/launch分开，整批完成后独立raw算术和图报告。

此前825/279/333/495数据不并批。owner当前primary独占、branch codex/sm8650-tlb-hierarchy-r2。无新增系统写入/内核模块/EL3操作；工程接入和physical未知继续 `docs/open-items.md`，有限反例不是总体目标完成。
