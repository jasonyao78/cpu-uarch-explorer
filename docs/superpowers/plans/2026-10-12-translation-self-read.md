# 自有root descriptor能力 Implementation Plan

## 本次任务的目的（给人类看）

实施 `docs/design/2026-10-12-translation-self-read.md` 的三进程有限能力检查，不恢复既有曲线或改内核安全设置。

**Goal:** 有独立双过滤反例的BPF直线程序，确定自有root descriptor是否可读。
**Architecture:** pure BPF emitter+native计划导出、Android FD生命周期loader；精确BTF绑定，匿名consumer及串行driver。
**Tech Stack:** C/NDK27.2/API34、Python unittest/自立BPF解释器、adb；single primary。

- [ ] 在 `tools/diagnostic/tests/test_translation_self.py` 写真实producer缺失RED；编译实际C计划，独立VM验证PID/syscall双过滤与5层probe_read、errno每层中断、两root实际索引和无跳越界，不用模拟读冒充真机。
- [ ] 实现 `probes/diagnostic/translation_self_bpf.h` / `probes/diagnostic/translation_self_read.c`，直线有限指令/显式map/program/link清理、运行时BTF前置driver；本机GREEN和NDK Linux编译后source scoped commit。
- [ ] consumer `tools/diagnostic/translation_self_analysis.py` / driver `tools/diagnostic/run_sm8650_translation_self.py`，真配置→raw落盘/回读，缺失/重/typed/negative不为0/owner不匹配/descriptor类型错均拒；三进程完整且每项门过才positive。
- [ ] 双NDK一致、recipe/source/plan/binary绑定，新码和关联诊断回归；commit build/launch，device idle+unfinished0+BTF/部署SHA+环境只读预检后串行3进程，无重试。
- [ ] raw第二算术独立复核、匿名capability状态/完整raw SHA入库，更新报告/README/open-items和授权记忆；leaf CONT/HPA/physical参数继续UNKNOWN。
