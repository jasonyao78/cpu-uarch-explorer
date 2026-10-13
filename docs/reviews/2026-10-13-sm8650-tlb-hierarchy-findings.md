# SM8650 Cortex-X4 TLB 层次和容量阶段结论（2026-10-13）

## 本次任务的目的（给人类看）

直接回答当前手机的iTLB/dTLB是否分层、一级容量及set/way组织；区分匹配官方资料、目标实测、尚未识别机制。用户新明确i/d一级目标，不再只用旧三个L2/ROB研究项的“0/3”描述整体进展。

## 可以交付的主表

| 结构 | 容量 | 组织 | 依据与适用范围 |
|---|---:|---|---|
| L1 iTLB | **48个4KiB页的稳定有效容量** | 官方记载fully associative | 本机六条缓存/分支合格曲线均48→49；匹配r0p1 RAM表10-4 Entry0..47支持。表6-1的128仍记录冲突，不替Arm发布勘误、不泛化其他page-size |
| L1 dTLB | **96个4KiB页的稳定有效容量** | 官方记载fully associative | 六条缓存合格曲线均96→97；与r0p1表6-1/10-7的96一致 |
| 共享L2 TLB（I/D unified） | **2048 entries（匹配核心的官方规格）** | **256 sets × 8 ways** | r0p1表6-1、10-32的Way0..7/Entry0..255；可缓存leaf translation及intermediate descriptor等，并非“保证同时容纳2048个4KiB leaf页” |

因此结构是**分离的一级iTLB和dTLB，共享二级TLB**，不需要臆造两个独立二级i/d TLB。目标MIDR=0x410fd821，r0p1匹配，匿名设备redmi-k70pro-01，Linux4KiB，CPU7。官方[TRM Issue04 r0p1](https://documentation-service.arm.com/static/6473ef18bae17b773b05d1e8)；版本/原PDF SHA/128-48冲突见 `docs/reviews/2026-10-13-x4-r0p1-source-audit.md`。

## 目标实测闭环

producer `probes/diagnostic/l1_tlb_reach.c`（粗sourcecd39b1e）/ `probes/diagnostic/l1_tlb_fine.c`（fine source721539c）；actual body data6ISA，instruction每page一个direct B及有界末环。NDK27.2/API34双构建一致；fine builda32587f、binary7d8a80edba6423661ad72f7fb2e87674d5d66137617a4bca2f1726e5dfbcf8c0。粗binary6f657fa1bc848061a44a46490561f8fac4359b4a2ba06bdea33c43d0f7edd328。branch codex/sm8650-tlb-hierarchy-r2。

- 同一memfd backing的192个唯一PFN、两个VA别名（stride5/17）、完全相同访问ordinal；固定offset与rotating(i&63)*64，实际alias/PFN身份C守卫与前后验证，不attach BPF。
- 粗扫描d12N×3process×18=648窗，i16N×3×18=864窗；两N32资格108窗。新细扫描各9N×3×18=486窗，另新N32资格108窗。**合计2700原窗口**，全SHA保留，旧批未回填。
- 原IR按data6/hop、instruction1+2/N精确检验、GROUP+ID无MUX、全部quiet-state pre/post合格，无profile修改。独立从原before/after再算signed empty扣除，不clip负值/refill>1。
- fine的6条primary曲线/结构，全no-walk/cache/aux门通过：d N96 refill≤.00035/hop、N97≥.5001；i N48≤.000089、N49≥.07005。阈值below.001/above.005在新protocol中先注册；i49的7%绝不回填到旧coarse .10门。
- 固定offset在小N32 cache refill可接近1，fine E0固定角色有ambiguous，全部保留。容量主证据只按预注册的缓存控制合格rotating，不使用固定offset cycles硬估容量。

报告 `docs/reviews/2026-10-13-l1-d-tlb-scan-results.md` / `docs/reviews/2026-10-13-l1-i-tlb-scan-results.md` / `docs/reviews/2026-10-13-l1-fine-d-tlb-scan-results.md` / `docs/reviews/2026-10-13-l1-fine-i-tlb-scan-results.md`；全部原匿名计数CSV与原库存SHA在各对应 `docs/reviews/evidence/2026-10-13-l1-tlb-reach/` / `2026-10-13-l1-tlb-fine/`。实际launch由每份scan-analysis.json给出，不把buildcommit当launch。

## 仍未确定的部分

一级两容量的当前4KiB测量目标可以交付；fully-assoc是匹配核心官方支持、有限VA布局与之兼容，不能说两步长唯一排除了任何假想bank/hash。其他page-size、多ASID、跨I/D替换/干扰和policy归open-items另案。

L2容量/256×8可以报告为**官方规格确认**；当前独立黑盒仍未将真实有效leaf reach唯一换算成物理entries，未识别完整VA/ASID/PA selector。`docs/reviews/2026-10-13-tlb-descriptor-dose-results.md` 的N1536/不同descriptor dose反证单纯N+P全局预算；同PFN不等于同所有cache活动，Linux PA/IPA不等于machine HPA。不得因规格2048/8而重新拟合旧数据或声称全hash已识别。

**ROB物理容量尚未确认**：旧proxy、partial SB N0、第三方384不是allocation证明。`docs/reviews/2026-10-13-pmu-own-counter-results.md` 实际直接counter已有前两process正控，但第三metadata变化导致原资格整批不通过；固定attempt新版将失效trace独立保留，依然需要short-window/单位/活跃约束后才容量扫描。新结果跟踪 `docs/open-items.md` 和 `docs/reviews/2026-10-11-tlb-rob-goal-ledger.md`。

目标距离：一级i/d容量本轮相邻页确认；L2容量与set/way有明确官方匹配证据；L2叶子有效占用/精确索引仍研究项，**ROB是剩余容量主阻塞**。不按测试数报完成百分比，不给没有辨識依据的时间承诺。无main merge/remote push，旧不完整A1/frozen不拼接。
