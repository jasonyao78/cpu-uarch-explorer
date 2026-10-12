# ROB两链register排程对照（2026-10-13）

## 本次任务的目的（给人类看）

检验实际FPSR k32 independent≈462 cycles的参考残差是否随blocked/interleaved寄存器排程变化，先分离reference/anchor贡献，不据此直接命名ROB容量。

**主判据 BLOCKED_ANCHOR_ORDER_DELAY，辅助k16 ORDER_CONTRAST_NOT_CHANGED_AT_REGISTERED_MEDIAN_SCALE。** 完整12进程/768窗口/54raw SHA，source d1c99ea / build ead5e51 / actual launch 9be15af，branch codex/sm8650-tlb-hierarchy-r2；binary `4125fa376c5d0cb7b34e2cef1a99e36f9c314552d60aa085ad60b4b1af2f291a`，NDK27.2/API34/static/C11/O2/Werror两build一致、8actual计划/64独立Capstone程序、13真实producer→driver→writer→immutable-source再生raw攻击测试通过。原FP1.0/FPSR0/checksum0、noMUX/IR/code/PFN/CPU/环境技术身份全部逐窗核验；端点温度38.0–41.3℃只属端点，不是窗内恒频证书。

两layout同进程同code PFN，四页PFN独立/前后稳定，normal/swapped位置交换；INDEPENDENT只换FSQRT寄存器顺序，hist/prefix/tail/branch相同；NONE/SERIAL两个layout逐字同码。每trial固定轮转、原重复次数和冷却间隔不变，全部控制门与失败保留，没有挑quiet窗或改阈值。表中I/S为cycles per iteration中位，DID=(Iblocked−Iinterleaved)−(Sblocked−Sinterleaved)，不是物理entries单位。

| process | I blocked / interleaved | S blocked / interleaved | median DID | 所有控制门 |
|---|---|---|---|---|
| e0-k16-normal | 225.004 / 225.004 | 432.007 / 432.006 | -0.000 | 通过 |
| e0-k16-swapped | 225.004 / 225.004 | 432.006 / 432.006 | 0.000 | 通过 |
| e0-k32-normal | 462.007 / 433.007 | 848.012 / 848.012 | 29.001 | 通过 |
| e0-k32-swapped | 462.007 / 433.007 | 848.011 / 848.011 | 29.000 | 通过 |
| e1-k32-swapped | 462.007 / 433.006 | 848.011 / 848.012 | 29.001 | 通过 |
| e1-k32-normal | 462.007 / 433.007 | 848.012 / 848.012 | 29.000 | 通过 |
| e1-k16-swapped | 225.004 / 225.004 | 432.006 / 432.007 | 0.001 | 通过 |
| e1-k16-normal | 225.005 / 225.004 | 432.006 / 432.006 | 0.001 | 通过 |
| e2-k16-normal | 225.004 / 225.004 | 432.007 / 432.007 | 0.002 | 通过 |
| e2-k16-swapped | 225.004 / 225.004 | 432.007 / 432.007 | 0.000 | 通过 |
| e2-k32-normal | 462.007 / 433.006 | 848.012 / 848.012 | 29.000 | 通过 |
| e2-k32-swapped | 462.007 / 433.006 | 848.011 / 848.012 | 29.001 | 通过 |

代码 `probes/diagnostic/rob_anchor_order.c`；严格入口 `tools/diagnostic/rob_order_analysis.py`，编排 `tools/diagnostic/run_sm8650_rob_order.py`，有限冻结 `docs/design/2026-10-13-rob-anchor-order.md`。private原始目录 `data/private/20261012T164352Z-rob-anchor-order-qualification/`；匿名完整窗口点/门/result/原SHA在 `docs/reviews/evidence/2026-10-13-rob-anchor-order/result.json`，直接第二算术 `independent-check.json` 从原程序字、branch、PFN、result、counts重算全部pair和gate，与consumer一致。

无论是否有order contribution，都不能唯一归因RS/PRF/ROB、认证实际allocation单位或拟合384。MRS等待较早FP执行/退休不认证阻止未来投机allocation；同码阴性、同code PFN及slot交换控制只约束本registered register-order contrast。旧scan的取指失败/INCONCLUSIVE及g+chain=(352,368]代理、旧FPSR/FPCR资格均不覆盖。

下一动作依据本新结果另案冻结：如果order贡献成立，后续长anchor采用更可解释的排程，并独立核验allocation/lifecycle；如果控制不合格，保留导致不合格的实际条件，先修reference设计；如果median尺度阴性，只排除本对照贡献达到该尺度。不能直接自动capacity扫描；整体physical TLB/ROB仍OPEN，责任与后置触发见 `docs/open-items.md`。

实际k32 blocked≈462.007 / interleaved≈433.006，六process配对DID=29.0000–29.0011，全部48trial方向一致；k16≈225.004两layout相同、辅助median尺度阴性。12process全部controls通过，主BLOCKED_ANCHOR_ORDER_DELAY。433以前作为公式外推没有观测资格，现在只属于新interleaved程序的实测，不用它覆盖旧blocked462。不能由“仅instruction order”进一步唯一叫32-entry scheduler。完整558/558诊断通过（471.147秒，exit0，tested source9be15af），证据 `docs/reviews/evidence/2026-10-13-rob-anchor-order/regression.json`。
