# ROB下一正交控制：退休边界与跨迭代输入重置v1.0（有限资格冻结，2026-10-12）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-rob-lifetime-heldout-results.md` 的g+chain=(352,368]盲留预测复制，但生命周期与分配单位不独立。下一原型直接限制跨迭代依赖/退休边界，先资格，不把384作为期望值。

本地官方 `../cpu-uarch-ref/docs/Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf` §4.10：FPSR读取等待所有可能更新status的先前指令execute/retire，FPCR读有不同约束。候选同码形对照MRS FPSR与MRS FPCR：固定FPCR0/FPSR0、FSQRT operand1.0；每iteration末MRS值与1.0 bit pattern做EOR并FMOV到D0/D1，next iteration不继承上一sqrt数据链。禁止零idiom丢依赖，实际码/两个mode只sysreg编码差需独立decode。

必须在任何输入重置前捕获D0/D1原结果到GPR；末次原结果与MRS raw值outside-loop写到owned buffer并核验，不让重置1.0掩盖错误结果。无锚点/串行D0/D0/独立D0/D1、chain16/32、NONE64供给和参考需逐mode标定。FPSR会增加额外退休/执行约束，因此差不能唯一命名ROB；FPCR模式重置可能释放跨iteration ILP并使原I/S模型失效，必须保留这种资格反例。

拟先三epochs×2mode×2chain×{NONE0,S0,I0,NONE64}=48process/384window有限资格，1048576 warm/measure与15秒间隔，GROUP+ID/noMUX/IR、FP/GPR结果、原取指门和供给门分列。本版只冻结有限资格，不包含capacity扫描。实际opcode/plan需独立NDK/Capstone验证后才能launch；不是宣称实现或采样已完成。拟组件 `probes/diagnostic/rob_fp_drain.c` / `tools/diagnostic/rob_drain_analysis.py` / `tools/diagnostic/run_sm8650_rob_drain.py` / tests，均尚未创建。owner当前ROB负责人，未完成项在 `docs/open-items.md`；不改原scan或g+k终态。

## 冻结的生成码/结果契约

只用NOP/NOP两ISA为一group、g={0,64}，64仅NONE。每个mode×chain四case=NONE0/S0/I0/NONE64，共16case×3epoch×8窗=384window。各epoch同矩阵，E1反序，固定15秒进程间隔和1048576 warm/measure iterations。每进程单RX65536映射，loop64-byte对齐；无code rewrite/全局环境mutation。

16ISA固定SQRT1.0 prologue初始化D0/D1（NONE也同prefix）；每side FSQRT chain或NONE，2*g NOP。loop尾先FMOV X13,D0/X14,D1保存原FP结果，再MRS X12,FPSR或FPCR（唯一sysreg编码差）、MOV X16,X12存raw值、EOR X12,X12,X15依赖构造1.0、FMOV D0/D1,X12、SUBS/B.NE。9条end ISA；loop IR=4g+2chain*(anchor!=NONE)+9。outside-loop epilogue STR原FP0/FP1/raw sysreg到owned3-word buffer，MOVZ checksum0/RET=5ISA；总窗口期望IR=ITER*loop+16+5，仍保留wrapper额外IR绝对差且要求相对误差≤1%。原FP0/FP1必须精确1.0、raw sysreg0、checksum0，不能用重置后的D0/D1作oracle。FPCR先确认0，每call前清FPSR（仅本进程EL0架构状态），清理不改设备sysfs。

同窗events[17,8,58,33133,35,1]，USER-only GROUP+ID、pinned、noRESET/noMUX。实际ID唯一/正确readformat、IR/结果/codeVA/code bytes/cpu/BTF不借其它batch。资格逐mode独立：每point八窗range/median≤.05、I0/S0 max(I)/min(S)≤.70、NONE0 range/min(I)≤.01、NONE64 max/min(I)≤.80且stable、所有L1I refill/ITER≤.001。两chain/三epoch全部满足才该mode qualified；只FPSR合格可命名FPSR_REFERENCE_QUALIFIED，FPCR不合格仍保留CONTROL_NOT_QUALIFIED，不能借前者把后者晋升。两mode都不合格即REFERENCE_NOT_QUALIFIED，无额外retry或自动N扫。frontend/rename/µOP完整signed原值公开辅助，不直接当allocation单位。

结果从actualproducer→driver→raw必经消费入口，mock/raw与真机证据分列，所有原失败、旧2352scan/E2代理区间原状；对照差只约束本新测量的输入/退休行为，不唯一认证ROB。主stop=技术/环境失败首次停，完整但不合格保留命名资格状态。ownerprimary，branch codex/sm8650-tlb-hierarchy-r2。
