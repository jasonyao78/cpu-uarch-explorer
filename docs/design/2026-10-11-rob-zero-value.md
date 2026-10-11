# ROB 零立即数有限对照（采样前设计 v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-11-rob-event-results.md`中GPR写入+fsqrt N128已有rename约87%而周期未增，NOP相同锚点24窗rename为0。问题是该关联是否对写入值域敏感；先比较同编码族的立即数0/1，避免以rename事件直接断言PRF/ROB条数。Arm知识库 `/Users/michaelyao/workspace/cpu-uarch-ref/docs/Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf`（Issue3.0/r0p1）§4.12列MOV Xd,#0为零延迟、不使用调度/执行资源，但没有说不占退休跟踪/ROB/PRF；寄存器MOV另有条件。官方优化提示是控制设计依据，不是目标设备实测真值。

选项比较：加密NOP网格不能识别资源；同时改依赖/锚点长度会增加码形与调度因素；本有限批先只扩立即数0，并保留NOP/非零立即数/寄存器MOV控制。依赖生命周期、锚点长度与唯一allocation单位仍按 `docs/open-items.md`后置触发，不能把“零值有效”直接升级容量结论。

## 软件与实际码形合同

计划最小扩展 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`：末尾追加class `mov0`，对应MOVZ X4..X11,#0；原七类编号、argv、生成码、输出形状和旧记录解析不变。MOVI仍MOVZ #1，MOVR源x16=0x1111；不要用XZR作为零值写入目的。新class在两gap轮转相同8dest，源、d0 fsqrt、loop/ABI寄存器不重叠。新mode/consumer拟为 `rob-zero-value`、`tools/diagnostic/rob_zero_analysis.py`，driver `tools/diagnostic/run_sm8650_minimal.py`；证据拟在 `docs/reviews/evidence/2026-10-11-rob-zero-value/`。以上是待实施路径，没有新binary或设备样本。不得覆盖历史build/plan/raw证据；旧模式在当前源变化后不能拿旧source SHA冒称新启动合格。

每epoch anchor{none,fsqrt}×N{0,128,256,704}×class{nop,movi,mov0,movr}交错，epoch1整体逆序，共64进程/192窗。i131072、rounds3、chain16、align0、FPCR0、CPU7/type8；六事件[11,08,3a,3b,816d,23]沿已完成控制资格，操作计数不作allocation分母。每gap N、每iter2N；程序继续fsqrt(1.0)稳定operand，不加入memory/THP或大足迹路线。

真实host导出逐config与独立A64字核对；同anchor/N下MOV0和MOVI的完整生成字节仅两gap共2N个MOVZ立即数字段bit5不同，N0代码完全一致；loop offset、branch、所有非filler字节不得变。实际NDK两次重建一致，独立解码全部64体、dest/source与两gap、branch/RET，并登记新binary source与launch分别的commit、source依赖/build/plan/driver/protocol/raw SHA。

## 接受与可推翻判据

技术接受先于统计：精确64条件与192轮次顺序、325 raw files、6个唯一kernel ID/typed uint64/正周期/no-mux、IR与生成码±max(1000,1%)、requested-realized、完整真实code/export/hash和环境策略。任一技术失败停整批，保留失败raw，不补格、不重试至过门。每进程固定1秒间隔，walt/既有policy，仅观察不改频率、温控、THP、全局PMU；初末及128 pre/post端点不能证明窗内恒频。

全部四类/两anchor/四N/两epoch，三窗和对各自N0有符号增量原值完整保存；rename/frontend比例>1命名cycle-semantics-incompatible，不作物理解释。每class/anchor/N的cycle与rename三窗range/median均保留，零中位但非零range为ambiguous。主检验仅fsqrt/N128 MOV0对MOVI：两个epoch分别MOVI rename/cycles中位≥.5且MOV0≤.1，并两组cycles/rename range/median≤.1（全零rename视为稳定），才称本输入“零值关联的rename响应下降”；同一N/anchor精确码字关系是前提。任一失败则无该限定资格，不调门。其它N仍完整报告，不事后从其中挑主点。

NONE/N128的MOV0/MOVI cycles中位比仅报告观察值及两epoch，不独立设elimination成功门。OP退休/执行密度仍只是所报操作响应；零值不出现rename停顿也不证明无PRF分配或已知ROB单位，含rename-full语义tap/前端/退休联动/跨进程VA和环境残差。即使满足下降门，也不能宣称MOV elimination全面认证、PRF容量或384 ROB；结论只限定值域关联。若未满足，官方列项在当前上下文不能解释旧资源差，优先同VA配对/依赖生命周期新控制，不无限加密NOP。

## 顺序实施与自审

已用brainstorming/writing-plans对三个候选、路径与门做自审；用户已有连续自主授权，没有新增人工例行关卡，不派子代理。按TDD/verification-before-completion顺序：

1. 真实C exporter测试先RED：`-t mov0`未支持；补class后GREEN，并核旧七类码字/配置无变化与MOV0/MOVI唯一bit差；先提交源并记实际source SHA。
2. 新consumer/driver完整实际plan→导出→写盘→回读正例，缺失/冲突/重复/乱序/typed identity/坏ID/IR/额外raw/来源/环境反例；仅外部执行/PMU/backing模拟。首个坏点必须停，移除守卫时测试应RED；历史driver测试明确用其真实启动版本，不能伪绑定旧commit。
3. 新NDK/source/build/plan/code registration、全量diagnostic/runner/analysis/CTest；已收口TLB/ROB六批完整raw重放无漂移。提交启动树才deploy/有限采样。
4. 直接JSONL第二算术路径逐192窗/64身份/325 SHA、全部判据与异常核对；公开匿名完整原值/图/报告、README/OI、本地范围提交。两条root算术路径不称另一独立评审人。

本文件仅设计出口，当前不计为新控制已完成。实施归当前端到端ROB负责人；真实TLB索引/descriptor控制与该设备采样串行，正式runner/schema/CMake及ALU/FPU、窗内clock沿既有归属/触发；本轮远程不操作。
