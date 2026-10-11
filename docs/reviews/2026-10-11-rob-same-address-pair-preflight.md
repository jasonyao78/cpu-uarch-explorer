# ROB 同地址配对的软件出口

## 本次任务的目的（给人类看）

按 `docs/design/2026-10-11-rob-same-address-pair.md` v1检验同进程/同代码VA的配对控制。只有软件/部署/来源出口已通过，本文不替代随后手机480窗的科学主门。

工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`，分支 `codex/sm8650-tlb-hierarchy-r2`；binary source `4cebc24e20f623f507d91eb610698a19602e8d8d`，consumer/build `11abe30`，实际launch由随后manifest记录。main/远端未操作。

- 代码 `probes/diagnostic/rob_dependency_pair.c` 与 `probes/common/rob_codegen.h`；旧 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c` 仅抽取pure生成器，56个实际legacy config和完整生成字节逐字不变。新12program/六schedule实码与另一条数学构造、Capstone逐指令完全一致；N0两流相同，N128只有256个Rn位域不同，无ABI保存寄存器污染。计划/构建/代码审计在 `docs/reviews/evidence/2026-10-11-rob-same-address-pair/`。
- NDK27.2.12479018/API34静态O2/Werror，两次构建逐字一致，SHA256=`695cfc381b3fef229b3a2796889d09f598c150472caf1b38e7ed2d6ce7a8b383`。目标执行同一mapping重写程序与清Icache在窗外；实际地址、kernel IDs及IR仍需目标raw验收，host exporter不能代替这部分实证。
- 消费 `tools/diagnostic/rob_pair_analysis.py`、驱动 `tools/diagnostic/run_sm8650_rob_pair.py`；真实producer计划→registered driver→writer→raw回读完整15进程/480窗软件正例通过，22类重哈希/身份/代码/VA/PMU/IR/环境反例拒绝；首bad-program只执行1进程。故意旁路audit_process会被首坏fixture抓住。外部执行/计数是明确模拟，不称手机数据。
- 主门反例含N0哨兵漂移、NONE非零/波动、符号消失与cycle事件语义不相容。绝对C漂移但同block配对稳定的fixture可通过冻结门，同时完整保留绝对范围，不能把“配对通过”说成“绝对供给恒定”。路径 `tools/diagnostic/tests/test_rob_pair_{producer,analysis,raw}.py`。
- fresh完整diagnostic **298/298，113.632s**；runner **203/203**、正式analysis **250/250**、macOS CTest **21/21**。日志 `/tmp/rob-pair-full-regression-fixed.log`、`/tmp/rob-pair-runner-regression.log`、`/tmp/rob-pair-analysis-regression.log`、`/tmp/rob-pair-ctest.log`。首次全量发现旧零值测试临时构建遗漏新头，294 tests/1 error已保留 `/tmp/rob-pair-full-regression.log`，补齐测试依赖后全量通过；不是删测试或跳Linux路径来救门。
- 只读独占检查：1个在线target，active probes=0，unfinished journals=0。每进程15s间隔、前后baseline环境验收，不写governor/热服务/全局THP或PMU设置；端点不证窗内恒频。手机15进程完整有限批若主门失败按not-qualified结束，不改阈值追门。
