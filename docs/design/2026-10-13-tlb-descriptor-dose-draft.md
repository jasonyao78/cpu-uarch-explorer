# TLB描述符足迹剂量对照（草案，未实现／冻结／采样）

## 本次任务的目的（给人类看）

检验r0p1规格2048统一条目中leaf与中间描述符可能竞争的解释，用预测而不是加密旧reach曲线。`docs/reviews/2026-10-13-tlb-observed-reach-scan-results.md` 已测同dataPFN/order而descriptor足迹差异；本候选继续区分leaf-only与joint-occupancy，不能独立排除全部地址hash/S2/cache。

## 候选控制与可推翻预测

N固定1536，同memfd/same ordinal physical order/4ISA LDR-MADD loop，A stride5pages，B stride grid[5,67,131,169,173,259,515]。全部奇stride保持完整VPN低8直方图；全部stride≥5确保每16KiB VA group至多一个选leaf，避免旧stride3“双选leaf组”混淆。A/B同处同root虚拟64B组，guard防fault-around，pernode初始observed descriptor绑定+卸载后匹配PMU；实际PT page/64Bline、Pmd、CONT、PFN与表关联都保留，不只从VA算。

无hash／coalescence且每不同leaf PT中间描述符占一个统一条目的最简候选：B的leaf PT page数15/201/393/507/519/777/1536，N+P=1551/1737/1929/2043/2055/2313/3072，预测169→173附近跨2048；额外上层和S2条目可能偏移，不把这条公式当已证。A stride5足迹15也需要独立floor／大N负控资格。高侧没有跃迁即可推翻这个简单计数解释；出现跃迁仅支持共同占用候选，不认证每PT分配1个条目／物理hash。

继续用actual代码/双NDK/typed producer→writer→loader→criterion、固定epochs与先N0，技术first-failure命名停；冻结前需确定walking阈值、持续／删失、dose单调约束、几何捕获与预算。源组件候选 `probes/diagnostic/tlb_descriptor_dose.c` 尚不存在；consumer/driver未交付。完整旧扫描已结束，不更改其配置／阈值。归属TLB physical组织，`docs/open-items.md`，primary branch codex/sm8650-tlb-hierarchy-r2。

2026-10-13后续：producer与消费栈已另行交付并预注册 `docs/design/2026-10-13-tlb-descriptor-dose.md`；本稿保留为推导历史，不作为最终协议入口。上板前尚需build／实际生产链验证。
