# ROB生命周期代理：E0发现、盲留E2验证（v1）

## 本次任务的目的（给人类看）

原 `docs/design/2026-10-12-rob-zero-latency-units.md` 的完整2352窗正在按原矩阵执行。E0已经完整，原始目录 `data/private/20261012T102234Z-rob-zero-latency-units-scan`，source5aecbbb/build7c7647e/actual launch3124a73；E1已采部分、不纳入新验证，E2尚未开始。目的：用原定但尚未观察的E2检验E0提出的生命周期预测；不增加设备采样、不改原协议、不把超Icache门的点回填成原主判据合格。

## 发现与模型的错误边界

E0两NOP-eligible类的chain16首次near-serial为g352、chain32为g336，前一点各为g336/g320。原U=g+2*chain的区间分别(368,384]和(384,400]没有共同交集；g+chain则两者都(352,368]。MOV/MOV只有g192末点near-serial，右删失，不能加入共同区间。

**不是把β=1宣布为真实硬件定律。** 长FSQRT依赖链在执行过程中逐条完成/退休，首链剩余pending、次链已dispatch和跨迭代指令数量都随时间变动；U=g+2k把全部两链始终算在同一时刻，缺少生命周期依据。g+k只是由E0形成的候选代理，可能还受packet/credit、融合/消除或其它限制影响，不能命名physical ROB entries。

E0的Icache refill/iter大量超过原.001门，而cycles范围很小；frontend stall/iter约.005–.016cycles，与hundreds cycles的曲线差不同尺度。原Icache门未通过仍原样登记，取指refill不被删除或隐瞒。新的观察性前端条件不等于所有前端成本已测完。

## 在E2开始前冻结的验证

仅四条E2曲线（nop-pair/nop-movzero × chain16/32）为确认集，E0为发现集、E1在本项不作确认。保持原六g点/每点8窗、真实code/IR/FP/GPR/ID/noMUX/环境完整硬审计；NONE/S/I全部range/median≤.10，NONE max≤.90*min(I0-short)。额外观察条件：全部这些窗口0x23 frontend stall /0x11 cycles≤.01，该比例远小于below(.90)/near(.95)的分界间隔，但不证明计数器覆盖全部前端影响。Icache原门的逐窗结果另外导出，**不改变原consumer终态**。

沿原near-serial与below定义、不可算/非单调/左右删失优先、至少两个高侧near点。固定预测：chain16=(336,352]、chain32=(320,336]，两个NOP-eligible类都必须逐点分类后复制这些区间；β=1候选proxy均(352,368]。全部满足→LIFETIME_PROXY_PREDICTION_REPLICATED；区间明确但不符→PREDICTION_NOT_REPLICATED；不可算/ambiguous/删失→INCONCLUSIVE。不得更改α、β、threshold或扩大验证集。不能把E0/E1混入E2提高复制数。

MOV/MOV完整原矩阵作为独立反例/删失继续报告；新确认即使通过也只认证一次新epoch对既定行为预测的复制，不认证6曲线共同物理容量、实际MOP/ROB分配或ROB是唯一活跃资源。

## 交付与追踪

新 `tools/diagnostic/rob_lifetime_analysis.py` / `tools/diagnostic/tests/test_rob_lifetime.py` 只分析原raw严格审计产物；不改 `tools/diagnostic/rob_zero_units_analysis.py` 或原driver。固定注册工件 `docs/reviews/evidence/2026-10-12-rob-lifetime-heldout/registration.json` 记录冻结时当前结果数、E2零记录以及E0输入SHA，报告列发现/确认分割与全部反例。任何目标异常沿原driver停块，不补拼E2。

branch codex/sm8650-tlb-hierarchy-r2，owner当前primary；物理条目、未观测生命周期/credit在 `docs/open-items.md`。此项是对第一epoch发现的预期留出验证，不冒充原scan开始前的预注册，也不放宽原容量判据。
