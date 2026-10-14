# 分支PC干预：稳定32/32错方向与near/far，资格通过

## 本次任务的目的（给人类看）

对同映射资格的稀少near机会作独立PC反证。协议 `docs/design/2026-10-14-rob-cold-head-branch-sites.md`；producer `probes/diagnostic/rob_cold_head_branch_sites.c`；consumer `tools/diagnostic/rob_cold_head_branch_sites_analysis.py`；controller `tools/diagnostic/run_sm8650_rob_cold_head_branch_sites.py`。

**通过：BRANCH_SITES_PRIMARY_QUALIFIED。** 12fresh process、6144/6144正式、24576/24576own warm、invalid0；所有原A8/Mpre0/IR/strict供给与long门通过。packet主配置在两epoch×head1/2四配置均near32/32、BR_MIS_PRED_RETIRED=1 32/32、far|near1；架构负控0x22=0 32/32、joint32/32，超过预先冻结24/29门。fixed控制near机会9、13、8、23；trial-role及packet均32/32。所有fixed原≥8门本批也通过，不据此改判旧7/4失败。

|epoch/head/layout|实际branch PC数量|cold near/错方向|架构错方向阴性|cold−hot周期中位范围|所有原门|
|---|---|---|---|---|---|
|e0-h1-fixed|1|9/9|16/32|275.5..301.5|通过|
|e0-h1-trial-role|256|32/32|32/32|229.5..240|通过|
|e0-h1-packet|512|32/32|32/32|224..230.5|通过|
|e0-h2-fixed|1|13/13|16/32|256.5..282.5|通过|
|e0-h2-trial-role|256|32/32|32/32|469..483|通过|
|e0-h2-packet|512|32/32|32/32|427.5..460.5|通过|
|e1-h2-packet|512|32/32|32/32|492.5..524|通过|
|e1-h2-trial-role|256|32/32|32/32|454.5..461|通过|
|e1-h2-fixed|1|8/8|16/32|239.5..243|通过|
|e1-h1-packet|512|32/32|32/32|254.5..276.5|通过|
|e1-h1-trial-role|256|32/32|32/32|255.5..258|通过|
|e1-h1-fixed|1|23/23|15/32|218..232.5|通过|

actual code/branch PC来自每个warm/formal/invalid/rejected的实际调用指针；base+slot、branch位移、全部source word、current own-index/64bit/seqlock/offset、FD绝对包含、六个Linux私有页及真实head链均核验。trial-role热/冷同role共享PC，packet明确不同PC；最大offset2044+程序<4096，mprotect/munmap仅mapbase。所有code在同一4KiB映射/PFN内，head/near/out/counter地址同process固定；数据不是合成fixture。

这组干预说明whole-program PC变化伴随稳定的wrong-direction/near/far机会，支持重复PC预测历史为旧稀少机会的解释；**没有唯一隔离branch PC**：LDR/其它指令PC也随整个routine移动、前端对齐不同，不能宣称已辨识预测hash或唯一因果。head2 fixed的cold−hot约240..283、trial-role/packet约427..524，需保留PC相关head行为差；不能将旧fixed-PC cache剂量资格直接外推到新LDR PC。下一先同packet配方cache palette四配置核验actual head1/2剂量与marker，随后冷头gap矩阵再做实际packing/PRF/供给/独立deadline。不是凭这一资格直接报告384或ROB entry数。

每配置hot/cold各32trial、DC CIVAC+DSB只指定head line，不保证DRAM；周期是own PMU实测，端点cpufreq不证明恒频；CPU7 MIDR0x410fd821/r0p1、4KiB，2026-10-14北京时间，诊断证据不晋升baseline。0x22准确名称BR_MIS_PRED_RETIRED，整ROI关联不等于per-PC事件归属；两个事件语义问题的旧erratum在 `docs/reviews/2026-10-14-rob-cold-head-interleaved-results.md`。

source `7ae0dd5d12fff034b1622af6de30426ca514fe1e`（7ae0dd5）；build/actual launch `1034c41b5ac15a3b22fe064d279792ec7a88a498`（1034c41）；binary `e52cbae4713293b6dee329f3d45579940df69fc7cc428db8e5978f4d39292b4e`。NDK27.2.12479018/API34双构建一致，12actual native index上下文/48程序及ABI/branch/两端SB审核通过；私有raw `data/private/20261014T014726Z-rob-cold-head-branch-sites` 保留全部round。公开 `docs/reviews/evidence/2026-10-14-rob-cold-head-branch-sites/matrix-summary.json` / `formal-windows.csv` / `raw-sha256.json`：同primary第二算术184320 event delta、68文件SHA、所有blob与saved source逐字核验，不冒称独立review。15perf事务restored/readback0、runner unfinished空、设备idle；频率/governor未写，无main/remote操作。

软件验证：branch-sites两新增native/地址/bounds/producer→consumer/controller合同测试与复用路径局部14项通过；733完整diagnostic是此前a44b3ce范围，未借作新branch-sites整树覆盖。formal paths本轮未改未重跑。L1 i48/d96既有实测保留；共享L2官方2048/256×8与独立leaf/set黑盒分列；physical ROB UNKNOWN，持续目标active。
