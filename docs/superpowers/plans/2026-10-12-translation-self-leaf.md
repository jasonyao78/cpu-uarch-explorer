# Owned leaf descriptor Implementation Plan

## 本次任务的目的（给人类看）

按 `docs/design/2026-10-12-translation-self-leaf.md` 验证直接owned leaf指针和PTE/PFN身份。

**Goal:** 三进程有限能力，负控双过滤，0事件命名NOT_EXCITED。
**Architecture:** 独立KPROBE emitter/实际C计划，FD生命周期loader，实际producer→driver→raw消费者。
**Tech Stack:** C/NDK27.2/API34/Python/独立BPF VM/adb；primary串行。

- [x] `tools/diagnostic/tests/test_translation_leaf.py` 真实producer缺失RED，再实现 `probes/diagnostic/translation_leaf_bpf.h` / `probes/diagnostic/translation_self_leaf.c`；编译真实plan、双过滤/首错锁存/跳界/PTE source反例GREEN。
- [x] `tools/diagnostic/translation_leaf_analysis.py` / `tools/diagnostic/run_sm8650_translation_leaf.py` / `tools/diagnostic/translation_leaf_raw.py` 实际plan→writer→回读。缺失/重复/typed/PFN错/未激励/权限拒绝测试，原root reader兼容。
- [ ] 双NDK与实际字节码plan/SHA/source谱系入库，新关联回归通过后冻结launch；设备ownership/未闭环/BTF/部署SHA及环境预检后3进程，首次不合格停止。
- [ ] 独立raw第二算术、完整匿名证据/未激励/失败/CONT观察作用域归档，更新状态/open-items/授权记忆；不认证稳态CONT/HPA/物理capacity。
