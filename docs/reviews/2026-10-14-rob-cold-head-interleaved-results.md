# 同映射冷头：缓存与长延迟通过，标记机会仍未稳定

## 本次任务的目的（给人类看）

对v1跨进程cold/hot缓存剂量反例，执行冻结的sameVA/PFN/context与head offset0/1024交错反证。组件路径：producer `probes/diagnostic/rob_cold_head_interleaved.c`；consumer `tools/diagnostic/rob_cold_head_interleaved_analysis.py`；controller `tools/diagnostic/run_sm8650_rob_cold_head_interleaved.py`；协议 `docs/design/2026-10-14-rob-cold-head-interleaved.md`。

**原资格不通过：INTERLEAVED_COLD_HEAD_NOT_QUALIFIED。** 16fresh process、8192/8192正式、32768/32768 own warm完整，invalid0；所有技术/架构/actual own-index/FD/PFN/内容链/ISA检查通过。1024主配置的全部long-delay、cache剂量、A8/Mpre0/IR校准与issue strict I-cache门通过；但两个配置near eligible仅7/32和4/32，低于预注册8/32。原门不改，不借offset0救主配置。

head1/2都是自己4KiB页，hot/cold同进程同VA/PFN/JIT/FD，冷态由DC CIVAC+DSB触发；不保证DRAM层。真实head地址=map_base+requested offset，heads2的A内容指向B真实偏移地址，munmap用map_base。initial/final六私有LinuxPFN稳定；HPA与Stage2未知。统计32trial signed paired差，CPU7/0x410fd821/r0p1；PMU实测cycles，不拿端点cpufreq做恒频证明。采样日期2026-10-14北京时间；资格批为诊断证据，不晋升baseline或物理容量。

|配置|cold−hot周期中位范围|cold marker near eligible/32|far given near|原失败门|
|---|---|---|---|---|
|e0-h1-issue-o0|230.5..249|13|1.0|通过|
|e0-h1-issue-o1024|242..295|9|1.0|通过|
|e0-h1-cache-o0|218.5..231|22|1.0|pre-taps-cache|
|e0-h1-cache-o1024|253.5..282.5|16|1.0|通过|
|e0-h2-issue-o0|245.5..273|19|1.0|通过|
|e0-h2-issue-o1024|448.5..488.5|7|1.0|cold_marker_observable|
|e0-h2-cache-o0|255..266.5|22|1.0|通过|
|e0-h2-cache-o1024|454.5..514|23|1.0|通过|
|e1-h2-cache-o1024|253.5..290.5|23|1.0|通过|
|e1-h2-cache-o0|258.5..265|7|1.0|pre-taps-cache, post-taps-cache, cold_marker_observable|
|e1-h2-issue-o1024|251.5..279.5|23|1.0|通过|
|e1-h2-issue-o0|251..293.5|23|1.0|通过|
|e1-h1-cache-o1024|227..240|4|1.0|cold_marker_observable|
|e1-h1-cache-o0|249..272|23|1.0|通过|
|e1-h1-issue-o1024|232.5..239.5|23|1.0|通过|
|e1-h1-issue-o0|229..235.5|25|1.0|通过|

1024主cache四配置全部mean ΔL1D/ΔL2D在[0.75×head,1.25×head]，四架构role长延迟全部通过；offset0有e0-head1/pre-taps、e1-head2/pre/post-taps剂量失败。它支持本控制改善窗口缓存差的复现，但不能把总refill唯一归于某个PC，也不能宣称已识别cache set/HPA。offset1024的e0-head2/issue near7、e1-head1/cache near4构成新的独立资格失败；条件far全部1，不能将near不足解释成ROB满或冷load无效。

下一可推翻问题：near机会少是branch预测已正确，还是误预测发生但head完成/供给/发射时机不足？**本报告首次提交把event4(0x22)误标BR_PRED，现明确更正：BR_PRED是0x12；实际0x22为BR_MIS_PRED_RETIRED**（匹配r0p1 TRM§18，既有 `docs/design/2026-10-13-rob-issue-marker.md` 同样正确）。raw事件号与source/binary不改，不重新评分。无需先加0x10才读取现有0x22事实。

追加原raw联合检验 `branch-near-joint.json`：512个issue profile的speculate/post/taps热/冷窗口，hot 150与cold142窗为(0x22=1, extraLD=8, extraST=8)，其余hot106/cold114为(0,0,0)，无反例；extraLD扣actual heads数，extraST扣两条架构结果写回，均由ISA与架构原值正控支持。e0-head2/issue/1024的7eligible对应7次0x22=1；整个ROI内关联与错误方向机会一致，不能宣称每PC硬件归属或cache profile4eligible已解释。下一冻结固定PC vs trial-role不同PC反证重复预测历史，保留实际branchPC、同role热/冷共享、strict供给与原阴阳门。原资格失败不回救、不降低8/32，稳定机会资格后再做gap/packing/PRF/supply/deadline。ROB物理仍UNKNOWN。

提交谱系：`157929b` source → `60a80bd`首次build；controller路径在mutation前被source gate拒绝，保留 `data/private/rob-cold-head-interleaved-preflight-failure.log`，没有probe/新PMU事务；`c7f7e44`修正并RED/GREEN锚点测试 → `a44b3ce`刷新build/实际launch。最终source `c7f7e440539ba94df2627eca212c275e6fc1371b`；actual launch `a44b3cea2b47e1d6d178c00e0c119de14fbe1e34`；binary `cbea6796bce9e9072a533260bb3250ccc39aade5bea76238a9734b47866f8328`。NDK27.2.12479018/API34双静态构建SHA一致，16actual native上下文/64程序逐词与独立Capstone解码通过。

全私有raw `data/private/20261014T011647Z-rob-cold-head-interleaved` 未裁剪。公开 `docs/reviews/evidence/2026-10-14-rob-cold-head-interleaved/matrix-summary.json` / `formal-windows.csv` / `raw-sha256.json`；第二算术245760 event delta、88文件SHA、所有source/build/launch blob及saved driver/consumer/helper逐字复核。这是同一primary的另一算术路径，不冒称独立review Agent。14perf事务全部restored，实际readback0、runner unfinished空、设备idle；频率/governor未写。局部19tests已通过；整树diagnostic733/733、644.752s通过（覆盖至a44b3ce）；正式runner/analysis/CTest路径本轮未改未重跑。

修订记录：首次938c105的BR_PRED(0x22)命名错误 → BR_MIS_PRED_RETIRED(0x22)，依据匹配r0p1§18与既有原协议；修订只纠正解释及后续路线，raw/source/event numbers及所有原资格失败保持。
