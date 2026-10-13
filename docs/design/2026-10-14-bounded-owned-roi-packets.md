# 自有ROI有限metadata失效契约 v1.0

## 本次任务的目的（给人类看）

偶发上下文切换可使一次ROI前后metadata改变，必须丢弃该次计数，但不必使整个预注册矩阵永久无法完成。原v3首失效停的2581正式/10324warm保持失败，不复评分。新采样固定256个ordinal，每process最多1个**完整packet**因明确ROI-metadata-changed命名拒绝；4warm+1formal中的任意一个失效均使packet无正式统计。无重试、补样、动态indices修复、指标筛选。其它错误（包括index改变、cap/index0、SIGILL、FD/架构、环境、写失败）仍立即终止；第2个metadata失效亦终止。

producer probes/diagnostic/rob_filler_resource_bounded.c 与 probes/diagnostic/rob_admission_window.c；共享packet消费 tools/diagnostic/owned_roi_packets.py；资源消费 tools/diagnostic/rob_filler_resource_bounded_analysis.py；窗口消费 tools/diagnostic/rob_admission_window_analysis.py；执行 tools/diagnostic/run_sm8650_rob_filler_resource_bounded.py 与 tools/diagnostic/run_sm8650_rob_admission_window.py。

每次真实current metadata核验仍不可省，失效返回时仅ROI-metadata-changed保持FD enabled以便下一个固定ordinal重新验证；若compiled index不再是当前自己的index则立即拒绝。所有partial successful warm原始hardware/metadata/checksum与共同FD包络保留，但失败packet任何warm/正式不进入统计。rejected-window带trial/position/stage及捕获raw字，metrics={}且hardware_values_usable=false；invalid-packet带相同身份和failure原因、completed_warm数量，不填0。final报告attempted256、valid255/256、invalid0/1，全ordinal必须恰好被valid或invalid覆盖。

消费者按实际native plan (trial,position) 对齐，不按输入顺序覆盖；未知/重复/冲突/缺失identity均拒绝。valid必须4个warm ordinal0..3+1formal；invalid恰1个匹配拒绝trace，允许0..4个已完成warm，全部审计但不进估计。partial warm不能被静默丢失。支持原始measurement rows乱序但结果不变，未知records不允许。

成对比较使用两角色同时存在的trial交集，每对至少31/32。原均值/分位/分离阈值、IR、供给门、near eligible≥8、far|near≥.9等不改；输出有效trial数，禁止把缺失zero-impute，门不满足命名拒绝。资源16进程及admission84矩阵/N0优先顺序不变，完整度口径改为所有256attempt齐、255/256或256/256有效；仍需资源复核/N0资格才正式扫描。

实施先以实际native --plan生成身份测试缺失/重复/冲突/乱序及invalid闭环，验证失败后实现；真实旧private clean数据仅作软件replay，不宣称新硬件结果。新NDK双构建/真实ISA及ABI/source-build-launch-raw SHA冻结，首板保留全部attempt再独立audit。temporary PMU访问仍0→1→0并durable finally/readback恢复。
