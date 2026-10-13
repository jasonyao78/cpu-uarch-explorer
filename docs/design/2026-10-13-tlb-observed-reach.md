# 实际descriptor绑定的TLB reach v1.0（N0先行，有限扫描冻结）

## 本次任务的目的（给人类看）

把 `docs/reviews/2026-10-13-translation-persistent-read-results.md` 的可扩展观察器连接到容量附近真实访存和PMU。直接记录每个actual node的PTE/两级父项、初始CONT及canonical PFN，在同数据页/stored ordinal/physical visit order下比较packed/spaced。该对照检验几何响应并限定reach，不能独自认证physical2048/8ways。

## 几何与实际指令

一个N-page memfd，两shape alias，guard页防fault-around。reserve16GiB纯VA，packed base向上8GiB对齐、spaced=packed+1GiB；stride分别3*4096与(512+3)*4096，都是奇page步长，实际VPN低8hist精确相同，N为256倍数时覆盖全部256候选bin。**旧32graph的2page步长只覆盖128 bin，故不能直接作为全局容量布局。** 新32低规模也需重新资格，不回填旧qualified/source。

LCG32 Fisher-Yates seed137建立一个ordinal cycle；reverse flag只反转visit order，两shape存同next ordinal，真实kernel固定 `LDR; MADD; SUBS; B.NE`。每窗口loads=N*ceil(1048576/N)，整数圈数，head必须闭环；PMU前同预算warm。page首word offset0，各N需求PA/offset/order匹配；page-base集中L1 sets可能有data refill，不能把全32页能放入L1总bytes当全hits，data refill作为独立tap披露。

## Observer/性能隔离及PMU

复用已实证entry102/return32/136B map，PID常量+private exactVA，actual reset/capture C gate必须接受前次状态才advance。每node wrongVA负控、首次foreign child一次，所有PFN/word/type/index/两级关系/bias/source/dynamic words硬门；两shape全部采完且observer全部FD关闭，再固定15秒准备冷却（不在性能窗），之后开6events[17,8,5,52,3,1]=cycles/IR/L1dTLB refill/genericDTLBwalk/L1Drefill/L1Irefill。无全局设置写；pagemap FD只在测量外读。

每process三round，packed/spaced按round轮转；reverse process反序。每数据窗前同budget warm，不在N之间拼接数据。同6PMU空窗三round置于数据前/后三round，完整原值；空窗减值不裁零。IR/loads需在4±.001，无MUX、ID唯一、CPU7；L1I refill/loads≤.001，各floor/data背景明确。不以cycles直接算memorylatency或allocation。

## N0和有限scan

N0三个fresh，N32/order[0,1,0]。每process实际64capture、两shape3round/六前后empty窗，12PMUwindow；直接capture/chain/source硬门必过。每shape三data窗校正walk/loads≤.01，技术/background全部过才 OBSERVED_GRAPH_QUALIFIED。不要求L1Drefill低（L1 set冲突并不等同TLB故障）。任一not-qualified不scan、不降门。

资格通过后同source/binary、原raw qualification SHA作为输入再scan：N[32,1024,1536,1792,2048,2304]×三epoch；奇epoch逆N顺序并reverse order，18fresh/216PMU窗。每process15秒间隔、最大600秒，首技术/环境/未激励停；未完整矩阵不拼接/不硬报主结果。此前旧泛化模型/失败门不改变。

主对照：每N、每epoch/round的(spaced−packed)校正walk/loads≥.10才该N replicated_geometry_difference；N32阴性需全≤.01。不是平均救门。单curve onset是三round全≥.10且至少两个高侧点、有低侧点、后续持续；左/右删失与非单调原样记录，不给唯一physical参数。实际leaf/parent PA line/pages直接计数，Linux IPA域不额外认证HPA/steady CONT。通用walk事件不分S1/S2；不把observed descriptors数直接当MMUTC occupied entries。

## 交付和后续

`probes/diagnostic/tlb_observed_reach.c`；复用 `translation_persistent_bpf.h`，C gates独立共享 `translation_persistent_gate.h`，旧8node API/字节/终态不变。`tools/diagnostic/tlb_observed_reach_analysis.py` / raw / driver，actual native layout/BPFplans、双NDK/独立kernel decode、真实producer→driver→writer→raw及缺失/乱序/首次失败/参数/source攻击后N0。branch codex/sm8650-tlb-hierarchy-r2；primary独占。

下一fixedVA/dataPFN改变真实PTE-table关联、VA/ASID身份倍增草案 `docs/design/2026-10-13-tlb-translation-identity-multiplicity.md`；两者另冻。物理TLBcapacity/organization、ROB仍0/3。工程/未知归 `docs/open-items.md`，不把本有限对照叫整个目标完成。
