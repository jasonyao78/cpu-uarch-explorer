# 自有热ROI资源复核：完整矩阵通过

结论：**通过有限资源响应资格（REPEATABLE_FILLER_RESOURCE_EFFECT）**。16/16 fresh、4096/4096正式、16384/16384当前绑定warm完整，metadata invalid=0；IR同构、原I-cache中位≤1/q95≤4供给门、全部高剂量配对资源门通过。所有PMU事务恢复0。

branch `codex/sm8650-tlb-hierarchy-r2`；source `dc58c1690a73c04e22380bbf5fae5fb1e39923cf`；build/actual launch `27d4793354f1631bf31f034ff2316710dc1fc5e4`；binary SHA256 `b4e301930489bd868696a5fc7e300a51b6de3738524af9d68c9972e8759b86cf`；raw `data/private/20261013T183709Z-rob-filler-resource-bounded`。入口 `probes/diagnostic/rob_filler_resource_bounded.c`，consumer `tools/diagnostic/rob_filler_resource_bounded_analysis.py`，协议 `docs/design/2026-10-14-bounded-owned-roi-packets.md`。

| 配置 | NOP / sink / live / zero cycles中位（seed0） | sink−zero配对中位（seed0/1） | I-refill中位范围 |
|---|---|---|---|
| e0-c32-f0 | 226.0 / 226.0 / 226.0 / 226.0 | 0.0 / 0.0 | 0.0..0.0 |
| e0-c32-f4 | 228.0 / 238.0 / 235.0 / 228.0 | 8.0 / 6.0 | 0.0..0.0 |
| e0-c32-f8 | 230.0 / 264.0 / 263.5 / 230.0 | 34.0 / 32.0 | 0.0..0.0 |
| e0-c32-f12 | 244.0 / 304.0 / 307.0 / 244.0 | 60.0 / 60.5 | 0.0..0.0 |
| e0-c64-f0 | 258.0 / 258.0 / 258.0 / 258.0 | 0.0 / 0.0 | 0.0..0.0 |
| e0-c64-f4 | 259.5 / 273.5 / 272.5 / 259.5 | 13.0 / 10.5 | 0.0..0.0 |
| e0-c64-f8 | 262.0 / 310.0 / 327.0 / 262.0 | 46.0 / 90.0 | 0.0..0.0 |
| e0-c64-f12 | 290.0 / 421.5 / 420.0 / 290.0 | 131.5 / 86.0 | 0.0..0.0 |
| e1-c64-f12 | 290.0 / 418.5 / 420.5 / 290.0 | 127.5 / 131.0 | 0.0..0.0 |
| e1-c64-f8 | 262.0 / 326.0 / 327.0 / 262.0 | 64.0 / 64.5 | 0.0..0.0 |
| e1-c64-f4 | 260.0 / 282.5 / 273.0 / 259.0 | 21.5 / 3.0 | 0.0..0.0 |
| e1-c64-f0 | 258.0 / 258.0 / 258.0 / 258.0 | 0.0 / 0.0 | 0.0..0.0 |
| e1-c32-f12 | 244.0 / 306.0 / 306.0 / 244.0 | 61.0 / 59.0 | 0.0..0.0 |
| e1-c32-f8 | 230.0 / 262.0 / 262.0 / 230.0 | 29.0 / 32.0 | 0.0..0.0 |
| e1-c32-f4 | 228.0 / 240.0 / 239.0 / 228.0 | 9.0 / 5.0 | 0.0..0.0 |
| e1-c32-f0 | 226.0 / 226.0 / 226.0 / 226.0 | 0.0 / 0.0 | 0.0..0.0 |

两个chain、两个fresh epoch，filler8/12的8配置/16seed比较全部达到周期中位≥8且≥80%配对为正，未重新调整阈值。最终RX后warm+formal之间无内核read/getcpu往返，所有当前binding独立检查且共享真实绝对FD包络。程序结果checksum和结束SB使结果可见、计时有完成边界。

解释权限：可以说sink相对zero具有重复的资源响应，与live方向一致；不能唯一归因ALU端口、排除decode/rename差别，不能认证一个ADD对应一个ROB slot。OP/DP的逻辑单位反例仍有效。旧v1/v2供给失败及v3metadata首停不回救、不重新判通过。

软件完整度：实际native16计划/64程序、ABI/分支/无x18/动态index配方及NDK双构建；生产plan缺失/冲突/重复/乱序、成对trial31/32测试和旧实际N0算术软件projection检查已完成。metadata预算只准1/256固定ordinal，无retry/补样/指标挑点，本批没有用到该配额。新局部19项测试通过；原整树715回归只覆盖旧58b7128，不冒称覆盖本轮全部代码。

下一：`docs/design/2026-10-14-rob-admission-window.md` v1.2先12个N0→72扫描点，窗口范围与物理entries分列；独立最老cold load路线 `docs/design/2026-10-14-rob-cold-head-qualification.md` 已冻结、尚未实现/采样。L1i48/d96已实测；共享L2有效leaf/setway独立证据及物理ROB仍OPEN。
