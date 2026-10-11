# ROB 原字节代码维护对照（冻结 v1）

## 本次任务的目的（给人类看）

前批 `docs/reviews/2026-10-11-rob-same-address-pair-results.md` 中，同VA的 NONE ADD N128 仍波动，不能以稳定 N0 哨兵或正差分认证稳定供给。本批只问：固定同一程序/VA/输入后，暖身前额外执行原字节重写与缓存同步，是否改变测量；同时保存未重写重复窗的完整轨迹。它不测物理 ROB 项数，也不修改前批未合格裁定。

备选方法：再扫 N 会重复未辨识曲线；同时换多个驻留 VA 会混入取指位置；选择单进程单程序单 VA 的原字节维护对照。新增 `probes/diagnostic/rob_resident_control.c`，直接复用 `probes/common/rob_codegen.h`，不修改 legacy 或旧配对协议。

## 预注册有限协议

每进程只生成/执行一个固定程序。条件为 NONE independent N0、NONE independent/dependent N128、FSQRT16 independent/dependent N128；输入/桥接/目的寄存器完全沿用旧生成体。初次安装代码 generation=1，每窗都验证实码并暖身131072 iterations，再测131072 iterations。resident不做额外RW/RX/cache维护；reinstall执行RW→相同words拷贝→memcmp→clear-cache→RX，generation加1。所有准备/暖身在PMU窗外，测量时RX固定。

8个block×2窗；偶block resident,reinstall，奇block reinstall,resident；奇epoch把整16窗反序。3 fresh epochs×5条件=15进程/240窗，奇epoch进程条件反序。CPU7、FPCR0、loop mod64=0、PMUtype8、GROUP+ID/pinned/exclude kernel,hv，事件[0x11,0x08,0x3a,0x3b,0x816d,0x23]，不mux/noRESET；进程间15s，环境只读baseline。保留每窗原计数/ns/代码VA/IDs/generation，不删异常科学结果。

resident可能跟在reinstall后，故本实验只识别“本窗暖身前是否额外维护”的效应，不证明从未维护代码的整个生命周期，也不等价于前批跨variant切换。相同程序也同时移除了variant切换；若两类窗均稳定，不能唯一归因旧波动。

## 消费与命名规则（在设备采样前冻结）

`tools/diagnostic/rob_resident_analysis.py` 验真实producer计划、完整15条件/240窗、精确代码words/顺序/generation、uint64 timing/count、唯一kernel IDs、单进程同VA、IR预期误差≤max(1000,1%)，源/build/launch/所有rawSHA与环境闭合。失败停块，禁止补窗。

C=CPU_CYCLES/131072，r=cycles/ns仅为观测比，不能命名瞬时频率。每block带符号Δ=C(reinstall)-C(resident)，保留所有24个Δ/条件，所有R/X绝对C与事件比。

主条件 NONE independent N128：
- 每种preparation分别计算3个进程各8窗的(max-min)/median；三进程全部≤0.10才称within-process-stable，明确不认证跨进程稳定。
- 若全部24配对Δ>2且Δ/C(resident)>0.05，命名maintenance-associated-increase；若全部Δ<-2且-Δ/C(resident)>0.05，命名maintenance-associated-decrease；其余effect-not-replicated。
- resident稳定、reinstall不稳定，只称maintenance-condition-associated-instability。两者都不稳定=resident-supply-still-variable；两者都稳定=both-conditions-stable-in-this-protocol。不能由某一命名直接认证ROB/PRF/scheduler或唯一根因。
- N0、NONE dependent、FSQRT两条件为控制/范围，不冒称独立频率计。事件比>1按event语义保留；不把rename比例当allocation标尺。

## 执行计划与验收

工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`，branch `codex/sm8650-tlb-hierarchy-r2`；user授权root串行端到端，不启动其他设备Agent，main/远程暂不动。

- [ ] 新 `tools/diagnostic/tests/test_rob_resident.py` 先检查真实C producer存在（RED），native clang编译后逐字比独立legacy byte oracle，五条件×顺逆序的全部计划和generation验证（GREEN）。
- [ ] 分析器测试仅用实际C计划，外部PMU合成标明mock级；缺窗/重复/乱序/错误程序/generation/IDs/mux/IR/类型/阈值边界均拒绝或命名，首坏驱动停机。
- [ ] 两次NDK API34 -O2 -Wall -Wextra -Werror -static构建同SHA；完整实际words独立反汇编。源commit、consumer/build commit与launch commit分开登记到 `docs/reviews/evidence/2026-10-11-rob-resident-control/`。
- [ ] `tools/diagnostic/run_sm8650_rob_resident.py` 实际producer→raw writer→consumer接线回归后再采有限15进程；设备不可达时保留软件交付并登记阻塞，不编造设备结果。
- [ ] 完整raw审计、独立第二算术、结果报告与目标台账更新，必要时追加下一项可推翻解释的控制；不改变旧冻结门。公开仅匿名派生证据，raw/private永不入库。
