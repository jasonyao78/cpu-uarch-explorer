# ROB filler 单位与ADD sink语义资格 v1.0

## 本次任务的目的（给人类看）

register-only marker已6/6/1536通过，但marker不是ROB slot标尺。先用真实OP_RETIRED(0x3a)、OP_SPEC(0x3b)、DP_SPEC(0x73)检测ADD XZR是否实际执行、每条增加多少执行µop；对照NOP（官方NOP+Any fusion）、ADD live、zero MOV（官方零延迟）避免用NOP数硬换entry。原配对发射资格不重判。

producer `probes/diagnostic/rob_sink_unit.c`，consumer `tools/diagnostic/rob_sink_unit_analysis.py`，controller `tools/diagnostic/run_sm8650_rob_sink_unit.py`，register-before/after及ABI/SB/warm无MRS同 `probes/diagnostic/rob_register_fenced_marker.c`。events固定[17,8,58,59,115,1] USER/type8/long64/pinned，OP两项/DP官方支持但必须actual正控，不以open成功为语义支持。

3fresh×count16/32=6process，每32trial×2seed×4role=256窗，共1536；role=nop/sink/live/zero，samecodeVA/PFN/ownindex/warm-PC，seed0/1只是返回bit输入、不代表wrongpath。源模板ADD XZR,X1,X2，live同操作到X9，zero MOV X9,#0，NOP单词；输入X1/X2是当前own两个映射base，输出checksum live=(X1+X2)mod2^64，其余0，return原bit。初始X9清零与输出STR恒定，跨count取差消去observer/输出固定µops；4role等长，原实际word核验。

先全current own metadata/FD/ABI/checksum/actualword完整。每process每seed的sink−nop DP_SPEC中位须count±1且至少30/32差在count±2；live对应同；zero−nop DP增量完整报告，不先假定0。每epoch每seed跨count16→32，sink/live IR增量16±1、OP_RETIRED增量16±1、DP增量16±1（每条1执行µop尺度）；OP_SPEC保留参考，不与allocation混用。所有配对pass才SINK_EXECUTED_ONE_UOP_QUALIFIED，否则命名UNQUALIFIED/MODEL_UNIDENTIFIABLE，不能Nscan/调门。NOP/zero斜率全部报告，没有预测精确allocation。

注册总预算/no retry/首metadata/CPU/FD/能力失败停；metric若不合格仍完整采完六process。不判PRF-free硬件实现/ROB每µop一slot，只资格化候选filler与尺度。后续冷load+两独立deadline+live/PRF/supply反证另冻结，不给384拟合；当前阶段只软件/硬件µops证据。group0→1→0 perf_user_access write-ahead/finally恢复，双journal终态/quiet/单操作者同前，15sec间隔。原raw/private/SHA保留，public无真实地址；diagnostic JSONL不是formal baseline。
