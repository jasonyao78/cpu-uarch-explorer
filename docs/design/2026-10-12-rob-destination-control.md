# ROB前置：架构结果目的与流量状态（冻结v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-rob-fusion-groups-results.md` 中ADD NONE64全三个进程在21–35.5cycles/轮间波动，NOP+ADD与双NOP稳定，不能进容量扫描。下一对照只改变ADD的Rd：原X4..X11循环写入与XZR丢弃结果。区分“架构结果目的与本协议的状态变化伴生”与“加NOP前缀才改变状态”，不把结果直接归为PRF或fusion，更不把它当ROB条目标尺。

新增 `probes/diagnostic/rob_destination_control.c`，复用 `probes/common/rob_codegen.h` opcode/prologue/纯公共GROUP+ID解码。五pattern=add-live/add-discard/nop-add-live/nop-add-discard/nop-pair。X16=0x1111、X17=0x2222；live目的X(4+j%8)、discard目的XZR。相同prefix对的循环只变ADD Rd5bits；loop外return live为0x3333、discard/双NOP为0。XZR没有架构结果，但实现可能消除或选择另一管线，**不预设它仍消耗相同ROB/ALU/µOP资源**；0x3a/IR只提供观察，不认证µOP=MOP=ROB单位。

每侧64组，只NONE；加三N0引用（none/serial/independent的双NOP g0，16×D0/D0或D0/D1）。24进程×8窗=192窗，三epochs、奇epoch整体条件/窗顺序reverse。每窗warmup/正式131072 iterations，单固定RX64KiB/进程，捕获live结果、N0 FP1.0；events[cycles,IR,retired µOP,rename-full,frontend stall,Icache refill]，CPU7/FPCR0/noRESET/noMUX/ID/read-only环境及5s进程间隔沿匹配组。全144旧窗不改，不复跑旧协议追门。

资格只检验模型引用/双NOP供给：I0/S0 max/min≤.70、两个FP引用各进程range/median≤.10、NONE0绝对range≤.01*minI0；双NOP NONE64各进程稳定且maxC≤.80minI0；全部192窗Icache/iteration≤.001（旧越门不回收）。不以待研究的live变化自身当资格失败而抹去现象；全部live/discard原值保留。

主对照ADD：三epochs的live range/median都>.10、discard都≤.10，且所有NONE64 maxC≤.80minI0，引用/双NOP/Icache资格全过，才命名DISCARD_DESTINATION_REMOVES_OBSERVED_VARIABILITY。对nop-add同样规则单独报告；所有live/discard均稳定=VARIABILITY_NOT_REPLICATED（有限，不认证机制不存在）；其它=INCONCLUSIVE，资格失败=not-qualified。稳定模式间median差及cycles/ns/µOP/rename/frontend比均保留，但不据事后选窗口做因果差分。无需本批启动任何N扫描；物理容量仍需α/活跃约束独立证据。

consumer `tools/diagnostic/rob_destination_analysis.py`、driver `tools/diagnostic/run_sm8650_rob_destination.py`、tests `tools/diagnostic/tests/test_rob_destination*.py`、evidence `docs/reviews/evidence/2026-10-12-rob-destination-control/`。独立实际code计划和Rd差分、结果/FP捕获反汇编、两次NDK及producer→writer→raw的全覆盖反例之后串行目标执行；源/build-consumer/launch/report分列。branch `codex/sm8650-tlb-hierarchy-r2`，owner=当前端到端负责人；其它部件/正式接入按 `docs/open-items.md`。
