# L1 dTLB 分层扫描结果

## 本次任务的目的（给人类看）

把一级translation refill、二级walk、cache/branch瓶颈分开。协议 `docs/design/2026-10-13-l1-tlb-reach.md`，producer `probes/diagnostic/l1_tlb_reach.c`，consumer `tools/diagnostic/l1_tlb_reach_analysis.py`，controller `tools/diagnostic/run_sm8650_l1_tlb_reach.py`。

**3/3 fresh、648完整窗口、12条曲线**，actual plan/全部布局与IR/noMUX门通过。全部原stdout库存23SHA重算；另以原before/after重新计算signed empty均值扣除，648窗第二算术误差0。i全部actual B/conditional/RET words和轨迹核对；d actual ELF6ISA已解码。public `docs/reviews/evidence/2026-10-13-l1-tlb-reach/d-scan-analysis.json` 和 `d-scan-windows.csv` 保留全部窗口。原始 `data/private/20261013T134314Z-l1-d-tlb-scan` 不裁剪。

分组判据完整输出：

- {"epoch": 0, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 0, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 0, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 0, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 1, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 1, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 1, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 1, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 2, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 2, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 2, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 2, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [96, 100]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}

轮换offset逐N范围：

- {"nodes": 32, "rotating_refill_range": [3.3e-05, 0.00011], "walk_max": 0.0, "rotating_cache_max": 7.8e-05, "cycles_range": [9.000770833333334, 9.251657]}
- {"nodes": 64, "rotating_refill_range": [6.2e-05, 0.000194], "walk_max": 0.0, "rotating_cache_max": 0.00011666666666666667, "cycles_range": [9.001092666666667, 9.251186]}
- {"nodes": 80, "rotating_refill_range": [8e-05, 0.000243], "walk_max": 1e-06, "rotating_cache_max": 0.00017066666666666665, "cycles_range": [9.001100333333333, 9.2515625]}
- {"nodes": 88, "rotating_refill_range": [8.800492827598346e-05, 0.00026801500884049504], "walk_max": 1.0000560031361757e-06, "rotating_cache_max": 0.00019034399259691877, "cycles_range": [9.001196400331752, 9.252871494137006]}
- {"nodes": 92, "rotating_refill_range": [9.200478424878094e-05, 0.000299015548808538], "walk_max": 0.0, "rotating_cache_max": 0.00018534297116783407, "cycles_range": [9.001451075455924, 9.252137777831113]}
- {"nodes": 96, "rotating_refill_range": [8.600550435227854e-05, 0.00042502720174091143], "walk_max": 0.0, "rotating_cache_max": 0.00020234628349547704, "cycles_range": [9.001846284828895, 9.253698403364481]}
- {"nodes": 100, "rotating_refill_range": [0.576304, 1.000005], "walk_max": 1e-06, "rotating_cache_max": 0.00021416666666666665, "cycles_range": [12.462924166666665, 15.2630765]}
- {"nodes": 104, "rotating_refill_range": [0.9999929997199888, 1.0000030001200049], "walk_max": 1.000040001600064e-06, "rotating_cache_max": 0.00025201008040321614, "cycles_range": [15.000780364547916, 15.335144239102899]}
- {"nodes": 112, "rotating_refill_range": [0.9999819988479263, 1.0000070004480286], "walk_max": 0.0, "rotating_cache_max": 0.0002616834144051886, "cycles_range": [15.001459093381976, 15.158979508021847]}
- {"nodes": 128, "rotating_refill_range": [0.999988999295955, 1.0000040002560164], "walk_max": 1.0000640040962622e-06, "rotating_cache_max": 0.0003061862625874723, "cycles_range": [15.002077799645843, 15.331894907940775]}
- {"nodes": 160, "rotating_refill_range": [1.0, 1.000004], "walk_max": 3e-06, "rotating_cache_max": 0.0004251666666666667, "cycles_range": [15.001415333333334, 15.245451333333333]}
- {"nodes": 192, "rotating_refill_range": [1.000001000064004, 1.000020001280082], "walk_max": 4.000256016385049e-06, "rotating_cache_max": 0.0006225398425499232, "cycles_range": [15.002312814686807, 15.33541413317119]}

branch `codex/sm8650-tlb-hierarchy-r2`，producer `cd39b1e74d9b0aa3b25020f82bff7f58c79b2add`，实际launch `5c9d412ae093f8129dc241e7761a93ffd03543cd`；binary `6f657fa1bc848061a44a46490561f8fac4359b4a2ba06bdea33c43d0f7edd328`，双NDK一致。全部逐进程原quiet-state无violation/warning，无global写入。

解释边界：固定offset在N32已cache refill接近1，不能用固定offset cycles单独估TLB；两轮换offset才是缓存控制合格的容量支持证据。PMU refill是pipeline事件、可能大于1，不clip成概率。当前粗grid仅给操作reach转折，不擅报相邻精确entry数；同data-PFN减少backing变动，但两VA并不认证hardware indexing，i四slot存在BTB残余。source规格、target独立实测分列；后续细化相邻点并审计候选组织，不改旧协议。main/remote未动作。
