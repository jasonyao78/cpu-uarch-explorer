# ROB 双独立 FSQRT 锚点资格与有限扫描（冻结 v2）

## 本次任务的目的（给人类看）

旧 `probes/common/rob_codegen.h` 的两侧 SQRT 均是 FSQRT D0,D0，互相串行。旧有效窗口曲线保留，但不能假定已有经典双独立长延迟锚点的重叠。新 `probes/diagnostic/rob_dual_anchor.c` 先问 D0/D1 两条独立链是否比同值 D0/D0 串行链明显重叠，再按资格门决定是否扫 NOP 间隔。它不校准 NOP 的 ROB 分配单位，不直接测物理 ROB 项数。

设计选择：继续原串行曲线不能验证重叠；再扫 ADD 会引入已观测供给波动；选两条同值 FSQRT 链与 NOP 供给控制。官方优化指南 Issue3.0/r0p1 表4-26给 FSQRT D 最小依赖延迟13、最大吞吐1；这是设计依据，不作为本机实测常数。全局知识库 `../cpu-uarch-ref/docs/Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf`。第三方384仍不作目标答案。

## v1反例驱动的修订与数据隔离

`docs/reviews/2026-10-11-rob-dual-anchor-v1-results.md` 144窗技术通过，但N0空循环一个进程range/median=10.297713%使整体not-qualified；独立208/串行416以及NONE N128约28.68的观测不能越门。v1冻结正文、消费、raw和失败终态均保留。v2只改变NONE N0的角色：其噪声range相对锚点信号≤1%，即约208cycle基线下≤2.08cycle，仍≤扫描1.25基线响应增量的4%；上界供给余量继续逐窗约束。非零NOP、锚点稳定及所有扫描门不放宽。这个定义面向干扰对待测效应的影响，不面向空循环自身的百分比。

这是看过v1后作出的新预注册，不宣称盲法。新资格与扫描都必须fresh raw，driver/consumer只接受v2 mode与v2注册协议/构建输入；旧资格目录即使相同binary也不能用。代码和binary不变，因为无需改变硬件激励。下面协议在v2设备数据产生前冻结。

## 精确程序与有限批

只复用共用纯生成器，不修改历史头文件/旧探针。class=nop、chain=16、无桥接、align=0。SQRT 两程序均把旧 prologue 的 FMOV D16,X15 改为 FMOV D1,X15，让 D0/D1 初值都为精确1.0；serial 两侧各16次 D0→D0，independent 第二侧16次改为 D1→D1，其余 words 完全一致。不碰 ABI 保留 V8..V15。NONE 为同 N 的真实 NOP 程序。每个独立进程只安装一种程序、固定一个64KiB VA、RX不变，无逐窗重写。

8窗，各窗先暖身131072 iterations，再测131072；奇epoch窗序反转。生成循环外立即捕获SQRT结果D0/D1原始位，两者必须仍为0x3ff0000000000000；两次FMOV计入PMU窗但不属于迭代循环（IR容差max(1000,1%)）。不通过时结构化失败空metrics。NONE不冒用FP输出。

资格块：N={0,128}×anchor={none,serial,independent}×3 fresh epochs=18进程/144窗。资格成功才运行完整扫描块：N={0,128,256,384,512,640,672,704,768,896}×3 anchors×3 epochs=90进程/720窗；扫描自带重新采集的N0/128，资格旧窗不拼接进入扫描。两块奇epoch将整条件序反转。进程间固定5s空闲；每进程约秒以下计算，环境端点仍硬门，这个间隔不声称保证不热。CPU7/FPCR0/4KiB、PMUtype8、GROUP+ID/pinned/user-only、无RESET无mux；事件[0x11,0x08,0x3a,0x3b,0x816d,0x23]。不改变governor/frequency/thermal/THP全局设置。设备异常或环境不合格立即停块，不补删窗。

## 消费与预注册命名

`tools/diagnostic/rob_dual_v2_analysis.py` 精确审计真实producer plan/program、每窗顺序/VA/uint64/IDs/IR/结果位、完整矩阵、source/build/launch/protocol/rawSHA、只读环境闭合。actual source与consumer/build、launch分别登记；独立第二算术验证全部窗。

C=cycles/131072；每进程8窗 (max-min)/median≤0.10 才stable。资格要求所有serial/independent N0进程stable，max(independent N0)/min(serial N0)≤0.70；NONE N128各进程stable且NONE N0/N128所有C≤0.80×min(independent N0)；全部NONE N0窗的绝对range≤0.01×min(independent N0)。N0仅是包装/空循环哨兵，不承诺相对自身稳定，不替非零NOP程序认证供给。通过仅命名dual-anchor-overlap-qualified，否则not-qualified，禁止扫描；PMU rate不当allocation标尺。

扫描重新满足同资格门。每非零N供给合格需三种程序每进程stable；N0的NONE改用上述绝对噪声门，serial/independent仍各进程stable。所有N还要求max(NONE N)≤0.90×min(independent N0)、max(serial N)≤1.10×min(serial N0)。不满足=supply-or-control-unqualified；合格时所有independent C≥1.25×max(independent N0)为overlap-loss-response，所有C≤1.10×min(independent N0)为no-overlap-loss，其余ambiguous。只有合格低点后至少两个相邻合格高点，且之后任何合格点不逆转，才报告有效重叠丢失区间(last low, first high]；末点孤高=right-censored，首点已高=left-censored，反转=nonmonotonic，缺口/模糊无法定位则inconclusive。N代表每侧NOP数，不除2/取OP比例换算物理entry；RS/FPPRF/退休/前端仍可能限速。

## 交付与出口

工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`，branch `codex/sm8650-tlb-hierarchy-r2`。组件：probe上述路径、consumer上述路径、`tools/diagnostic/run_sm8650_rob_dual_v2.py`、`tools/diagnostic/tests/test_rob_dual_v2.py` / `test_rob_dual_v2_raw.py`、构建证据 `docs/reviews/evidence/2026-10-11-rob-dual-anchor-v2/`。先真实producer RED/GREEN，生产driver→writer→raw consumer（只mock外部PMU/adb）成功/反例，再双NDK构建、代码逐字与独立反汇编，提交后由primary串行上板。停止/阴性与未合格窗完整保留；raw/private不入库，公开完整匿名派生计数/审计/谱系。正式schema-v2接入及物理归因继续 `docs/open-items.md`。不启动并行设备Agent，不推送远端。
