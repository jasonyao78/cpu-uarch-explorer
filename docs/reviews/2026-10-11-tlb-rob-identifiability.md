# SM8650 TLB/ROB 有限探测结论与可识别性（2026-10-11）

## 本次任务的目的（给人类看）

回应“先把CPU部件探测出来”：从实测里分离可复现的运行行为、结构候选与尚不能确定的物理参数，给下一阶段真正可用的边界。手机由当前root Agent独占，所有探针NDK交叉编译成Android arm64、adb部署、有限串行实测、完整raw审计；没有恢复旧大矩阵或等另一上板Agent。

本报告汇总的是用户授权的第一性原理路线，不把原r2任务书所有历史正式Phase自动标成已执行。**有限TLB与ROB对照交付可以结束；“精确物理TLB ways/hash及ROB entries已经测得”不通过。** 物理参数未识别是本组方法的正式终态，不是“CPU不存在该结构”、没有效应、永久不可测或所有CPU部件研究已完成。下一轮只有新增可识别的控制/单位标尺才重开；不是继续复跑当前曲线。

## TLB：已回答的问题与保留边界

| 问题 | 观测与有限裁定 | 可使用的结论 | 不允许的升级 |
|---|---|---|---|
| Q-A L1热端转折 | 2175窗/2160背景门；三页集合、两offset、两order、五mapping，60曲线全部(96,112] | 在旋转offset、固定page-count协议下，0.5 refill/load交叉在96之后、112之内 | 不由交叉给出exact slot count；官方96仅外部结构参考 |
| Q-A 集合分布 | 主INCONCLUSIVE；random-set N1024十个delta全正[.04997349,.09777514]，严格未全过.05 | 保留方向、幅度和映射残差，分布是否达到冻结复制门未确定 | 不改名“无差异”，不后验调.05救门 |
| latency反证 | N64/96 constant约11–12cycles/load并伴cache refill；rotated约4，TLB refill两者都低 | 数据布局足以改变延迟，单延迟曲线不足以判TLB容量；同N页/loads还须控制offset/line压力 | 不把约6cycles净差当纯translation latency |
| Q-B victim冲突 | W9跨victim/历史/方向复制，W8仍有保留的孤立walk；固定victim的后续五mapping/双方向/双跨度得到target7/C1=(7,8]、100/C1=(8,9]，C2至10无onset | 可作地址族条件化的victim响应/操作性reach边界；通用“8页全命中”已被反例推翻 | 不命名7/8ways、LRU或纯数据entry容量；lookup不是admission，整圈walk不是初始缺失项数 |
| Q-C 索引族探索 | 原单域C1/C2差异；新增四域34560窗W12两target十曲线全部I/G1正、G3负，主replicated-low-only-candidate-favored | 在这组共同victim/匹配几何条件下，低位候选获复制支持；旧H1/H3单域等价被打破 | 不把有限候选偏好命名全地址域唯一hash；PTE/CONT/PFN/cache/replacement未唯一排除，W8残差保存 |
| Q-D 并行响应 | 495窗，长窗240/240门；固定总8192页K1/2/4/8的A/C=.553/1.085/2.106/3.039 | 同窗walk occupancy积分随并行链增大；完整counts支持有效在飞占用描述 | A/C>1不是“忙碌概率>100%”，不等于physical walker/MSHR/LQ数量 |
| Q-D 两种作用域 | 固定每链8192页时，K8 loads/C低于K4，A/M与cache/walk流量增大；短门235/240 | 并行收益依赖总working set与窗长；不能只挑固定总页数曲线 | 不把全部短窗也叫qualified，不把A/M直接当纯walk延迟 |

对应完整报告：`docs/reviews/2026-10-11-tlb-page-distribution-results.md`、`docs/reviews/2026-10-11-tlb-victim-history-results.md`、`docs/reviews/2026-10-11-tlb-address-geometry-results.md`、`docs/reviews/2026-10-11-tlb-local-turn-results.md`、`docs/reviews/2026-10-11-tlb-walk-parallel-results.md`（均位于 `docs/reviews/`，各自列全部source/build/launch/raw）。Q-B新standalone协议回答victim/竞争的有限问题；旧任务书B1/B2替换率与正式A1/A2/A3不是同一证据合同，不能自动视为执行完成。

