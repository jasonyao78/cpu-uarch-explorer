# TLB描述符剂量对照 v1.0（预注册，producer／consumer已交付，生产链尚待验证）

## 本次任务的目的（给人类看）

在fixed1536leaf的同memfd/samePFN/order条件下，让实际leaf-table footprint跨过统一TLB2048预算候选，不只加密旧页数曲线。前置依据 `docs/reviews/2026-10-13-x4-r0p1-source-audit.md` 与 `docs/reviews/2026-10-13-tlb-observed-reach-scan-results.md`，推导稿 `docs/design/2026-10-13-tlb-descriptor-dose-draft.md`。不认证VPNhash／每PT固定1entry／HPA。

## 固定激励

N32资格三fresh：A stride5pages、B515；N1536 formal固定A5，B dose[5,67,131,169,173,259,515]三epochs，E1逆dose/visit/order。所有dose奇数，1536低8VPN各bin6；stride≥5每16KiB VA quartet至多一个选leaf。samephysical ordinal路径，同实际4ISA LDR-MADD-SUBS-BNE，一百万load_budget按完整circuits取整；warm同loads，3data rounds、3empty前／后、layout交替。共12PMU窗／process，events[17,8,5,52,3,1] USER-only/pinned/ID/noMUX。

## 几何与观察硬门

复用已资格的 `probes/diagnostic/translation_persistent_bpf.h` + `translation_persistent_gate.h`，自己的精确PID+requestVA／foreign/wrongVA negatives、首错sticky、逐node gate、dataPFN配对／word／descriptor link自洽。全部observer FD关闭、15秒固定cool，才PMU。same8GiB alignedA、B+1GiB、16GiB VA reservation，guard阻fault-around。初始CONT／LinuxtablePA不是steadycoalesced／HPA。实际PTpage/line/Pmd/domain完整输出，数据原样，不依据formula补表。整体root VA64B组必须同一。

## 资格、正式判据及停止

硬件前actual28C layouts（N32/1536×reverse0/1×7dose）/BPF动态words/ELF4ISA解码、双NDK、producer→driver→writer→immutable raw反例先通过。资格三N32全部各shape |walk/loads|≤.01，IR/loads=4±.001、Irefill/loads≤.001，全技术／环境门才DOSE_GRAPH_QUALIFIED；否则STOP。formal必须锁同二进制与三资格原文件SHA，不借旧stride3资格。

formal每epoch：N32 floor before→7doseN1536→N32 floor after，共9fresh；三epoch27process、324窗、64,896安装观察。每floor同原资格门，所有N1536 IR/I门，全部N1536 A baseline每round walk/load<.10，B5 paired negative每round|B−A walk/load|≤.10，任何不足则命名INCOMPUTABLE，不选择process救门。dose状态按每process三round：全≥.10=above、全<.10=below、mixed=ambiguous。onset低側觀察且高側至少2持續point；left/right censored/ambiguous/non-monotone保留，不算锐转折。

条件最简预算模型N+P（P实际capturedleaf PT数，额外PMD/S2/代码未知）预测169→173附近跨2048：理论P15/201/393/507/519/777/1536仅先验、捕获不符报告实值。全三epoch上述相邻剂量interval且同geometry门支持simple-budget-compatible；其它有效interval或no-onset记录simple-budget-not-replicated，完整原率/表计数不藏。即使compatible也只是几何与描述符共同干预，仍可有hash／walk-cache/S2/cache/prefetch替代，不独立认证pool或ways。

## 交付与生命周期

producer `probes/diagnostic/tlb_descriptor_dose.c` 已实现，consumer/driver/raw候选 `tools/diagnostic/tlb_descriptor_dose_analysis.py`、`run_sm8650_tlb_descriptor_dose.py`、`tlb_descriptor_dose_raw.py` 已实现但生产链尚待验证，不能上板。源／构建／计划／actual launch提交分列，证据未来 `docs/reviews/evidence/2026-10-13-tlb-descriptor-dose/`；branch codex/sm8650-tlb-hierarchy-r2，primary独占，no global env mutation／journal。技术first failure即停，raw private、匿名计数／SHA public；后续 `docs/open-items.md`。预算约27×双15秒cool+observer/counters实际运行，热或环境异常不扩大门。
