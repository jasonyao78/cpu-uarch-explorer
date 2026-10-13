# 临时perf用户访问profile的自有元数据资格 v1.0（无MRS）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-13-pmu-user-metadata-results.md` 证明policy0下cap=true/index0不能直接读。现在只验证官方接口的临时policy1是否给自己的long64事件暴露合法index/width，仍不执行PMU寄存器读取。新协议承认host临时改一个全局sysctl，producer `probes/diagnostic/pmu_user_reader.c` 本身不写策略；不能把两者混说“全程无设置改动”。不回救SB旧N0。

## 注册条件和恢复事务

source/binary使用metadata-only已审代码（C3d13bc5/buildccece66，SHA5a367fcf16974954b488227902ebe05fd34cba6c6493b999c988013458458006），三fresh固定flag3（user-access+long）。先exact源码／双NDK/plan／设备MIDR=0x410fd821、4KiB、无并发probe／runner unfinished journal、基线环境和当前perf_user_access=0。另建private write-ahead事务state=created、baseline0，写盘后才apply1；命令真实stdout/stderr/rc及readback记录，readback1才state=applied。进程间15秒固定；自己的4个pinned USER-only perf metadata；所有map/FD关闭，不执行MRS。

三process全部policy1、真实cap=true、index1–32且四个unique、width64、seq前后相同偶数、CPU7／result完整才METADATA_PREREQUISITES_OBSERVED，仍counter_read_qualified=false。首次拒绝／index0／width不足／seq异常即命名停止，不调flag、不重试、不猜index；全部raw保留，不能当物理ROB单位或容量。

**finally必须恢复baseline0并读回验证**，成功state=restored，失败state=restore-failed及两错误保存，无论work成败都持久化。状态applied/restoring/restore-failed等未终态阻止下一实验；恢复只能使用下述工具，不手改journal。异常原始原因和restore原因分别保留，真实exit不接tail。设备意外／journal不能闭环则停止并回传。

## 实现与复核

controller `tools/diagnostic/run_sm8650_pmu_enabled_metadata.py`，纯恢复原语 `tools/diagnostic/perf_user_access_transaction.py`，tests同名，已交付，4恢复异常与3完整controller生产链测试通过；private `data/private/perf-user-access-transactions/`登记，metadata raw在其工作目录。记录global setting host0→1→0与producer register reads0，不暗改baseline／别的频率policy。所有样本／源码／调用／配置／baseline与恢复谱系清楚，source/plan/build/launch独立SHA。后续counter direct MRS要自己的当前FD/index/seqlock/width/offset/wrap/actual正控独立资格，不复用本metadata snapshot。

官方Linux接口 https://www.kernel.org/doc/html/v6.16/arch/arm64/perf.html ，版本仅指导，以target真实metadata为证。purpose primary branch codex/sm8650-tlb-hierarchy-r2独占；原TLB27矩阵已完成，不并发。恢复命令（已交付）：`.venv/bin/python tools/diagnostic/run_sm8650_pmu_enabled_metadata.py --restore data/private/perf-user-access-transactions/<tx>.json`，只恢复该已登记baseline，check ownership／实际状态，不覆盖别人的事务。只有metadata-only，不执行MRS。
