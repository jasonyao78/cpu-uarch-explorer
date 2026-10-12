# ROB零延迟MOV资源类与两链长对照（冻结v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-rob-retirement-units-results.md` 的ADD/SUB NONE流45–50%波动、9取指窗越门，旧2352扫描禁止启动。新问题：利用官方明确列为零延迟、无需调度/执行资源的MOV #0类，能否建立稳定且能区分NOP融合资格的退休窗口对照？不是重跑旧ALU组求过门，也不预设物理ROB=384。

来源 `/Users/michaelyao/workspace/cpu-uarch-ref/docs/Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf` Issue3.0/r0p1 §4.11/§4.12：NOP+相邻任意指令列为fusion资格，MOV Xd,#0列为零延迟类。实际fusion/零值内部消除/PRF分配及一个ROB entry对应多少MOP仍未认证。MOVZ循环写X4..X11，架构结果实际返回并验证0；避免只用XZR把有架构作用的更新也丢掉。

## 新激励与证据

新 `probes/diagnostic/rob_zero_latency_units.c`：nop-pair=(NOP,NOP)、nop-movzero=(NOP,MOVZ X[4+j%8],0)、movzero-pair=(MOVZ X[4+2j%8],0,MOVZ X[4+(2j+1)%8],0)。g语法组各2ISA，两个gap，FP chain16/32，D0/D0串行 vs D0/D1独立，输入/结果精确1.0；NOP或g0返回0，非空MOV组返回X4且必须0。NONE两chain真实code一致。

warmup和每窗iteration统一**1048576**（原131072的8倍），8窗/进程；原因是把已观察到的固定调用/取指扰动摊到更长窗口，不提高旧Icache门、不挑首窗；不同代码类与窗口长度共同变化，不能将新稳定性唯一归因MOV或长窗。source/namespace/binary/raw全部独立新模式，不晋升旧数据。CPU7/4096/FPCR0、单64KiB固定RX、六事件[0x11,0x08,0x3a,0x816d,0x23,0x01]、GROUP+ID/pinned/user-only/noRESET/noMUX沿旧资源单位合同。进程间统一15秒（长窗低占空比），只读基线，不写sysfs/内核。

## 两阶段程序与固定判据

资格：每epoch共享NONE0、两chain各S0/I0及三类NONE64，8条件×3epochs=24进程/**192窗**。原参考/供给/取指门完全沿 `docs/design/2026-10-12-rob-retirement-units.md`：range/median≤.10（NONE0用绝对noise≤.01*min I0-short）；maxI0/minS0≤.70，两chain均要过；全部NONE64 max≤.80*minI0-short；全部Icache/iteration≤.001。MOV架构结果/FP/IR/真实code硬门；未过本批结束，不扫描。

扫描仅同新模式完整qualified raw/同binary可授权：nop-pair/nop-movzero g={256,288,320,336,352,384}；movzero-pair g={128,144,160,168,176,192}。每point NONE16、两chain S/I，90条件+8refs/epoch，294进程/**2352窗**；原各point稳定、取指、供给≤.90*I0-short门不变。near-serial I_min≥.95*S_max且I_max≤1.05*S_min；below I_max<.90*S_min；其它ambiguous。不可算/非单调/左右删失、至少两个high点、三epoch完全复制后才有操作性区间。

被检验的候选模型仍为U=α*g+2*chain（NOP-eligible两类α=1，未列NOP fusion的MOV/MOV α=2）。六条复制曲线共同交集→COMMON_RETIREMENT_PROXY_COMPATIBLE，否则INCONCLUSIVE。α与loop/跨迭代/FP生命周期、活跃替代约束是显式假设；共同代理也不是physical entries或actual allocation证书。MOV类可能在更早阶段被消除/压缩，若不支持α模型就是反例，不能再按结果改α迎合384。

consumer `tools/diagnostic/rob_zero_units_analysis.py` / driver `tools/diagnostic/run_sm8650_rob_zero_units.py` / tests `tools/diagnostic/tests/test_rob_zero_units*.py` / evidence `docs/reviews/evidence/2026-10-12-rob-zero-latency-units/`。先真实288plan/144独立decode（所有MOV Rd/imm与return）、producer→writer→raw/冻结授权反例、双NDK与完整诊断回归，再串行目标资格；source/build/launch/report分列。owner=当前primary独占，r2 branch；失败及未知落 `docs/open-items.md`。
