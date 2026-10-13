# L1 iTLB N32 资格结果

## 本次任务的目的（给人类看）

先验证同PFN aliases、四role完整轨迹、原IR及一级refill/二级walk低侧，再启动有限一级扫描。协议 `docs/design/2026-10-13-l1-tlb-reach.md`。

3/3 fresh、54窗口，全部原技术和N32低侧门通过，**L1_QUALIFIED**。这只证明N32资格，不是容量或setway结论。完整原始私有 `data/private/20261013T134045Z-l1-i-tlb-qualification`，原库存23SHA逐文件重算；原JSONL经actual plan/word/计数第二算术重判，不依赖saved summary。公开 `docs/reviews/evidence/2026-10-13-l1-tlb-reach/i-qualification-analysis.json`。

branch `codex/sm8650-tlb-hierarchy-r2`，producer `cd39b1e74d9b0aa3b25020f82bff7f58c79b2add`，实际launch `21608f5368d59530af6cb589a4a1ecf75ecb9ac1`，binary `6f657fa1bc848061a44a46490561f8fac4359b4a2ba06bdea33c43d0f7edd328`。目标规格与识别分列。无全局设置修改，逐进程quiet-state pre/post无违例；失败不裁剪。

每process范围（signed扣空窗，不clip）：

- {"epoch": 0, "windows": 18, "refill_range": [2.3166666666666666e-05, 0.00010216666666666667], "walk_range": [0.0, 2e-06], "cache_range": [7.333333333333333e-06, 1.0001173333333333], "IR_range": [1.062505, 1.062505], "actual_PFNs_unique": 192}
- {"epoch": 1, "windows": 18, "refill_range": [2.25e-05, 7.45e-05], "walk_range": [0.0, 2e-06], "cache_range": [3.5e-06, 1.0000615], "IR_range": [1.062505, 1.062505], "actual_PFNs_unique": 192}
- {"epoch": 2, "windows": 18, "refill_range": [2.566666666666667e-05, 7.166666666666667e-05], "walk_range": [0.0, 1e-06], "cache_range": [1.4666666666666666e-05, 1.0000646666666666], "IR_range": [1.062505, 1.062505], "actual_PFNs_unique": 192}

下一同binary的有限scan；main/remote未动作。
