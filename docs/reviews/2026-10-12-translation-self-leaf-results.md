# 自有leaf PTE：实际指针与PFN身份通过（2026-10-12）

## 本次任务的目的（给人类看）

在已通过root能力基础上，安全取得自有leaf PTE指针，直接观察descriptor并与真实pagemap对账，避免猜测direct-map PA偏置。

**SELF_LEAF_DESCRIPTOR_READ，3/3真机进程通过。** 每进程foreign PID/wrong VA负控0，selected owned VA正控恰1，read_errno0；old/requested PTE都page类型、PFN都与before/after pagemap相同。精确目标BTF/MIDR/4096页/CPU7核验通过，观察器结束前event/program/map关闭，无pin或全局安全/内核PTE写。

新代码 `probes/diagnostic/translation_leaf_bpf.h`（45实际BPF指令）、`probes/diagnostic/translation_self_leaf.c`；consumer `tools/diagnostic/translation_leaf_analysis.py` / immutable raw `tools/diagnostic/translation_leaf_raw.py`，driver `tools/diagnostic/run_sm8650_translation_leaf.py`。source0e8cd63 / build49c7123 / actual launchd235ce3，branch codex/sm8650-tlb-hierarchy-r2；NDK27.2/API34/static/O2/Werror两构建一致，binary SHA `630b1a55317c710b0266b4f24c31b85fa3a4c97371377fb36255c033d82658b9`。13新leaf测试加15原root关联测试=28通过；真实bytecode VM和实际driver→writer→reader都过，软件模拟不冒充目标能力。

原raw `data/private/20261012T135604Z-translation-self-leaf/`；匿名证据 `docs/reviews/evidence/2026-10-12-translation-self-leaf/validation.json` / `independent-check.json`，20raw文件SHA，私有保留完整kernel pointer/VA/PFN/verifier。独立第二算术逐进程核对actual PID/VA双过滤及helper序列、两个snapshot PFN、PTE类型/PFN、count/errno，完全一致。

**可用的新能力**：目标perf-kprobe允许本限定函数/读法，能取得自有leaf PTE pointer并读实际descriptor，属于比VA/PFN代理更直接的证据。COW触发时三项old CONT都为0；这只属于本次COW/reuse入口时点。fork/write改变了mapping状态，不能将该值补给旧TLB匿名/alias批次、steady CONT或HPA，也不认证物理2048条目。旧未观测状态仍UNKNOWN。

后续优先验证shared-memfd read→write触发可否取得实际alias leaf pointer；通过才设计descriptor组身份/CONT endpoint与性能窗口分离的新同PFN几何对照。所有性能窗口前卸载observer，考虑观测本身的缓存/翻译准备效应；kernel pointer只是页表身份代理，physical table PA仍未直接给出，不盲走未观测偏置。ROB下一正交退休生命周期对照独立冻结。owner/触发在 `docs/open-items.md`，本有限能力任务结束，整体physical目标继续OPEN。
