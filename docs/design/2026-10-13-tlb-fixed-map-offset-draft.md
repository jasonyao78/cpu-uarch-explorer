# 固定映射的页内cacheline对照（草案，未实现／冻结／采样）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-13-tlb-descriptor-dose-results.md` 的N+PT预测不够；每页offset0可能引入严重data-cache set压力。下一保持VA页/PFN/PT关联不变，在同process、同代码里改变页内cacheline，分辨纯translation键解释与data/cache/时序相关响应。不能先假定缓存confound就是全部原因。

候选三几何stride5/131/515，同memfd/same页访问ordinal／低8直方图，每页在offset0及(i&63)*64各放同next ordinal，两种copy不新增翻译页。整个映射与PTE表在六role（3geometry×2offset）期间保持；初始observer读page-base的安装（do_set_pte地址page-aligned），不以非零offset当requestVA导致NOT_EXCITED误诊。测后检查两份word/PFN/页映射，不把初始table PA当稳态。

同6ISA loop用于所有role：LDR x0,[x0]；AND x11,x0,x12；MADD x0,x0,x9,x10；ADD x0,x0,x11,LSL#6；SUBS x8,x8,#1；B.NE。x12=0或63，只输入变；head也含对应offset，完整circuit返回。同offset时跨geometry物理需求line/order一致；跨offset刻意改变data cacheline但VA页、dataPFN、PT映射相同。实际ELF/IR=6／typed消费链／独立资格与前后floor需另冻结，不能借旧4ISA资格。

预判仅报offset-sensitive/not-changed-at-frozen-scale的translation响应，匹配paired geometry×offset DID，所有unexcited/mixed/删失保留；cache/refill/cycles并列，6ISA新增ALU地址生成／到达时序也是替代原因，不唯一叫L1D conflicts。尚无producer/consumer/threshold/grid/frozen预算，不能上板。

另一独立候选：同VA/dataPFN/ordinal重新安装而验证实际PT PA关联发生变化，matched remap/sham、准备和mm/ASID约束；不激励则NOT_EXCITED。完整设计未交付；禁止猜全局PA或修改PTE／EL3。两者 `docs/open-items.md`，primary branch codex/sm8650-tlb-hierarchy-r2。
