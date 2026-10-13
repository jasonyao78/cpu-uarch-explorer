# 自有发射标记的 admission 转折 v1.0

## 本次任务的目的（给人类看）

已合格的 register-only ROI 能区分8次近端 load、8次远端 store。现在在近/远之间插入 filler，测远端仍能越过未决分支的范围，并用两种分支截止时间、三种 filler 推翻单纯供给/PRF/融合解释。输出先称有效发射范围；必须补充冷 load 退休阻塞等独立对照，才能晋升物理 ROB 容量。

producer probes/diagnostic/rob_admission_window.c；consumer tools/diagnostic/rob_admission_window_analysis.py；controller tools/diagnostic/run_sm8650_rob_admission_window.py。基线 probes/diagnostic/rob_register_fenced_marker.c，实测资格 docs/reviews/2026-10-14-rob-register-fenced-results.md；资源反例 docs/reviews/2026-10-14-rob-sink-unit-results.md。独立事件数≠分配数；源头预算包含阻塞链、branch、sentinel、observer，不扣一个凭猜测的常数得到384。

## 冻结矩阵、实施及验证

chain{16,32} × gap{0,128,256,384,512,640,768} × filler{sink,zero,nop} × fresh epoch{0,1}=84进程，每进程256窗，共21504窗。均匀128网格预注册，不围绕384拟合；epoch1反转配置顺序。same-code-VA 的64训练+4warm、8角色旋转反转、进程间15秒间隔、前后环境只读门与自有PMU0→1→0 finally事务不变；不改governor/频率、不补点、不删坏窗。

原 near8 LDR 后插入 gap 条 ADD XZR,X1,X2 / MOV X10,#0 / NOP，再 far8 STR；CBNZ按实际 gap 调整目标，分支PC与同chain下各gap保持相对不变。pre/post只交换原两个SB/NOP字，gap filler完全相同。original architect/speculate输入、FPSR、近/远架构校验不变；所有filler均不改变函数架构返回。gap最大程序仍单个4KiB代码页，不增加ITLB工作集。ABI/counter当前FD绑定/actual JIT全字/visiblePFN/noMUX/absoluteFD包络全按生产记录复核。

新增源码由实际native plan对独立Python配方；NDK/API34双构建相同，Capstone复核每种实际指令/分支目标/observer无内存与无x18，代码提交与构建提交分别锚定。分析先逐窗审计，再完整matrix，不允许调用旧N0分析器的容量禁止入口并打补丁规避。

## 判据与解释边界

每进程同试次 taps−nop 成对差分；Apre/Apost near/far各均值7..9且abs(x−8)的90分位≤3；Mpre阴性均值绝对≤1且abs的90分位≤3；正控10分位与阴性90分位差≥4，取中点阈值，否则 MARKER_NOT_QUALIFIED。IR taps−nop各role均值绝对≤2、Mpost−Mpre每marker均值绝对≤2。L1I_REFILL各role中位≤1、95分位≤4，否则 SUPPLY_NOT_QUALIFIED。所有差分与eligible逐窗保留。

Mpost near过阈值≥8/32，否则 DEADLINE_NOT_OBSERVED；只对这些eligible观察far，响应率≥.9为 reached，≤.1为 blocked，中间为 transition。相同epoch/chain/filler的转折报告最后reached与首个后续blocked的gap区间；前后未观察则左右删失，非单调记非单调，不补插值。两epoch交集为空不得称重复。

chain16→32延长deadline，若转折明显移动则拒绝稳定capacity解释；NOP/MOV/ADD的差别只能作为fusion/rename/execute/admission模型的约束。即便长deadline下某转折稳定，FP链可以逐条退休，后续供给、整数PRF、FP资源、分支/调度均须专门控制；本批不会认证物理ROB或µop单位。前一g+chain代理区间与第三方384保持原证据等级，不择近者报告。后续冷loadhead+两deadline/PRF对照另冻新矩阵。
