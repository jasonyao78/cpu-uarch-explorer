# Shared-memfd alias leaf观测适用性 v1.0（2026-10-12）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-translation-self-leaf-results.md` /77a3293认证owned anonymous COW入口，现在验证该方法能否用于TLB实验实际采用的shared-memfd alias。先能力检查，不采性能、不回填旧CONT。

同一memfd8192B，canonical两个4K页写prefault，第二组alias相同offset映射但先仅read prefault；canonical/alias两端pagemap present/非swap/非零unique且各页相同PFN。复用 `probes/diagnostic/translation_leaf_bpf.h` 的同45指令PID+VA过滤：foreign child的alias selected write与父wrong-page write为negative，父selected write为positive，读ptep及requested PTE PFN须一致。共享页不会COW换PFN；child写改变shared数据属于本toy触发，不声称performance图/稳态相同。

三fresh进程、15秒间隔、每进程30秒，预先规定负控0/正控1、source/BTF/部署SHA/CPU/环境/FD门；全部通过才SHARED_LEAF_DESCRIPTOR_READ。0事件=NOT_EXCITED、首个不合格停且无重试；capability denied留errno/verifier，无global settings/PTE写，event/program/map全部FD关闭。CONT只观察read→write函数入口，不认证未来benchmark稳态/HPA。

新producer `probes/diagnostic/translation_shared_leaf.c`，consumer `tools/diagnostic/translation_shared_leaf_analysis.py`、raw `tools/diagnostic/translation_shared_leaf_raw.py`、driver `tools/diagnostic/run_sm8650_shared_leaf.py`。consumer复用已验证typed leaf合同并强制shared backing及canonical身份；不可变source重新生成实际计划。新测试 `tools/diagnostic/tests/test_shared_leaf.py` 真实producer计划→writer→回读、canonical不一致/typed/PFN migration/negative/无事件反例；生产链延续已验证source重生方法，双NDK/source/build/actual launch/raw SHA分列，software和target证据分开。成功后才设计descriptor cohort+instrumentation匹配控制，不直接进入旧曲线或宣称capacity。owner primary，branch codex/sm8650-tlb-hierarchy-r2。
