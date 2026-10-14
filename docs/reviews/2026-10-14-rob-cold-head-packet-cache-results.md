# 当前packet cache反例：总窗口refill不等于head剂量

## 本次任务的目的（给人类看）

对branch-sites搬动整个routine后新的LDR PC，核验缓存剂量而不外推旧PC。producer wrapper `probes/diagnostic/rob_cold_head_packet_cache.c`，唯一ROI源 `probes/diagnostic/rob_cold_head_branch_sites.c`；consumer `tools/diagnostic/rob_cold_head_packet_cache_analysis.py`；controller `tools/diagnostic/run_sm8650_rob_cold_head_packet_cache.py`；协议 `docs/design/2026-10-14-rob-cold-head-packet-cache.md`。

**原资格不通过：PACKET_CACHE_NOT_QUALIFIED。** 四fresh process2048/2048formal、8192/8192own warm、invalid0；current index/ABI/所有实际位置与head内容链/LinuxPFN/架构/FD均通过。marker机会全32/32、conditional far1、原阴阳/IR和long全部通过；原剂量门在三个head1/taps cell失败，原上界1.25不改。

|配置/role|cold−hot cycle median|mean ΔL1D|mean ΔL2D|原剂量|
|---|---|---|---|---|
|e0-h1-packet/pre-nop|232.5|1.15625|1|通过|
|e0-h1-packet/pre-taps|235.5|1.34375|1.03125|不通过|
|e0-h1-packet/post-nop|250.5|1.09375|1.0625|通过|
|e0-h1-packet/post-taps|271|1.34375|1|不通过|
|e0-h2-packet/pre-nop|554.5|2|2|通过|
|e0-h2-packet/pre-taps|544.5|2.40625|1.96875|通过|
|e0-h2-packet/post-nop|542|2|2|通过|
|e0-h2-packet/post-taps|535|2.1875|2|通过|
|e1-h2-packet/pre-nop|521.5|2|2|通过|
|e1-h2-packet/pre-taps|514.5|2|2|通过|
|e1-h2-packet/post-nop|508|2|2|通过|
|e1-h2-packet/post-taps|506|2|2|通过|
|e1-h1-packet/pre-nop|242.5|1.09375|1|通过|
|e1-h1-packet/pre-taps|242.5|1.28125|1|不通过|
|e1-h1-packet/post-nop|234|1.1875|1|通过|
|e1-h1-packet/post-taps|241|1.125|1|通过|

所有NOP窗口剂量通过；head2所有roles通过；head1/taps的三格L1D均值1.28125或1.34375超原门，而L2D均近1。四配置L2D剂量全通过，但不能拿一个level回填另一个。无需把失败叫cold head没激励：实测LD依赖、32机会与长延迟都成立。整个带标记窗口还包含near/far数据和两条结果store；metadata读取在捕获外仍可改变缓存状态。它们是extra L1D差的候选，尚无唯一归因，HPA/cache hash未知。

下一独立head-only ROI保留原head LDR PC、head实址/链与current own计数，但没有CBNZ、near/far marker或捕获内结果store；observer只GPR、结果与硬件buffer写回均在after counter+SB之外。它以自己代码/条件阴阳正控证明head-local冷热剂量，不重评分本批、不裁掉失败taps、不把NOP窗口单独晋升本批。head-only成功及既有branch-sites32机会/供给资格之后，另冻真正cold-head gap/packing/PRF/two-head deadline；原单位失败与384候选不动。

4KiB自己mapping/PFN，hot/cold同数据地址/FD、packet code/branch PC按真实注册偏移变化；DC CIVAC+DSB不承诺DRAM。32trial同role signed配对，PMU实测cycles；CPU7 MIDR0x410fd821/r0p1，2026-10-14北京时间；端点cpufreq不证明恒频。该palette是0x3/0x17，没有0x22/I-cache，不能补成同窗错方向或供给证书。issue事实分列 `docs/reviews/2026-10-14-rob-cold-head-branch-sites-results.md`。

source `50135613392b07b4872f45c6478d5eb4bc8f4c0d`（5013561）；build/actual launch `769c8f862284f77438d4b653ea576b759eec64f7`（769c8f8）；binary `37a384105cd2fe5cd3ae8599d1f4cd56795b03131806fd69fd1010fe75c6336f`。NDK27.2.12479018/API34双build一致，4actual native上下文/16程序、默认issue兼容与actual cache-only wrapper/ABI审核通过。私有raw `data/private/20261014T020904Z-rob-cold-head-packet-cache` 保留；公开 `docs/reviews/evidence/2026-10-14-rob-cold-head-packet-cache/` 全匿名窗口/原差/门及SHA。第二算术61440 event delta/28SHA和全source/build/launch blob核验，非独立review Agent。16事务restored/readback0，runner unfinished空、设备idle；频率/governor未写，无main/remote。

局部16tests通过、旧6144/24576issue真实raw重读仍原通过且summary完全相同；新共享宏/审计回调的全diagnostic回归正在执行，后续单列，旧733不冒称覆盖新增。L1i48/d96既有实测与共享L2官方2048/256×8分列；独立L2 leaf/set及ROB物理容量UNKNOWN，持续目标active。
