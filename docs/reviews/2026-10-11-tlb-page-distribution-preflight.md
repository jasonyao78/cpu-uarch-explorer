# Q-A页集合/offset/order上板前软件出口

## 本次任务的目的（给人类看）

用 `docs/design/2026-10-11-tlb-page-distribution.md` 冻结v1，完成Q-A分布敏感性及局部refill响应的有限对照。本文仅软件与构建，不代替目标测量。

r2 `codex/sm8650-tlb-hierarchy-r2`；源57f96a9，consumer/build b6143a8，实际launch另记manifest。真实producer host计划145cell/435窗；全部144真实映射指针图/闭环/page-set/order/offset匹配，页集合不由order冒充。两次NDK27.2/API34静态O2构建SHA相同：5cb662dfd5e0d88cbc0502b510fc499a32de3f1dbdf103020f9c7c1ceec39cbf。实际ELF核独立Capstone逐指令核对，自依赖LDR/SUBS/B.NE无spill；证据 `docs/reviews/evidence/2026-10-11-tlb-page-distribution/{build,plan,code-audit}.json` / `decode.py`。

消费者背景门失败曾仍给curve interval/comparison replicated，两生产形态反例RED→GREEN修复；INCOMPUTABLE曲线及admissible/replicated门与全局INCONCLUSIVE贯穿，numeric_replicated仅数值保存。来源 `tools/diagnostic/tests/test_tlb_distribution_analysis.py`。

真实C++计划/图→registered driver→writer落盘→raw consumer成功5进程/2175窗（仅外部PMU/adb模拟）；25类重哈希反例拒绝，首bad-N停在1进程；旁路audit使停机测试RED。`tools/diagnostic/tests/test_tlb_distribution_{producer,analysis,raw}.py`。fresh diagnostic289/289，120.867s，完整本地日志 `/tmp/tlb-distribution-full-regression.log`；formal runner203/analysis250/CTest21是未改路径此前基线，不冒称本次fresh。

启动必经独占online/no-active/journal0、每块读环境/部署SHA/MIDR/4K；不写cpufreq/热策略。预算5×435窗完整不救门，UNKNOWN HPA/PTE_CONT不升级属性归因，诊断JSONL不是formal schema v2，main/远端本轮不操作。
