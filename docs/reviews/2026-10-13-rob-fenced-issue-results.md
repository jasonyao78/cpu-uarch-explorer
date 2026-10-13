# ROB同错路SB结构阴性：chain16复制通过，完整资格未通过

## 本次任务的目的（给人类看）

用marker前SB构造真正结构性阴性，和相同错误路径的marker后SB比较，修正“训练一定能阻止推测”的错误前提。冻结 `docs/design/2026-10-13-rob-fenced-issue-marker.md`，六process1536窗。

**整体FENCED_ISSUE_MARKER_NOT_QUALIFIED，不N扫描。** chain16三个独立process全部通过原冻结门：pre结构阴性接近0、post近／远响应率均100%，原bits/FPSR/near/far架构检查保持未退休。chain32近端可分、post near 31–32/32 responsive；但far的A q10=5、M-pre q90=3，gap2小于冻结4，阈值无法定义。不能只保留chain16作为整协议通过。

|process|near threshold|far threshold|near eligible|far conditional rate|原冻结结果|
|---|---:|---|---|---|---|
|e0-k16|3.0|2.5|32/32|1.0|通过|
|e0-k32|4.0|None|32/32|None|不通过|
|e1-k32|4.0|None|32/32|None|不通过|
|e1-k16|3.0|2.5|32/32|1.0|通过|
|e2-k16|3.0|2.5|32/32|1.0|通过|
|e2-k32|4.0|None|31/32|None|不通过|

未知far率显示None，不写0：f2f4f12修复了消费报告的缺陷，实际生产形态反例先复现0错误，再通过12项回归；不改变原门或整体不通过。数据采集consumer仍按launch谱系保存；独立分析版本与SHA另登记，原source/raw不重写。

1536/1536原始窗、全部六PMU ID/time/CPU/code/PFN端点技术门和自身架构状态合格，30rawSHA；逐对独立原始JSONL复算4control/fence×6事件以及所有结果/均值/分位数。全窗口含空／负差保留，无clip，无选择某些trial补格。公共 `docs/reviews/evidence/2026-10-13-rob-fenced-issue-marker/qualification-analysis.json` / `qualification-independent-check.json` / `qualification-windows.csv`。

## 已取得与尚缺的证据

与旧864窗的prediction-only阴性相比，pre-SB使两个事件阴性均值回到约0，支持其作为发射观察的结构干预；“所有错误路径都没有被激励”已不符合chain16结果。这是已测事实，不是ROB容量或allocation单位。每process Icache绝对范围0到2–41，全部披露，本N0不认证前端供给，不回救旧失败I门。chain32尾部带约2load/3store差，短窗包络／PMU流水等是候选而非唯一归因。匹配r0p1 TRM §18（印刷页128）明确短时间enable时pipeline计数变化不能忽略，出处 `docs/reviews/2026-10-13-x4-r0p1-source-audit.md`。

下一措施先改可观测性：Linux perf用户读取需sysctl+config1+mmap seqlock，官方内核文档 https://www.kernel.org/doc/html/v6.16/arch/arm64/perf.html ，版本仅方法参考，目标实际内核另验。2026-10-13只读目标perf_user_access=0，未修改；不能未经map capability就MRS、不猜counter index。不支持则另冻批量信号放大，目标是减少端点误差；本资格不重跑追门，不自调阈值，allocation/deadline/资源/单位仍另注册。

## 源码与提交谱系

branch `codex/sm8650-tlb-hierarchy-r2`；binary source4d3964d/builda1e6e10，实际launch `9debbfb498c484df796bf70758ab65b0c2941674`；binary SHA `df2028f76023f86534234f72efb561c621f5954968d1e13ae8f295de53d88ea8`；analysis fix `f2f4f12be0f69aa3bb372a545675739076f344ef`。NDK27.2/API34双构建相同、8套实际动态程序独立解码，原11生产链／修复后12测试通过；此前完整647回归不包含本新模块，不冒称全树本轮647覆盖。组件 `probes/diagnostic/rob_fenced_issue_marker.c`、`tools/diagnostic/rob_fenced_issue_analysis.py`、`run_sm8650_rob_fenced_issue.py`；private `data/private/20261013T102104Z-rob-fenced-issue-marker-qualification`；端点CPU温度[38.8, 43.0]°C，no journal／全局环境无改。
