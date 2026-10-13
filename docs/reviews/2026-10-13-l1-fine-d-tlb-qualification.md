# L1 dTLB N32 资格结果

## 本次任务的目的（给人类看）

先验证同PFN aliases、四role完整轨迹、原IR及一级refill/二级walk低侧，再启动有限一级扫描。协议 `docs/design/2026-10-13-l1-tlb-fine.md`。

3/3 fresh、54窗口，全部原技术和N32低侧门通过，**L1_QUALIFIED**。这只证明N32资格，不是容量或setway结论。完整原始私有 `data/private/20261013T135903Z-l1-d-tlb-qualification`，原库存23SHA逐文件重算；原JSONL经actual plan/word/计数第二算术重判，不依赖saved summary。公开 `docs/reviews/evidence/2026-10-13-l1-tlb-fine/d-qualification-analysis.json`。

branch `codex/sm8650-tlb-hierarchy-r2`，producer `721539c33454cab5353442e9c8848caef3fad2b0`，实际launch `a32587fc30fc0d82d3c00a032a6ada743916e8de`，binary `7d8a80edba6423661ad72f7fb2e87674d5d66137617a4bca2f1726e5dfbcf8c0`。目标规格与识别分列。无全局设置修改，逐进程quiet-state pre/post无违例；失败不裁剪。

每process范围（signed扣空窗，不clip）：

- {"epoch": 0, "windows": 18, "refill_range": [3.3e-05, 9.7e-05], "walk_range": [0.0, 0.0], "cache_range": [3.633333333333333e-05, 0.6704233333333334], "IR_range": [6.000025, 6.000025], "actual_PFNs_unique": 192}
- {"epoch": 1, "windows": 18, "refill_range": [3.2e-05, 9.8e-05], "walk_range": [0.0, 1e-06], "cache_range": [8.5e-06, 0.6821415], "IR_range": [6.000025, 6.000025], "actual_PFNs_unique": 192}
- {"epoch": 2, "windows": 18, "refill_range": [0.0, 0.00013], "walk_range": [0.0, 0.0], "cache_range": [3.35e-05, 0.6706625], "IR_range": [6.000025, 6.000025], "actual_PFNs_unique": 192}

下一同binary的有限scan；main/remote未动作。
