# ROB自有cache marker N0：计时/对照通过、错误路径资格不通过（2026-10-13）

## 本次任务的目的（给人类看）

通过own line cache footprint与独立架构marker验证退休阻塞后的年轻load，避免旧无效LD_RETIRED事件。冻结合同 `docs/design/2026-10-13-rob-cache-marker.md` v1.0。

**CACHE_MARKER_NOT_QUALIFIED；不扫N、不声称ROB容量。** 六fresh进程1536/1536原值完整，实际代码/原bits/FPSR/架构marker/CPU7/三个独立page PFN/计时能力全部技术接受，30raw SHA独立核验。所有校准、A架构正控、B及各NOP阴性都过，唯一科学门失败为M-load hit率。

| process | hot q90 / cold q10（ticks） | 阈值 | M-load hit率 |
|---|---|---:|---:|
| e0-k16 | 1.0 / 4.0 | 2.5 | 0.31250 |
| e0-k32 | 1.0 / 4.0 | 2.5 | 0.31250 |
| e1-k32 | 1.0 / 4.0 | 2.5 | 0.18750 |
| e1-k16 | 1.0 / 4.0 | 2.5 | 0.21875 |
| e2-k16 | 1.0 / 4.0 | 2.5 | 0.34375 |
| e2-k32 | 1.0 / 5.0 | 3.0 | 0.21875 |

每process hot正控/A-load均100% hit，cal-cold、A-nop/B-nop/B-load/M-nop均0%；CNTFRQ=19200000Hz，ticks不是CPU cycles。实际A-load架构marker=0x12345678，M及B均0；原program SB及独立output page确保观察架构值不重读marker。**冷热计时和cache干预已可分辨，M footprint仍不稳定。** 原.90门不降低成.18，不能因有部分hit就扫描。没有单独branch PC采样/issued-load tap，未唯一鉴别history、load发射、fill completion/cache层级等；“没及时得到hit”不能等于“没分配/没发射”。不是physical ROB小的反例。

## 交付谱系与核验

branch `codex/sm8650-tlb-hierarchy-r2`，source `b9cf58a`（C2475db2）；build `9dfbd64`；actual launch `7a64a8023ab4da3a2eb707343050c8be5fd67f52`；binary SHA256 `4994994c780f1129128f9683dc264d8496d72d4446d41ce53bd0f245d98935b8`。代码 `probes/diagnostic/rob_cache_marker.c`、consumer `tools/diagnostic/rob_cache_marker_analysis.py`、driver `tools/diagnostic/run_sm8650_rob_cache_marker.py`。两NDK27.2/API34/O2/static字节一致；两实际C plans/四program独立Capstone分支/SB/架构STR解码；13生产链/缺失/重复/乱序/原结果/阈值来源/PFN/首失败测试通过（timer只是软件模拟，不冒充实测）。

private `data/private/20261013T042705Z-rob-cache-marker-qualification`，公开 `docs/reviews/evidence/2026-10-13-rob-cache-marker/`：完整匿名 `windows.csv`、全部判据 `analysis.json`、直接JSONL第二算术Type7/hit率及30SHA `independent-check.json`。所有tails保留，原始地址/PFN只private；端点CPU温度[38.4, 42.6]°C。无环境事务或全局PMU/security/frequency写；own DC只证明本次能力与状态响应，不认证native/HPA。旧单count PMU失败及其它旧终态不改变。

## 接下来如何减少不确定性

TLB优先实施可扩展的exact-owned-address descriptor observer，把large-N真实页表身份接到既有几何/容量转折；逐node重复attach/fork开销需先解决，但不得牺牲PID/VA过滤、sticky first error和实际字节身份。随后固定VA/data PFN改变真实PTE-table关联，再比较walk响应，不把Linux IPA当HPA。

ROB需独立观测“issued”与“fill completed”或控制history；候选为受支持LD_SPEC的多marker信号放大，配架构输出证实未退休，或不同completion delay对照。先另注册资格，不能悄悄复跑本失败块。三个最终物理参数仍0/3，单位和活跃约束没关闭；后置项 `docs/open-items.md`。
