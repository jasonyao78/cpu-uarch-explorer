# L1 dTLB 分层扫描结果

## 本次任务的目的（给人类看）

把一级translation refill、二级walk、cache/branch瓶颈分开。协议 `docs/design/2026-10-13-l1-tlb-fine.md`，producer `probes/diagnostic/l1_tlb_reach.c`，consumer `tools/diagnostic/l1_tlb_fine_analysis.py`，controller `tools/diagnostic/run_sm8650_l1_tlb_fine.py`。

**3/3 fresh、486完整窗口、12条曲线**，actual plan/全部布局与IR/noMUX门通过。全部原stdout库存23SHA重算；另以原before/after重新计算signed empty均值扣除，486窗第二算术误差0。i全部actual B/conditional/RET words和轨迹核对；d actual ELF6ISA已解码。public `docs/reviews/evidence/2026-10-13-l1-tlb-fine/d-scan-analysis.json` 和 `d-scan-windows.csv` 保留全部窗口。原始 `data/private/20261013T141326Z-l1-d-tlb-scan` 不裁剪。

分组判据完整输出：

- {"epoch": 0, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "ambiguous", "interval": null}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 0, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 0, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 0, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 1, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 1, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 1, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 1, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 2, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 2, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 2, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 2, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 97]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}

轮换offset逐N范围：

- {"nodes": 32, "rotating_refill_range": [3.1e-05, 0.000112], "walk_max": 1e-06, "rotating_cache_max": 7e-05, "cycles_range": [9.0003335, 9.2507095]}
- {"nodes": 94, "rotating_refill_range": [9.600268807526611e-05, 0.00031700887624853496], "walk_max": 1.000028000784022e-06, "rotating_cache_max": 0.0001953388028198123, "cycles_range": [9.001512042337186, 9.262480849463785]}
- {"nodes": 95, "rotating_refill_range": [9.200276008280249e-05, 0.00032200966028980867], "walk_max": 1.000030000900027e-06, "rotating_cache_max": 0.0002063395235190389, "cycles_range": [8.983844848678794, 9.251736052081563]}
- {"nodes": 96, "rotating_refill_range": [9.700620839733743e-05, 0.0003480222734254992], "walk_max": 0.0, "rotating_cache_max": 0.00020151289682539681, "cycles_range": [9.001585934833164, 9.252991024758918]}
- {"nodes": 97, "rotating_refill_range": [0.5001435038746046, 1.0000030000810023], "walk_max": 2.0000540014580394e-06, "rotating_cache_max": 0.00022233933649541871, "cycles_range": [12.099001339702838, 15.20421718053054]}
- {"nodes": 98, "rotating_refill_range": [0.6643233145865167, 1.0000080000640006], "walk_max": 1.0000080000640005e-06, "rotating_cache_max": 0.00023250186001488011, "cycles_range": [13.156086748693989, 15.244364454915639]}
- {"nodes": 99, "rotating_refill_range": [0.563003563003563, 1.000005000005], "walk_max": 2.000002000002e-06, "rotating_cache_max": 0.00022633355966689302, "cycles_range": [12.379865213198547, 15.32985632985633]}
- {"nodes": 100, "rotating_refill_range": [0.5554968333333333, 1.000005], "walk_max": 1e-06, "rotating_cache_max": 0.00021716666666666667, "cycles_range": [12.334328, 15.282448166666667]}
- {"nodes": 104, "rotating_refill_range": [0.5952058082323293, 1.0000060002400095], "walk_max": 1.000040001600064e-06, "rotating_cache_max": 0.00022917583370001465, "cycles_range": [12.588459705054868, 15.297559569049428]}

branch `codex/sm8650-tlb-hierarchy-r2`，producer `721539c33454cab5353442e9c8848caef3fad2b0`，实际launch `bfe592fe0a6b97c7ffabc69dc5722c5e3fbcf116`；binary `7d8a80edba6423661ad72f7fb2e87674d5d66137617a4bca2f1726e5dfbcf8c0`，双NDK一致。全部逐进程原quiet-state无violation/warning，无global写入。

解释边界：固定offset在N32已cache refill接近1，不能用固定offset cycles单独估TLB；两轮换offset才是缓存控制合格的容量支持证据。PMU refill是pipeline事件、可能大于1，不clip成概率。新细grid给出4KiB独占自身轨迹的相邻转折；固定offset缓存失败仍不作主证据；同data-PFN减少backing变动，但两VA并不认证hardware indexing，i四slot存在BTB残余。source规格、target独立实测分列；后续细化相邻点并审计候选组织，不改旧协议。main/remote未动作。
