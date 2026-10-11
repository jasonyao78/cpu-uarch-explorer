# ROB 原字节维护对照：软件出口

## 本次任务的目的（给人类看）

冻结协议 `docs/design/2026-10-11-rob-resident-control.md` v1，仅检验固定程序的额外代码维护关联，不认证物理ROB项数、不改前批not-qualified。工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`、branch `codex/sm8650-tlb-hierarchy-r2`，main/远端未操作。

## 已核验的出口

- source `fe53c23755747e509963538153f04181ef0594b3`；consumer/build `71cb2a339bbc5d9392c070800cfb560635a40f12`。probe `probes/diagnostic/rob_resident_control.c` 共用 `probes/common/rob_codegen.h`，legacy路径和旧协议未改。5种实际程序、顺逆10份完整native计划与独立字节oracle一致，完整逐指令Capstone解码、全部ADD来源寄存器/256条filler/32条FSQRT/branch目标64/RET核验；证据 `docs/reviews/evidence/2026-10-11-rob-resident-control/{plan,code-audit,build}.json`。
- NDK27.2.12479018/API34 -O2 -Wall -Wextra -Werror -static双构建逐字一致，binary SHA256 `09ff24e3672d71fdda478de3e258d26f4419024ec55be0c9ae621cf28963dd67`。source/C与两共享头SHA登记；运行时固定单程序单VA，每窗实码核验和generation仍待目标raw验证。
- `tools/diagnostic/run_sm8650_rob_resident.py` → writer → `tools/diagnostic/rob_resident_analysis.py`真实native计划软件全链15进程/240窗通过。保存真实committed driver及consumer字节；23类重哈希/身份/完整性/环境反例拒绝。首bad program只执行1进程；故意旁路audit_process时测试会失败。只对外部PMU/部署模拟，不称设备实测。路径 `tools/diagnostic/tests/test_rob_resident.py`、`tools/diagnostic/tests/test_rob_resident_raw.py`。
- 新9测试及完整diagnostic **307/307（139.698s）**；runner **203/203**、正式analysis **250/250**、native CTest **21/21** fresh通过。完整日志 `/tmp/rob-resident-{targeted,full-regression,runner-regression,analysis-regression,ctest}.log`。测试反例曾错误把resident改成resident，已改为真正相反值，随后完整反例通过；不改消费规则救测试。
- 用户重新连接手机后，只读独占检查1在线、active probes0、unfinished journals0、环境violations/warnings均空、CPU最高温35.3°C。实际launch由随后raw manifest记录；15进程间15s、每步先审计再推进，前后/最终环境核验。设备参数无写入、无旧A1/frozen拼接。

本软件出口通过；后续240窗的科学结果依预注册规则如实命名，无效应复制不等于证明无效应，两种preparation稳定也不唯一解释前批跨variant波动。
