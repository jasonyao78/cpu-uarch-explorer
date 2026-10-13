# ROB同错路结构性发射阴性 v1.0（仅N0冻结）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-13-rob-issue-marker-results.md` 的864窗证明trained-taken不等于不发射，旧N0保持失败。本任务用marker前SB阻止年轻推测执行，和marker后SB交换，作同错路、同训练／bits的结构性阴性；只确认发射观察能力，不作capacity scan。

## 实际程序与观察范围

沿用自有code/near/far/output四页、0/1.0原bits、k16/32 FSQRT延迟CBNZ、8near LDR／8far STR（不同64B line）及自身寄存器／far8字架构核验。新增一个pre位置与post位置，pre-fence = SB,NOP；post-fence = NOP,SB；结束另有固定SB，CBNZ跳到固定结束SB。互换两word、相同长度和opcode histogram、同branch PC／skip target／code VA/PFN。NOP/taps16word差固定；4程序pre-nop/pre-taps/post-nop/post-taps同页原位重写，仅计数外RW/RX／清cache。

A(train0/test0)两fence均架构执行tap，实际LD_SPEC/ST_SPEC差应8；M(train0/test1)架构跳过，两fence均near0/far不改。M-pre在tap前SB是结构性阴性，M-post是观测对象，二者不依赖“训练一定正确预测”假设。SB被支持和自身架构核验仍不能唯一定位计数来源／branch-PC；不读他人／秘密地址。

32trial×A/M×pre/post×NOP/taps=256窗／process，8trial轮转、奇block反序，各member每position4次；3fresh×k16/32=6process1536窗。64固定train+4完整wrapper warm，各窗在外清far、hot16line、DSB，同C代码；15秒进程间隔。6事件[17,8,112,113,34,1] USER-only GROUP+ID/pinned/noMUX；HWCAP_SB、CPU7/MIDR r0p1/4KiB、代码及visiblePFN端点不迁移、结果/flags与原字节硬门，技术失败first-stop。

## 先校准、后判读

各process、两tap：A-pre和A-post均mean[7,9]、q90(abs(delta−8))≤3；M-pre absmean≤1、q90(abs(delta))≤3。阈值=(min(A-pre q10,A-post q10)+M-pre q90)/2，gap≥4才定义，否则None。M-post不参加校准，32条全保留，不clip；near eligible=其delta≥冻结near阈值，至少8条；eligible中far delta≥独立far阈值比例≥.9，六process全过才FENCED_ISSUE_MARKER_QUALIFIED，否则NOT_QUALIFIED、无N扫描。0 eligible须区分None阈值与有效阈值下不响应。

IR同control/fence taps−NOP均absmean≤2且M pre/post各marker均值差abs≤2，配合自身架构结果验证不退休。BR_MIS／L1I所有窗口和分布披露，不作其PC唯一归因。**本N0没有前端供给认证**：资格只证明16tap响应可与结构性阴性分开；旧864窗I增量门4/6失败保持终态。没有把新观察资格当容量资格；正式N扫仍须独立证明完整固定text供给、deadline/资源控制及单位标尺。因此不能用缺失I-gate回救旧N0或证物理ROB。

## 交付、停止与下一阶段

`probes/diagnostic/rob_fenced_issue_marker.c`、`tools/diagnostic/rob_fenced_issue_analysis.py`、`run_sm8650_rob_fenced_issue.py`；actual C生产计划、独立decode、双NDK与producer→driver→写盘→immutable raw测试先通过；证据 `docs/reviews/evidence/2026-10-13-rob-fenced-issue-marker/`。primary branch codex/sm8650-tlb-hierarchy-r2独占，环境原样、no journal，全FDclose，raw private。程序没有filler/单位认证，没有自动容量scan；fail不增chain、不调整校准。后续deadline/MCQactiveconstraint/filler单位与TLB描述符footprint均 `docs/open-items.md`。

SB依据：Arm官方《Straight-line Speculation》v1.0（印刷页2）列SB为推测屏障：https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Security%20Update%2008%20June%202020/Straight-line_Speculation-v1.0.pdf 。这份文档只支持屏障候选；本probe仍需实际M-pre事件阴性核验，不能由架构说明推导PMU内部计数时点。
