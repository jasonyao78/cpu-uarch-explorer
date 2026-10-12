# ROB退休边界资格 Implementation Plan

## 本次任务的目的（给人类看）

执行 `docs/design/2026-10-12-rob-retirement-drain-next.md` v1.0，仅384窗新资格，不做capacity scan。

**Goal:** 实际MRS mode/原FP结果捕获和数据重置，独立reference资格。
**Architecture:** newC/consumer/driver，复用pure rob_codegen/GROUP，不修改旧探针；每mode单独命名资格。
**Tech Stack:** C/NDK27.2/API34/Capstone/Python/adb；primary串行。

- [x] 实际producer计划缺失RED；创建 `probes/diagnostic/rob_fp_drain.c`，native计划覆盖32含reverse、真实唯一sysreg差、结果捕获先于reset、IR/branch/loop alignment金样GREEN；不把software opcode当实际分配。
- [x] `tools/diagnostic/rob_drain_analysis.py` / `tools/diagnostic/run_sm8650_rob_drain.py`，实际plan→driver→writer→raw入口；typed/缺失/重复/顺序/IR/结果/模式负控、每mode不同资格反例、不合格不scan。
- [x] 双NDK/实际32计划/独立Capstone和ASMoracle，source/plan/binary证据；相关新旧生产链回归后冻结launch，设备idle/unfinished0与全基线再384窗。
- [x] raw第二算术核验资格和全部aux事件，更新报告/目标账/README/open-items及授权记忆，physicalROB allocation仍OPEN。
