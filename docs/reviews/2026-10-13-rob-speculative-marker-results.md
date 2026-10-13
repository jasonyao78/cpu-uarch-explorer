# ROB延迟分支单marker N0：不通过（2026-10-13）

## 本次任务的目的（给人类看）

先确认退休受阻的年轻marker能执行而不能退休，作为容量实验的前提。冻结合同 `docs/design/2026-10-13-rob-speculative-marker.md` v1.0.2；没有filler/容量扫描。

**技术链通过；科学资格不通过，终态 MARKER_NOT_QUALIFIED。** 六fresh进程、648/648窗口完整、七事件唯一ID/无MUX/原bits/FPSR/code/PFN/环境端点全部通过。原冻结信号门失败，不降门、不重跑追门、不晋升容量。

| 问题 | 实际事实 | 裁定 |
|---|---|---|
| 退休tap | 648/648的0x06原值为0；A架构load−NOP也为0 | 该tap不能证明退休对照 |
| SPEC增量 | A均值[.556,1.0]；M[.667,1.111]；B[-.333,.333] | 原单次1-count门不能全部通过 |
| direction | 4/6进程过；两进程NOP/bypass branchmiss median1 | 不靠选择process晋升 |
| 取指背景 | 648/648原门失败，每窗2–10 refill | 原每窗≤1资格无效，不把它改成≤10 |

根因的一项已由公开资料定位：本地官方 `/Users/michaelyao/workspace/cpu-uarch-ref/docs/Arm_Cortex_X4_Core_TRM_102484_0003_06_en.pdf` r0p3的PMCEID0.ID6=0、事件实现表也无LD_RETIRED。目标r0p1与资料revision分列；实际A正控证明目标本次该事件没有可用响应。perf raw open/read成功不等于事件implemented或语义合格。**设计预审漏了该表，是作者遗漏；不能归为芯片退休失败。** 对取指/LD_SPEC背景尚无唯一根因：计数窗口包含用户态ioctl wrapper及供给/分支历史，不能把上述噪声直接叫ROB响应。

## 原始谱系与独立复核

branch `codex/sm8650-tlb-hierarchy-r2`；source `973baf4`（C首次94bb46e，实际依赖修正7fff70b）；build `937f007`；actual launch `b8ef9c4fc1592b20322e984134e9e120ee4f490c`；binary SHA256 `8297d72672cf48133d50f439e5963b9b374a244496fd85e517dcce3e06ae7b30`。NDK27.2/API34/O2/static两次字节一致；两actual host plans、四program独立Capstone CBZ/B/SB解码、15producer→driver→writer→immutable raw测试通过。模拟PMU仅软件回归，表中数值才是目标实测。

private `data/private/20261013T040732Z-rob-speculative-marker-qualification`，30raw SHA绑定；`docs/reviews/evidence/2026-10-13-rob-speculative-marker/independent-check.json` 直接JSONL复算所有648窗口及三control×七事件差分，与consumer精确一致；`windows.csv`完整匿名计数、`analysis.json`完整冻结门。地址/PFN/真实serial只private。端点maxCPU=[38.8, 45.5]°C，walt baseline，无环境事务/全局设置写，不认证窗内恒频。旧终态不改。

## 下一有区分力的方案

更换观测原理：仅own cache line的清除/冷热校准与错误路径cache footprint，加架构marker返回值证明确实未退休，避免未实现0x06和单count软件包络。先验证own DC/timer及A/B/M正负对照，再独立冻结filler；不得把新N0直接叫ROB entries。当前物理TLB容量/组织/ROB仍0/3，`docs/open-items.md`。
