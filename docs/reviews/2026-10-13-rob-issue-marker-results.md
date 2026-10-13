# ROB近端／远端发射资格：采样完整，资格未通过

## 本次任务的目的（给人类看）

为ROB容量建立“分支后发射但未退休”的观察手段。`docs/design/2026-10-13-rob-issue-marker.md` 的独立A/B校准不允许用M挑阈值；本轮只N0。

**结论：ISSUE_MARKER_NOT_QUALIFIED，不启动N扫描。** 六process864窗技术完成，A正控两个事件均约8，证明LD_SPEC/ST_SPEC可观察自有操作；但训练为taken的B虽架构绕过、内存不改，仍有明显推测计数。B不是可靠“没有发射”阴性，A/B q10/q90重叠，near/far阈值全部不可定义。0 eligible是阈值不可定义后的命名状态，绝不是零推测发射。

|process|A近／远均值|B近／远均值|A q10 / B q90（两tap）|I-cache匹配增量门|训练方向门|
|---|---|---|---|---|---|
|e0-k16|8.083/8.125|4.667/4.667|8.0/8.0|False|False|
|e0-k32|8.000/8.000|4.417/4.292|8.0/8.0|False|False|
|e1-k32|8.083/8.125|3.000/2.833|8.0/8.0|False|True|
|e1-k16|7.833/7.750|1.500/1.417|8.0/8.0|False|True|
|e2-k16|7.833/7.750|4.917/5.042|8.0/8.0|True|False|
|e2-k32|8.167/7.917|2.750/2.792|8.0/8.0|True|True|

所有864条原bits/FPSR/near与far8字架构状态正确，所有control IR配对均值门通过；各process绝对L1I范围0到9–29，匹配增量门4/6失败，不能据此认证完整前端无瓶颈。计数仍有包络噪声，未clip、未按结果删窗。记录全部保留；30rawSHA，独立原始JSONL逐对复算6事件差分、全864架构状态及A/B均值/分位数。公共 evidence `docs/reviews/evidence/2026-10-13-rob-issue-marker/qualification-analysis.json` / `qualification-independent-check.json` / `qualification-windows.csv`。

## 解释和下一反证

“architecturally bypassed”不等于“没有推测执行”；predictor训练不能当不执行的结构性保证。当前B差值可能由fall-through transient、分支训练／识别、代码改写准备或包络影响共同贡献，未做PC采样不能唯一归因。不能事后让B正信号变成通过标准、不能用A/M阈值替A/B救资格。旧648/1536窗失败保持终态。

下一候选：在同一个错误路径、相同分支PC／bits／训练下，交换marker前后的SB与NOP位置，用pre-tap SB构造结构性阴性，再与post-tap SB比较；保留自身架构不退休检查及实际事件正控。它需要新协议、新源码／冻结／N0，不是重跑本协议。即使该资格通过，deadline/supply/资源与MCQ allocation单位仍需正交控制，不会自动得到384。

## 源码与提交谱系

branch `codex/sm8650-tlb-hierarchy-r2`；C/consumer/driver source `401086c`；build `8f2aed8`；实际launch `b28f7f672c6087d0b08f06c8e4328851ea328c29`；二进制SHA `17afa2a459877a05e90271c13a382d05c32811d257318b5a2939fe87f813c36f`。NDK27.2/API34/O2/static双构建相同、两个实际C计划、四套Capstone解码，15生产链测试全部通过（counter软件夹具，不冒称上板）；组件 `probes/diagnostic/rob_issue_marker.c`、`tools/diagnostic/rob_issue_marker_analysis.py`、`run_sm8650_rob_issue_marker.py`。private `data/private/20261013T094844Z-rob-issue-marker-qualification`；CPU端点温度[39.3, 41.9]°C，环境/计数技术门完整；未改全局环境，无journal。完整diagnostic回归尚运行，另交证据后才报告通过。

完整diagnostic回归终态：647/647通过579.112秒，源码b28f7f6；记录 `docs/reviews/evidence/2026-10-13-rob-issue-marker/regression.json`，不包括随后新增SB对照模块。早先错误-t发现入口未执行测试，不算回归失败或通过。formal runner/analysis/CTest路径未改，本轮未重跑。
