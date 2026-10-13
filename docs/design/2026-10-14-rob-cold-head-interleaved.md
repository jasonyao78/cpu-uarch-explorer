# 同映射冷热交错与head offset控制 v2.0

## 本次任务的目的（给人类看）

v1整批不通过，但cold issue marker/供给、230..500cycle long-delay均通过；cache/nop的head剂量成立而若干cache/taps L1D差偏离。下一独立实验把hot/cold放在同一个进程、同一VA/PFN/counter context里交错，排除fresh process布局变化；将head移到页offset1024，和offset0对照，检验head与near/out/metadata都集中offset0的缓存交互。旧v1原样不改，不把L2正响应直接说成整个缓存模型已过。

producer probes/diagnostic/rob_cold_head_interleaved.c；consumer tools/diagnostic/rob_cold_head_interleaved_analysis.py；controller tools/diagnostic/run_sm8650_rob_cold_head_interleaved.py；共享current-binding/FD包络和 `tools/diagnostic/owned_roi_packets.py`。实际基线 `probes/diagnostic/rob_cold_head.c`、反例 `docs/reviews/2026-10-14-rob-cold-head-results.md`。

## 冻结矩阵与生产链

2fresh epoch × heads{1,2} × palette{issue,cache} × head_offset{0,1024}=16process。每process32trial×state{hot,cold}×8role=512固定attempt，共8192formal/32768warm。两个状态共享同一mapping/physicalPFN/JIT VA/branchPC/own FD context；每trial16格轮转，8trial分块反序，epoch1参数逆序。每packet warm64无PMU+最终RX后4独立own warm+1正式，FD read/getcpu/打印/写code都在热链外。每process最多1个明确ROI-metadata-changed packet；所有512ordinal必须account，无retry/补样/结果挑点，其它错误仍停。

head_a_map/head_b_map为4KiB页，真实load地址=map_base+head_offset；实际x4参数必须用该地址，heads2的A内容必须指向B的真实偏移地址。runtime报requested offset、map bases、load addresses、initial链、visible LinuxPFN，round报实际head contents与0/1返回；尾部backing不迁移。munmap必须用map_base，不对偏移地址munmap。模型/实际native/NDK/解码逐层核验此requested→realized出口。raw/PFN/VA/serial仅private。

hot/cold state显式写在每个schedule、warm、formal、invalid/rejected packet。资源/统计分组键必须包含state；不能因其余键相同覆盖两状态。同trial同role冷热成对，共同有效trial至少31/32；warm固定hot0，不因正式cold改训练。16配置只改变head offset/状态调度，JIT head LD依赖/marker/ABI/counter采样ISA不变。

## 主判据、对照与停止线

offset1024在采样前指定为主配置，offset0用于反证缓存交互；理由是metadata/near/out主要使用0..448偏移，1024隔离低页内index位，**不是宣称已知道machine HPA或唯一cache hash**。两offset全部结果保留；0失败不回填为1024成功，也不因此不报告0。

主配置offset1024两个epoch/heads/profile：原A正控/结构阴性/IR/near eligible≥8/far|near≥.9/strict issue I-cache供给门必须通过；cache palette冷热mean ΔL1D/ΔL2D各在[.75*heads,1.25*heads]；每architect role周期差中位heads1≥64/heads2≥96。全部同时通过才INTERLEAVED_COLD_HEAD_PRIMARY_QUALIFIED。原百分位/分离/有限metadata阈值不改。0配置的同样门与差分全列；若0与1024都差则冲突解释未被支持，保留UNKNOWN并检验其他来源，不能再按结果改offset。

新同PFN/counter的冷热差取代跨process可比性假设；它仍不证明DRAM层或µop/ROB allocation。资格成功后另冻gap精扫，保持cold-head最老阻塞、two-head deadline剂量、NOP/zero/sink/PRF/取指反证与actual raw far计数，不用384拟合。

实施先实际native的state512身份与指针出口RED测试，generalize packet parser只接受注册256/512并保留旧256合同；duplicate/conflict/missing/order与state覆盖反例。源码→NDK双构建→build/plan→设备独占/双journal基线→新16配置→独立复核。用户已授权端到端持续推进，无常规人工审批节点；目标容量仍未宣称完成。
