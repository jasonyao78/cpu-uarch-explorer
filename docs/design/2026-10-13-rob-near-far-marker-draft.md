# ROB near/far issue marker候选（草案，未冻结/未实现/未采样）

## 本次任务的目的（给人类看）

把 `docs/reviews/2026-10-13-rob-cache-marker-results.md` 的不稳定错误路径cache footprint，转换为“近marker证明本次错误路径被发射，远marker判定跨过filler后的发射”。区分prediction-not-excited、issued、fill-completed、retired；本草案不能被当作已交付容量方法。

候选采用支持事件的信号放大：branch后8个自有hot LDR作为near tap（LD_SPEC0x70），远侧8个自有hot STR作为far tap（ST_SPEC0x71）。每marker都用不同64B line，避免store合并解释；所有页仅本probe持有、已知非秘密常量。ST_SPEC是否目标implemented/语义可用必须官方表+真实A正控验证，不能再用open成功代替。LD_RETIRED0x06继续禁止作为退休证书。

## 架构/条件观测边界

延迟CBZ前置near寄存器清零、近载入改变它；finish有SB和独立output。A train0/test0，architectural near输出常量、8far words真实更新；B train1/test1，near0/far未改；M train0/test1，near0/far未改但可能LD_SPEC/ST_SPEC增量。所有own words和original FPSR/bits严格验证，不仅相信branch label。没有其它memory/state泄漏对象。

独立A/B校准near/far计数阈值，M标签不参与选择。近tap若无信号，本次不能区分没预测/没发射/未到达，不得硬判ROB小；原始window全保留并命名prediction/issue未激励，不删除当坏点。近tap有信号才报告远/近条件响应；要求预注册足够eligible数量、阴性误报界和跨process复制。条件化可能选择较好的supply状态，不能自动推广整个CPU物理容量，必须报告eligible率并检查其随N变化。

N0必须先证明A/B计数差为8的可分辨响应、M架构未退休、near eligible中far响应复制、计数器/同码/PFN/CPU/准备完整；不预设所有M都错预测。128trial、3fresh、最少eligible数量、阈值规则和停止线目前仅候选，实施前另冻结，不能从未来数据选最有利规则。

## 冻结filler前的必要设计

- 固定codeVA/PFN、branch PC、skip target与整个text大小；near始终在同位置，far在N之后，其余padding保持全部opcode histogram。两code页/固定full-body warm，RW/RX/cache maintenance不在窗内。NOP+Any fusion及zero-MOV elimination的正式资料必须分别解读，不把IR/OP_SPEC/OP_RETIRED直接叫allocation slots。
- 延迟branch限制年轻指令退休；早于branch的FSQRT链会逐渐退休，不能把整条k都算常驻占用。k和filler/resource类的正交控制区分deadline/supply与容量；不是再拟合g+k代理到384。
- near/far固定load/store资源占用需控制；NOP/zero-MOV不同class和rename/supply counter只能约束替代原因，不能仅凭dropout唯一命名MCQ/ROB。实际unit标尺和唯一active constraint依旧是最终出口缺口。
- one-shot的完整ioctl包络不可拿旧每窗Icache≤1失败门直接改大救门；新pipeline和匹配cal前先注册有解释力的supply约束。旧648/1536窗口终态保持不通过。

组件候选 `probes/diagnostic/rob_issue_marker.c`（尚不存在），consumer/driver尚未命名冻结。branch codex/sm8650-tlb-hierarchy-r2，primary负责；TLB当前descriptor-bound scan独占手机，ROB本稿不同时操作设备。追踪 `docs/open-items.md`。
