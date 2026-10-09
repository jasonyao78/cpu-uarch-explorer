# ROB long-load锚点资格（冻结v1）

## 本次任务的目的（给人类看）

在用户已授权持续端到端推进的范围内，先检验能否获得两个独立长延迟load的可解释锚点，再决定是否扫描ROB窗口。此前16MiB多数访问未形成稳定远层miss；fsqrt链逐条退休，也不等价于一个持续13k周期的单门闩。当前Agent独占手机，实验与TLB串行；`codex/sm8650-tlb-hierarchy-r2`，起点`245d4e0`。本协议先提交后测。

## 有限资格矩阵

`tools/diagnostic/run_sm8650_minimal.py` 新mode `rob-miss-qualify`：N=0/NOP/同VA paired独立-串行，各3轮，epoch0 m={1,64,128}MiB、epoch1反序。共6进程/36窗；每进程前固定冷却15秒再检查环境。全部用旧已验证源码`217e5e3`的静态Android binary，不改JIT。

每call重新从heads开始，**不是跨round继续走环**。因此i={131072,524288,1048576}，保证`2i >= memory_bytes/64`、每call覆盖全部line；runtime distinct_lines_per_call必须=ring_nodes。1MiB为L2/hot方向对照，不作为长延迟资格点。相同allocation的P/S访问相同VA顺序，但不预设cache层级相同。

PMU type8、CPU7、exclude kernel/hv；cycles0x11、INST_RETIRED0x08、L1Drefill0x03、L2Drefill0x17、LL_CACHE_MISS_RD0x37、DTLB_WALK0x34，全组必须有效且无mux。0x37是远层读miss代理（可能包含remote/inter-cluster），不独证DRAM；新事件的方向资格需和1MiB对照及0x17相干一起看，开得出来不等于语义已完全认证。

## 采数前资格门与后续分支

软件接收与科学资格分开。技术失败按已有驱动立即停止保留，不换配置补救；技术通过而科学资格失败也完整发布。

长负载每member/epoch须同时满足：L1Drefill、L2Drefill与LL读miss代理均在1.8–2.2/iter，datawalk≤0.02/iter；各member三轮cycles范围/中位≤10%；三轮P/S配对比都在1.6–2.4，P/S两种miss代理均值差相对两者均值≤10%。每epoch独立双链中位cycles还须≥max(同epoch1MiB独立中位×4,171cycles)，而1MiB的LL读miss代理须≤0.1/iter。171参照前批N768 none约170.9，为后续填充留下余量。64/128MiB分别判，不跨footprint/epoch平均救门。阈值是保守工程资格，不是硬件参数/显著性检验；合格也只称“低翻译干扰、远层miss主导的双长load候选”，不能自动称DRAM或物理ROB。

- 满足门：用合格最小footprint做有限N0/128/256/384/512 paired试验，先看响应是否符合两锚点模型，再细扫，不以384作预定答案。
- miss代理充分、但datawalk超门：不扫N，下一轮实现显式THP2MiB对照，读实际hpage_pmd_size、精确VMA的AnonHugePages完整覆盖，并在测前/后验证；MADV请求成功不算实际backing证据。THP失败保留命名不可用，不关闭内核热保护。
- miss不足/串并关系或稳定性失败：分别登记原因；先排查命中层级、实际足迹、访问/预测/相位，之后才选择其它single-latch方法，不用旧fsqrt曲线除2救容量。

私有完整stdout/stderr/environment/exported bytes及manifest；公开匿名派生表另立evidence目录。来源绑定沿 `docs/reviews/evidence/2026-10-09-minimal-probes/build.json`，source HEAD与launch HEAD分开。软件测试只验证覆盖、请求-memory自描述及计数合同，不能冒充设备资格。