官方资料 `../cpu-uarch-ref/docs/Arm_Cortex_X4_Core_TRM_102484_0003_06_en.pdf` §5.1/r0p3给L1D fully-associative/96的结构参考；目标MIDR0x410fd821是r0p1，资料revision与目标revision分列。HPA/PTE_CONT/PFN没有观测，不以AnonHugePages=0证明无PTE聚合。[Arm事件表](https://raw.githubusercontent.com/ARM-software/data/master/pmu/cortex-x4.json)的refill/walk事件属于各自tap；0x03还含walk造成的cache流量，0x8128是按并行walk数积分。refill/load可>1，不截成概率，不把一次walk必然归为一个起始PTE缺失。

## ROB：有效响应与物理容量的分界

同一fsqrt稳定operand/实际代码对照已得到：NOP fine align0 k8每gap(672,704]、k16(640,672]；align32 k8右端未确认，完整保留。另一资源粗网格NOP(512,704]、ADD/MOVI/MOVR(128,256]，FADD因波动为ambiguous。网格不同结果分别报告，不跨批拼窄区间；N每gap是ISA filler数量，不是entry。

MOVZ #0/#1只有immediate位不同、目的集合相同，但fsqrt/N128 rename/cycle从约.871降到0，周期都约416；N704 MOV0仍约487cycles，NOP约430、MOVI约555。依赖与值域控制明确反驳“指令数量一个单位标尺足以通用于所有流”和“rename近零就没有任何资源限制”。事件名称只提供观察约束，不直接定位PRF/RS/ROB是哪一个先满。

跨进程同值ADD依赖批48进程/144窗技术接受，四DID>5但NONE负控波动使主门not-qualified，已完整封存。新同进程/同代码VA的15进程/480窗结果在 `docs/reviews/2026-10-11-rob-same-address-pair-results.md`，**技术通过、主门not-qualified**：15/15 N0哨兵、80/80 D>5，但NONE T中位−8.072620、范围38.219238超过冻结门；同VA不能自动保证局部供给稳定。不能用后者替换或删除前者失败。新判据T/D、N0哨兵与NONE门先冻，全部signed/raw/绝对波动保留。

长load路线并非完全没做：4K长随机链翻译walk较高；实际full THP降低walk但远层miss代理未满足原门；更大THP有initial backing技术失败并保留缺失/分型；高/低XOR编码有限路线也未过原资格。单冷/双冷同码形小探针的冷激励可过，串行理想相加模型仍被四状态反例推翻。详见 `docs/reviews/2026-10-09-long-load-4k-qualification.md`、`docs/reviews/2026-10-09-long-load-thp-results.md`、`docs/reviews/2026-10-09-long-load-fixed-results.md`、`docs/reviews/2026-10-09-encoded-load-results.md`、`docs/reviews/2026-10-09-canonical-load-results.md`、`docs/reviews/2026-10-10-cold-load-model-results.md`、`docs/reviews/2026-10-10-cold-state-results.md`（均在 `docs/reviews/`）。这些资格门是工程定义，不是一般CPU定理；失败不证明所有memory-based方法必然不可行，但不容许本数据被投入原ROB容量公式。

### 为什么更多同曲线点数不能补上条目标尺

在一个用来说明歧义的简化模型中，可观察指令窗口可能受 `min(R/α_i, P/β_i, S/γ_i, supply×anchor-time, …)` 限制。R是ROB物理单位，α_i是该filler流的分配/packing单位关系；其余项是寄存器、队列、供给及执行生命周期约束。这不是拟合本机的最终模型，只用于暴露未知量。

若只测W_i而α_i未知，R与α_i同时按比例缩放就保留R/α_i；其它资源先限制也可产生同一W_i。退休指令数、执行/退休operation tap、rename stall不直接测α_i，也没有独立证明ROB那一项是min的活跃约束。NOP/MOV融合、zero/rename消除及早释放影响单位/寿命；“13cycles fsqrt”标定的是锚点响应，不是ROB单位。因此本批即使配对差分稳定，也不能直接导出R。

**物理ROB终态：MODEL_UNIDENTIFIABLE，entries=None。** 这是相对于本批已观测量与允许替代模型的判断；不会泛化成物理ROB永不可识别。384仅来自第三方Cardyak框图，不是Arm官方值、拟合中心或实测答案。当前能交付的是可复现的有效窗口与资源响应，而非384/768/某个整数容量。

## 吸收的参考与软件结构

[travisdowns/robsize](https://github.com/travisdowns/robsize)提供值得吸收的类别对照、生成码导出与golden回归思路；当前实现采用独立A64编码、实际decode、同窗PMU和匹配原型，不复用x86补偿/字节公式或硬件假设。`../cpu-uarch-ref/cpu微架构材料/src/pattern.c` 的ROBSize_NOP_Build给fsqrt依赖锚点+可控filler思路；本项目额外固定operand/实际对齐、双gap/chain、no-anchor和资源/值域对照。BTBSize_Probe_H2实际是注册BTBSize_Build；后者生成B+3NOP，能作为可控branch-footprint骨架，不能作为ROB真值或BTB容量已测。I-cache/iTLB/分支吞吐与布局对照需独立BTB项目，不在本批偷渡完成。

代码结构维持小独立探针：TLB布局/header与计量分开、consumer复验真实plan/geometry；ROB公共pure生成器 `probes/common/rob_codegen.h` 被旧 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c` 与新 `probes/diagnostic/rob_dependency_pair.c` 共用，避免两套opcode漂移。`probes/common/perf_group_read.h`复用GROUP+ID的纯解码；不能说旧PerfWindow保存了未输出的kernel IDs。正式runner/schema/CMake接入仍待稳定正式合同需要，当前JSONL不是schema-v2 run record。

所有探针遵循source/binary-source、consumer/build、actual launch、protocol、plan、raw SHA分列。新软件测试用实际producer→driver→writer→loader，外部PMU模拟与本机/手机证据分列。macOS CTest不是Linux VMA/PMU执行证明。

## 收口与触发下一轮的条件

本轮停止同一曲线无限加密、重复增足迹、改mask或放宽阈值；有限对照和阴性结果均已交付，不要求外部Agent反复“清零”才承认事实。物理容量/open机制不是隐含完成项，也不靠永续m0b兜底。

下一轮应先形成能观测/校准α或排除活跃替代约束的方案，再采数；例如经资格确认的资源生命周期/packing干预，或可直接约束分配单位的公开实现资料/目标事件。ALU/FPU完整operand与依赖/独立链latency/throughput是后续独立部件项目；本轮sqrt(1)锚点不是FPU全探测。TLB机制ATTRIBUTED需新增PFN/PTE/可观测聚合或投机tap的正交控制。窗内clock、专门事件正控、formal schema接入等owner与触发均在 `docs/open-items.md`。

r2不是main：m0b已完成软件集成使命，r2承担本批探测；main集成/回归/推送完成后才满足分支删除条件。远端按本轮指令暂不处理；旧六run目录和他人.gitignore改动原位保留，没有代提交、清理或回收。原A1/frozen/14条L1不拼接，失败目录不删。本有限科学任务终态不授权自行把后续未知量重新包装成已测参数。


## 本轮交付路径与commit索引

全部位于branch `codex/sm8650-tlb-hierarchy-r2` / worktree `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`，无push。旧报告保留其真实source/launch，不绑定当前HEAD来制造重构历史。

| 交付 | 代码/报告路径 | source / consumer-build / actual launch / result commit |
|---|---|---|
| TLB 地址族转折 | `probes/diagnostic/tlb_local_turn.cpp`、`tools/diagnostic/tlb_turn_analysis.py`、`docs/reviews/2026-10-11-tlb-local-turn-results.md` | ac38cd3 / fd0685c / 4aa3fe2 / 890206f |
| TLB walk并行两scope | `probes/diagnostic/tlb_walk_parallel.cpp`、`tools/diagnostic/tlb_walk_parallel_analysis.py`、`tools/diagnostic/run_sm8650_parallel.py`、`docs/reviews/2026-10-11-tlb-walk-parallel-results.md` | 0bda583 / 757bb46 / 38eb983 / dd2d773 |
| TLB page-set/offset/order | `probes/diagnostic/tlb_page_distribution.cpp`、`tools/diagnostic/tlb_distribution_analysis.py`、`tools/diagnostic/run_sm8650_distribution.py`、`docs/reviews/2026-10-11-tlb-page-distribution-results.md` | 57f96a9 / b6143a8 / f14f3de / 0917f64 |
| ROB同VA配对与公共生成器 | `probes/diagnostic/rob_dependency_pair.c`、`probes/common/rob_codegen.h`、`tools/diagnostic/rob_pair_analysis.py`、`tools/diagnostic/run_sm8650_rob_pair.py`、`docs/reviews/2026-10-11-rob-same-address-pair-results.md` | 4cebc24 / 11abe30 / 4f44c98 / 494a981 |

fresh整树软件出口：diagnostic298/298、runner203/203、formal analysis250/250、macOS CTest21/21；双NDK与目标执行逐批单独验证，不将native覆盖冒充Linux PMU。各批所有匿名count、完整schema-independent summary、实际code/plan、raw SHA和图在各自 `docs/reviews/evidence/2026-10-11-*/`。有限技术出口通过，物理容量命名出口不通过，两者不是同一个验收标准。

## 本次继续推进的新增证据

`docs/reviews/2026-10-11-rob-resident-control-results.md`（sourcefe53c23/launchb27d95b）240窗技术接受，但未额外本窗重写的NONE仍44–72cycles波动，原字节维护效应未复制；不唯一归因频率/Icache。`docs/reviews/2026-10-11-tlb-cross-region-results.md`（source7ed6434/launchf8edac7）34560窗主候选辨识通过，1440激励门全过、一个W8多walk比较INCOMPUTABLE完整保留。317诊断与本轮未改runner203/analysis250/CTest21通过。上述新增正交结果不改变物理ROB未测得的边界，但补充Q-C可使用的候选证据；下一ROB先校验双FSQRT独立性模型。

## 双独立锚点的新实证边界

`docs/reviews/2026-10-11-rob-dual-anchor-v2-results.md`，source0d5ac03 / v2consumer-buildf685c8a / actual launch91e0cb7，新增fresh144资格与720扫描全部技术接受。原两FSQRT链同D0为串行，新D0/D1确有208/416重叠；NOP同N供给稳定，90进程各8窗稳定。N384开始约8%渐进增加，N512约21%处模糊带，N640以上响应、N704近串行，N896供给/控制门未过；单区间INCONCLUSIVE，物理entries仍None。旧v1的144窗not-qualified完整保留，未因修门晋升。343诊断通过。

官方r0p1优化指南§4.11明确NOP+任意相邻指令fusion资格、MOP可分µOP；0x3a/0x3b是µOP计数，不直接标定ROB分配。`docs/reviews/2026-10-11-rob-fusion-unit-audit.md` 给下一匹配ADD/NOP+ADD/双NOP组的正交控制与单位校准边界；当前不以N/2迎合384，不复跑旧曲线追锐knee。旧MODEL_UNIDENTIFIABLE只限定当时模型族，新可用的重叠/流量证据独立保存。


## 2026-10-12 均衡几何与匹配组新证据

`docs/reviews/2026-10-12-tlb-balanced-reach-results.md`（sourcefee3fbe / build-consumer7fb7bb0 / launch82871d1 / result698cf30）825真机窗与810技术门全过；控制实际VPN低8位/offset分布后，spaced与random相对dense仍有跨五mapping/双order复制的walk差。GEOMETRY_SENSITIVE是对简单页数/低位reach解释的新反证，三族各十曲线均heterogeneous，含右删失与ambiguous，不据均值给精确容量。官方r0p3 MMUTC还服务I/D/intermediate descriptor，不能预设2048纯4KiB leaf；下一物理PFN能力与descriptor VA代理控制须另冻，不回填历史UNKNOWN。

`docs/reviews/2026-10-12-rob-fusion-groups-results.md`（source9a09fa2 / build-consumerb5e260f / launch04f3980 / result82871d1）144窗技术接受、锚点约208/416，但ADD NONE64三进程21–35.5cycles/轮波动，另1Icache窗134/131072越门。本批not-qualified，扫描未启动；NOP+ADD/双NOP更稳不能证明fusion/MOP allocation。架构目的/结果生命周期及活跃约束仍需新对照，不以NOP/2迎合384。全部raw/SHA、失败窗及直接第二算术保存，新整树diagnostic368/368通过；未改formal路径沿既有基线。


## 同PFN的新因果边界（2026-10-12）

`docs/reviews/2026-10-12-tlb-shared-alias-results.md`（sourcea32ee8d/buildd74851d/consumer855350b/launchf5ae99a/result392d097）三fresh memfd279真机窗与270门全过，330240次原始pagemap位及PFN身份独立核验一致。同physical demand页/offset/order与候选低8位hist下，七个N×族差均六配对≥.10，GEOMETRY_SENSITIVE_WITH_MATCHED_DATA_PFNS。data PFN不同不是本协议几何效应必要条件；旧anonymous未观测PFN不能据此回填。descriptor物理布局/层级索引、pointer值引起的投机或DMP/cache流量、CONT/HPA仍没有唯一分开；16页连续条件0/160是非预注册诊断，不能冒充CONT位。此结果比单VA曲线更有区分力，但不提供physical entries证书。下一先ROB架构目的控制，再选择TLBpointer/descriptor可识别干预；386/386全diagnostic通过。


## 架构目的控制与相对单位下一门（2026-10-12）

`docs/reviews/2026-10-12-rob-destination-control-results.md`（sourcef85e2bb/build083c386/launchf640160/resultb93a392）192真机窗技术与参考资格过，XZR并未消除裸ADD波动，NOP+ADD两目的均稳定；主INCONCLUSIVE而非PRF/前端唯一归因。下一 `docs/design/2026-10-12-rob-retirement-units.md` 明示相对α只是被检验假设，比较同bytes无架构结果的三pattern及chain16/32；先192窗资格，过后2352窗有限扫描。新source df2171d / build47ff455，144独立反汇编/288实际计划、两NDK构建一致，7算法/码形及9生产链软件测试通过；本段登记时尚未上板。即使共同proxy区间存在，也不能把它直接改名物理ROB entries；仍须独立认证实际分配单位和活跃约束。
