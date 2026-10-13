# ROB退休阻塞的speculative marker v1.0（仅N0资格冻结）

## 本次任务的目的（给人类看）

用一条未解决分支挡住年轻指令退休，判断后方自有只读marker是否发射；先验证N0可观测性，再另冻filler窗口。旧FSQRT双链/loop模型有渐进退化、跨iteration与单位残差，`docs/reviews/2026-10-13-rob-anchor-order-results.md` 已实证register-order29cycles。新one-shot不以更多同曲线点拟合384，亦不读秘密/他人地址。

候选：单长load需要重新证明变动的内存激励；单FDIV/SQRT不足以覆盖长窗口。采用32/16个依赖FSQRT得到延迟分支输入（1.0/0.0），源代码明确branch后marker，执行与退休tap区别marker。它证明retirement-blocked speculation响应，不直接认证physical ROB entries/slots。

## Actual代码与三control

一个RX code VA/PFN；所有condition原字节相同，只有marker位置LDR X9,[X1] vs NOP一个word变化，重写/RW->RX/clear-cache在计数外、两mode都做。FMOV D0,X0；k次FSQRT D0,D0；FMOV X12,D0；CBZ X12,marker；B finish；marker LDR或NOP；finish SB；FMOV X0,D0；MRS X12,FPSR；STR X12,[X2]；RET。SB保证marker之后的caller不能在未决分支下贡献错误路径load；先HWCAP_SB检查，缺失命名拒绝，未实证就不假设SB可用。实测input只有0.0/1.0，original返回bits对应input，FPSR0，FPCR0（只清自身FPSR）。N0无filler。

A architect:64次train input0，然后measure0，marker应架构执行；B bypass:train1/measure1，marker应不执行；M speculate:train0/measure1，source分支方向改变，marker可推测执行但不得退休。Load/NOP每control配对，测前同一owned hot marker line读preparation。A/B/M不跨history补格，每trial6格固定轮转，奇trial反序。18trial×6格=108window/process；3epochs×chain16/32=6fresh process/648window，15秒进程间隔。一次JIT调用，移除窗口内libc计时；不把userPMU cycles当direct内存latency。marker/data/code仅own mappings，无BPF在测量时活动。

7events[17,8,112,6,34,59,1] = cycles/IR/LD_SPEC/LD_RETIRED/BR_MIS_PRED_RETIRED/OP_SPEC/L1I_CACHE_REFILL，USER-only GROUP+ID/pinned/noMUX；7不能完整open/read则CAPABILITY_UNAVAILABLE，first failure stop，不降为6假装同合同。group decoder复用 `probes/common/perf_group_read.h`，原结果/codeVA/PFN/stored bytes/typedcounts/time/sysfsbaseline硬门。

## N0判据与停止

逐trial作Load−NOP LD_SPEC与LD_RETIRED，先统计不扣别的PMU。两chain/三epoch每项：A LD_SPEC/RET mean均[.9,1.1]；B均absmean≤.1；M LD_SPEC mean[.9,1.1]、LD_RET absmean≤.1；对应abs(delta−expected)线性q90≤1，所有tails保留。每mode M branchmiss median−B median≥.75、A/B median≤.25，作为训练方向干预激励，不未经PC采样声称每miss只属CBZ。IR两marker均值差abs≤1，证明执行marker未带额外retired path；L1I refill披露并要求全window≤1（一shot非旧per-ITER .001门），不改旧failed gates。

6process均过 SPECULATIVE_MARKER_QUALIFIED；否则MARKER_NOT_QUALIFIED、无N扫。别把OP_SPEC/OP_RETIRED当allocationunit，别从NOP+Any eligibility推1 physical slot。后续filler窗口需另注册不同class/单位和supply/activeconstraint反证。技术/环境first failure立即停，partial保持private结构化empty metrics与source/launch谱系；不追门重试。

## 实现与证据

`probes/diagnostic/rob_speculative_marker.c`、`tools/diagnostic/rob_spec_marker_analysis.py`、`run_sm8650_rob_spec_marker.py`；tests producer/analysis/raw，实际NDK code/hostplan/独立decode/typed producer→driver→writer→immutable raw攻击通过后才6process。branch codex/sm8650-tlb-hierarchy-r2，primary独占；未完成 `docs/open-items.md`。TLB Gunyah/Stage2及large-N干预独立跟踪，本probe不改变它们。
