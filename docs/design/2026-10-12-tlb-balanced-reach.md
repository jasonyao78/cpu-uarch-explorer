# TLB 均衡低位页集合与全局翻译可达范围（冻结v1）

## 本次任务的目的（给人类看）

在 `docs/reviews/2026-10-11-tlb-page-distribution-results.md` 的N1024/2048粗网格之间，测更窄的**操作性walk转折**，并给当前容量解释一个能推翻它的地址几何对照。不能用同一密集页集的单曲线代表物理2048项；本次匹配候选低8位分布而改变页间距/页表父项VA代理。参考 `/Users/michaelyao/workspace/cpu-uarch-ref/docs/Arm_Cortex_X4_Core_TRM_102484_0003_06_en.pdf` r0p3事件定义，设备r0p1；0x2f为统一TLB访问事件，不假设它仅计hit，也不硬加“access+refill=load”的守恒。TLB event发生率不是概率。

## 激励与几何证据

新增 `probes/diagnostic/tlb_balanced_reach.cpp` 和 `probes/diagnostic/tlb_balanced_reach_layout.h`；旧producer、旧门、旧raw不改。4GiB VA reserve (2^20 base pages)，不是逐字节flush。dense page=i；spaced page=257i；balanced-random page=256*perm4096_seed271[i]+i%256。每格N={512,1024,1280,1536,1792,2048,2304,2560,3072}，全是256倍数，三个族实际VPN低8位histogram精确相等。节点offset=64*(page_id%64)，三族offset直方图匹配。visit-order=seed137 Fisher-Yates及其reverse，独立于页集合选择。导出全部page/order/offset、实际baseVPN低8位hist与 `(baseVPN+page_id)>>9` 唯一父项列表。后者只是4KiB/512descriptor的VA代理，不是读取PTE或缓存行证据。HPA/PTE_CONT/PFN/data cache state均UNKNOWN，匹配虚拟颜色不能认证物理cache pressure或真实hardware set。

仅预触每族max3072节点offset处，一个进程的union≤9216页（payload≤36MiB）；实际union和触达page IDs写raw。MADV_NOHUGEPAGE，每格前后AnonHugePages=0；仅认证基础页政策，不认证硬件无聚合。单寄存器闭环pointer chase：LDR/SUBS/B.NE，warmup/每个正式窗loads=floor(1048576/N)*N，结束head必须回原点。三族×两order×九N=54格+空窗，3round=165窗/进程；五fresh mapping、奇epoch整矩阵reverse，总825窗。5进程间15s，只读环境与journal/ownership检查，异常停块，数据原样留private，不拼旧A1/frozen。

PMU GROUP+ID/pinned/user-only/noRESET/noMUX/type8/CPU7，六事件[0x11 cycles,0x08 IR,0x05 L1 dTLB refill,0x2d L2 TLB refill,0x2f L2 TLB access,0x34 data walk]。IR在3*loads±5%，base page=4096；空窗cycles中位≤正式窗cycles的1%，空窗各翻译事件中位≤.001*loads；各正式窗L1 dTLB refill/load∈[.75,1.25]确认翻译层激励。任何不合资格原值留存，相关curve=INCOMPUTABLE；本次没有cache/i-walk专用tap，不强作归因。

## 数据前冻结判据

每curve=epoch×shape×order（30条），不用跨mapping均值救门。阈值为原始0x34/loads≥.10：每N三round全越线=above，全未越线=below，跨线=ambiguous。先查资格/跨线及high后low非单调，再左删失；最后仅一个high点为right-censored，否则取首次high前后N为interval。无crossing报no-crossing-through3072。三个布局分别十条curve区间都相同才给replicated operational interval；不一致报heterogeneous，不把它除以ways命名physical entries。

同epoch/order/N以三窗count sum/三窗loads比较spaced或balanced-random对dense的walk事件率。对任一N，十个配对差全部≥.10（或≤−.10）才为复制几何效应。全部技术门通过且有此项=GEOMETRY_SENSITIVE；无复制且全部差绝对值<.10=NO_DIFFERENCE_DETECTED（有限效应门）；其余INCONCLUSIVE。cycle、L1/L2 refill、L2 access、walk所有原值/率和空窗校正值保留，负校正不裁零。不能用总曲线的漂亮knee掩盖布局差异或删失。

## 实现、证据与出口

branch `codex/sm8650-tlb-hierarchy-r2`、worktree `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`。组件 `tools/diagnostic/tlb_reach_analysis.py`、`tools/diagnostic/run_sm8650_tlb_reach.py`、tests `tools/diagnostic/tests/test_tlb_reach*.py`、构建/plan/机器码证据 `docs/reviews/evidence/2026-10-12-tlb-balanced-reach/`。source/build-consumer/actual launch/report分列commit、SHA。producer公开--plan和--layout base（与生产共用geometry输出）；只外部PMU/adb用mock，实际图逐节点访问、真实配置到写盘回读、缺失/重复/乱序/类型/几何/层激励/归档改SHA反例必过。两次NDK27.2/API34/O2/Werror/static及实际loop独立disassembly，全诊断回归后才上板；全窗独立第二算术与完整匿名CSV/图报告。手机未接不能用合成窗冒充目标测量；物理容量归因、正式runner/schema接入归 `docs/open-items.md`。
