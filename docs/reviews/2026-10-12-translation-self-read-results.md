# 自有root descriptor：真机只读能力通过（2026-10-12）

## 本次任务的目的（给人类看）

从VA/PFN间接代理迈向实际descriptor可观测性。按 `docs/design/2026-10-12-translation-self-read.md`，检查BPF load/attach/owned read是否可用，不推导TLB容量。

**裁定 SELF_ROOT_DESCRIPTOR_READ：3/3 fresh进程通过。** 每进程指定getpid正控恰3次、wrong syscall/foreign child负控0，TGID和实际BTF偏移匹配，mm/pgd非零、两个自有root项均table类型，stage6/read errno0。首次读失败会锁存不被后续成功覆盖，故hits3/stage6需经过三次成功；所有link/program/map在输出前已close，无pin、无sysctl/内核写入。

`probes/diagnostic/translation_self_bpf.h` 78实际BPF指令，`probes/diagnostic/translation_self_read.c` Android loader，`tools/diagnostic/translation_self_analysis.py` 合同，`tools/diagnostic/translation_self_raw.py` 从binary_source不可变源码重编实际计划审计，`tools/diagnostic/run_sm8650_translation_self.py` 三进程串行driver。源7224957 / 两NDK build30e6082 / actual launch21c3034，branch `codex/sm8650-tlb-hierarchy-r2`；binary SHA256 `ab9fd93fc919527bf20c34e9d8b483df7bc4a40baf229c27a42a7995ed1ba7e6`，精确目标BTF SHA `edf0efa6c0a4d661367567ae7386985c58e42d6e4cc700a0903f8eb831c6c6e1`。

原raw `data/private/20261012T132605Z-translation-self-read/`，20文件SHA，所有绝对VA/PFN/内核指针私有。匿名验证 `docs/reviews/evidence/2026-10-12-translation-self-read/validation.json` 和 `independent-check.json`；另一算术逐进程直接raw核对双过滤、实际helper序列、负/正count、两root索引与类型，无差异。完整producer→driver→落盘→回读15软件测试与两NDK字节一致通过，软件内核模拟不冒充本次真机能力。

**实质意义**：root确实具有本路径的BPF load/attach和kernel read能力，已获得自有root descriptor直接读数。它解除“类型可读但kernel read尚未验证”的局部阻塞；不证明一般内核任意读权限、当前协议leaf CONT=0、HPA开关状态或物理2048容量。叶PTE/CONT/HPA仍UNKNOWN，kptr_restrict=2和masked全局地址没有改变。

下一步先取得自有leaf PTE指针并对照pagemap身份，避开未观测direct-map偏置。`ptep_set_access_flags` 符号名可见而filter_functions未列出仅是线索，attach/实际事件触发尚未验证；完整叶页表检查需独立冻结，不把函数名可见当实证。owner/触发与剩余physical目标在 `docs/open-items.md`。
