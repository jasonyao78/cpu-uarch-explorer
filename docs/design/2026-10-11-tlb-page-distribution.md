# TLB 页集合分布敏感性（Q-A，冻结 v1）

## 本次任务的目的（给人类看）

完成Q-A的有限必做：L1D TLB refill/访问曲线是否受页集合影响，检查cache-line offset及同集合order反证。页集合与遍历随机化分开实现。只报告分布敏感与该协议转折，不将refill计数直接换算物理TLB entry，也不将差异归因PFN着色/HPA。

## 构造与预算

`probes/diagnostic/tlb_page_distribution.cpp` / `probes/diagnostic/tlb_page_distribution_layout.h` 在同一guarded 1GiB VA pool（262144个4K页）准备3族最大2048节点，然后每N使用固定前缀集合：

- contiguous：page_id(i)=i。
- sparse：page_id(i)=65i（非连续页集合，mod64=i mod64）。
- random-set：seed271的xorshift64(13,7,17) Fisher-Yates对4096个group置换，page_id(i)=64group[i]+(i mod64)。每节点选不同256KiB组，page_id的mod64和另两族一致；这是随机页集合而非只打乱连续集合的顺序。

节点地址=base+4096page_id+offset(page_id)，offset两策略独立：constant0 / rotated=64(page_id mod64)。每页一节点、64B line footprint一致，3族同N在rotated策略有完全相同offset直方图；链order为同N seed137置换及其逆序。每族集合、offset、order独立全量记录，relink只改页内节点内容。初始化最大3族都在窗外，实际union触碰页与VA保留跨度分列。各N/shape共用该mapping，不将seed复现充当独立PFN分配；五fresh进程为独立mapping epochs。匿名physical PFN/PTE_CONT/HPA不可观察则在原始geometry明确UNKNOWN；AnonHugePages=0不证明无聚合。

N=[32,64,80,96,112,128,160,192,256,512,1024,2048]，3集合×2offset×2order×12N=144非空cell+1floor。warmup与正式总loads均为floor(2^20/N)*N，保证每窗完整闭环；同N对照访问次数一致。3round/cell全留，5fresh mapping×435窗=2175窗，奇epoch整序反转（floor也移动），15s间隔，无反复到过门。显式单寄存器LDR/SUBS/B.NE核，与K链K1算法一致，独立反汇编验无spill；链头回归真核验。

## 观测与判据

CPU7/type8/GROUP+ID/exclude_kernel,hv/pinned；六事件[0x11 cycles,0x08 IR,0x05 L1D_TLB_REFILL,0x03 L1D_CACHE_REFILL,0x34 DTLB_WALK,0x35 ITLB_WALK]。完整请求/实现/源二进制谱系、PMU IDs、before/after4K backing、每窗等时不mux、计数不回退与同N三族offset直方图通过才接受技术记录。IR门[.95,1.05]*3loads，包含read/call固定user开销。

消费者 `tools/diagnostic/tlb_distribution_analysis.py` 输出每窗及Σ比的refills/load、walks/load、data-refills/load、I-walk/load、cycles/load；保留空窗相减及负值，不用ratio-of-medians。背景门：floor中位cycles≤非空窗C的1%；floor L1D-TLB refill≤非空loads*.001；每非空I-walk/loads≤.001。未过门保持原窗，全局输出INCONCLUSIVE；该epoch/集合/offset/order任一N背景失败时，曲线出口INCOMPUTABLE，不再命名区间；比较出口admissible=false/replicated=false，数值复制另保留numeric_replicated，不可脱离门读为已确认差异。禁止删点救门。0x03包括walk产生的cache流量，不是纯data load miss；常量offset只能揭露cache竞争解释，不能严格单独剥离它。

主对比只用rotated：sparse-contiguous与random-set-contiguous，按同epoch/N/order配对。预注册有限可复现差异：至少一个N/对照在两order、五epochs共10个delta均同方向且|delta|≥.05 refill/load →DISTRIBUTION_SENSITIVE；所有主delta都|delta|<.05 →NO_DIFFERENCE_DETECTED（报告实际delta范围与.05操作检出门，不冒称置信区间/物理无差异）；其余INCONCLUSIVE。非主constant结果完整并列，若offset也改变响应必须醒目保留。不存在ATTRIBUTED升级态，本协议无HPA或PFN干预能力。

局部曲线另报0.5 refills/load的操作性交叉区间（计数不等于miss概率）：每epoch/集合/offset/order的N曲线，非单调越线回落优先ambiguous；首点越线left-censored，末点首次越线或后续平台不足2点right-censored；无越线no-crossing-through2048；其余首越线前/后N为区间，余后点都需≥.5。不强求曲线给出96；TRM96是官方结构参考，不是手机参数的独立测量。

## 原理依据与执行计划

`/Users/michaelyao/workspace/cpu-uarch-ref/docs/Arm_Cortex_X4_Core_TRM_102484_0003_06_en.pdf` §5.1公开描述L1D TLB fully associative/96 entries，解释为什么单独PFN着色不成立；聚合/页表局部性/缓存/替换/投机仍可竞争。PMU事件参照 [Arm官方JSON](https://raw.githubusercontent.com/ARM-software/data/master/pmu/cortex-x4.json)。原问题 `docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md` §1.2 Q-A。

1. `tools/diagnostic/tests/test_tlb_distribution_producer.py` 先RED：真实144+floor计划、实际node链接闭环、page set与order不同、同Noffset直方图匹配；实现两C++文件后GREEN。
2. 双NDK构建/独立Capstone核解码；`docs/reviews/evidence/2026-10-11-tlb-page-distribution/` 登记source/build/plan，另记实际launch。
3. 消费+`tools/diagnostic/run_sm8650_distribution.py`，真实producer→driver/writer→raw消费，首坏停机、缺失/冲突/重复/重哈希/乱序、非单调/删失/背景反例。外部模拟与目标板证据明确分开，全量diagnostic回归后有限上板。
4. 第二套直接raw数学重算2175窗、所有对比/区间，与正式consumer一致；完整raw/SHA/匿名derived证据+图+报告+`docs/reviews/2026-10-11-tlb-rob-goal-ledger.md`终态更新，小步本地提交。

r2工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`，分支 `codex/sm8650-tlb-hierarchy-r2`；单代理独占手机，无环境写入。formal schema/runner暂不改，诊断JSONL不冒称schema v2。若有限域不识别，按上述命名真实终态而不是无限加点。
