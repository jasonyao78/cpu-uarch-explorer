# Cold-head分支PC重复历史反证 v1.0

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-14-rob-cold-head-interleaved-results.md` 已得cache/long正证据，但near机会不足。原事件0x22就是BR_MIS_PRED_RETIRED；512issue hot/cold窗口0x22=1/0与extraLD/ST=8/8或0/0零反例。下一独立改变每packet实际branch PC，检验固定PC的重复预测历史是否影响机会；不重评分旧失败、不降门、不做容量扫描。

producer `probes/diagnostic/rob_cold_head_branch_sites.c`；consumer `tools/diagnostic/rob_cold_head_branch_sites_analysis.py`；controller `tools/diagnostic/run_sm8650_rob_cold_head_branch_sites.py`。基线 `probes/diagnostic/rob_cold_head_interleaved.c`、parser `tools/diagnostic/owned_roi_packets.py`；原同PFN cache资格只是cold route正控，不代替新PC控制。

## 冻结干预与完整矩阵

2fresh epoch × heads1/2 × layout{fixed,trial-role,packet}=12process，每32trial×hot/cold×8role=512固定attempt，共6144formal/24576own warm。head offset1024、issue palette[17,8,112,113,34,1]；实际0x22称BR_MIS_PRED_RETIRED，保留whole-ROI而非per-PC归属限制。epoch1配置逆序；所有数据head/near/out、counter/JIT页PFN同process稳定；group/state身份不变。

role=i%8、state=(i>=8)、i由原member16轮转/分块反序给出。fixed code_offset=0；trial-role=8*(trial*8+role)，hot/cold同role同PC；packet=4*(trial*16+i)，每formal不同PC，两个状态PC不同是显式干预。最大offset2044，94/95指令程序整体留在同一4KiB JIT映射。不是知道cache/branch predictor hash、也不宣称所有新PC无此前非条件branch历史。

mmap/mprotect/munmap始终用code_map_base；memcpy/cache maintenance/调用用base+offset。每warm/formal/invalid/rejected报actual code_base、code_offset、branch_offset/branch_pc；schedule注册offset与branch_offset。branch_pc=code_map_base+offset+4*(33+heads)。函数调用的ABI head实址仍map_base+1024，二headA内容指向真实B；dynamic counter index/words/64byte callee-save/两端SB不变。实际code memcmp、warm/formal同地址、architecture返回必须通过。不同PC可能改变frontend缓存，strict供给门仍原样。

## 冻结判据

原Apre/Apost约8、Mpre约0、IR、near eligible≥8/32、far|near≥.9、I-cache median≤1/q95≤4全部保留。hot/cold的A/negative校准均需通过；hot deadline不用于cold容量。primary预先指定packet，两epoch×heads四cold配置必须同时：原marker/供给门全过；near eligible≥24/32；speculate/post/taps的0x22==1 ≥24/32；architect/post/taps的0x22==0 ≥29/32；至少29/32 spec/post/taps满足(0x22=0,extraLD/ST=0/0)或(0x22=1,extraLD/ST≥4/4)。extra基线为head_count与两架构结果store，原ISA/结构阴性继续核验。全部同时通过命名BRANCH_SITES_PRIMARY_QUALIFIED，仍无µop或ROB allocation证书。

fixed与trial-role原门、机会率、mis-pred联合全部列出，不要求其达到packet强机会门，也不能择优它们救primary。若packet失败，保留UNKNOWN并检验预测别名/actual方向/独立head deadline，不能在本批结果后换stride或减24。最大1个明确ROI-metadata-changed/process、每比较共同有效≥31/32，无retry/补样；所有512account，其它技术错误首停。头冷热long差描述全保留，既有long门另算不借失败掩盖。

## 实施与证据出口

实际native RED核验512计划和固定/role/packet真offset、branch目标/actual实址；所有warm与rejected字段必须接受同一身份检查。NDK双build、Capstone每个actual上下文，source/build/launch/rawSHA分列。只primary串行设备，双journal基线0，durable finally/readback恢复。主资格稳定后另冻oldest load/gap/packing/PRF/供给/独立deadline，物理ROB和共享L2 leaf/set黑盒仍UNKNOWN。
