# ROB下一正交控制：退休边界与跨迭代输入重置（设计草案，2026-10-12）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-rob-lifetime-heldout-results.md` 的g+chain=(352,368]盲留预测复制，但生命周期与分配单位不独立。下一原型直接限制跨迭代依赖/退休边界，先资格，不把384作为期望值。

本地官方 `../cpu-uarch-ref/docs/Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf` §4.10：FPSR读取等待所有可能更新status的先前指令execute/retire，FPCR读有不同约束。候选同码形对照MRS FPSR与MRS FPCR：固定FPCR0/FPSR0、FSQRT operand1.0；每iteration末MRS值与1.0 bit pattern做EOR并FMOV到D0/D1，next iteration不继承上一sqrt数据链。禁止零idiom丢依赖，实际码/两个mode只sysreg编码差需独立decode。

必须在任何输入重置前捕获D0/D1原结果到GPR；末次原结果与MRS raw值outside-loop写到owned buffer并核验，不让重置1.0掩盖错误结果。无锚点/串行D0/D0/独立D0/D1、chain16/32、NONE64供给和参考需逐mode标定。FPSR会增加额外退休/执行约束，因此差不能唯一命名ROB；FPCR模式重置可能释放跨iteration ILP并使原I/S模型失效，必须保留这种资格反例。

拟先三epochs×2mode×2chain×{NONE0,S0,I0,NONE64}=48process/384window有限资格，1048576 warm/measure与15秒间隔，GROUP+ID/noMUX/IR、FP/GPR结果、原取指门和供给门分列。尚未冻结consumer阈值/实际opcode/plan；当前是下一设计草案，不授权声称采样已进行，capacity扫描必须在实际资格/模型核验后另案。拟组件 `probes/diagnostic/rob_fp_drain.c` / `tools/diagnostic/rob_drain_analysis.py` / `tools/diagnostic/run_sm8650_rob_drain.py` / tests，均尚未创建。owner当前ROB负责人，未完成项在 `docs/open-items.md`；不改原scan或g+k终态。
