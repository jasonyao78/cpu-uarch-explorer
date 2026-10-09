# TLB target100 与 ROB 有效窗口局部确认（冻结 v1）

## 本次任务的目的（给人类看）

用户已批准继续 `docs/reviews/2026-10-09-minimal-probes-results.md` 的两个最小后续：独立确认TLB另一target；缩小FP锚点+NOP的响应区间，并攻击简单供给交叉解释。当前Agent独占手机、串行采样。分支 `codex/sm8650-tlb-hierarchy-r2`，起点 `1798d3e`；本文件与驱动先提交再测，实际commit进入manifest。不扩大到原A1，不以物理ROB或8ways为预定结论。

## 协议、预算与停止线

- **TLB**：`probes/diagnostic/tlb_local_pair.cpp` 原样用于target100。5 fresh-process mapping epoch，奇数epoch `--reverse`；每epoch40格×20窗（r0预排除），共4000窗/3800保留窗。其余选址、maxW9嵌套W8/9、F128/512、seed42/137、offset0/rotate均与target200相同。独立汇总，不把两target称为配对epoch。
- **ROB NOP主网格**：每gap N={0,512,544,576,608,640,672,704,736,768}，anchor={none,fsqrt k8,fsqrt k16}，loop mod64=0；两进程epoch×三轮，共60进程。
- **真实对齐对照**：NOP N={0,608,640,672,768}，同三anchor，loop mod64=32；两epoch×三轮，30进程。只能检查中心区域及所测点，不能声称全域对齐不变。
- **资源sentinel**：ADD/FADD N={0,128,640}，anchor={none,fsqrt k16}，align0；两epoch×三轮，24进程。N128用于发现远早于NOP的响应，不估其精确onset。
- ROB共114进程/342窗。每窗131072迭代；epoch0固定枚举，epoch1完全反序。无临时加点、补挑样本、删异常或按结果大小接收。矩阵权威路径 `tools/diagnostic/run_sm8650_minimal.py::conditions`（`tlb-confirm100` / `rob-fine`）。
- 复用源码 `217e5e3` 的已验证Android arm64静态二进制与host生成码器；构建与依赖摘要权威为 `docs/reviews/evidence/2026-10-09-minimal-probes/build.json`。分别记录本轮launch HEAD、binary source HEAD、binary/driver/protocol SHA，不冒称重新编译。
- 每进程前后及每批初末只读环境核查；不改governor、频率、热服务。未闭journal/其它探针活动、环境warning/violation、请求与自描述不符、缺格/重复、计数/事件/mux/输出失败立即停止，保留全输出，不靠换profile挽救本批。末尾环境失败也不得标complete。

## 预注册计算规则

**TLB**沿用 `DID=(A9−A8)−(C9−C8)`，datawalk/window。每格取19保留轮均值，各epoch先平均两个seed，再展示5epoch的全部值及均值/中位/范围；保留seed分层值与floor。与target200并列对比方向/幅值，不能按80个相关对计算独立置信度。方向不稳、零或负均完整披露。两批异时、非配对，不能把差异只归target。

**ROB**每cell/epoch三轮取中位 `m_e(N)`，`D_e(N)=m_e(N)−m_e(0)`；绝对阈值固定δ=1 cycle/iteration，两个k共用。主判据仅用于align0的NOP+fsqrt：最小采样N_i，使两个epoch在N_i及下一点都D>δ，此前全部点|D|≤δ。报告 `(N_prev,N_i]`，不给插值精确数。若首个非零点512已越线，记左侧网格不足；仅最后一点越线记右端未确认；epoch分类冲突、负向越界、回落或不满足前段平台，记ambiguous，保留原因。对齐32可用同算法作稀疏网格描述，权限明确低于主网格。

对none只报原始曲线。每epoch分别比较简单全重叠吞吐参考 `max[m_k(0),m_none(N)]`；不把相减残差当ROB条目。参考低于实测说明该简单模型不够，仍不能排除前端分配/融合、PRF或FP调度等。ADD/FADD只比较三个sentinel及自身none；不由类别差直接命名结构容量。δ来自上一批平台漂移<0.03的效果量选择，不是显著性阈值/置信区间。

## 软件接缝与交付

先用真实旧日志复现并拒绝target误标签、重复epoch顶替、driver脱离launch commit，再测；保留旧四批脱敏汇总字节一致重放。`tools/diagnostic/summarize_sm8650_minimal.py` 绑定注册矩阵、请求/realized、唯一epoch/round、来源与全环境端点。新ROB派生身份必须含epoch、class、anchor、chain、N、真实loop mod64、iterations、seed；新TLB run显式保存tlb_target，不能和设备匿名代号混用。

新原始数据存 `data/private/`；脱敏派生表、分析脚本、图和报告另放 `docs/reviews/evidence/2026-10-09-local-confirmation/`，不覆盖前批证据。当前只交付有效响应及机制约束；W7–10/目标顺序、物理容量、miss资格和ALU/FPU完整标定继续在 `docs/open-items.md` 跟踪，触发由本批结果决定。
