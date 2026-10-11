# Cortex-X4 ROB 单位标尺复核（2026-10-11）

## 本次任务的目的（给人类看）

给正在执行的双独立锚点扫描明确解释边界：即使有效重叠转折复制，也先审查所数的是ISA指令、MOP还是µOP，不能直接宣称物理ROB entries。工作树r2，branch `codex/sm8650-tlb-hierarchy-r2`；不改变已冻结扫描或producer字节。

## 原始资料与证据等级

`/Users/michaelyao/workspace/cpu-uarch-ref/docs/Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf` Issue3.0/r0p1 §2.1说明指令解码为MOP，MOP可能拆成两个µOP；§4.1给dispatch上限10 MOP/20µOP每cycle；§4.11明确列出NOP与相邻任意指令可融合，§4.12列部分MOV为零延迟、无需调度/执行资源。这些是官方结构/优化说明，不是本机各条指令每次实际融合的测量，更没有给出每个ROB entry存几个MOP。

`/Users/michaelyao/workspace/cpu-uarch-ref/docs/Arm_Cortex_X4_Core_TRM_102484_0003_06_en.pdf` Issue06/r0p3 §17.1把0x3a定义为退休µOP、0x3b定义为投机执行µOP，0x816d只有rename-full周期描述。目标MIDR是r0p1，revision差异保留；[Arm公开PMU列表](https://raw.githubusercontent.com/ARM-software/data/master/pmu/cortex-x4.json)本次核验一致，未找到明示ROB占用/entry-allocation tap。这个公开列表中未见不证明硬件没有内部信号；rename标签也不证明某一物理队列已满。

**推论**：fusion资格、µOP计数和物理ROB分配是三份契约；0x3a/0x08或N/2都不足以校准最后一份。第三方384图仍是候选先验，不是校准真值。

## 本机新事实的使用范围

`probes/diagnostic/rob_dual_anchor.c` 的D0/D1与D0/D0只差第二段16条寄存器位，初值/结果均1.0。`docs/reviews/2026-10-11-rob-dual-anchor-v1-results.md` 留有144窗技术通过、整体资格未过的事实；fresh v2资格144窗重叠/供给门通过（独立约208、串行约416、NONE N128约28.68），完整scan720窗技术通过，单区间INCONCLUSIVE；完整结果 `docs/reviews/2026-10-11-rob-dual-anchor-v2-results.md`。v2源/驱动/门 `docs/design/2026-10-11-rob-dual-anchor-v2.md`，不拼入v1窗口，不提前给扫描命名。

下一有区分力的单位控制可保持相同独立锚点、相同ADD实际值/目的集合，比较ADD组、NOP+ADD相邻组与双NOP组。NOP+ADD对照把ALU工作保持一致、改变ISA长度和官方fusion资格；双NOP组提供无GPR目的压力的控制。必须先认证各自真实NONE供给、导出完整字节/对齐/执行结果，并为不同模式复制；只有操作性窗口/资源响应可以从该对照直接命名。若拟合R/α，须显式报告α与活跃替代约束，不能把同窗口当成MOP或ROB单元已经校准。具体实施需独立新预注册，不能改变在跑数据来迎合384。

归属当前ROB负责人；触发=双独立扫描完整审计后。在 `docs/open-items.md` 登记，不靠永续m0b、无穷加密旧NOP曲线或静默宽门兜底。ALU/FPU完整部件项目仍后置，此单位控制只服务ROB辨识。
