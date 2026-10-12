# Shared安装descriptor能力 Implementation Plan

## 本次任务的目的（给人类看）

执行 `docs/design/2026-10-12-translation-installation-read.md`，在自有read fault读取leaf+parent并验证两级关联。

**Goal:** 三进程能力和实际PTE/PFN身份，无猜基址、无重试。
**Architecture:** entry/return双KPROBE及128Bmap、guarded shared alias、不可变source重生计划与严格raw入口。
**Tech Stack:** C/NDK27.2/API34/独立BPF VM/Python/adb；single primary。

- [x] 实际producer缺失RED，创建 `probes/diagnostic/translation_install_bpf.h` / `probes/diagnostic/translation_install_read.c`；VM覆盖双过滤、合法entry/return、首错/重复/配对、全部read失败，GREEN。
- [x] `tools/diagnostic/translation_install_analysis.py` / `tools/diagnostic/translation_install_raw.py` / `tools/diagnostic/run_sm8650_translation_install.py`；实际producer→driver→落盘→raw、typed/PFN/两级bias不同/缺失/不触发/拒绝反例；scope先冻结，不借前次COW。
- [x] 两NDK/真实plan/全部注册source binding，关联新旧测试通过；commit launch，idle/unfinished/BTF/MIDR/部署/环境全门后3进程，首不合格停。
- [x] raw独立第二算术及匿名能力/读数/完整SHA归档，更新状态/open-items/记忆；physical capacity与steady CONT/HPA不自动认证。
