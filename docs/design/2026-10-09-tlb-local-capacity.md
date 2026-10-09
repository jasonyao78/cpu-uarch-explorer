# TLB 局部转折与 victim 竞争（冻结v1）

## 本次任务的目的（给人类看）

承接`docs/reviews/2026-10-09-tlb-history-results.md`的历史反证：W8整圈高walk不能当成窗前八项全不驻留，初始效应可消退。本轮固定准备过程，测W6–12稳定段和单victim对K个竞争页的响应；可命名的是局部工作集/eviction响应区间，不自动命名物理ways。当前Agent独占设备，用户已授权持续推进；TLB/ROB串行，不拼旧正式A1。

## 实现与有限矩阵

新独立组件`probes/diagnostic/tlb_capacity.cpp`、`probes/diagnostic/tlb_capacity_layout.h`及其host测试；复用`probes/diagnostic/tlb_history_layout.h`的target100旧9+追加3选址、seed137 filler及闭环槽。生产`--plan [--reverse]`输出唯一矩阵，驱动`tools/diagnostic/run_sm8650_minimal.py`新mode=`tlb-capacity`；分析组件`tools/diagnostic/tlb_capacity_analysis.py`。5mapping，奇数epoch完整反序。每个H/W/K条件建链一次；条件内不写target。target rotate64*i；history12固定正序，无按结果挑history或方向。

| 子实验 | 每mapping | 窗 |
|---|---|---:|
| 局部工作集 | H1/H2×W6..12×dir顺/逆，F128，每条32步 | 896 |
| filler哨兵 | H1/H2×W7/8/9/10，dir顺，F512，每条32步 | 256 |
| L1屏蔽 | H1/H2×W8/12，F0，dir顺，每条16步 | 64 |
| victim竞争 | H1/H2×K0..11×competitor顺/逆，每条16次重新准备 | 768 |
| floor | F0/128/512，前后各16步 | 96 |
| 合计 | 94 cells，2080窗 | **5mapping / 10400窗** |

trajectory共同准备`[F→history12]×8`后，连续记录`F→snapshot→activeW一圈→snapshot`；无每步额外target预热。比较末8步与前8步（32步条目的17..24 vs25..32）均值，不删初始步。

victim固定index0；K个竞争页为同一最大12集合的index1..K，顺/逆使用同一页集，K0跳过competitor。第五link槽在同一cache line闭环1..K；probe指针为victim slot0单次读取，返回值不作第二次load。每个trial先`[F128→history12]×8`，再F128→victim单次训练→F128→K competitors一次→F128→snapshot→victim单次→snapshot。最后训练、竞争与试探之间不写target；每次重做准备不等于架构reset或独立Bernoulli。指针/页集元数据尽量在最后F前取得；窗口仍含snapshot包装，用floor与事件诊断披露残差。

## 预注册判据与命名限制

- 技术门：target12几何、filler排除两候选占位、真实4K backing每cell前后、完整生产matrix/顺序、PMU六事件有效无mux、CPU7/MIDR与环境端点、binary/source/launch/driver/protocol/plan SHA。任何技术失败停块留证。
- 局部工作集：逐epoch、F、direction计算末8步A−C；某W及下个相邻W均≥1 datawalk/圈才算越线。前点<1且前点/首高点/下个确认点三点的末8/前8均值差对A和C都≤0.5才给相邻区间（非整网格稳定声明）；首点已高且首两点稳定为左删失，末点刚高为右端未确认；越线后又落到阈值下命名非单调，不给容量区间。同一mapping的顺/逆必须各自给同一有界区间，再计至少4/5mapping给同一区间，才称重复的局部工作集转折；否则逐区间披露，禁止跨epoch平均救门。F512只作方向哨兵，不代替F128主判据。
- victim：保留16个原始窗口、walk>0比例、均值、count>1、前后8样本漂移及0x05/0x2f。K0对A与C walk>0比例均≤0.125才允许命名竞争诱发的响应；相同K与下一K的A−C walk>0比例均≥0.5，前K<0.5给响应区间。同一mapping两order各自给同一有界区间，再计至少4/5mapping同一区间才称重复的victim-eviction响应。非单调硬阻断为越过0.5后回落其下，任意相邻下降另作诊断；任一K的A或C后8对前8率绝对漂移>0.25、任一count>1均阻断该epoch/order整条curve。K0失败、阈值后回落、漂移>0.25或count>1分别命名受污染/非单调/准备漂移/单load窗口残差，不静默裁剪或命名miss概率。
- 左/右删失、无响应仅报告对应界限/计数，不进入有界区间joint成功门。两估计量互相约束，观察到8附近转折也只报告此访问协议下的区间。共同descriptor、未知索引/替换策略、I/D共享及PFN/cache残差仍在；不能用圈walk数换算初始缺失项数。

注册构建位于`docs/reviews/evidence/2026-10-09-tlb-capacity/build.json`；raw仅`data/private/`，公开保留全部脱敏窗口和图。新问题由当前端到端负责人登记`docs/open-items.md`，不靠永续分支兜底。
