# TLB/ROB离最终目标的距离（2026-10-12，完成批次更新）

## 本次任务的目的（给人类看）

说明实测已回答什么、下一步为何有区分力。用户目标是SM8650/X4上可复核的TLB/ROB画像与结构/容量结论。**有限批次完成，整个物理参数目标尚未完成。** 不以采样量或测试数量给完成百分比，不以第三方384为答案或拟合中心。

| 方向 | 已验证的新证据 | 尚需完成 |
|---|---|---|
| TLB | 同PFN几何279窗；高位333/全位495窗编码对照后几何效应仍未达到.10尺度变化；新PFN关联297窗/288背景门通过，零邻接六曲线有效reach=(1792,2048]复制 | 原关联主INCONCLUSIVE、自然邻接激励NOT_EXCITED。物理2048entries、ways/完整hash、descriptor/CONT/HPA因果仍未认证；需要新的可观测descriptor或aggregation干预 |
| ROB | 零延迟live MOV参考/供给192窗资格通过；294进程2352扫描与1182raw SHA完整审计。四条E2盲留预测匹配，候选g+chain=(352,368] | 原.001取指门1792窗失败，18曲线INCOMPUTABLE、原main INCONCLUSIVE。链长移位反驳简单g+2k静态模型；实际allocation、跨迭代释放、唯一活跃ROB约束仍需独立校准 |
| 工程 | m0b已在r2结束使命。真实producer/NDK/PMU-ID/IR/raw审计及480诊断一次全量回归通过 | 结果汇总持续同步；稳定正式协议接入、main相关变化核对/集成回归及远端备份仍按open-items处理 |

## 已完成批次的明确裁定

1. `docs/reviews/2026-10-12-tlb-pfn-association-results.md`（d4a6e9a）：技术与背景门通过、有效reach复制；关联因果不通过命名出口。自然连续性没有达到冻结激励条件，不能用这个阴性宣称HPA无效；π还改变虚拟遍历顺序，阳性也不是HPA唯一归因。
2. `docs/reviews/2026-10-12-rob-zero-latency-scan-results.md`（a1f0082）：完整scan结束，原判据INCONCLUSIVE、共同代理None。取指失败保留，不后验宽门或只选合格窗。
3. `docs/reviews/2026-10-12-rob-lifetime-heldout-results.md`（6f98b27）：E0发现/E1不确认/E2注册时零记录，四条预先指定区间复制。所选E2的434原取指失败仍保留；另冻frontend≤1%只是观测条件，不认证所有前端影响。代理区间不是物理条目数，不任意加offset迎合384。

旧ADD/SUB192窗not-qualified（`docs/reviews/2026-10-12-rob-retirement-units-results.md`）没有升为合格，也没有借新MOV结果回填。旧MODEL_UNIDENTIFIABLE只适用于当时允许模型族，不是永不可测。

## 接续动作与停止条件

优先TLB只读descriptor可观测性。目标BTF可读且类型可解析；新增实际owned root读取能力3/3进程通过；`docs/reviews/2026-10-12-translation-observability-feasibility.md` 分列能力与未知。`docs/reviews/2026-10-12-translation-self-read-results.md` /64dcbe4已完成有PID过滤、短生命期的自有进程能力检查，不修改kptr_restrict/内核/sysfs，不盲猜direct-map物理偏置；实际leaf CONT/HPA仍UNKNOWN。

ROB下一选择直接约束跨迭代生命周期/释放的正交原型，先模型和无filler/串并负控，供给与计时资格满足后才有新有限矩阵。继续同一chain/grid无法补齐分配单位标尺，故不默认追加扫描。

所有未竟项有归属与触发：`docs/open-items.md`；结果总账 `docs/reviews/2026-10-11-tlb-rob-goal-ledger.md`；source/build/launch/报告索引 `docs/reviews/2026-10-11-tlb-rob-identifiability.md`。当前树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2` / branch `codex/sm8650-tlb-hierarchy-r2`，无main合并或推送。其他会话.gitignore与六个旧run目录保留。

## 验证口径

最新一次完整diagnostic495/495、456.790秒，source至21c3034、完整测试日志SHA见 `docs/reviews/evidence/2026-10-12-translation-self-read/regression.json`。本次未改变formal runner/analysis/CMake，不重复既有203/250/21，也不把旧基线冒充新执行。两批NDK/真实Android测量及三份raw第二算术与本机测试分列。

## 最新leaf能力检查

`docs/reviews/2026-10-12-translation-self-leaf-results.md` /77a3293：45实际指令、3/3进程正控1/负控0，old/requested PTE PFN与两端pagemap一致，20raw SHA及第二算术无差异。COW入口CONT0只属本次时点，不回填旧批/稳态CONT/HPA；页表physical PA仍未直接读到。下一shared-memfd read→write alias适用性资格优先，observer与性能窗口分离，缓存/翻译准备效应需匹配控制。最新完整508诊断通过（441.465秒）见 `docs/reviews/evidence/2026-10-12-translation-self-leaf/regression.json`，未重复formal基线。
