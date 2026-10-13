# ADD sink 单位正控：计数标尺不等于分配标尺

## 本次任务的目的（给人类看）

在register-only issue已经通过后，检验NOP/ADD sink/live/zero执行计数能否给ROB单位。协议 `docs/design/2026-10-14-rob-sink-unit.md`；producer `probes/diagnostic/rob_sink_unit.c`、consumer `tools/diagnostic/rob_sink_unit_analysis.py`、controller `tools/diagnostic/run_sm8650_rob_sink_unit.py`。

**SINK_UNIT_NOT_QUALIFIED，6/6fresh、1536/1536完整**。所有原scope/FD/metadata/ISA/checksum通过；DP sink−NOP预注册“count±1”失败，实际所有trial为0。不是unsupported/all-zero：N16各类DP中位35，N32=51；IR43→59、OP_RETIRED43→59、OP_SPEC42→58，各四类都同样+16。raw斜率里的 `executed_one_uop=true` 只表示per-count计数增量条件通过，不能越过总失败说硬件执行/分配单位认证；ROBallocation=false。

重要反例：官方优化guide明确NOP+Any fusion、zero MOV不消耗调度/执行资源，然而这些OP/DP事件仍将本Nop/zero/sink/live每ISA一份计数。**OP_RETIRED/OP_SPEC/DP_SPEC本对照不能区分融合/消除后的真实调度/ROB分配**。不要把sum值正确的live ADD当成全部sink都执行或一份计数=一条ROB entry。参考原文 `Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf` §4.11/4.12（全局知识库 `/Users/michaelyao/workspace/cpu-uarch-ref/docs/`），匹配r0p1 TRM §18 的0x3a/3b/73语义。

计数已表明逻辑统计尺度，但cycle+4/16等差不能直接做ALU/容量推断：本单位模板pure body末尾到after计数之前未加完成型workload边界，cycle可与独立work重叠。后续visible依赖链+明确完成边界+同ISA zero/nop资源竞争、实际packing/admission对照需要另注册。不能重打旧DP门，不能用失败标尺启动物理ROB扫描。

source `43b1a539d6ffa90277b6b3542f69d2881007d095`、actual launch `4331ac67a9696cb76a437456010b409ceba7f8d8`、branch `codex/sm8650-tlb-hierarchy-r2`；binary `9d4dd3bb40cb11cba97ba3dba974c7cbb0566f0d77427092580c565868f66a0d`，双NDK/actual16 proposed programs及palette注册。全1536原total/FD第二算术、库存38SHA复算；公开 `docs/reviews/evidence/2026-10-14-rob-sink-unit/qualification-analysis.json` 和全窗CSV，原 `data/private/20261013T170928Z-rob-sink-unit` 未裁剪。host perf0→1→0/restored/readback0，频率/governor未写，原quiet全部无违例。局部两新tests通过；不能蹭历史708整树。

下一路径：先用有可观察最终结果的依赖链测候选sink相对zero/nop的资源竞争（模板count16/32微op计数非资源证书），再用冷load阻塞、独立deadline及打包/PRF/supply反证定位有效退休窗口。物理384仍第三方候选，未确认；整体持续目标active，有限反例不是全目标结束。
