# TLB 地址族局部转折（采样前冻结 v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-11-tlb-address-geometry-results.md` 显示target7的W8已稳定响应，而target100/200在W9复制。现在定位各地址族的操作性victim转折，检验target差异在新mapping与匹配负控中能否复制。不估计物理ways，不把所有target合并成一个容量数。

方案：继续只测8/9不能确定低侧；扩全target×seed没有必要；采用7/100两族×1/16跨度、W6–10、同victim rank4与分散C2负控。W10提供第二个高侧点，避免只有W9一个高点就宣布interval。target200已在几何批复制100模式，此局部设计不再扩大。

## 地址、程序与预算

新独立组件 `probes/diagnostic/tlb_local_turn.cpp`、`probes/diagnostic/tlb_local_turn_layout.h`；复用 `probes/diagnostic/tlb_address_geometry_layout.h` 的算术选址和 `probes/diagnostic/tlb_history_layout.h` 的walk/filler。旧geometry/victim组件的默认argv、配置和行为不改。consumer `tools/diagnostic/tlb_turn_analysis.py`、driver `tools/diagnostic/run_sm8650_turn.py`、证据 `docs/reviews/evidence/2026-10-11-tlb-local-turn/`。

同256MiB4K池，target={7,100}、step={1,16}、C={1,2}，八family各12个最大页集。q0=ceil(baseVPN/256)、q=q0+i*step；C1 VPN=(q<<8)|target，C2 VPN=(q<<8)|(target XOR(q&255))。两收集签名互为12不同索引。F128共享闭合prefix、seed137、512候选排除全部八族的两模型占用sets；全部VA/实际几何保存在private。全域固定正序12页history，W1/v0空竞争；W={6,7,8,9,10}/victim4，W变化只改competitor prefix，victim与页偏移不变。

每mapping target×step×order{0,1}×C×W{1,6,7,8,9,10}=96cell；每trial八遍F→history，再F→victim训练；八遍F→snapshot→K竞争load→snapshot，最后F→snapshot→单victim→snapshot。16trial×9窗=13824窗/mapping；五fresh-process映射共69120窗，奇数mapping全计划反序，进程间15秒。继续CPU7/type8、events[11,05,2d,2f,34,35]、noTHP4K、原窗口包装，元数据在最终F前取得。新生产helper负责W6/7/10验证与链接；不扩大旧helper允许值偷换旧合同。

## 接受和有限判据

技术接受在统计之前：实际--plan与独立96期待、八地址族/完整实际链接/69120 shot、4K backing、无mux/typed uint64/positive cycles、source/build/launch/plan/driver/protocol/raw SHA、双NDK与实际窗码核验。完整五mapping必须齐，缺失/重复/冲突/乱序/额外raw或首坏step停整批、不补格、不拼旧批。仅观察既有walt环境，不改频率/温控/THP/全局PMU，无事务；端点不证窗内恒频。

每K/pass matched W1差分的0x05及0x2f均须∈[.75K,1.25K]；任一失败点命名INCOMPUTABLE，不能当no-response。W1任一datawalk或single-victim walk>1同样阻断该比较命名；保留全部计数。每mapping/order/target/step/C/W的16trial datawalk非零率≥.5才response，低于.5为本协议no-response，不把偶发零/非零裁剪。

每mapping/order曲线独立按W6..10判定：全部低→no-onset-through10；W6已高→left-censored；只有W10高→right-censored；否则须所有低侧为no-response、所有高侧为response且至少两高侧点，才interval=(最后低W,首高W]；非单调→ambiguous；任一不可计算→INCOMPUTABLE。每target/step/C只有五mapping×双order十条曲线全部相同interval，才replicated-operational-interval；不以多数或总平均掩盖差异。其它状态与原值全部报告。转折是条件化victim响应，不是结构项数，lookup不证明admission。

## 实施和终点

按已授权第一性原理路线、brainstorming/writing-plans与TDD执行：先真实C++ plan/selector/链接轨迹RED→GREEN；提交源→双NDK/独立consumer与所有维度负例→真实driver写盘/raw回读/首坏点/守卫mutation→提交launch→串行有限采样。直接JSONL第二算术路径逐全部窗/身份/判据/SHA；匿名全计数/图/报告，README/OI范围提交。完成此有限批后停止围绕同一victim无限加密，转原目标对账及TLB Q-A/Q-D缺口；物理ways/descriptor/hash/PFN/cache用有限不可识别边界收束或有新区分力的正交设计。旧A1/frozen/14条L1不拼接，正式runner/窗内clock后置项保留 `docs/open-items.md`。
