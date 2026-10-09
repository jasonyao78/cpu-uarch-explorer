# 同码形单cold状态注入（冻结v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-10-cold-load-model-results.md`的5120窗证明冷端单load有LL激励，但理想串并模型0/8相容。下一步保持P/S代码完全相同，在同一VA与同一准备流程中只改变哪条line执行DC CIVAC，检验条件内存延迟与单独延迟和的关系。本轮只N0，不认证DRAM、物理ROB、PRF、原资格或N扫描。

已比较三个方向：更大足迹不能解决码形/上下文差异；用户态PMU直接读取能改善时间分辨率，却需另行能力和恢复合同，沿 `docs/open-items.md` 后置；本轮选四状态同码形，直接缩小当前反例。改变频率profile也沿既有后置，不把端点频率当窗内证据。用户授权根Agent持续端到端执行，手机仅根Agent串行操作，无例行人工批准点。

## 生产合同与有限矩阵

扩展 `probes/diagnostic/rob_cold_pair.c`，显式 `--single-cold`，与 `--singletons`互斥。version3/probe rob-cold-state；members仍[P,S,E]、JIT仍29word/116B，与原pair所有机器码逐字节相同。只新增状态[hot,first-cold,second-cold,cold]，分别冷位掩码0/1/2/3；第一/第二指当前swap后的head0/head1，不是固定页偏移。两目标仍偏移0/4096、8KiB对齐、mask0/4096，raw self几何仍验。A/B成员拒绝，未知flag拒绝，实测N非0拒绝。

每cell写入同两节点链→同member代码128次暖身→总是只读两line并DSB→按冷位掩码DC CIVAC选中的line→DSB。所有准备在PMU/内部clock窗外；hot也经过相同准备屏障。只冷状态不承诺另一条必为L1命中，实际计数是激励审计。维护条数不同可影响窗前上下文，E同状态哨兵披露残差，不做自动补偿；能力检查不证明DC原生无trap。旧pair/singletons配置、JIT导出和生产顺序保持不变，旧source/build仍只能由各自注册binary运行。

`tools/diagnostic/run_sm8650_cold_pair.py --profile singlecold`的mode=rob-cold-state，2mapping×64trial×48格=6144窗，每进程3072。base=mask0/4096×swap0/1×P/S/E×四状态，trial%48左轮转，再(trial+epoch)奇数反序。64trial完整保留，不补点、不拼部分进程。每epoch前15秒冷却，沿现有sole-owner/journal、4K backing、CPU7/MIDR、完整PMU/no-mux、源/launch/binary/plan/driver/protocol及6环境端点门；不改频率、温控、sysctl。

新增config字段single_cold_requested=true、state_cold_slot_masks=[0,1,2,3]，严格bool/int区分。driver录入实际shape并导出12份代码（epoch2×mask2×member3）；新消费者 `tools/diagnostic/analyze_cold_state.py`独立期待48格、完整6144窗、全部生成码/config与Git绑定，不从driver或raw猜预期。原consumer不改合同。

## 数学、激励与命名

单位为每epoch/mask/swap/trial的同member四状态内部CNTVCT ticks（00/10/01/11），不池化epoch或swap；全有符号差、原始事件count、零tick、尾部与时间序列保留。先逐trial算值，再median/MAD/Type7 q10/q90：

- P四状态模型：R_P=T_P11−max(T_P10,T_P01)。两单cold代码本身已有相同hot/fence底座，不再扣E。
- S四状态模型：R_S=T_S11−T_S10−T_S01+T_S00。这是同码形四状态的可加性检验，不把单独A/B码形的延迟作为基线。
- 两个模型分别与冻结描述分辨率带比较：abs(median residual)≤2 ticks且q90(abs residual)≤3 ticks。带外只称不相容，不能单归memory耦合、bank、LLCC、DMP、频率或cache-maintenance trap，也不是统计显著性检验。
- 激励审计：P/S各非hot状态cold-state减hot的tick中位≥3；first/second的L2与LL count差均值在[0.75,1.25]，both在[1.5,2.5]，各datawalk差绝对均值≤0.1；P/S hot端L2与LL原count均值≤0.25。L1 raw与差值全部单列，无致命L1差门。本轮不使用MAD/中位做新资格（方差直接进入完整模型残差），绝不回填先前singleton7/8或pair失败门。
- E三种非hot状态相对hot：abs(tick差中位)≤1、q90(abs差)≤2；L1/L2/LL/walk各count差绝对均值≤0.5。E只哨兵，不从任何P/S计数或四状态残差扣除。

逐8单元分别报告stimulus_passed、model_compatible和失败门。缺格/重复/乱序/错type/code/source/env是技术失败，CLI不产出分析工件；完整但激励或模型失败照常输出完整证据。顶层n_scan_authorized始终false，不存在eligible masks。两mapping重复是2个上下文，不将6144窗当6144独立实验。

## 实施计划与验收

根Agent直接实施，无新代理或设备操作者。设计/计划以本文件为唯一冻结源。

1. 在 `tools/diagnostic/tests/test_cold_state_producer.py`先编译真实C并请求 `--single-cold --write-asm`，应因未知flag RED；另include真实C的 `cell_at_single_cold` 与冷位到实际head选择函数打印全部6144顺序/slot，未交付应RED。GREEN后覆盖互斥/未知/A-B/N错误、默认48旧config/bytes及6144独立顺序/冷slot。
2. `tools/diagnostic/tests/test_cold_state_driver.py`先断言 `plan('singlecold')`6144窗、48格、明确flag/typedconfig，未注册profile应RED；再最小接线driver/配置/完整round审计，测坏类型/缺重复乱序/旧shape拒绝。
3. 新消费者/test先写显式四状态金样：P(1,11,15,15) residual0、S(1,11,15,25) residual0；若S11=18则residual−7，不能被其他epoch救。加入max与状态差次序、signed尾/zero/全门消费及实际host code/config/order→synthetic measurement→raw/CLI破坏反例，再GREEN。合成数据不冒称设备。
4. 邻近/全诊断回归、旧3072与5120 raw字节重放、独立只读接缝复核；只提交本轮自有源/测试。NDK27.2/API34 `-O2 -Wall -Wextra -Werror -static -Iprobes/common`两次独立重建字节相同，登记新source/build/plan SHA到 `docs/reviews/evidence/2026-10-10-cold-state/`并提交。
5. 根Agent执行6144窗→新消费者完整审核→独立数学/raw SHA复算→报告 `docs/reviews/2026-10-10-cold-state-results.md`。更新README和 `docs/open-items.md`，raw仅private。无论结果，有限预算不续跑到过门；据同码形条件对照再设计操作性重叠/资源辨识，不能用384硬套。
