# L1 iTLB 分层扫描结果

## 本次任务的目的（给人类看）

把一级translation refill、二级walk、cache/branch瓶颈分开。协议 `docs/design/2026-10-13-l1-tlb-fine.md`，producer `probes/diagnostic/l1_tlb_reach.c`，consumer `tools/diagnostic/l1_tlb_fine_analysis.py`，controller `tools/diagnostic/run_sm8650_l1_tlb_fine.py`。

**3/3 fresh、486完整窗口、12条曲线**，actual plan/全部布局与IR/noMUX门通过。全部原stdout库存23SHA重算；另以原before/after重新计算signed empty均值扣除，486窗第二算术误差0。i全部actual B/conditional/RET words和轨迹核对；d actual ELF6ISA已解码。public `docs/reviews/evidence/2026-10-13-l1-tlb-fine/i-scan-analysis.json` 和 `i-scan-windows.csv` 保留全部窗口。原始 `data/private/20261013T141639Z-l1-i-tlb-scan` 不裁剪。

分组判据完整输出：

- {"epoch": 0, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "ambiguous", "interval": null}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 0, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 0, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 0, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 1, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 1, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 1, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 1, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 2, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 2, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 2, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 2, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 49]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}

轮换offset逐N范围：

- {"nodes": 32, "rotating_refill_range": [2.1e-05, 6.833333333333333e-05], "walk_max": 1e-06, "rotating_cache_max": 5.216666666666666e-05, "cycles_range": [1.0000585, 1.0004925]}
- {"nodes": 46, "rotating_refill_range": [3.7166889668004675e-05, 8.850053100318603e-05], "walk_max": 1.0000060000360003e-06, "rotating_cache_max": 6.200037200223201e-05, "cycles_range": [1.0002545015270092, 1.0439657637945827]}
- {"nodes": 47, "rotating_refill_range": [4.050113403175289e-05, 0.0001045029260819303], "walk_max": 1.6667133346400367e-06, "rotating_cache_max": 7.766884139422571e-05, "cycles_range": [1.0002640073922069, 1.0429692031376878]}
- {"nodes": 48, "rotating_refill_range": [4.500072001152018e-05, 8.816807735590437e-05], "walk_max": 1.000016000256004e-06, "rotating_cache_max": 6.650106401702427e-05, "cycles_range": [1.0002923380107416, 1.0626575025200404]}
- {"nodes": 49, "rotating_refill_range": [0.07005406043248345, 0.07226507812062496], "walk_max": 2.000016000128001e-06, "rotating_cache_max": 8.583402000549337e-05, "cycles_range": [1.0620476630479712, 1.0986946228903163]}
- {"nodes": 50, "rotating_refill_range": [0.233647, 0.242412], "walk_max": 2e-06, "rotating_cache_max": 8.916666666666667e-05, "cycles_range": [1.96596, 2.019779]}
- {"nodes": 51, "rotating_refill_range": [0.5892875060294259, 0.5948050766182946], "walk_max": 2.000086003698159e-06, "rotating_cache_max": 0.00010067099551947401, "cycles_range": [4.210024697728669, 4.244760358028728]}
- {"nodes": 52, "rotating_refill_range": [0.6741197981252584, 0.7440245943171061], "walk_max": 2.000080003200128e-06, "rotating_cache_max": 0.00010383748683280664, "cycles_range": [4.7192816045975166, 5.209092197021214]}
- {"nodes": 56, "rotating_refill_range": [0.8587042029669572, 0.8936734827211952], "walk_max": 3.0000240001920015e-06, "rotating_cache_max": 0.00013500108000864006, "cycles_range": [6.011121755640712, 6.255887880436377]}

branch `codex/sm8650-tlb-hierarchy-r2`，producer `721539c33454cab5353442e9c8848caef3fad2b0`，实际launch `bfe592fe0a6b97c7ffabc69dc5722c5e3fbcf116`；binary `7d8a80edba6423661ad72f7fb2e87674d5d66137617a4bca2f1726e5dfbcf8c0`，双NDK一致。全部逐进程原quiet-state无violation/warning，无global写入。

解释边界：固定offset在N32已cache refill接近1，不能用固定offset cycles单独估TLB；两轮换offset才是缓存控制合格的容量支持证据。PMU refill是pipeline事件、可能大于1，不clip成概率。新细grid给出4KiB独占自身轨迹的相邻转折；固定offset缓存失败仍不作主证据；同data-PFN减少backing变动，但两VA并不认证hardware indexing，i四slot存在BTB残余。source规格、target独立实测分列；后续细化相邻点并审计候选组织，不改旧协议。main/remote未动作。
