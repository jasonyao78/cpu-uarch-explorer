# 最终可执行配方下的资源对照 v2.0

## 本次任务的目的（给人类看）

v1完整4096窗有 sink−zero 周期响应，但非空 filler 的 L1I_REFILL 中位4..27，违反供给门。旧数据不复评分。本版只改变预热接线，不改事件、矩阵、阈值、资源判断或归因范围。原协议 docs/design/2026-10-14-rob-filler-resource.md 所有判据沿用。

producer probes/diagnostic/rob_filler_resource_hot.c；consumer tools/diagnostic/rob_filler_resource_hot_analysis.py；controller tools/diagnostic/run_sm8650_rob_filler_resource_hot.py。沿用64次无PMU的同VA warm-image训练；完成measured-image最后一次RW→RX之后，再执行4次**当前自有ROI**的训练输入调用，然后唯一正式调用。两者间无mprotect/clear-cache/代码写入。每个warm也逐次before/after检查own metadata/index/width/seqlock/offset/SIGILL、绝对FD包络、架构校验；不许可无当前metadata的PMU访问。

4×256×16=16384个warm ROI，单独type=warm-roi记录，包含ordinal、原始hardware/meta/FD/checksum。正式4096窗分开消费，不把warm纳入统计或挑温度/指标。每组固定4warm→1正式，任何warm技术失败立即停止，finally恢复0。纯热/冷干预不改变payload ISA、代码VA/PFN、架构输入或原生配方；配置明确post-RX-owned-ROI。结果若refill降到原门内而资源差仍在，说明之前供给污染已受控制；未降低则保留SUPPLY_NOT_QUALIFIED。不把热程序有效资源响应自动晋升ROB单位。

实施：先实际producer缺失测试；实现与native独立配方及warm消费、缺失/冲突反例；源码提交；NDK双构建与真实解码、构建提交；16个fresh正式进程；全部原样证据及0→1→0恢复。admission v1大扫描暂不执行，完成这个接缝修复后同步采用同样最终RX预热，需新源码/协议/构建。
