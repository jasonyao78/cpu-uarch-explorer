# L1 iTLB 分层扫描结果

## 本次任务的目的（给人类看）

把一级translation refill、二级walk、cache/branch瓶颈分开。协议 `docs/design/2026-10-13-l1-tlb-reach.md`，producer `probes/diagnostic/l1_tlb_reach.c`，consumer `tools/diagnostic/l1_tlb_reach_analysis.py`，controller `tools/diagnostic/run_sm8650_l1_tlb_reach.py`。

**3/3 fresh、864完整窗口、12条曲线**，actual plan/全部布局与IR/noMUX门通过。全部原stdout库存23SHA重算；另以原before/after重新计算signed empty均值扣除，864窗第二算术误差0。i全部actual B/conditional/RET words和轨迹核对；d actual ELF6ISA已解码。public `docs/reviews/evidence/2026-10-13-l1-tlb-reach/i-scan-analysis.json` 和 `i-scan-windows.csv` 保留全部窗口。原始 `data/private/20261013T134635Z-l1-i-tlb-scan` 不裁剪。

分组判据完整输出：

- {"epoch": 0, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 0, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 0, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "ambiguous", "interval": null}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 0, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 1, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 1, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 1, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 1, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 2, "role": 0, "stride": 5, "offset": "fixed", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 2, "role": 1, "stride": 5, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}
- {"epoch": 2, "role": 2, "stride": 17, "offset": "fixed", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": false, "aux_gate": true}
- {"epoch": 2, "role": 3, "stride": 17, "offset": "rotating", "onset": {"status": "localized", "interval": [48, 52]}, "walk_gate": true, "cache_gate": true, "aux_gate": true}

轮换offset逐N范围：

- {"nodes": 32, "rotating_refill_range": [2.45e-05, 6.75e-05], "walk_max": 2e-06, "rotating_cache_max": 6.116666666666666e-05, "cycles_range": [1.000006, 1.0004155]}
- {"nodes": 40, "rotating_refill_range": [3.1333333333333334e-05, 6.583333333333333e-05], "walk_max": 2e-06, "rotating_cache_max": 6.833333333333333e-05, "cycles_range": [1.0002373333333334, 1.0504993333333332]}
- {"nodes": 44, "rotating_refill_range": [3.5333757338421395e-05, 0.0001170014040168482], "walk_max": 2.0000240002880036e-06, "rotating_cache_max": 7.200086401036812e-05, "cycles_range": [1.0003255039060468, 1.0455443798658917]}
- {"nodes": 48, "rotating_refill_range": [4.2500680010880175e-05, 0.00017750284004544072], "walk_max": 1.8333626671360075e-06, "rotating_cache_max": 0.00011366848536243247, "cycles_range": [1.000317838418748, 1.0450335538701954]}
- {"nodes": 52, "rotating_refill_range": [0.6757315292611704, 0.7370778164459912], "walk_max": 2.000080003200128e-06, "rotating_cache_max": 0.00010433750683360667, "cycles_range": [4.732121618198061, 5.16694417776711]}
- {"nodes": 56, "rotating_refill_range": [0.8477476153142559, 0.8936788160971955], "walk_max": 3.0000240001920015e-06, "rotating_cache_max": 0.00011583426000741339, "cycles_range": [5.934395641831801, 6.255985547884383]}
- {"nodes": 64, "rotating_refill_range": [0.957449, 0.9574676666666666], "walk_max": 3e-06, "rotating_cache_max": 0.00016883333333333334, "cycles_range": [6.702197333333333, 6.7025413333333335]}
- {"nodes": 96, "rotating_refill_range": [0.9838716344512715, 0.9838846352833248], "walk_max": 3.0001920122887865e-06, "rotating_cache_max": 0.00023968200631507082, "cycles_range": [6.887140276977727, 6.887460464136372]}
- {"nodes": 112, "rotating_refill_range": [0.9999998333226661, 1.0000135008640554], "walk_max": 3.0001920122887865e-06, "rotating_cache_max": 0.00031602022529441884, "cycles_range": [7.0000511699415435, 7.001021232025517]}
- {"nodes": 120, "rotating_refill_range": [1.0000006666933343, 1.00001250050002], "walk_max": 4.000160006400256e-06, "rotating_cache_max": 0.0003453471472192221, "cycles_range": [7.000069169433444, 7.000381348587276]}
- {"nodes": 124, "rotating_refill_range": [1.000001000064004, 1.0000153343147296], "walk_max": 3.0001920122887865e-06, "rotating_cache_max": 0.00033235460402799113, "cycles_range": [7.000132675157877, 7.000359523009473]}
- {"nodes": 128, "rotating_refill_range": [1.000000500032002, 1.0000128341547192], "walk_max": 3.0001920122887865e-06, "rotating_cache_max": 0.00037119042285372933, "cycles_range": [7.000096672853729, 7.000374523969534]}
- {"nodes": 132, "rotating_refill_range": [1.00000133346668, 1.00001466813348], "walk_max": 4.0004000400040005e-06, "rotating_cache_max": 0.00036837017035036833, "cycles_range": [7.00011367803447, 7.00039270593726]}
- {"nodes": 144, "rotating_refill_range": [1.000000500032002, 1.0000136675413893], "walk_max": 4.000256016385049e-06, "rotating_cache_max": 0.00038469128690902886, "cycles_range": [7.000103839979092, 7.00045902937788]}
- {"nodes": 160, "rotating_refill_range": [1.0000035, 1.0000128333333334], "walk_max": 4e-06, "rotating_cache_max": 0.00048266666666666667, "cycles_range": [7.000107333333333, 7.0003545]}
- {"nodes": 192, "rotating_refill_range": [1.000002000128008, 1.000012000768049], "walk_max": 5.000320020481311e-06, "rotating_cache_max": 0.0005883709890766342, "cycles_range": [7.000018834538744, 7.000454529089862]}

branch `codex/sm8650-tlb-hierarchy-r2`，producer `cd39b1e74d9b0aa3b25020f82bff7f58c79b2add`，实际launch `4016b50168b8f102bd662d64a0979becbe45276d`；binary `6f657fa1bc848061a44a46490561f8fac4359b4a2ba06bdea33c43d0f7edd328`，双NDK一致。全部逐进程原quiet-state无violation/warning，无global写入。

解释边界：固定offset在N32已cache refill接近1，不能用固定offset cycles单独估TLB；两轮换offset才是缓存控制合格的容量支持证据。PMU refill是pipeline事件、可能大于1，不clip成概率。当前粗grid仅给操作reach转折，不擅报相邻精确entry数；同data-PFN减少backing变动，但两VA并不认证hardware indexing，i四slot存在BTB残余。source规格、target独立实测分列；后续细化相邻点并审计候选组织，不改旧协议。main/remote未动作。
