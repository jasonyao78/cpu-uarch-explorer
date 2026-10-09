# TLB历史与级联驱逐反证（冻结v1）

## 本次任务的目的（给人类看）

用户授权持续端到端推进TLB/ROB。先区分target100的W8整圈8walk、W9反而较少和逐轮衰减属于准备历史还是窗内级联，再决定容量扫描。当前Agent独占手机，TLB/ROB串行；分支`codex/sm8650-tlb-hierarchy-r2`。先提交协议及代码，再交叉编译与测量，不拼旧正式A1或frozen。

## 同一prefix、不在历史之间重连

新增 `probes/diagnostic/tlb_history.cpp` / `probes/diagnostic/tlb_history_layout.h`，复用 `probes/diagnostic/tlb_local_layout.h` 和既有PMU。target100先按旧collector取得max9，再追加三页（自身同set、另一候选总共12不同set），明确保留该mapping的旧prefix9；不是把need直接改12后声称旧选址不变。不同新mapping仍不是旧批相同VA/PFN。

每页rotate offset=64*i，同一64B line四个8B link槽分别activeW顺/逆、history6、history12。每个H/W组开始一次建链，之后所有history/direction条件之间不再写链。activeW两方向均闭合在同一prefix内，避免计数前缀尾指向W+1后可能投机访问窗外页；history6/12也分别闭合。每次遍历重新从指定head起，不沿上次末指针继续。F512为seed137固定shuffle，F128同序prefix；filler在同一cache line有两个link槽，128/512分别闭环，禁止prefix末指针投机越界；filler排除两H全部target占位，F0不访filler。

## 固定5mapping ×800窗

每process一个mapping；奇数epoch反转H/W组及组内case顺序。所有步保留，不排r0、不以结果大小接收。

| 子实验 | 每epoch配置 | 窗 |
|---|---|---:|
| 核心history | F128×H1/H2×W8/9×history6/12×probe顺/逆；16步 | 256 |
| F512哨兵 | H1/H2×W8/9×history12×probe顺/逆；16步 | 128 |
| F0 L1屏蔽 | H1/H2×W8/12×history12×probe顺；16步 | 64 |
| 单页probe | F128 W8；H1/H2×history6/12×victim0..7；8轮转trial | 256 |
| floor | F0/128/512，块前后各16窗 | 96 |
| 合计 | 38个cells（4个victim bundle）、5epoch | **800 / 4000** |

trajectory先共同参考`[F→history12]×8`，再请求的`[F→history6/12]×8`，历史固定正序；随后16步`F→snapshot→当前W单圈→snapshot`，无额外未记录target预热。history准备只在trajectory开始执行，完整记录0..15变化。与旧每轮active预热再F协议不同，不能拼绝对曲线。单页每个样本重新做同样common+requested history，再F→snapshot→只load指定victim→snapshot；每个bundle按trial0..7和位置0..7轮转victim=(trial+位置)%8，每页在每个位置恰一次；不是架构TLB reset，也不称独立trial。与正序trajectory第一步的准备相同。F0低walk且低0x2f只说明L1屏蔽，不能否定L2竞争。

## 预注册比较与边界

- 每epoch展示完整16步，比较第1/8/16步和末4步均值；不把混合瞬态均值叫稳态。主history差为`(A12−C12)−(A6−C6)`，同页集顺−逆也先作A−C再作差，均逐epoch计算并保留各族原始差。
- 同一符号且每epoch绝对差≥1 datawalk/圈，联合至少4/5epoch，才称可复现历史/顺序敏感。第一步|差|≥1且同epoch末4步|差|<0.5，联合4/5epoch才称有限准备瞬态；末4步同向绝对差≥1且4/5epoch才称持久历史敏感。边界冲突完整披露，不改门。
- 单victim各8重复准备样本平均并保留trial漂移与count>1诊断；这首先是single-load window walk rate，非已认证miss概率。将8victim均值之和与同epoch/history正序W8 trajectory第一步并列。整圈高而部分单页低支持级联/试探扰动，不能从整圈8walk推窗前8项全不驻留；不同trial的隐藏状态残差仍保留。
- 下一步只有在准备状态可识别后，才固定max12扩W6–12及victim+competitor eviction曲线。不以本轮history效应直接命名ways；L2共享I/D和descriptor竞争、PFN/cache/隐藏索引仍开放。

CPU7/PMU type8/MIDR0x410fd821/base4K，六事件0x11/0x05/0x2d/0x2f/0x34/0x35，全部有效且无mux。每cell前后精确backing检查，初末及每process环境只读核验；不改governor/频率/热服务。任何技术/环境失败停块留证。新binary独立NDK27.2/API34构建、source/build/driver/protocol先锚定再部署。原始VA与日志私有，公开脱敏逐步计数、分析脚本及图。未完成项登记`docs/open-items.md`。
