# admission v1.2：N0供给门停止，未扫描

结论：**原协议不通过（ADMISSION_N0_NOT_QUALIFIED）**，第7个N0因I-cache尾部失败。7×256=1792正式、7168warm完成，invalid0；no nonzero gap调用，全部事务恢复0。旧批不晋升。

branch `codex/sm8650-tlb-hierarchy-r2`；source `27d4793354f1631bf31f034ff2316710dc1fc5e4`；build/actual launch `a1b4916a86d7bd44e0e77b1751e8a6d8883bd8f1`；binary `21c6c4184eab0d36f31cae960d17d829a707765631c67b2c384a4851f9808077`；raw `data/private/20261013T184409Z-rob-admission-window`。

| 配置 | 原classification | eligible | far|near | supply |
|---|---|---|---|---|
| e0-k16-sink-n0 | reached | 27 | 1.0 | True |
| e0-k16-zero-n0 | reached | 28 | 1.0 | True |
| e0-k16-nop-n0 | reached | 28 | 1.0 | True |
| e0-k32-sink-n0 | reached | 21 | 1.0 | True |
| e0-k32-zero-n0 | reached | 19 | 1.0 | True |
| e0-k32-nop-n0 | reached | 21 | 1.0 | True |
| e1-k32-nop-n0 | SUPPLY_NOT_QUALIFIED | 22 | 1.0 | False |

第7个e1-k32-nop-n0的Apre/Apost近/远均8，Mpre均0，IR全通过，eligible22/32，far|near1。Mpost-nop三个窗口I-refill9..11，中位0而95分位越过4；同角色taps中位0、q95≤4。不能单独把aggregate refill归到payload的PC，也不能据此直接证明前端不是容量混淆。

新v1.3另行冻结采集权限与推断权限：全部12个N0标记+硬完整度资格才采72点，absolute supply失败仍保留；新结果response只叫观察范围，供给失败曲线原classification/INCOMPUTABLE保留，物理ROB仍须独立cold-head/PRF/packing反证。原本批保持失败，不用新collection gate回救；新raw另目录独立source/build/launch绑定。
