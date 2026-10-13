# 自有 perf 直接计数读取资格 v1.0

## 本次任务的目的（给人类看）

建立只读自己perf FD的安全MRS读取能力，减少ROB短窗口系统调用端点误差。metadata合法不等于counter读数已正确；本批只资格，不重判旧SB失败、不启动ROB容量扫描。源码 `probes/diagnostic/pmu_own_counter.c`，公共pure guard `probes/common/perf_user_counter.h`，consumer `tools/diagnostic/pmu_own_counter_analysis.py`，controller `tools/diagnostic/run_sm8650_pmu_own_counter.py`。

## 接口、对照和有限预算

Linux接口 https://www.kernel.org/doc/html/v6.16/arch/arm64/perf.html 。继承已实测metadata route，host私有write-ahead事务 `tools/diagnostic/perf_user_access_transaction.py` 临时perf_user_access0→1→0，其余频率/温控不改。CPU7 own-thread RAW type8/pinned USER-only group [17,8,112,113]，config1=3。每个FD自己的read-only mmap，index必须1..32/unique、width64/cap true/even稳定seq；每次重新读取，不能复用旧进程index。index32使用PMCCNTR_EL0，其余PMSELR_EL0=index-1+ISB/PMXEVCNTR_EL0；仅选择自有事件counter，不写PMCR/PMUSERENR或counter值。

metadata前后acquire/barrier；MRS前后seq相同，四counter从before到after seq/index/offset一致。invalid/index0/policy0先拒绝不MRS；SIGILL受保护捕获后退出资格；无重试、无猜index、无fallback。64位值以offset+hardware模2^64合成，delta模2^64；窗口期间不允许metadata变化。每次FD累计GROUP+ID read包围direct snapshot→payload→direct snapshot。before/after direct绝对total均必须落在该own FD包围读数内；每一个direct event delta不得超过包围FD delta；IR wrapper差≤4096、LD/ST差≤512，cycle只检包含/正值，不称同步采样。

固定N=8192，等长3ISA NOP/SUBS/BNE、LDR xzr/SUBS/BNE、STR/SUBS/BNE；own64B热line，warm后8round×3role，E1反转顺序，三fresh共72窗。不用0x06，实际支持0x70/71。每process每role8完整，IR−NOP差≤128；direct LOAD−NOP LD_SPEC和STORE−NOP ST_SPEC中位在8192±82，交叉差绝对≤128，原始逐轮全部保留。包围FD一致性和独立已知工作正控都过才OWN_DIRECT_COUNTER_QUALIFIED；任何能力/技术失败停，数据不丢，不调门。资格只验证长工作与读取路径，不自动证明单事件短窗精度、无推测wrapper或ROB实际分配单位。

## 实施与停止线

先pure metadata guard/unsigned-wrap和实际producer plan/native fail/typed全覆盖+旧index反例红绿测试；双NDK/实际ELF3loop+MRS路径解码注册；source/build/launch 分列。当前runner与private perf journal全restored及无并发probe/基线0才开始；每process固定15秒，pre/post quiet-state原基线。首次拒绝即整批not-qualified，不并行手机。finally恢复0/readback、restore-failed持久化，无论work/parse/counter是否失败；unfinished阻止下一实验。

完整原始JSONL、metadata原值/offset/index/seq、hardware/combined/FD包含值、SHA在data/private，public仅匿名范围与验证，不入库kernel/PFN/serial值。后续short-window空操作/known marker校准要另冻结，再依资格推进发射/分配容量；TLB扫描不依赖此全局profile。
