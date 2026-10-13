# 寄存器内保存计数的SB发射资格 v1.1

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-13-rob-direct-fenced-results.md` 完整1536窗证明six long64/FD路径有效，却没有8marker分离。旧ROI确实含observer自己的LDR/STR。新对照彻底移除observer ROI内访存，原失败保留，不调门。

producer `probes/diagnostic/rob_register_fenced_marker.c`，consumer `tools/diagnostic/rob_register_fenced_analysis.py`，controller `tools/diagnostic/run_sm8650_rob_register_fenced.py`。同一个JIT函数：保存ABI callee-saved及DSB在所有before MRS之前；六before值留x20..25，六after值留x13..17/x19；六before后SB阻止payload越过采样，六after后SB阻止observer写回/恢复ABI提前发射，才用x5的私有96B缓冲写回/恢复ABI。x18(Android reserved)、x29/x30不改。中间只有固定MOVZ/MSR-PMSELR/ISB/MRS和原marker程序，observer无LDR/STR、无C loop/branch。原payloadFPSR/status/near两STR保留并按A/NOP差抵消。

当前own FD metadata在整个JIT调用前后检查cap/index1..32 unique/width64/sequence/offset稳定。这里采用Linux标准seqlock包住原始register read；SIGILL保护整个调用，changed metadata首拒，不从invalid窗口取数字。PMSELR选择值由本process真实own metadata生成，不从上次或硬编码32/3等取得。`--run --chain k`不接受indices覆盖；`--plan --chain k --indices CSV`仅为native/dynamic recipe复核，不执行MRS。actualruntime indices与计划word必须逐样本共用同一份binding，不能只输出标签。

新程序同process固定codeVA/PFN/branchPC，原四payload只SB/NOP两word交换；prefix/suffix全四同构、保留原relative CBNZ目标。原输入/架构/FPSR/8near/8far不变。训练64+warm4使用同VA/同body PC的warm-image：只将observer counter-prefix/suffix/写回字替换为NOP，payload和ABI保留，因此warm不MRS且不要求warm期间计数锁稳定。改为measured-image时只修改/flush observer字段，原body字保持；Linux权限/ICache剩余影响仍记录，不认证取指容量。每个真实measured call须全6当前绑定cap/index/width/锁有效，结束全锁/offset一致，再核kernel GROUP+ID绝对包围。所有一次unique ordinal、无retry、首技术失败停，invalid trace保留。suffix位置按actual程序长度−36推导，不硬编码chain偏移；source/ABI模板/实际动态word/recipe/解码/launch/raw SHA全登记。

矩阵同3fresh×chain16/32×32trial×8role=1536窗，原near/far正控/结构阴性/≥4分离/IR/eligible≥8/条件far≥.9门全部不改，15秒进程间隔。全部six process通过才REGISTER_FENCED_MARKER_QUALIFIED；即使通过也不认证allocation单位、frontend supply、物理ROB或384。硬件register-only观察本身仍会增加指令/寄存器压力，后续容量模型须计入、做单位/供给/延迟对照。

host唯一定义profile为perf_user_access0→1→0/write-ahead/finally恢复，双journal/CPU7/MIDR/4KiB/quiet-state/single-owner同前；producer不写global counter/control。所有raw在private；失败不回救以前两种ROI。后续single cold-load阻塞+ADD xzr非fusion、DP_SPEC正控及两独立deadline/PRF对照只作为下一设计候选，未冻结/未实现、不拟合384。
