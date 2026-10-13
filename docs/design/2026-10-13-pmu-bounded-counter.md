# 自有 counter 固定窗口预算资格 v2.0

## 本次任务的目的（给人类看）

v1在E2第二窗检测metadata改变，完整49窗/两个process正控通过，但whole批未通过。不要为了稳定窗口去重跑旧批。本新协议补齐被拒metadata原值，在固定72个唯一ordinal上评价读取能力；丢弃条件仅kernel自有metadata有效性，不看计数信号。保留旧failed verdict和raw。

producer `probes/diagnostic/pmu_own_counter_bounded.c` 复用 `probes/diagnostic/pmu_own_counter.c`；guard `probes/common/perf_user_counter.h`，consumer `tools/diagnostic/pmu_bounded_counter_analysis.py`，controller `tools/diagnostic/run_sm8650_pmu_bounded_counter.py` 复用完整controller `tools/diagnostic/run_sm8650_pmu_own_counter.py` 和恢复helper。新version2/新双NDK/新source/build/launch，不拿旧binary资格。

固定3fresh，每process8round×3role=24attempt，共72，E1反转role。每ordinal恰一次，无补采、无同窗retry，无按metric选窗。seq奇数/变更或index0使该窗口invalid（before/after metadata、attempted/register-read flags、可能已经执行的payload、原因和空metrics全部保留），下一不同ordinal重新读取当前metadata。cap/width不足、非法index>32、duplicate own index、SIGILL、FD/CPU/noMUX/absolute-envelope异常全部fatal停整批。不能在invalid index下MRS；MRS自身受保护。时间窗口失效时丢失计数不是0，不进中位。

每processinvalid≤1/24且每role≥7/8有效，三个process各自满足才覆盖合格；否则not-qualified。有效样本正控门和绝对FD身份/包围门**完全沿用v1**：LOAD−NOP LD_SPEC8192±82、STORE对应同值、cross/IR≤128，wrapper IR≤4096、LD/ST≤512。各role invalid分布全部报告，不能称非随机丢失对所有因果估计无影响。这里只验证长known-work读数可用，不认证单事件短窗或ROB allocation/容量。

所有attempt完整metadata trace，sticky首invalid ordinal和总数审计；没有header/currentcap/index/width/even seq就不MRS，不猜index，invalid数据保留不拼成v1整批。parent只临时perf_user_access0→1→0，private write-ahead/finally持久恢复及live独占/双journal终态同v1，固定15秒进程间间隔，不并行手机。首fatal保留而停止；full finite budget若完成仍按门验收。
