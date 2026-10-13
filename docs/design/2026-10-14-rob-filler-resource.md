# 可见依赖链与 filler 资源对照 v1.0

## 本次任务的目的（给人类看）

检验 ADD XZR filler 是否相对零延迟 MOV 与 NOP 产生可重复的资源竞争。此前 OP/DP 事件对四种 ISA 均逐条计数，不能据此声称实际执行或 ROB allocation。此实验先测资源响应，不直接报告 ROB 容量。

源码 probes/diagnostic/rob_filler_resource.c；消费 tools/diagnostic/rob_filler_resource_analysis.py；执行 tools/diagnostic/run_sm8650_rob_filler_resource.py。沿用已实测合格的 probes/diagnostic/rob_register_fenced_marker.c register-only 自有计数器模板。参考全局知识库 Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf §4.11/4.12：NOP 可融合；零 MOV 不用调度/执行资源。OP 计数不提供分配单位。

## 冻结设计与实施顺序

1. 实际 native --plan 与独立 Python ISA 生成器一致；Android NDK/API34 两次构建逐字节一致；实际反汇编校验 ABI、无 x18、observer 无内存污染。
2. 每进程 chain 为 32 或 64 次 ADD X9,X9,X4，最后 STP X9,X10 写可见校验和。每次 chain ADD 前插入 0/4/8/12 条 filler：nop；ADD XZR,X1,X2；ADD X10,X1,X2（活结果）；MOV X10,#0。X9/X10 初始为零。不允许编译器修改 JIT ISA。
3. payload 最后有 SB，阻止 after timestamp 提前越过工作；保持两道 observer SB。此前 sink-unit 无工作完成边界的周期结果不得混用。warm-image 在同 VA/同 body PC，不读 PMU。自有当前 FD metadata/index/offset、前后绝对 FD 包络、CPU7/PFN/校验和必须逐窗通过。
4. 两个 fresh epoch × chain{32,64} × filler{0,4,8,12} = 16 进程，每个32试次×2种输入×4角色 =256窗；总4096。epoch1 反转配置次序，窗内旋转/反转角色。每进程固定等待15秒、环境前后检查；不改频率/governor。所有输入保留，不结果挑点。
5. 事件 [cycles,IR,OP_RETIRED,OP_SPEC,DP_SPEC,L1I_REFILL]；计数仅按定义使用，不作 allocation 单位。checksum chain*0x12345678；活结果=两个自有 VA 之和，其余0。工作纯寄存器，两个最终可见 store；代码小于单一4KiB页。

## 预注册消费与推翻路径

技术门：16配置/4096窗全齐、当前自有读/FD包络/架构校验完整；IR 在每个角色同试次相对 NOP 的差值绝对值≤2；L1I_REFILL 每进程每角色中位≤1、95分位≤4。失败明确 TECHNICAL_FAILURE 或 SUPPLY_NOT_QUALIFIED，保留原始窗，不填0。

每配置输出所有角色原始中位和 MAD，配对 sink−zero/live−zero/sink−nop 周期差分。资源正响应要求：在 filler=8 和12、两个chain和两个epoch的8个配置，配对 sink−zero 中位≥8 cycles，且每配置≥80%配对值>0。此门未过则 RESOURCE_EFFECT_NOT_ESTABLISHED；过为 REPEATABLE_FILLER_RESOURCE_EFFECT。两者均不认证执行端口、µop、ROB条目：decode/rename/fusion 同样可能导致周期差，需后续 admission/deadline 对照。

filler=0 提供同程序空对照：四角色 checksum相同、周期差分应小；任何额外资源解释先检查其分布。周期差不回溯修改阈值，先完整公开曲线与反例。被推翻的事件单位解释不恢复。后续窗口转折需另行冻结，不能拿本批周期外推384。
