# TLB同物理页、不同VA几何对照（冻结v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-tlb-balanced-reach-results.md` 已反证页数/低8位分布的简单解释，但数据PFN未知；`docs/reviews/2026-10-12-pagemap-visibility-results.md` 新证实本目标可读非零PFN。下一步保持**同一物理数据页身份/实际节点offset/闭环访问次序**，改变VA几何，检验“数据PFN分布差异足以解释旧几何效应”的替代模型。不是再追一次容量knee，也不把同PA轨迹升级成全部cache流量相同。

## 可审计激励

新增 `probes/diagnostic/tlb_shared_alias.cpp`、`probes/diagnostic/tlb_shared_alias_layout.h`。memfd backing=2560×4KiB（10MiB）；canonical mapping prefault，每个physical page只建立一次。三独立自有arena各2^20页（12GiB合计仅VA reserve），base对齐256基础页，使实际VPN低8位hist相同。每族i映射同一fd的offset=i×4096到页id=dense i / spaced257i / balanced-random256*perm4096_seed271[i]+i%256；三个alias同时存在，没有测量中remap、mprotect或TLBI。MAP_FIXED仅在该进程自有reservation以内使用，销毁由RAII完成。

N={1024,1536,1792,2048,2560}，三族×两order=30格+空窗；三round/格，每窗及warmup loads=floor(1048576/N)*N；三fresh进程，奇epoch整条件reverse，共279窗。固定offset=64*(i%64)，随机seed137及reverse。每次link向同physical node写当前族的next VA，LDR/SUBS/B.NE核心闭环返回head。因此demand数据页/offset/访问顺序配对，**pointer数值、页表descriptor物理布局、虚拟高位、其它投机/预取流量仍改变或未知**；CONT/HPA仍UNKNOWN。

canonical PFN非零/unique；每格alias前后全部N个PFN必须逐项等于初始canonical[:N]，present/not-swapped，任何masked/迁移/缺失为技术失败，首坏停止，不挑静默窗口。PFN读取在warmup之前和所有正式窗之后，不能夹进PMU窗口。每格前后smaps必须KernelPageSize/MMUPageSize=4KiB，AnonHugePages/ShmemPmdMapped/FilePmdMapped=0（canonical及三arena），显式区分memfd与anonymous后端；这些仍不是CONT位读数。所有absolute PFN及canonical/alias VA留private，公开仅配对成功数、匿名geometry与SHA。

PMU与旧均衡对照同事件[0x11,0x08,0x05,0x2d,0x2f,0x34]，GROUP+ID/pinned/user-only/noRESET/noMUX/CPU7/4096。IR=3*loads±5%，空窗cycles中位≤正式窗1%，翻译事件空窗中位≤.001*loads，L1 refill/load∈[.75,1.25]。同process/order/N三窗sum count/sum loads，spaced或random−dense差值，三epochs×两order六配对全部≥.10（或≤−.10）才复制；全部门过且任意N复制=GEOMETRY_SENSITIVE_WITH_MATCHED_DATA_PFNS。全部差绝对值<.10=NO_DIFFERENCE_DETECTED，否则INCONCLUSIVE；不靠均值/删窗救门。任何技术错误仅停止，完整raw保留。

## 软件与证据出口

helper允许以宿主基础页尺寸运行同一mmap/MAP_SHARED/link算法：macOS16KiB真实共享fd/图测试是软件证据，目标4KiB真实PFN核验不可替代。actual --plan/--layout（共用生产geometry）与独立oracle；native所有30图同canonical backing逐节点核验和闭环访问；producer→driver→writer→raw的缺失/重复/乱序/类型/PFN冲突/endpoint/masked/共享backing反例；两次NDK字节一致、内核反汇编后才串行采数。consumer `tools/diagnostic/tlb_alias_analysis.py`、driver `tools/diagnostic/run_sm8650_tlb_alias.py`、tests `tools/diagnostic/tests/test_tlb_alias*.py`、evidence `docs/reviews/evidence/2026-10-12-tlb-shared-alias/`。SOURCE/build-consumer/launch/report分列commit。旧数据不改，不回填UNKNOWN。

branch `codex/sm8650-tlb-hierarchy-r2`；owner=当前端到端Agent。精确physical entries/ways/hash、descriptor直接观察及ROB α/active constraint仍OPEN。全局几何对照只关相应有限替代模型，不以单个通过宣告CPU部件全部完成。
