# 自有shared PTE安装与父项读取能力 v1.0（2026-10-12）

## 本次任务的目的（给人类看）

shared write触发NOT_EXCITED已终态（`docs/reviews/2026-10-12-translation-shared-leaf-results.md`），新路线观察shared alias首次正常页表安装，不循环同页追事件，不写PTE/全局安全配置。检验能否直接取得owned leaf和parent descriptor，并在本实例验证两级地址关系，无猜测direct-map基址。

## 已有线索与新合同

目标do_set_pte/finish_fault符号存在，精确BTF `edf0efa6c0a4d661367567ae7386985c58e42d6e4cc700a0903f8eb831c6c6e1`：vm_fault类型700/112B，address24/pmd48/pte88；task.mm1440、mm.pgd56。只是metadata能力，不是新hook实证。[Linux6.1 memory.c](https://raw.githubusercontent.com/torvalds/linux/v6.1/mm/memory.c) 的do_set_pte(vmf,page,addr)接收实际addr并在调用方PTE锁内安装，finish_fault设vmf.pte；通用源实现不替代目标load/触发核验。

一个memfd8192B canonical写prefault；owned3-page arena PROT_NONE，中间guard，offset0 selected alias/fileoff0、offset8192 negative alias/fileoff4096，MAP_SHARED但不prefault。guard防wrong-VA fault-around提前给selected建立PTE；before canonical两PFN present/unique，parent selected alias non-present。child读取selected为foreign PID负控，parent读negative为wrong VA负控，parent最后第一次读selected为positive。

一个ARRAY128B map，两个GPL KPROBE程序，do_set_pte entry/return perf事件CPU7；sysfs type/retprobe bit确认，无tracefs固定事件/无pin。entry先helper14 owner TGID过滤、pt_regs.x2==selected VA过滤，再读内核提供的vmf.pmd/vmf.pte、当前task.mm/mm.pgd、selected PGD/root和PMD descriptor。ret仅owner且map pending-entry通过才读取captured ptep的8B leaf，必须entry1/return1、完整stage/error0。无匹配入口=NOT_EXCITED；dup/partial/errno/type/PFN/偏移不符为技术失败且首坏状态粘滞保留。任何退出关闭两event、两prog、map及其它FD；异常进程由内核回收。

## 身份/层级裁定

两端canonical PFN不变、after selected/negative alias PFN分别相同；installed leaf&3==3、leaf PA48/PFN等于selected canonical。pmd/pte pointer低12位分别为8*((VA>>21)&511)、8*((VA>>12)&511)；PGD/root和PMD项均table type3。比较(PMD pointer page−PGD child PA)与(PTE pointer page−PMD child PA)的u64差，两者相同才 OWNED_SHARED_DESCRIPTOR_HIERARCHY_READ。不同或未完成不得补成一致；差值/所有kernel VA/absolute PFN私有，公开仅bool/匿名identity/计数/SHA。这只认证本owned实例的Linux页表关系与观测能力，不认证任意kernel内存读、DRAM物理布局或EL2 stage2/HPA状态；未来owned走表先另注册范围。

三fresh进程×15秒间隔，每个30秒；完整3/3上述门通过才positive，首个不合格停止不retry，保留原NOT_EXCITED不升级。不采PMU性能；任何将来性能窗前卸载所有observer，观测对cache/translation准备效应另配对。CONT只属首次read-fault安装时点，不回填旧数据/稳态，不命名2048capacity。

## 实现/验证路径

emitter `probes/diagnostic/translation_install_bpf.h` / producer `probes/diagnostic/translation_install_read.c`；`tools/diagnostic/translation_install_analysis.py` / `tools/diagnostic/translation_install_raw.py` / `tools/diagnostic/run_sm8650_translation_install.py`；tests `tools/diagnostic/tests/test_translation_install.py` / raw producer chain。真实指令VM攻击PID/VA、entry/return配对、首错、dup、每层read错误；真实C计划→driver→writer→immutable source回读，typed/root-PMD-PTE关系/PFN/未激励反例，双NDK/实际plan/source/binary/launch闭环。模拟不当目标能力。owner primary，branch codex/sm8650-tlb-hierarchy-r2；未知与触发 `docs/open-items.md`。
