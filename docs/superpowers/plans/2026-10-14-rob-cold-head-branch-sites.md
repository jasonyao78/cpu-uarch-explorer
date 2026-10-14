# 分支PC反证实施计划

## 本次任务的目的（给人类看）

实现 `docs/design/2026-10-14-rob-cold-head-branch-sites.md`。primary内联执行，无常规人工节点。

- [ ] `tools/diagnostic/tests/test_rob_cold_head_branch_sites.py` RED：actual native每layout512schedule中code/branch offset、同role两state是否共享、packet512不同PC/页边界；controller必须共享consumer协议路径。
- [ ] producer `probes/diagnostic/rob_cold_head_branch_sites.c`：base和active code指针分开，actual per-packet offset/branch_pc，mprotect/munmap只基址；原ROI words/ABI/own current binding保留。
- [ ] consumer `tools/diagnostic/rob_cold_head_branch_sites_analysis.py`：逐word/native/current index/实际位置与state完整度/FD审计，12配置主packet强机会与全部controls分列。
- [ ] controller `tools/diagnostic/run_sm8650_rob_cold_head_branch_sites.py`：精确freeze/source/build、known probes idle、双journal检查，6144/24576固定完整度、durable restore/readback。
- [ ] 局部tests RED→GREEN、旧8192 raw不改判、小步source提交；NDK双build/actual native双index/Capstone；build提交。
- [ ] 独占上板，原始所有counts/失败私有；同primary第二算术/全SHA/实际current位置和joint复核，报告并记open-items/workflow/memory。
