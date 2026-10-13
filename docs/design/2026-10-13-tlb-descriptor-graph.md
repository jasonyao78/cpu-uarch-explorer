# TLB实际地址链与descriptor身份 v1.0（有限连接资格）

## 本次任务的目的（给人类看）

把 `docs/reviews/2026-10-13-translation-installation-read-results.md` 的单页能力连接到实际指针链：相同32个memfd数据页、相同stored ordinal/order/data PFN，packed/spaced各32alias，直接观察实际leaf及两级父项并验证真实链闭环。先证明可观测布局激励，随后独立协议扩大到容量转折；本资格不计PMU，不用小N叫TLB容量。

方案比较：未认证的PA->VA全局走表扩大权限/假设；新多key BPF增加配对状态复杂度。采用已实证entry99/return32 exact-VA程序逐节点有限安装读取，保持kernel-read许可范围和错误锁存，代价是每节点独立load/attach/close。本新producer不修改已验证emitter。

## 实际mapping和链

canonical32页shared memfd，每页首8B存next ordinal，固定LCG Fisher-Yates seed137形成一个32-node cycle。reserve4GiB PROT_NONE，packed base向上对齐2GiB，spaced base=packed+1GiB；packed stride8192，spaced stride(2MiB+8192)。两个layout的VPN低8hist相同；root两个索引同属一个64B virtual root line。每node用one-page MAP_SHARED|MAP_FIXED、相邻guard保持fault-around不能替其它declared node建立PTE。每layout保留一个独立guarded negative alias，fileoff=node^1；negative之前重映射，parent selected/negative均须absent。

每node map128B/entry+return仅当前TGID+selectedVA，foreign child触发和parent wrongVA负控0，然后parent first read selected触发entry1/return1；source当前mm/pgd、PTE/PFN、类型/索引、两级关系必须过。独立child/scratch只属准备，全部observer FD关闭后才调用真实链核验；无pin/PTE或全局配置写，正常fault/map更新owned页表。

核心 `LDR; MADD(index,stride,base); SUBS; B.NE` 固定4ISA，同stored ordinal和physical demand order，仅base/stride参数不同。每layout512loads恰16圈，head必须返回初始、逐节点内容和logical cycle由consumer独立核对；原alias3ISA协议不回填或假装码等价。canonical及alias所有32PFN两端present/unique/stable、两layout分别match同一canonical vector。先保存每capture实际99/32动态计划与16word数据，绝对kernel VA/PFN只private。

## 硬门与命名

三新进程、15秒间隔、每进程120秒；计划64capture/进程，共192；首技术/环境/未激励停止，不重复同节点追事件、不跳过缺节点。允许CAPABILITY_UNAVAILABLE/NOT_EXCITED命名停止；任一partial/dup/identity/类型/索引/链/PFN/source/actual计划错为技术失败，不以较晚成功覆盖。完整3/3才DESCRIPTOR_GRAPH_BOUND。

derived Linux leaf-table PA来自PMD descriptor，PMD-table PA来自PGD；leaf entry PA=table PA+VA index8，PMD entry PA同理。只有已核对关系才能分组；每shape需同一mm/pgd、同一两级关系，packed leaf table pages=1、spaced=32且leaf entry64B lines=8/32作为本真实布局激励硬门。root kernel pointer line只是virtual identity，不猜pgd physical PA；Linux table PA不自动认证machine DRAM/EL2 HPA。initial-installation CONT按每节点报告，不作为steady或旧run读数。

## 交付与后续

`probes/diagnostic/tlb_descriptor_graph.c` / 复用 `probes/diagnostic/translation_install_bpf.h`；`tools/diagnostic/descriptor_graph_analysis.py` / `descriptor_graph_raw.py` / `run_sm8650_descriptor_graph.py`；tests `tools/diagnostic/tests/test_descriptor_graph.py` / analysis/driver。actual C --plan/--bpf-plan -> emitted VM -> driver -> writer -> immutable-source再生raw，typed/缺失/重复/乱序/PFN/descriptor/首次坏节点/无事件攻击，两NDK/实际MADD解码/source/build/launch链后才上板。独占primary，branch codex/sm8650-tlb-hierarchy-r2；成功后才另冻结large-N容量与allocator顺序布局干预，ways/hash与ROB单位仍OPEN，`docs/open-items.md`。
