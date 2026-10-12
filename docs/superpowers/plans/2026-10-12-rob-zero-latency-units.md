# 零延迟MOV单位控制 Implementation Plan

## 本次任务的目的（给人类看）

按 `docs/design/2026-10-12-rob-zero-latency-units.md` 建立不含ALU执行工作的新类，对NOP fusion资格/两链长共同边界作有限检验，保留旧不合格组。

**Goal:** 先验证192资格，过后2352有限扫描；所有实际分配/物理entries声明仍保留未认证。
**Architecture:** 新独立C/consumer/driver模式，复用纯rob_codegen/GROUP，独立MOV opcode/Rd/返回oracle；1048576 warm/measure统一窗口和15秒固定间隔。
**Tech Stack:** C/NDK27.2/API34/Python unittest/Capstone/adb；primary串行，不再交给旧上板Agent。

- [x] `tools/diagnostic/tests/test_rob_zero_units.py` 先RED：新producer缺失；真实288plan，MOV live Rd/imm0/return与NONE chain code共享；相对α模型/删失/非单调/供给失败/typed等旧控制反例保留，不能把synthetic384当target。
- [x] 新 `probes/diagnostic/rob_zero_latency_units.c` / `tools/diagnostic/rob_zero_units_analysis.py` / `tools/diagnostic/run_sm8650_rob_zero_units.py`，同步8倍iteration IR公式、live0 checksum及新的固定matrix，旧C与consumer不动；GREEN后source commit。
- [x] 双NDK/actual 288plan/144 independent Capstone与FP/GPR返回捕获审计，recipe/source/plan/binary SHA输出到 `docs/reviews/evidence/2026-10-12-rob-zero-latency-units/`，source/build分开。
- [x] `tools/diagnostic/tests/test_rob_zero_units_raw.py` 真计划→driver→写盘→审计两阶段正例/重哈希反例；旧模式、未合格/错误qualification SHA/binary不能扫描；整树diagnostic一次验收本轮两TLB+ROB新代码，再冻结launch。
- [x] 等TLB full块完成后串行192资格；合格再2352扫描，不合格禁止；目标数据独立复算每窗/每gate/曲线及common proxy，完整raw/signed effects保留，更新结果/目标ledger/README/open-items和授权记忆，不宣告physical参数完成。
