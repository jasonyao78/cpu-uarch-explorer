# ROB 冷load单独延迟与串并模型诊断（冻结v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-09-cold-pair-results.md`的N0完整3072窗技术通过但旧资格不通过：e0串并比不足、e1热端L1 refill导致差值偏低。冷端约两次L2/LL miss、walk0，不能把资格未过等同于无冷load。本轮补单独A/B测量，直接检验串并理想模型，**只N0，不授权容量扫描、不改原批门或回填原资格**。用户授权根Agent独占设备持续研究，所有测量串行。

## 代码与有限矩阵

`probes/diagnostic/rob_cold_pair.c`新增显式`--singletons`；只有该flag允许A/B成员。原P/S/E码形、legacy config/24格顺序不变。A仅第一次LDR/EOR x0，第二位置两NOP；B第一次两NOP、第二次LDR/EOR x1，保持与P/S/E同29word、相同屏障/内部clock/常量。same8KiB mapping、两个页偏移0/4096、mask0/4096、swap0/1及prep保持；A/B命名指第1/第2slot，swap1时实际节点互换；A不恒等页偏移0。跨member同VA，单load仍共同清两line，避免维护工作量差异。mask4096的raw自指几何仍实证核验。IR范围29..1029、PMU事件和64轮暖身128call不变。

新profile singletons，mode rob-cold-load-model，config version2/probe rob-load-model、singletons_requested=true、members[P,S,E,A,B]、40格/trial、2560窗/epoch。`tools/diagnostic/run_sm8650_cold_pair.py --profile singletons` 固定两mapping×64trial，共5120窗，不补点。base=mask×swap×member×hot/cold，trial%40左轮转，然后(trial+epoch)奇数反序。每epoch前15秒冷却，原环境/实际backing/no-mux/源与binary/launch/plan/raw SHA门；不写perf_user_access（只读当前0）、频率或任何sysfs。技术失败停块，保留raw且不拼前缀。旧profile默认pair仍可重放，旧source/build档案保持原版。

## 分析单位、预测与推翻路径

`tools/diagnostic/analyze_cold_load_model.py`严格完整身份/source/code/raw审核后，每epoch/mask/swap/trial/state分别保留五个内部tick与全部PMU原count，零tick/负差/尾部不删，CNT19.2MHz实际值登记而不换成corecycles。

- 理想独立时间预测max(T_A,T_B)，每state残差R_P=T_P-max(T_A,T_B)。
- 理想串行时间预测T_A+T_B-T_E（仅数学模型的共同仪器开销假设），每state残差R_S=T_S-(T_A+T_B-T_E)。E仅代理共同clock/fence开销的可加性，NOP与LDR/EOR的issue/完成行为不等同，模型残差不能单归memory耦合。E原值单列；不自动从PMU计数或任何容量判据扣除E。
- 先逐state构造max/sum，再形成cold-hot差；不得将max(ΔA,ΔB)当作max的冷热差。报告每trial残差、median/MAD/q10/q90，不池化epoch、mask、swap。
- 1 tick量化会使组合残差放大；预注册“与理想模型相容”仅描述每state残差median绝对值≤2ticks且绝对残差线性q90≤3ticks的分辨率带，不是统计显著性或物理机制证明。单load冷/热tick差中位≥3、MAD/中位≤0.2，L2/LL count差均值[0.75,1.25]、walk差绝对均值≤0.1作为激励审计；L1 hot/cold原值分列，不能由差小推断cold未激励。

结果可推翻“两个coldload各自延迟相等且完美重叠/相加”的简化解释；不能定位DRAM bank、预取器、kernel模拟或频率根因。不同cell先后执行，个别trial不是瞬时同时测量；相同mapping内仍有历史/状态变化。模型相容也不自动复活旧pair资格或授权N扫；下一步必须根据实测另行冻结阻塞/资源/频率或几何鉴别。所有未竟物理ROB/PRF/RS/融合在 `docs/open-items.md` 有负责人和触发。

## 实施与工件

先真实producer与driver合同RED→GREEN，独立审查/相关及全量回归；源码提交→NDK独立重编相等→build/plan提交→根Agent固定5120窗→consumer全审核→报告。分支 codex/sm8650-tlb-hierarchy-r2，source/launch/binary分别登记 `docs/reviews/evidence/2026-10-10-cold-load-model/`；raw只data/private，report `docs/reviews/2026-10-10-cold-load-model-results.md`。相关测试 `tools/diagnostic/tests/test_cold_pair_producer.py`、`test_cold_pair_driver.py` 与 `test_cold_load_model.py`；旧冷pair记录不改名。
