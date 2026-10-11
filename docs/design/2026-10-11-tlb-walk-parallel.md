# TLB K 链有效在飞占用（冻结 v1）

## 本次任务的目的（给人类看）

完成原任务书 Q-D 的有限必做对照：显式 K 独立指针链能否提高该负载的翻译在飞占用，还是同一内核首先受到数据供给限制。结果只认证有效响应，不认证硬件 walker/MSHR/load queue 深度。用户授权 root 在 r2 串行独占设备继续设计、实现、验证与本地提交。

## 冻结条件与反证

`probes/diagnostic/tlb_walk_parallel.cpp` / `probes/diagnostic/tlb_walk_parallel_layout.h` 实现 K={1,2,4,8}。两个 scope：total 固定8192节点；per-chain 每链8192节点（总8192K）。每节点恰占一个64B cache line。high 一节点/4K页，VA页索引17i，页内offset=64(i mod64)，稀疏未触碰页阻止把连续虚拟地址等同连续翻译；low 64节点/4K页、line offset轮转相同。低walk负控的数据line数/访问次数/链拓扑与high相同，物理页/PTE/cache set仍不同，缓存压力必须由实测0x03/0x17报告，不能声称完全隔离数据侧。

每个条件独立 guarded 匿名 mapping，MADV_NOHUGEPAGE + before/after smaps AnonHugePages=0；mapping span与实际触碰页/line footprint分别输出。high最大VA span约4.25GiB、实际触碰65536页/256MiB、有效line4MiB；不扫描未触碰保留空间。每链固定无重复闭环。seed137的xorshift64（13,7,17）Fisher-Yates全局置换后均分K链，C++/Python独立复现，每个完整索引链保存供审计。

每cell warmup总2^20 loads；正式总loads={2^18,2^20}，每链迭代loads/K，恰为链长度整数倍。每窗三round全保留，不择点。K核内每迭代K条LDR自依赖 + SUBS + B.NE；无数组循环/stack spill/额外内存。输出结束heads必须回到起点。空窗三round无内核。一个mapping进程32非空cell+1空cell=99窗，5 fresh进程=495窗，奇epoch整序反转，间隔15s。空cell也随整序移动。全部有限预算，不以重复直到通过救门。

六事件同窗GROUP+ID：type8 [0x11 cycles,0x08 INST_RETIRED,0x03 L1D_CACHE_REFILL,0x17 L2D_CACHE_REFILL,0x34 DTLB_WALK,0x8128 DTLB_WALK_PERCYC]，exclude_kernel/hv、pinned，PERF_EVENT_IOC_ID逐成员保存并用 `probes/common/perf_group_read.h` 拒绝重复/未知/缺失。无RESET，enabled==running、计数不回退。CPU7/MIDR0x410fd821/4K与现有quiet-state读门，环境不写频率/热策略。继承事件长链资格不等于K链自动合格。

## 消费规则（先冻结后上板）

`tools/diagnostic/tlb_walk_parallel_analysis.py` 验完整请求/实现/序列/索引/PMU IDs/backing/窗口/源二进制谱系。每观测 C=cycles,M=walk,A=walk-cycle积分，给出A/C、M/C、A/M（M=0为None+walk-inactive）、loads/C。汇总是Σ计数比，禁止median(A)/median(C)。不预设A/C≤1；驻留量是事件定义下的有效平均而非每个walker的物理时延。

技术IR门：[.95,1.05]*(loads+2loads/K)，允许固定函数/读包装开销；空窗不套此门。作用域资格：每个长窗high M/loads≥0.1且A>0，low M/loads≤0.001；0x8128/0x34随high/low方向共变：每个high长窗A必须大于同epoch/scope/K/loads的low三窗中位A，二者load数相同。空窗中位C、A、M分别必须≤每个非空窗对应值的1%才能声明其事件背景可忽略；分母为0时要求背景0。分别命名每个背景门，不因为A/C或M/C失败丢数据。短/长统计并列，给背景相减值（负值保留）；命名合格以长窗high/low及背景门为依据，任一不满足输出not-qualified，不追改阈值。不设置拟合平台或硬件容量门。

技术全合格也不保证缓存压力匹配。每K报告每load L1D/L2D refill、low loads/C与high loads/C；若两者同样受限，不能独归因walker。翻译占用可以支持有效并发有增长，平台只能称有限K范围的负载响应。

## 一手依据与实现计划

事件定义：`/Users/michaelyao/workspace/cpu-uarch-ref/docs/Arm_Cortex_X4_Core_TRM_102484_0003_06_en.pdf` §12 PMU事件0x8128计数每周期在进展的walk个数；[Arm Cortex-X4 PMU JSON](https://raw.githubusercontent.com/ARM-software/data/master/pmu/cortex-x4.json)。原问题与比值规则：`docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md` §1.2 Q-D/§G0。保留对事件作用域的资格检查，不移植Intel语义。

1. `tools/diagnostic/tests/test_tlb_parallel_producer.py` RED：真实host producer冻结32cell+floor；真实chain traversal/闭环/无重叠/footprint，非法参数拒绝。
2. 实现两probe文件与局部GROUP/ID adapter；native测试GREEN；双NDK构建、独立Capstone四核解码，检查register依赖/loop边界/IR。
3. consumer及`tools/diagnostic/run_sm8650_parallel.py`：真实producer输出→driver写盘→raw重读；成功、首坏STOP、缺失/重复/冲突/重哈希/乱序负例。模拟仅外部PMU/adb，不代表手机。
4. 完整软件回归、冻结source/build/launch各commit→独占检查后5进程手机有限块；私有raw原样保留。独立第二套算术逐窗重算495窗及门；完整报告/图/匿名证据/目标对账更新，小步本地提交。

工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`；分支 `codex/sm8650-tlb-hierarchy-r2`。protocol冻结不含未来commit循环引用，build与launch分别在登记/结果中追踪。旧formal runner/schema不改；独立JSONL依旧是诊断协议，不冒称schema v2。
