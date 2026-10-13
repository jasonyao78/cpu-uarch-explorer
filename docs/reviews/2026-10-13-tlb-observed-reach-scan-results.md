# TLB实际descriptor绑定reach：几何差通过，统一物理容量仍不通过（2026-10-13）

## 本次任务的目的（给人类看）

以same dataPFN/storedordinal/order和真实页表身份比较packed3page与spaced515page，完整覆盖256候选低8bin。N0已过 `docs/reviews/2026-10-13-tlb-observed-reach-qualification.md`，本scan同binary/冻结合同 `docs/design/2026-10-13-tlb-observed-reach.md`，无跨run拼接或旧门改写。

**DESCRIPTOR_BOUND_GEOMETRY_DIFFERENCE。** 18/18 fresh进程、52,416/52,416安装捕获、216/216PMU窗，所有IR/I背景门与N32阴性通过。95raw SHA绑定（另锁定资格20SHA），独立直接JSONL复算所有登记边、PFN、descriptor grouping、窗口率与差分精确。每process抓到的同一virtual table bucket没有不同Linux table PA（漂移组=0），仍只安装时点，不能认证performance时/稳态不变。

| N | packed walk/load全部9窗范围 | spaced walk/load全部9窗范围 | 差分全部9窗范围 | 原.10复制门 |
|---:|---|---|---|---|
| 32 | [0.000000,0.000000] | [0.000000,0.000000] | [0.000000,0.000000] | not-replicated |
| 1024 | [0.000006,0.000019] | [0.000001,0.000013] | [-0.000008,0.000005] | not-replicated |
| 1536 | [0.000028,0.000167] | [0.985249,1.000004] | [0.985212,0.999976] | replicated_geometry_difference |
| 1792 | [0.000352,0.150027] | [0.975365,0.994674] | [0.829938,0.990111] | replicated_geometry_difference |
| 2048 | [0.763339,0.931983] | [0.974945,0.993979] | [0.044971,0.221690] | not-replicated |
| 2304 | [0.610775,0.990076] | [0.972117,0.998337] | [-0.004218,0.365329] | not-replicated |

spaced三epoch均为操作转折(1024,1536]；packed E0/E2为(1792,2048]、E1为(1536,1792]，不以均值合成唯一容量。packed E0的2048→2304率下降仍高于.10，冻结规则仅保证高侧越线持续，不承诺率严格单调；所有原值/尾部保留。walk率>1未裁为1，事件数不是缺失leaf条目的单射计数。

## 已缩小的机制缺口

N1536实际packed leaf-table pages=9、Linux leaf64B groups=576；spaced分别1536/1536，PMD tables1/4、PMD64B groups2/193。同1536 dataPFN需求轨迹、所有初始CONT0、候选低8bin每格6、同4ISA loop，却walk差约1。**仅用活跃data页数与低8hist的统一纯leaf-reach模型不足。** 现在descriptor几何不是只从VA估算，是真的已读到；但这是伴生与联合干预，不能唯一归因walk-cache entry占用/PA索引/S2/cache/prefetch/硬件coalescing。

N32的same-demandPA仍有L1D tap差见资格报告；大N也完整保留data/cache tap，不把latency差全部归TLB。Linux table/data PA是guest/IPA，不认证HPA。初始PTE.CONT0不等于硬件TLB coalesced位0，具体r0p1资料核对另列；不能从1024操作转折报告1024 physical entries、不能乘2凑2048或用平均换ways。

## 源码、原始证据和出口

branch `codex/sm8650-tlb-hierarchy-r2`；source7f1c824（C f9c9e1b/consumer b45da5f/driver980c4b3），build3a4ad87；actual launch `ba0ccfd0ce27a7c32151def5cb1d94622f1bd72f`；binary SHA `63df10356c1818cd6190b5dbf4e24e080c6a77ae5735dfc072b0540eb90ea547`。组件 `probes/diagnostic/tlb_observed_reach.c` / `translation_persistent_bpf.h` / `translation_persistent_gate.h`；`tools/diagnostic/tlb_observed_reach_analysis.py` / `tlb_observed_reach_raw.py` / `run_sm8650_tlb_observed_reach.py`。

两NDK27.2/API34/O2/static字节一致、12actual C layouts及真实ELF 4ISA loop独立解码；15生产链测试含完整scan软件正例/transport坏帧/重hash/错PID/PFN/request/source/资格绑定/删失；完整diagnostic632/632通过549.508s（source c9e5231），formal paths未改、不冒称本轮重跑。private `data/private/20261013T075243Z-tlb-observed-reach-scan`，public `docs/reviews/evidence/2026-10-13-tlb-observed-reach/scan-analysis.json` / `scan-independent-check.json` / `scan-windows.csv`。52416个安装CONT全部0只该时点；端点CPU[38.4, 41.9]°C，无环境事务或全局设置写，不认证窗内恒频。

本有限协议结束。下一优先严格区分硬件coalescing/PTE.CONT、固定VA/dataPFN实际table关联、同IPA的VA/ASID身份倍增（`docs/design/2026-10-13-tlb-translation-identity-multiplicity.md` 尚草案）；不能继续同grid加密追某个数字。ROB仍需独立issued/retired/单位和activeconstraint，`docs/design/2026-10-13-rob-near-far-marker-draft.md` 尚草案。三最终参数的目标实測独立识别0/3，官方规格确认与实測独立识别分列；main/远端未集成。
