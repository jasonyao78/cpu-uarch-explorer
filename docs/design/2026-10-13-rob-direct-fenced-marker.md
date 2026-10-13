# 同位置 SB 发射标记的自有直接 ROI 资格 v1.0

## 本次任务的目的（给人类看）

长known-work已72/72证明自有4event MRS路径，但旧SB N0在K32 far校准不足。新批改变测量端点，保持生成程序/架构结果/marker/训练数学不变，检验短ROI是不是可观测。不是ROB容量扫描，不重判旧raw。

producer `probes/diagnostic/rob_direct_fenced_marker.c`；consumer `tools/diagnostic/rob_direct_fenced_analysis.py`；controller `tools/diagnostic/run_sm8650_rob_direct_fenced.py`；公共guard `probes/common/perf_user_counter.h`。新producer复制冻结旧生成器 `probes/diagnostic/rob_fenced_issue_marker.c` 的实际words，直接计数及warm边界显式改变。sameVA/PFN/page/branchPC、两word SB/NOP swap、16marker slots、finalSB、FPSR结果保持原输入输出证据。

## 有限矩阵及读数契约

3fresh epochs×chain16/32=6process，固定32trial×8role=256window/process，总1536窗，进程间15sec。每case64训练、4同routine warm不计数，wrapper不再反复perf-warm，先实际own FD metadata资格。USER-only type8 pinned sixevents [17,8,112,113,34,1]、config1=3（six long64未证过；本批必须cap/currentindex1..32 unique/width64/even锁全部实测，失败停）。

每窗enable group→kernel FD snapshot→direct own metadata+MRS before→routine→direct after→metadata一致校验→kernel FD after→disable；counts为**direct ROI**，time_enabled/running属于包围FD窗，明确不同边界。每MRS都重新验证自己的FD metadata，index32读PMCCNTR，其余仅PMSELR select(index−1)+ISB/PMXEVCNTR；SIGILL保护，seq/index/offset跨ROI变动或任一cap/width/ID/CPU/noMUX失败首停，输出被拒原trace而不是伪0。没有重试/挑点/丢窗。FD绝对total及delta包含每event核对，64位mod回绕；producer不写global control，host只用持久事务perf_user_access0→1→0/finally恢复，source/plan/binary/launch分列。

原架构status/near/far全部比对，actualwords核验，页/PFN前后不变。calibration仍Apre/Apost正控与Mpre结构性阴性，不用Mpost定阈值。**原门不变**：A mean7..9且abs(signal−8)q90≤3，Mpre abs(mean)≤1且abs(q90)≤3，Aq10−Mpreq90≥4；IR成对mean差≤2及fence匹配，near eligible≥8/32，far|near≥.9。全部六process过才DIRECT_FENCED_MARKER_QUALIFIED；即使通过也不是frontend capacity、ROB allocation或384entries证明。

失败cap/metadata/技术首停，完整stderr/raw/失效trace及命名状态保留；数值校准若完整但不通过仍收完预定六process，不自动N扫。资格后下一要冻结filler单位、deadline及供给对照，不能组件过了就跳到系统容量。
