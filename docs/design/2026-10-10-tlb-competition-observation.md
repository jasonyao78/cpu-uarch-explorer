# TLB竞争访问观测与遍数对照（冻结v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-09-tlb-capacity-results.md`在F128下工作集转折(8,9]重复5/5，但单victim竞争响应有界0/5。需要检查竞争访问本身的翻译激励，及重复竞争能否改变该响应。观测对象是whole-window事件及受控访问协议，不把lookup计数当allocation证明，不把无walk当物理容量>11。用户已授权root端到端推进，root独占串行设备，不另派上板Agent。

比较三方向：直接扩大K会改变页集并遗漏相关层是否被激励；全局TLB/cache操作无法给出可移植且可审计reset；本轮保留最大12页、victim0及竞争1..K，测每次竞争遍的窗口，并扫描1/2/4/8遍，先回答访问是否进入相关翻译查找。snapshot包装会改变历史，本批是新的“带观测竞争”协议，不与旧无观测竞争拼接成因果配对。

## 组件与精确生产合同

新增 `probes/diagnostic/tlb_competition.cpp`、`probes/diagnostic/tlb_competition_layout.h`；复用 `probes/diagnostic/tlb_capacity_layout.h` 最大页集、slot4竞争闭环与旧9页前缀，不修改旧probe/header。driver `tools/diagnostic/run_sm8650_minimal.py`新增mode tlb-competition，消费者 `tools/diagnostic/tlb_competition_analysis.py`，raw与来源归档沿 `tools/diagnostic/summarize_sm8650_minimal.py`。build/plan注册在 `docs/reviews/evidence/2026-10-10-tlb-competition/`。

5 mapping；奇数epoch反转全部cell，cell内trial/pass不反。固定target100、seed137、F128、offset64*i、history12；H1/H2×K{0,7,8,9,10,11}×competitor顺/逆×passes{1,2,4,8}=96cells/mapping。每cell16trial，每trial有passes个competition窗及1victim窗，合计7296窗/mapping、36480窗。K0也执行相同次数F/空竞争snapshot，用作各pass位置/遍数的匹配控制；不从K0到7的稀疏网格给相邻容量区间。

每cell只建链一次，trial内不写target。每trial先[ F128→history12 ]×8，再F128→victim单次训练。随后逐pass：F128→snapshot→K竞争页slot4一圈→snapshot，记录该pass；最后F128→snapshot→victim单load→snapshot。所有目标/竞争起点与count/slot元数据在最后F前取得；noinline窗函数沿旧protocol边界，窗口含用户态snapshot/read/memcpy开销。准备不等于架构reset，观测窗也不证明纯TLB访问。保存全部trial与pass，末指针使用compiler barrier防消除。

config version1/probe tlb-competition，显式k_grid、pass_grid、96cells/7296windows。round含cell/position/h/k/direction/passes/round/role/pass_index：competition索引0..passes-1，victim索引passes。每cell前后base4K/AnonHugePages0；geometry保留私有VA，仅消费者输出匿名记录。PMU六事件[11,05,2d,2f,34,35]完整/no-mux/uint64，CPU7/MIDR、journal/owner与12环境端点、source/launch/driver/protocol/plan/build/binary SHA闭合。失败空metrics+failure，不补格或重复直到过门。每epoch前固定15秒冷却，保持walt原频率/温控策略。

## 描述判据与命名

逐epoch/H/order/passes/pass_index，在各K的16窗原值上统计；K0匹配相同条件。竞争可观察性：每个非零K/pass的0x05及0x2f均值减K0均值都在[0.75K,1.25K]，只称与K次L1 miss/L2 lookup激励相容，不称真实同set、驻留/替换或每页admission。datawalk/ITLB/L2refill及计数背景全部披露，不事后扣ITLB；配对A=H1/C=H2用于同epoch一致条件的差，K0/floor不能代替C。

victim逐H/K/order/passes披露walk>0率、均值、count>1、前后8率差；A−C率≥0.5称有竞争响应观察，K0 A/C各≤0.125才允许使用该称谓。count>1或任一H前后8漂移>0.25则命名窗口残差/准备漂移，不给victim miss概率或有界容量。两order/每mapping独立保留，≥4/5mapping双order都观察到响应才称该K/pass下重复响应；只归本新协议，不救旧joint门。所有竞争pass的可观察性门及失败数量一并输出，不能无响应直接归“竞争没进入”，也不能有lookup直接归“必占ways”。没有物理ways估计量，不返回capacity/eligible masks。

## 实施计划与自检

按brainstorming/writing-plans完成设计自审；用户持续自主授权优先于例行人工确认，直接由root执行。唯一冻结源为本文件，采用executing-plans与TDD，不引入新框架。

1. `tools/diagnostic/tests/test_tlb_competition_producer.py`先真实clang++编译/请求--plan，缺源RED；独立Python96cell/7296role顺序期待；include真实layout打印每trial production schedule；覆盖K/遍数/方向/slot4闭环，GREEN后源提交。
2. `tools/diagnostic/tests/test_tlb_competition_analysis.py`先实际producer plan/config/geometry→仅合成外部测量→审计，缺消费者RED；全36480覆盖和typed字段/no-mux/role/pass/缺失重复乱序、坏plan/raw/source/env/code绑定反例。纯计数金样分别测K事件激励、K0背景、重复响应/污染、漂移和H/epoch不得覆盖。GREEN后接driver/summarizer，旧10400raw重放字节一致；新/邻近及完整diagnostic回归。
3. 已提交源以NDK27.2/API34 `-O2 -Wall -Wextra -Werror -static -DCPU_UARCH_HAVE_PERF=1 -Iprobes/common -Iprobes/diagnostic`加 `probes/common/perf_window.cpp`两次独立构建一致；真实host --plan正反生成注册计划，登记全部递归自有依赖SHA并提交，实际binary窗反汇编核最后F/竞争/单victim load边界。
4. root有限5mapping→消费者全raw接受→另一条直接计数复算→ `docs/reviews/2026-10-10-tlb-competition-results.md`、全部匿名窗口/图、README/OI，按结果另案选择replacement/geometry反例，不拼旧A1或不停重测。任何未竟科学问题登记OI与触发，物理ROB沿已登记资源/计时合同。
