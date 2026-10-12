# SM8650 pagemap可观测能力（冻结v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-tlb-balanced-reach-results.md` 的同低位几何反证不能唯一归因。先用小的只读自进程pagemap查询确认PFN是否实际可见，而非再扩大TLB网格。[Linux官方pagemap文档](https://www.kernel.org/doc/html/latest/admin-guide/mm/pagemap.html)说明present bit63、swapped bit62、PFN低55bits；缺CAP_SYS_ADMIN时PFN可被清零。Android root不是非零PFN的证书，也不能读ARM CONT位。

`probes/diagnostic/pagemap_visibility.cpp` 共用 `probes/diagnostic/tlb_balanced_reach_layout.h` 的三族各前16node页，union47页，4GiB仅VA reserve，192KiB以内payload；MADV_NOHUGEPAGE、4096 base page、前后AnonHugePages0。按sorted union逐页写非零marker避免共享zero page，所有页两次查询 `pread(/proc/self/pagemap,8,8*VPN)`，解码共用 `probes/common/pagemap_decode.h`。不读其它进程，不修改sysfs/频率/内核/PTE，不用EL3指令。raw仅private，公开只计数/源SHA，不公开absolute PFN/VA。

三fresh进程，每个前后两快照；native实际--plan、独立selector/bitmask测试、driver写盘回读、typed/missing/duplicate/conflict及masked-zero反例后才上板。两快照所有页present/not swapped、所有PFN非零/unique/相等才为visible-stable；零域=opaque-or-zero，任何变化/partial/missing保留命名状态，不能把零当PFN0。非零raw证据仅证明本权限/本映射可观测，不能识别旧映射PFN、CONT/HPA、cache压力或容量。看见PFN后另冻将PFN与同窗事件配对的实验，不因本能力过门自动命名机制。

branch `codex/sm8650-tlb-hierarchy-r2`；driver `tools/diagnostic/run_sm8650_pagemap_visibility.py`，consumer `tools/diagnostic/pagemap_visibility_analysis.py`，tests `tools/diagnostic/tests/test_pagemap_visibility*.py`，build/plan证据 `docs/reviews/evidence/2026-10-12-pagemap-visibility/`。source/build-consumer/launch/report与SHA分列，read-only基线/journal/ownership门仍复用；3进程间5s，异常留原样，不改变旧raw/门。
