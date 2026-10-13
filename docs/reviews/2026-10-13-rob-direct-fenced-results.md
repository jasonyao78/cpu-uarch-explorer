# 同PC SB直接ROI发射资格结果

## 本次任务的目的（给人类看）

用长正控已合格的MRS路径检验8marker短窗，不把counter可读当marker已分离。协议 `docs/design/2026-10-13-rob-direct-fenced-marker.md`。

**DIRECT_FENCED_MARKER_NOT_QUALIFIED**：6/6fresh、1536/1536实际完整；全部six long64/currentindex/seq/绝对FD/原架构/词/PFN/IR通过，原校准门全部六process失败，不能Nscan。每process calibration/delta都在 `docs/reviews/evidence/2026-10-13-rob-direct-fenced/qualification-analysis.json`，完整原计数CSV，未挑K或换阈值。

每A near pre/post mean范围−2.15625..15.125，结构阴性near mean−3.8125..5.15625；far A1.28125..12.375，阴性−2.0625..2.4375；分位严重重叠、全部threshold=None，eligible=0表示校准未定义而不是没有发射，far|near=None。IR gates通过，绝对Icache计数仍报告；不是单位/供给/ROBentries。

新事实：sixevent own long64和1536绝对FD包含已验证；短8marker波动远大于信号，出现near±36/far±18等离散差。source `probes/diagnostic/rob_direct_fenced_marker.c` 的ROI包住 `roi_snapshot` 后半及下一snapshot前半，其中存在metadata/trace自身LDR/STR，这是源码确定事实；它对具体波动的贡献尚非唯一实证。下一**register-only内嵌snapshot**把metadata和内存trace移到ROI之外，既排除本路径访存，也避免用事后校准救门。

source `43e1def60eb8a5a4e1f9bc330aeb34d3e8a95aaa`、actual launch `231123f5e5c6509b16b4aea068f3cbbe74ae64b1`，branch `codex/sm8650-tlb-hierarchy-r2`，binary `aa3999573135a6dc7967fef5b2577ef267300d895b632e00cdcbd7f90e715078`；双NDK一致/actual8program与原JITwords一致和ELF读寄存器解码在对应build/plan/decode。原 `data/private/20261013T145811Z-rob-direct-fenced-marker` 库存38SHA逐文件重算、1536原ROI total/raw/FD第二算术。

hostperf_user_access0→1→0、state restored/readback0，frequency/governor未写，原pre/post quiet无违规。两新producer/guard局部测试过，不把此前708全回归当新source整树验证。后续另注册no-memory ROI，所有本批原失败和图形都保留。
