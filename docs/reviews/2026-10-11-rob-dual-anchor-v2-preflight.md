# 双独立锚点v2软件出口（2026-10-11）

## 本次任务的目的（给人类看）

只修订空循环哨兵的信号尺度口径，不改producer/二进制/非零NOP稳定门，不晋升v1失败数据。冻结 `docs/design/2026-10-11-rob-dual-anchor-v2.md`；旧 `docs/reviews/2026-10-11-rob-dual-anchor-v1-results.md` 的144窗not-qualified与扫描未执行保持不变。

**v2软件出口通过；允许fresh18进程资格块，完整90进程扫描仍必须实测资格通过。** 工作树r2、branch `codex/sm8650-tlb-hierarchy-r2`。

- 真实未改C producer→新消费/driver→writer→raw两阶段：15/15，`/tmp/rob-dual-v2-pipeline.log`。PMU/adb替身是mock证据，不当设备实测。
- 独立v2模块缺失时RED 8项失败；GREEN覆盖N0相对自身不稳但绝对信号噪声小、新绝对噪声精确边界（多一个计数即拒绝）、非零NOP原门、旧mode拒绝、不合格资格拒扫、typed/缺失/重复/乱序/bit/ID/mux/VA/IR以及重算SHA后仍拒的反例。原v1完整测试同时保留。
- full diagnostic343/343，167.986s，`/tmp/rob-dual-v2-full-regression.log`；本轮正式runner203/analysis250/CTest21已实跑，本批未改这些组件。
- source0d5ac032bb6d37a930b7aef56d2b19aa24c7e750，v2consumer/build f685c8a3fc7b36dbf4722b0afb4c90e18b91322b，actual launch另记。NDK两次byte-identical证据和30程序/60plan完整解码沿用未变源码/二进制；SHA7cb9bdefee5efb833565f038361777108805c22d844d7f93bd58db905f1aa99f，重建不会提供额外证据。
- v2精确路径 `tools/diagnostic/rob_dual_v2_analysis.py`、`tools/diagnostic/run_sm8650_rob_dual_v2.py`，build/plan/code-audit/result-capture/check_raw/plot均 `docs/reviews/evidence/2026-10-11-rob-dual-anchor-v2/`。driver和raw consumer共同强制v2完整资格raw、同binary与manifestSHA；完整扫描自带fresh参考，不拼接资格窗。

硬件采样尚未发生时冻结；raw/private与全console保留不入库，无环境写入、无并行设备代理、无main/远端操作。物理ROB单位/活跃约束仍未校准，任何新曲线都不自动命名entries。
