# 寄存器内计数的SB发射资格结果（10/13冻结，10/14完成）

## 本次任务的目的（给人类看）

检验observer自身访存能否移出短ROI，原8marker/A/Mpre分离门不改；不是ROB容量扫描。协议 `docs/design/2026-10-13-rob-register-fenced-marker.md`，producer `probes/diagnostic/rob_register_fenced_marker.c`，consumer `tools/diagnostic/rob_register_fenced_analysis.py`，controller `tools/diagnostic/run_sm8650_rob_register_fenced.py`。

**REGISTER_FENCED_MARKER_QUALIFIED，6/6fresh、1536/1536原窗口，全部原门通过。** 关键区别是六before/六after值在GPR中保存，metadata在JIT之外，ABI及timestamp写回有两端SB隔离，不能靠程序顺序假设OOO不会提前访存。全部Apre/Apost LD/ST增量精确8；全部Mpre精确0；threshold near/far=4。Mpost每trial为0或8，eligible比例37.5%–78.125%，所有六process **far|near=1.0**，未激励trial如实保留。

完整原1536窗/库存38SHA复算，直接原total/raw/FD第二算术，current6own long64/seq/index/offset、runtime own indices与实际生成words、ABI/无observer memory/原body相对目标/PFN/架构结果均通过。真实own-index的所有2种chain/context又用native实际producer重放，不能把blueprint32/3等当手机索引证据。公开 `docs/reviews/evidence/2026-10-13-rob-register-fenced/qualification-analysis.json`、全窗CSV；原 `data/private/20261013T164301Z-rob-register-fenced-marker` 不裁剪。

source `933776faec5c7c6858382ace077c35fb2e8b2410`、actual launch `f8cabd926b701887fd2563885a55004859a3327b`，branch `codex/sm8650-tlb-hierarchy-r2`；binary `d549740db4d4a37533afa3d51ebf6f9a98243e39304731ebee0fbdeca1231580`，两个NDK一致，16 proposed dynamic programs解码/ABI assembler参考在对应build/decode，actual设备contexts另记录。proposed nativecontext只是recipe测试，run不允许indices override。

prototype上板前warm suffix硬编码错误由回归挡住，已按actual长度−36修；x18的十六进制偏移误判改成实际regs-access检查，未登记build的预检拒绝也保留终端证据，无该次设备测量/设置修改。

root profile只perf_user_access0→1→0，journal restored/readback0，全部pre/post quiet-state无违规；FD/maps关闭，无频率/governor写入。两旧失败（C ROI1536、原SB1536）不回救。此前708全回归截至bounded代码，新register3+direct2局部测试通过；后续新code不能蹭708。

**边界**：近端证明被激励，远端证明错误路径存储发射；没有给实际ROB占用/条目标尺/供给唯一性证书。observer虽无访存仍有指令/寄存器/屏障开销，必须进入后续模型。下一优先OP_RETIRED/OP_SPEC/DP_SPEC正控资格化非fusion ADD sink、区分PRF/单位；再用single cold-load及独立deadline做容量，而非把FPchain g+chain硬凑384。
