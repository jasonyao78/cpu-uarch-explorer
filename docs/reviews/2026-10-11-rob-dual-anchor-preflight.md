# ROB 双独立锚点软件出口（2026-10-11）

## 本次任务的目的（给人类看）

在设备采样前核实双独立链的代码真不同、结果真被核验、资格值真控制扫描。协议 `docs/design/2026-10-11-rob-dual-anchor.md` 冻结v1；当前工作树r2、branch `codex/sm8650-tlb-hierarchy-r2`，不改旧代码/旧判据，不让旧不完整矩阵进入新批。

**软件出口通过，可以启动18进程/144窗资格块；完整扫描仍受实测资格门约束。** 物理ROB尚未识别，软件绿灯不等于硬件假说通过。

| 证据 | 实际结果 |
|---|---|
| 真实native producer RED | 缺producer与driver时按预期两处失败，`/tmp/rob-dual-red.log` |
| 真实计划/独立码字oracle + 外部PMU/adb mock执行链 | 11/11，`/tmp/rob-dual-pipeline.log` |
| 完整诊断回归 | 328/328，155.124s，`/tmp/rob-dual-full-regression.log` |
| 正式runner/analysis/native CTest | 本轮此前已实跑203/203、250/250、21/21；本批未改这些组件 |
| NDK27.2/API34两次独立构建 | SHA相同：7cb9bdefee5efb833565f038361777108805c22d844d7f93bd58db905f1aa99f |
| 30程序/60顺逆真实计划 + Capstone | 全码字独立解码；各N serial/independent恰好只有第二段16条Rn/Rd字段不同 |
| 实际NDK结果捕获反汇编 | `docs/reviews/evidence/2026-10-11-rob-dual-anchor/result-capture-disassembly.txt`，BLR后先两FMOV，再调用ns；无中间FP库调用 |
| 真实driver→raw落盘→消费两阶段 | 完整资格144 + 扫描720窗软件管道；只有PMU/adb替身，属于mock证据，不冒称上板 |
| 失败闭环 | 首坏仅执行1进程后stopped；绕过audit会被同测试捕获；缺失/重复/乱序/结果位/typed值/VA/IDs/mux/IR与重算SHA反例拒绝；不合格资格raw拒绝启动扫描 |
| 资格谱系 | scan必须绑定同binary完整qualification manifest SHA；消费重新审计资格原始数据、检查linked phase（防递归scan引用）并重算资格，不信qualified标签 |
| 当前设备只读准备 | 唯一online、active probes0、unfinished journals0、环境violations/warnings空，maxCPU36.1°C |

binary source=`0d5ac032bb6d37a930b7aef56d2b19aa24c7e750`；consumer/build=`10173531e58eed9b1516f6cced2ade22cf74c219`（consumer随后增加linked-phase防环保护，实际launch另记）。精确recipe/source dependency SHA/plan存在 `docs/reviews/evidence/2026-10-11-rob-dual-anchor/build.json` / `plan.json` / `code-audit.json.gz`。新采样独立JSONL，不是schema-v2；raw/private与console私有保存。第二算术 `docs/reviews/evidence/2026-10-11-rob-dual-anchor/check_raw.py` 不import主消费，逐全部原计数/比值/门/命名及SHA复核；同一作者，不伪称双评审。
