# ROB两deadline/三filler完整粗矩阵

结论：**探索矩阵完成，物理ROB尚未确定**。84/84 fresh配置、21504/21504正式、86016/86016 current-binding warm、invalid0、所有技术/架构/FD完整度通过；12个N0 marker-observable均通过。两epoch、chain16/32复制三种不同响应范围。部分strict供给门失败仍INCOMPUTABLE，未使用探索权限晋升容量。

branch `codex/sm8650-tlb-hierarchy-r2`；source `c046ed7314a64b37fc84f93fc9eb0d162e94f8ab`；build/actual launch `0ae447c8a1ae3cb85a090a54dcd22d2878e116a0`；binary SHA256 `21c6c4184eab0d36f31cae960d17d829a707765631c67b2c384a4851f9808077`；raw `data/private/20261013T185437Z-rob-admission-window`；source `probes/diagnostic/rob_admission_window.c` / consumer `tools/diagnostic/rob_admission_window_analysis.py` / protocol `docs/design/2026-10-14-rob-admission-window.md` v1.3。全部事务restore0。

| epoch | chain | filler | strict curve | observed last reached / first blocked |
|---|---|---|---|---|
| 0 | 16 | sink | INCOMPUTABLE | 128 / 256 |
| 0 | 16 | zero | bracketed | 256 / 384 |
| 0 | 16 | nop | INCOMPUTABLE | 640 / 768 |
| 0 | 32 | sink | bracketed | 128 / 256 |
| 0 | 32 | zero | bracketed | 256 / 384 |
| 0 | 32 | nop | bracketed | 640 / 768 |
| 1 | 16 | sink | bracketed | 128 / 256 |
| 1 | 16 | zero | INCOMPUTABLE | 256 / 384 |
| 1 | 16 | nop | bracketed | 640 / 768 |
| 1 | 32 | sink | bracketed | 128 / 256 |
| 1 | 32 | zero | bracketed | 256 / 384 |
| 1 | 32 | nop | bracketed | 640 / 768 |

供给失败点：e0-k16-sink-n384, e0-k16-nop-n256, e1-k16-zero-n128。完整原计数、paired trial差分、反例以及原资格全部公开在 `matrix-summary.json` / `formal-windows.csv`，无数据删除或clipping；raw SHA对应全部私有输入、source/build各依赖blob核验。

事实与推断：两倍FP链长度没有使粗网格响应区间改变，说明单纯deadline解释不足；ADD sink、MOVzero、NOP之间明显差异推翻per-ISA等价filler解释。零MOV和NOP响应与官方NOP+Any fusion/zero-latency资源语义相容，但不能仅NOP/2命名entries；sink较早转折可以由其它资源/分配行为解释。未证明actualfusion单位、退休占用或精确ROB，不选择靠近第三方384的数据拟合。

因此下一步是独立最老cold LDR头（1/2个serial head、issue/cache两个palette、hot/cold）N0资格，软件/构建已交付并串行上板；冻结 `docs/design/2026-10-14-rob-cold-head-qualification.md`。它移除FP链可逐条退休及FP资源混淆，成立后才精扫与packing/PRF/取指控制；科学目标保持完整。

软件回归：727/727、623.629s覆盖至0ae447c的bounded/admission v1.3，cold-head2额外测试和实际NDK/native/decode另过；formal runner/analysis/CTest本轮未改未重跑。一级TLB i48/d96已实测；共享L2官方2048/256×8已核验，独立leaf/selector及ROB物理容量继续研究。
