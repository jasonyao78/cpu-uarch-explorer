# ROB 同进程/同代码地址配对（冻结 v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-11-rob-dependency-results.md` 的NONE三窗绝对周期波动使主DID未合格。本批检验在相同代码VA、同进程、交错顺序中，配对差分是否能控制供给变化；若仍失败，给有限不合格终态，不重跑至过门。结果只认证依赖相关有效窗口响应，不认证物理ROB项数。

## 选择与实现边界

只重复跨进程不能阻止ASLR/代码位置/时序残差；同时驻留四个代码地址仍混入不同取指位置；选择同一代码mapping反复RW→copy→clear-cache→RX，全部准备/暖身在窗外，每窗运行期固定RX，无同时修改执行。代码维护按小范围pure generator抽取，禁止复制/手改两套ADD生成规则。

从 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c` **逐字移动**opcode/options/build到 `probes/common/rob_codegen.h`，legacy解析/PMU/测量路径不改；无新增legacy旗标。新独立 `probes/diagnostic/rob_dependency_pair.c` 用该同一生成器；host支持plan/export，实测Linux AArch64。legacy旧8class、cold-load与依赖exporter全部重放，逐实际config/字节不变；历史source/build/launch档案不改写。

## 有限协议

每进程固定anchor/chain∈{none16,fsqrt8,fsqrt16}。四variant=i0,d0,i128,d128：same ADD族、8个dest轮转、每gap N0/128、两侧FMOV X12,D0，独立Rn16/依赖Rn12，输入bits都是sqrt(1)的0x3ff0000000000000，实际输出相同。N0两variant逐字相同，N128仅2N个ADD Rn位不同，遵守原 `docs/design/2026-10-11-rob-anchor-dependency.md` 算法。

每进程8blocks×四窗=32窗，每block四variant，偶block[i0,d0,i128,d128]、奇block完整反序。奇epoch整32窗再反序。每variant重写到同64KiB RX mapping基址，memcmp实码匹配计划、清Icache，warmup131072iter后测同131072iter；所有窗口保留。5fresh epochs×3进程=15进程/480窗，进程间15s，只读baselinequiet-state。循环mod64=0、CPU7/FPCR0/type8、六事件[11,08,3a,3b,816d,23]，GROUP+ID/pinned/exclude kernel,hv、等时不mux/noRESET。导出并保存4program words/完整schedule、实际code_base/PMU IDs、每窗C/IR/OP/rename/frontend及ns。cycles/ns只作用户执行/墙钟比诊断，不冒称真实频率。

## 预注册消费门

`tools/diagnostic/rob_pair_analysis.py` / `tools/diagnostic/run_sm8650_rob_pair.py` 验全部15身份/3种anchor-chain/4program/32schedule/480窗、精确源/构建/launch SHA，IR=(loop_words*iterations+prologue_words+RET)误差≤max1000或1%，每窗同一code_base/对齐、6唯一kernel IDs，失败不拼补。cycle类比>1命名semantics-incompatible，不直接命名PRF full。

每block定义 T=[C(d128)-C(d0)]-[C(i128)-C(i0)]，C是该单窗 cycles/131072，四项带符号、先逐block配对再汇总；N0哨兵 E=C(d0)-C(i0)。保留绝对C各variant范围，不能只画差。

主门全部满足：① 每进程8个E的|median|≤1且max-min≤2 cycles/iter（逐字相同N0证明能量化噪声）；② 5个NONE进程的全部40个T |median|≤5且max-min≤5cycles（只有这种局部配对负控稳定才允许差分）；③ 与同epoch/block NONE匹配的 D=T(fsqrt)-T(none)，两个chain全部80个D>5cycles/iter。通过命名paired-dependency-associated-response；任何失败not-qualified，主门不替代绝对供给稳定性证明。外部中断/DVFS/前端残差均不作无证据归因，rename仍仅事件名的占比。

## 执行计划与有限终点

1. `tools/diagnostic/tests/test_rob_pair_producer.py` 先RED实际新producer missing；legacy golden抓当前C导出，与抽取后all classes/code/config逐字比；真实新plan全部12program/96schedule匹配，N0相同/N128仅Rn不同、逆序覆盖。
2. 抽取pure header/新producer后GREEN，双NDK、实际所有生成体独立Capstone检查；`docs/reviews/evidence/2026-10-11-rob-same-address-pair/`登记code/build/plan及source，launch另记。
3. 实际producer→driver/writer→raw consumer成功、首坏停机、缺失/冲突/重复/乱序/重哈希身份/codebase/IDs/mux/IR/主门/绝对波动配对反例；全量诊断及native/runner/analysis适当集成回归。
4. 有限15手机进程，独立直接raw第二算术480窗/40NONE T/80D及所有SHA一致；完整图/匿名证据/结果。与已有冷load资格失败、零值反证、NOP操作转折合成可识别性报告，若无法认证allocation标尺则正式终态physical-ROB-unidentified，不以384图或OP/IR强填数字。

r2工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2` / branch `codex/sm8650-tlb-hierarchy-r2`。一个root串行拥有手机，user持续授权；main和远端暂不操作。纯codegen抽取是功能复用与legacy契约，macOS测试不冒称Linux PMU覆盖；正式runner/schema后置按 `docs/open-items.md`。
