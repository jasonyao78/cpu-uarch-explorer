# TLB翻译身份倍增：下一鉴别方案草案（未冻结、未采样）

## 本次任务的目的（给人类看）

在Gunyah下保持同一数据IPA/PFN轨迹，主动改变Stage-1的VA/ASID身份数，区分叶翻译身份与物理数据页数量解释。`docs/reviews/2026-10-13-translation-persistent-read-results.md` 提供可扩展own descriptor入口；本稿只定义新控制，不冒充已实现、已冻结或物理容量结论。

三个配对：A同ASID同一alias反复访问N物理页；B同ASID两VA alias各N页，2N翻译身份仍N物理页；C两own进程不同mm/ASID、相同VA各N页，2N身份仍N物理页。三者每组物理需求顺序相同（同N-page ordinal cycle重复两次），实际storedwords/offset/dataPFN一致。当前OS同一VM的相同IPA数据被复用，但不假称已读HCR/VMID/HPA；只把差异的Stage-1身份作为干预。

## 必须先解决的接缝与反证

1. 两进程不同mm不自动证明当时硬件ASID数值。优先查目标BTF下mm.context.id合法自有观察；或把“两个context”作为保守名字，用跨context无数据访问阴性证明没有强制TLBI。root/PTE observer分别按各自TGID加载，不让父observer任意读子mm/其它进程。
2. C增加了其它页表/intermediate translation，B也增加页表空间；两者所有root/parent/leaf身份和初始CONT须实际捕获。不能简单2N横轴直接反推出纯leaf容量；先做descriptor-aware reach、固定VA/dataPFN的实际table关联控制。
3. **禁止每次切回先warm自己N页再测**：这会把对方逐出后本地收敛，从而消掉要看的容量响应。应比较切回后的first-pass与不再切换的second-pass；其它context先访问自己的declared graph，协议精确固定。A/B需要相同IPC/context包络的无访问伙伴阴性。
4. 所有IPC、context等待/唤醒在计数外；core7串行、task-owned PMU GROUP/ID/无MUX。所有thread/child可控收尾；原始pid/VA/PFN只private。观察器全部卸载才性能窗；切换额外kernel数据/cache污染需匹配控制与独立tap，不把exclude_kernel误称无系统干扰。
5. 小规模必须先证明samePFN、current context切换、首/二pass计数和低walk负控，然后才大N。例子N256用于L2无容量压力/有L1压力的控制；N32可辅助L1，但一次读数/计时包络粒度需独立校准。具体grid/round/阈值留待实现前冻结，不从当前或未来结果调门。

## 预测权限与停止

若B/C在相同总身份数附近复制转折、A低walk，会削弱“仅数据IPA页数”解释；若C与A一样而B变坏，则需考察ASID索引、页表几何/上下文刷新，不能强名唯一hash。若first/second-pass阴性或ASID/context激励失败，命名拒绝/NOT_EXCITED，停止矩阵。中间descriptor和组合翻译仍可能共享MMUTC，物理2048/8way必须额外证据。

现物理参数0/3。近期执行顺序：已验证persistent observer → large-N真实descriptor/graph/PMU连接 → 固定VA/dataPFN改变实际table关联 → 冻结本身份倍增对照 → 若可识别再精测容量/候选index。ROB issued/fill/history缺口独立另案，旧not-qualified不回填。所有owner/触发 `docs/open-items.md`。
