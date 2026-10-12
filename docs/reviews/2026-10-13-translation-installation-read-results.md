# Shared 安装时的 leaf 与父表描述符直接观察（2026-10-13）

## 本次任务的目的（给人类看）

补上shared write触发NOT_EXCITED的能力缺口，直接观察本进程shared alias首次安装时的leaf/PTE父项关系，为后续TLB的descriptor物理布局对照建立证据入口。

**通过：3/3新进程 `OWNED_SHARED_DESCRIPTOR_HIERARCHY_READ`。** 每进程foreign PID与wrong VA负控0，selected安装entry1/return1，canonical与两个alias的PFN稳定一致。installed leaf PFN匹配canonical；实际PMD/PTE指针的索引匹配目标VA；PGD与PMD都是table descriptor，两个Linux父表子页不同；从两级实际pointer page与descriptor child PA独立求出的关系相等。没有猜direct-map基址，没有改变全局环境、安全设置或PTE，event/program/map均无pin并已关闭。BPF写自己的结果map及正常page fault安装owned PTE是本观察机制，不应表述成“内核没有任何写”。

目标branch `codex/sm8650-tlb-hierarchy-r2`；producer `probes/diagnostic/translation_install_read.c` / emitter `probes/diagnostic/translation_install_bpf.h`；consumer `tools/diagnostic/translation_install_analysis.py` / raw `tools/diagnostic/translation_install_raw.py` / driver `tools/diagnostic/run_sm8650_translation_install.py`。source `0fcccb2`，build `fc2fdcc`，actual launch `81fc4d1`；binary SHA256 `8b8dca91e8ab6913cf8f2e7d63362c7d30b2e43f077f47f7c6c755711d7ed9d1`；NDK27.2/API34/static/C11/O2/Werror两次独立构建一致。实际entry99条、return32条；31项关联验证含actualproducer→实际指令VM→registered driver→writer→immutable-source raw reader及损坏重哈希反例。软件模拟不作目标证明。

raw保存在 `data/private/20261012T162402Z-translation-installation-read/`；实际时区为2026-10-13本地，目录名使用UTC。所有kernel VA/绝对PFN/地址关系数值留private，公开 `docs/reviews/evidence/2026-10-13-translation-installation-read/validation.json` 与 `independent-check.json` 只列谓词、匿名状态和20 raw SHA。第二算术不从消费者结论反推，直接对原始16-word capture、canonical/alias pagemap、类型、索引、两个层级差和原SHA逐项核对，3/3一致。

| epoch | entry / return | PID / VA负控 | leaf PFN匹配 | 两级关系 | 初始安装CONT |
|---|---|---|---|---|---|
| 0 | 1 / 1 | 0 | 是 | 一致 | 0 |
| 1 | 1 / 1 | 0 | 是 | 一致 | 0 |
| 2 | 1 / 1 | 0 | 是 | 一致 | 0 |

这比VA父项分组代理更进一步：本owned安装实例的Linux table descriptor、子表PA及leaf身份可以直接观察。它不等于任意kernel memory读权限、machine DRAM物理地址/HPA证书，也不证明旧TLB performance runs的descriptor布局或steady CONT。CONT读数只属于首次shared read安装时点；第三方或官方2048候选不能由本能力直接变为实测capacity。

原 `docs/reviews/2026-10-12-translation-shared-leaf-results.md` 的NOT_EXCITED维持原终态；新入口没有覆盖或回填旧记录。下一有限设计应把已观察的leaf/父表身份绑定到同一进程的性能graph，先卸载observer再计数，并对观察造成的cache/translation准备历史做对称控制；只有实际descriptor布局形成激励，才能讨论它对几何reach的贡献。ROB继续独立anchor顺序控制；整体physical TLB/ROB目标仍OPEN，owner/触发见 `docs/open-items.md`。
