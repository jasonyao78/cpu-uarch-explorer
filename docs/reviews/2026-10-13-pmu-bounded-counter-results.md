# 固定预算自有直接 counter 资格结果

## 本次任务的目的（给人类看）

验证实际MRS能力与真实FD绝对身份、8192 known-work；不把计数读资格当ROB容量。新协议 `docs/design/2026-10-13-pmu-bounded-counter.md`，producer `probes/diagnostic/pmu_own_counter_bounded.c` / `probes/diagnostic/pmu_own_counter.c`，consumer `tools/diagnostic/pmu_bounded_counter_analysis.py`，controller `tools/diagnostic/run_sm8650_pmu_bounded_counter.py`。

**OWN_DIRECT_COUNTER_QUALIFIED：3/3fresh、72/72固定ordinal有效、0invalid、0补采**。全部原正控（LD/ST8192±82、cross/IR≤128）和metadata/绝对FD包含门通过；预先允许的最多1invalid/process本次根本未用。旧v1 E2失败及49完整窗保留，不能重标v1。

每样本自己当前cap/index/64位/offset/seq before-after全部核验，独立直接从原hardware+offset及FD算包围计数。公开 `docs/reviews/evidence/2026-10-13-pmu-bounded-counter/qualification-analysis.json`、全72窗CSV。全22原库存SHA复算。原始 `data/private/20261013T142407Z-pmu-own-direct-counter` 和journal私有不裁剪。

source `2479353236e52ca77b89579cf816b01e3e66d1bc`、actual launch `014f981c1a25ddb7c32993a7937bb4ccbb6b8c5f`，branch `codex/sm8650-tlb-hierarchy-r2`；binary `86f74bc61f206246203d566990ce0cd25d044dcc918de54024b00c380954f920`，两NDK一致/actual3ISA和寄存器解码见对应build/decode。host perf_user_access0→1→0，state restored/readback0，CPU频率/governor无写入；pre/post原环境无违例。无PMCR/PMUSERENR/control-value写入，仅自有counter select。

边界：这证明长known-work条件的安全读取路线和计数语义；单个/8个marker在短window里的endpoint精度、6event group是否全部long64可暴露、ROB实际分配单位和active bottleneck仍须另资格。不得自动修复旧SB实验或拟合384。下一为same-PC pre/post-SB matched marker的直接ROI N0，保留相同架构/branch/IR/校准门，先验证而非直接扫N。14相关守卫/生产/controller/恢复测试通过，全量诊断回归仍进行，不声称新short probe已测。
