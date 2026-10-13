# Descriptor graph连接实施计划

## 本次任务的目的（给人类看）

执行 `docs/design/2026-10-13-tlb-descriptor-graph.md`；以真实32-node链、两alias布局和actual descriptor身份闭环，作为large-N容量下一步基础。

- [ ] `test_descriptor_graph.py` actual producer missing RED；C --plan、--bpf-plan PID/VA/FD、固定LCG cycle、guard geometry和exact99/32复用；host拒测，NDK严格编译GREEN。
- [ ] `descriptor_graph_analysis.py` / raw / driver强制64captures和同PFN/data graph，实际PTE关系/物理descriptor line激励门；真实C与VM→driver→writer→immutable-source raw反例；named no excitation/denial/first bad stop。
- [ ] 两NDK相同/实际kernel解码/注册source/plan/build/launch；idle/journal/BTF/身份/环境后3fresh进程，first bad stop。
- [ ] raw独立第二算术与匿名布局/CONT/SHA报告；更新goal距离/README/open-items/workflow/memory；不叫physical容量或steady CONT。
