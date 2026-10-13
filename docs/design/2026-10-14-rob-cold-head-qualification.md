# 冷load头部阻塞资格 v1.0

## 本次任务的目的（给人类看）

FP依赖链允许早期指令逐步退休，不能直接从gap+chain推导ROB。独立替换为一条最老的自有cold LDR（或两条串行cold LDR），直到地址值返回才可解析CBNZ，期间不能越过该head退休。保持已合格的近8load/远8store标记，先只N0核验延迟、结构阴性、正控和供给，再批准gap扫描。用户要求第一性原理、持续独占设备；软件可与其他采样准备串行推进，不并发上板。

方法参照 https://github.com/travisdowns/robsize 的cache-miss-separated filler与PRF对照。仅借方法，x86 NOP/µop/容量不迁为Arm事实。旧 `probes/diagnostic/rob_cold_pair.c` 的DC自有line可执行及cold positive是路线依据，旧串并理想模型资格失败不回救。

producer probes/diagnostic/rob_cold_head.c；consumer tools/diagnostic/rob_cold_head_analysis.py；controller tools/diagnostic/run_sm8650_rob_cold_head.py；将复用当前register ROI/current binding和 `tools/diagnostic/owned_roi_packets.py`；所有readonly/private/source-build-launch-raw边界不变。

## 冻结最小矩阵与预测

- 2fresh epoch × heads{1,2} × palette{issue,cache} × state{hot,cold}=16进程，每32trial×8标记角色=256固定attempt；总4096attempt。epoch1配置逆序。每packet64无PMU warm-image训练、最终RX后4 current-binding热调用、正式调用1，包络外read/getcpu，进程间15秒；metadata预算同有限packet合同，仅1/256，无重试/补样。
- head1的LDR从x4指向私有页A加载0/1；head2先LDR x12,[x4]得到私有页B地址，再LDR x12,[x12]得0/1；CBNZ x12判定。训练0，architect正式0，speculate正式1。页A/B分别4KiB映射，近/远页独立；runtime/尾部visible LinuxPFN稳定及内容链审计。无FP操作；8store常量由MOVZ/MOVK生成。原pre/post SB交换、最终SB与架构输出保持。
- 正式前先写0/1并touch所有数据，cold只DC CIVAC指定head line（heads2清A/B）+DSB；所有操作在direct捕获前，最后热调用后不进内核。先SIGILL保护验证自有DC完成，不宣称无trap/DRAM；触发能力失败命名拒绝。hot做共同写/touch/DSB不做DC。4warm总用head0并始终hot，正式可见head值和链必须真实实现。
- issue事件[17,8,112,113,34,1]；cache事件[17,8,112,113,3,23]。两profile分别独立6FD/current dynamic indices，cache palette不冒称I-cache qualification；issue palette才审计原refill median≤1/q95≤4。
- N0近/远Apre/Apost约8、Mpre约0、分离≥4、IR同构、near eligible≥8/32且conditional far≥.9，原门不改。所有输出保留完整counts与trial。hot可因deadline不足而不资格，**不拿hot failure当cold容量**。
- cold−hot的architect pre/post taps及nop配对周期差单列；heads1每profile/epoch这四差分中位都≥64cycles，heads2≥96cycles，命名LONG_HEAD_EXCITED，否则SHORT_HEAD_NOT_QUALIFIED；不根据384调延迟阈值。cache profile每cell cold−hot的L1D/L2D_REFILL均值分别在[.75*heads,1.25*heads]；不是每次必须精确相同，不据此命名DRAM层。issue profile cold全部8个N0资格通过、source/no-FP/owned-backings/实际链/有限loss均合格，才COLD_HEAD_MARKER_QUALIFIED。

heads2的总cold周期大于heads1仅描述延迟多剂量，未得到的时间不补零；同时使用一个较长的blocked oldest instruction与两条串行head可比较window是否由deadline限制。之后gap/PRF/fusion/rename/供给的容量对照另冻，不能以N0结果宣称ROB。

## 实施与停止线

先实际native words/branch/counter上下文配方测试RED；实现后独立解码每条head load依赖和CBNZ目标/ABI、NDK双构建；源码与构建分别提交。核对设备独占及双journal基线后执行16配置，首非metadata硬错停；完整raw/private与签名SHAs再复核。此文仅预注册N0，不授权无资格的容量拟合。
