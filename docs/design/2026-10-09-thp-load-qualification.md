# ROB 长load的大页反证（冻结v1）

## 本次任务的目的（给人类看）

在用户授权的连续端到端探测中，检验4K长随机load的翻译混杂能否被实际2MiB backing显著削弱。4K资格失败还包含L2/LL代理率及一次配对差失败，不能预设换大页便合格。本轮不是ROB容量扫描，也不将0x37命名为DRAM。当前Agent独占设备，不改内核THP策略/频率/热服务；与TLB串行。

## 固定实验与验收

分支`codex/sm8650-tlb-hierarchy-r2`；探针源码`ec1d284`：`docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`、`probes/common/rob_backing.h`。驱动`tools/diagnostic/run_sm8650_minimal.py` mode=`rob-miss-qualify-thp`。epoch0 footprint={1,64,128}MiB、epoch1反序，6进程、3轮同VA P/S、36窗。每进程前固定15秒冷却；所有成员用同一新binary。1MiB热对照显式`--backing 4k`，64/128显式`--backing thp2m`；其余N0/NOP/seed42/CPU7/type8/完整足迹及事件与`docs/design/2026-10-09-long-load-qualification.md`相同。

只读读取THP enabled/defrag/hpage_pmd_size与MemAvailable。长点申请2MiB对齐匿名映射，fault之前MADV_HUGEPAGE，必须实际hpage_pmd_size=2097152；精确单VMA AnonHugePages=Rss=请求bytes、Swap=0，无nh。在initial以及每窗warmup后/enable前和disable后核验。KernelPageSize/MMUPageSize可为4k，不能用它们单独否认THP；也不能把advice成功当成实际覆盖。任何部分覆盖/分裂/读取失败立即停块，空metrics结构化failure，禁止fallback或边跑边改全局策略。来源：[Linux proc文档](https://docs.kernel.org/filesystems/proc.html)、[Linux6.1 THP文档](https://www.kernel.org/doc/html/v6.1/admin-guide/mm/transhuge.html)。

新代码窗前读smaps可影响cache/TLB状态，所有新binary成员流程相同；本批独立判断，不能与旧4K绝对cycles直接配对。端点检查不能证明窗内从未发生短暂拆页；PMU walk同时作为干扰方向证据。

## 原资格门原样保留

沿`c93e788`冻结门，由`tools/diagnostic/analyze_long_load.py`复算：P、S每轮L1/L2/LL率均1.8–2.2/iter，walk≤0.02；各member cycles range/median≤10%；各轮S/P均1.6–2.4；P/S L2、LL均值差/两者均值≤10%；P中位cycles≥max(同epoch热P×4,171)；热P/S每轮LL≤0.1。64/128分别在两epoch独立通过才有资格；不改门救结论。无合格点则不进入N扫描，保留miss代理/翻译/配对各项失败原因，再选择替代长锚点或诚实限定可辨识量。

请求/自描述、生成码、实际backing、PMU组、环境、完整矩阵与source/build/driver/protocol逐项绑定。NDK27.2/API34静态Werror交叉编译；注册`docs/reviews/evidence/2026-10-09-long-load-thp/build.json`后采数。原始输出及VA只入`data/private/`；公开脱敏全部轮计数/分析，失败不删除、不升baseline。下一步若合格，按旧协议有限N={0,128,256,384,512}双锚点扫描，先检验模型再细扫；若失败，未竟事项进`docs/open-items.md`。
