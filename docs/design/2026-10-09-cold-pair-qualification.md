# ROB single-shot冷line资格与实施计划（冻结v1）

## 本次任务的目的（给人类看）

循环长load路线已经以不合格结束，见 `docs/reviews/2026-10-09-canonical-load-results.md`。不再改mask/升足迹追旧门；现在直接制造两次同VA冷load，检验冷延迟、串并依赖和计时是否可辨识。比较三条路：继续大足迹仍受实际THP/命中层级限制；fsqrt链逐条退休，不能当单个长门闩；**选小型single-shot双line**，其代价是cache维护/屏障/时间戳资格必须先实测。本阶段只N0，不许未合格先扫N。用户持续授权，根Agent独占手机，软件可复核，设备采样串行；分支 `codex/sm8650-tlb-hierarchy-r2`，设计起点7c8cf44。

## 几何、依赖和计时

新producer `probes/diagnostic/rob_cold_pair.c`，不修改旧 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`。自有8KiB数据VMA、8KiB对齐、两侧PROT_NONE guard、MADV_NOHUGEPAGE，恰好两个4KiB页，初始/最终 `probes/common/rob_backing.h` 精确验收。A/B节点页偏移0/4096，互换head顺序swap0/1；均为不同64B行。不输出VA/PFN。

同VA依次比较mask0/4096：A存(B xor mask)、B存(A xor mask)，显式零mask也执行同两EOR。8KiB对齐保证A xor4096=B，因此mask4096使raw节点自指，软件解码后仍访问对页。此为整数地址算术，不认证任何DMP存在/关闭，也不排除zero elision。两mask在同一mapping/同一trial访问相同实际line，是值域对照；两个独立mapping不是3072个独立硬件实验。

P为LDR/EOR x0、N个NOP、LDR/EOR x1、N个NOP；S两次均x0，A→B。E为同位置四条NOP及同N，保留相同码长/时钟/屏障。无循环分支，调用一次。全部JIT先4word常量x12、NOP填至64B；随后 **DSB SY;ISB;MRS x13,CNTVCT_EL0;ISB; [双load/filler];DSB SY;ISB;MRS x14,CNTVCT_EL0;SUB x0,x14,x13;RET**。N0=116B/29word，P/S/E长度一致，起点前DSB隔离前序内存操作，start后的ISB防止load跨越timestamp；两anchor之间绝不加屏障。内部ticks为时间，CNTFRQ单独记录，不换算为核心cycles。ticks=0合法（尤其empty/hot），不作为技术失败。

每窗先写两节点并128次同码暖身；共同DSB完成。hot显式读两line，cold对**自身两line**分别DC CIVAC，然后共同DSB；上述prep在PMU关闭时，之后才启窗。JIT内部独立计时，PMU组覆盖调用/用户wrapper全部，不减固定退休数或把PMU总窗串并比当单shot模型。DC到PoC不认证DRAM/所有缓存层已清；signal能力检查不能证明DC或CNTVCT/CNTFRQ访问不被内核模拟；若timer被trap，ticks包含相应elapsed而kernel-excluded PMU不计该段kernel事件，因此不称裸load latency。Linux6.1参考源码有用户cache维护trap路径（[traps.c](https://raw.githubusercontent.com/torvalds/linux/v6.1/arch/arm64/kernel/traps.c)），不能据此认定Android当前相同实现。访问/维护信号输出空metrics结构化failure，不fallback。能力测试在窗外检查CNTVCT/CNTFRQ/DC、实际返回递增与预期映射；计时分辨率来自本机实际CNTFRQ。

## 唯一生产矩阵与技术验收

`tools/diagnostic/run_sm8650_cold_pair.py` 固定mode=`rob-cold-pair-qualify`、2进程（epoch0/1各新mapping），每进程64trial。每trial恰好mask{0,4096}×swap{0,1}×member{P,S,E}×state{hot,cold}=24格；base顺序按上述维度字典积，先轮转trial%24，再按(trial+epoch)%2反序。每epoch1536窗，总3072；不删样本、不补测。两进程前各15秒统一冷却，环境基线前/后检查，不改频率/governor/热策略；CPU7/MIDR0x410fd821、4KiB/root/type8。注册 `docs/reviews/evidence/2026-10-09-cold-pair/plan.json` 与 `build.json` 先提交后执行。

事件固定0x11/08/03/17/34/37；全部开组并按ID解码，kernel/hv excluded、无mux、正enabled/running、所有整数count非负、CPU未迁移。初始/最终实际backing合格、每窗29≤IR≤1029（N0，wrapper保留）、精确24格/64trial覆盖与顺序、实际mask/同VA几何、全部6份导出生成码与当前source/build/launch/protocol/driver/raw SHA审核。probe结构化failure或环境失败停整块，缺失前缀科学不可计算，不造零值。三层证据分开：纯曲线/host producer/目标板完整raw。

## 预注册科学资格（新机制，不能救旧批）

先技术完整审核。每mask/swap/epoch/P或S，按trial形成64个cold−hot的**内部tick差值**以及逐事件count差值（可负，全部保留）。使用median与MAD，事件使用64项算术均值。E同样配对，仅作仪器哨兵，**不自动从P/S扣底噪**。

每mask须在两个swap×两个epoch的四单元分别同时满足：

- E冷热tick差中位绝对值≤1tick，64项绝对差的线性分位q90≤2tick；L1/L2/LL/datawalk的E count差均值绝对值≤0.5。hotE与coldE各自64项的内部tick中位分别≤min(hotP中位,hotS中位)+2，不合并state。
- P、S冷热tick差中位各≥3tick；MAD/中位≤0.2；S差中位/P差中位∈[1.5,2.5]。
- P和S的L1/L2/LL冷热count差均值均∈[1.5,2.5]（每call两load）；datawalk差均值绝对值≤0.1；hot/cold IR差中位绝对值≤4。wrapper/cacheprep与preload残差由E/事件和完整分布披露，不能靠总PMU窗“约2miss”认定load语义。

这是保守工程资格，不是显著性检验或物理容量。完整3072窗只有某mask四单元均合格，才另行预注册有限N0/128/256/384/512窗口扫描（P/S/E、冷/热都保留），暂不实施/授权自动无限加密。若cache维护不支持、时间分辨率或冷信号不合格，先报告对应机制不足，不扩大样本或调门直到通过。即使合格也仅称可辨识的操作性双冷load候选；后续NOP响应不能直接换算ROB，PRF/RS/前端/融合与384候选沿 `docs/open-items.md`。

## 实施顺序与交付路径

1. root写 `tools/diagnostic/tests/test_cold_pair_producer.py`：缺producer断言RED；真实host生成6种N0及N128/4096字节、29word/屏障/clock/dep/ABI；map与节点自指/软件decode harness；非法参数/unsupported measurement命名失败。实现C至GREEN，独立NDK反汇编与两次relative构建相等。
2. root写 `tools/diagnostic/run_sm8650_cold_pair.py`：先真实矩阵/order/actual核验RED，再固定mode实施。使用现有AdbExecutor/环境只读组件与PG decoder，不接旧正式A1/schema；private raw完整保留。
3. consumer `tools/diagnostic/analyze_cold_pair.py`、`tools/diagnostic/tests/test_cold_pair_analysis.py`：先独立预期矩阵/失败金样，真实producer config/导出码对账；纯qualification另标合成，CLI必须完整raw/source审核。coverage/类型/乱序/重复/错mask/错event/坏生成码/冻结值入口负例；正/边界曲线和阴性资格不丢。
4. 自有文件各自scoped commit；root登记NDK/source/binary/protocol/plan；fresh相关及全量回归、独立审查后再上板。不得代提交其他会话文件/旧run，root sole device；remote暂不动。
5. report `docs/reviews/2026-10-09-cold-pair-results.md`、脱敏 `docs/reviews/evidence/2026-10-09-cold-pair/`；列分支/源commit/launchcommit及全部SHA，图区分P/S/E、hot/cold与mapping，完整负值保存。README更新实际状态，所有后置项 `docs/open-items.md` 保留归属与触发，不用永续分支伪装科学完成。
