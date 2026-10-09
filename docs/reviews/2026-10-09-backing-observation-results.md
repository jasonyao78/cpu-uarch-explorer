# 256 MiB带仪表backing观测回执（2026-10-09）

## 本次任务的目的（给人类看）

独立审计 `data/private/20261009T091658Z-rob-backing-observe/` 的一次有限复现，判断本次失败属于已解析覆盖不匹配还是解析/I/O失败。**本次在initial backing验收因AnonHugePages未覆盖全映射而技术停块：Rss=256 MiB，AnonHugePages=224 MiB，差额32 MiB。** 单次观测目的已完成，没有PMU窗口，不能计算科学资格，不进入N扫描。该观察只归属于当前带仪表批次，不能追溯指定旧256/512 MiB失败为同一根因。

## 来源与工件

- 启动commit：`07bb9ba95e7427ab42ed6dcf1ee4e1e7c357c503`；binary source：`1474a7abca040fc01bf340b087bdb855811879e2`；binary SHA256 `3781b56f0e75926b153b47671b5ced0350fa2acdbd0debbf97e2d67873c6c6d1`。
- driver `tools/diagnostic/run_sm8650_minimal.py`，SHA256 `f359db5344d5fda3f74d7d9ad54774138ee316521158038dc4ca006f3b8ce42b`；协议 `docs/design/2026-10-09-backing-observation.md`，SHA256 `75cd71de9b3437891e64c8dfb3cd87952f4b6b2c94e90b3a66d3af1ecff9a25e`。
- 构建注册 `docs/reviews/evidence/2026-10-09-backing-observation/build.json`，SHA256 `d174e6517301ca036403c2611c5586eaa947286643685cf3252a2ef957854ff7`；私有manifest SHA256 `a7a6e26829d43718c0856935050a7102281a452b0de52b0cb2669103074a73ed`。
- 脱敏回执 `docs/reviews/evidence/2026-10-09-backing-observation/attempt.json`，SHA256 `eac7959e196f379d78cbcf24a1667578061a1d7b7239d5bf78fa0cdb5799ecfa`。包含完整config/failure、实际字段与逐项原谓词、两份生成码SHA、环境核验及**10个raw文件全部SHA256**。

saved driver与启动commit、protocol、build blob的SHA均独立复算匹配。构建的 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`、`probes/common/perf_group_read.h`、`probes/common/rob_backing.h` 在binary source和启动commit中均匹配注册SHA。binary绑定依据build、manifest和启动driver的部署SHA检查；raw无binary副本，本审计未操作设备，不能另称运行后再次hash了设备binary。

## 当前失败与停止纪律

注册mode=`rob-backing-observe`，仅 `e0-miss-m256-n0` 一个进程；CPU7/type8、N0/NOP/miss、seed42、chain8、alignment0、iterations2097152、3轮同VA paired，事件0x11/08/03/17/34/37。单次调用exit1，无timeout，host记录wall=0.188220秒；这只是整次调用耗时，不是映射或某个阶段的计时。manifest status=`stopped`，reason=`STOP probe failure e0-miss-m256-n0`。没有第二次尝试，没有runtime或round，没有PMU计数。

stdout SHA256 `810374cc8b0845842b6051de1ca466a14a60fcdd47339f06b21aebe50b20c337`，恰好config和下列failure两行：

```json
{"type":"failure","metrics":{},"failure":{"reason":"chase-backing-not-thp2m","backing_requested":"thp2m","memory_bytes":268435456,"pmd_bytes":2097152,"backing_status":"coverage-mismatch","backing_info":{"kernel_page_kb":4,"mmu_page_kb":4,"anon_huge_kb":229376,"rss_kb":262144,"swap_kb":0,"no_huge":false}}}
```

stderr为 `error[chase-backing-not-thp2m]: backing observation status=3`，SHA256 `098f6acce13216dfda1672391fbb1e5523d1452e9cb4c045ecf4d3d5fa802f4e`。按binary source的 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c` 初始分支，失败在映射、HUGEPAGE请求和环初始化之后，PMU setup之前。`probes/common/rob_backing.h` 的 `rob_backing_inspect()` 只有完整exact-VMA解析成功后才返回coverage-mismatch；wrapper的close失败会覆盖为独立状态。因此本次可区别于解析/open/close失败，实际字段不是零填充未知值。原始smaps片段未保留，公开证据是探针输出的完整脱敏字段及stdout SHA。

| 原验收项 | 当前观察 | 判定 |
|---|---:|---|
| Rss=memory/1024 | 262144 kB=256 MiB | 通过 |
| Swap=0 | 0 kB | 通过 |
| PMD=2 MiB，mapping长度为其整数倍 | 2097152 bytes，268435456 bytes | 通过 |
| AnonHugePages=memory/1024 | 229376 kB，要求262144 kB | **不通过** |
| no_huge=false | false | 通过 |
| Kernel/MMUPageSize为4或2048 kB | 4/4 kB | 通过 |

AnonHugePages/Rss=0.875，32 MiB未计入AnonHugePages。**这证明当前初始映射未满足full THP门，不证明为何出现缺口。** 不能仅凭该聚合观察命名物理碎片化、分配策略根因、未覆盖区域的精确位置或页子类型；Kernel/MMU为4 kB本身也不是本模式的失败项。

P/S两份host导出生成码均84字节，config逐项绑定实际config，仅paired=false和member serial不同。逐word验证初始化、alignment padding、两load、分支及RET；P SHA `a4b0acfd3d5425d45570d0fe2a16116f276ed18df193c7303bd27eca820b22ce`，S SHA `bc4e1aff0023d06ac0b163f57a40493501a0d8f6068a9839c6ef51ea83031568`。这些字节与旧N0生成码相同；成功导出不代表本次runtime backing或PMU测量成功。

initial、进程pre、final共3个环境端点完整保留；失败后没有post符合立即停止路径。saved policy与启动commit的 `configs/platforms/redmi-k70pro-01.json` charging-thermal profile加既有walt override一致，重新计算preconditions和相对initial稳定字段均通过，warnings/violations全部为空。端点max CPU温度38.0–40.7°C，final40.7°C。环境通过不能把coverage-mismatch解释成热失败，也不能解释其分配根因。

## 可命名结论与后续边界

完整summarizer CLI按complete guard拒绝本批，exit1且未写summary。该观察mode不在科学 `QUALIFICATION_MODES` 或 `tools/diagnostic/analyze_long_load.py` 的mode列表中，纯qualifier也拒绝；原c93逐轮科学门没有被评估。**当前可命名结论是“此单次256 MiB初始映射的已解析AnonHugePages覆盖率为87.5%，未通过full THP技术门”**。没有长load周期、miss率、配对比、headroom或物理ROB/DRAM结论。

`data/private/20261009T035527Z-rob-miss-wide-thp/` 的512 MiB和 `data/private/20261009T090043Z-rob-miss-fixed-thp/` 的256 MiB旧失败都缺实际字段；它们仍只能登记为未分型initial backing失败。当前仪表化结果不能回填或替它们指定根因。

根Agent提出下一步单独设计仅作用于自有mapping的一次同步MADV_COLLAPSE请求，相关新稿位于 `docs/design/2026-10-09-local-collapse-qualification.md`。本回执不启动该动作，也不假定调用可成功或其返回值可替代actual backing。若实施，应先完成独立source/binary/协议注册与软件契约验证，保留请求/返回状态和请求前后观察，仍以完整actual THP和每窗pre/post为硬门，再在新完整双epoch矩阵中沿原c93科学门裁定。不得改变sysfs/全局defrag、追加旧批次、重复直到成功或放宽覆盖门来救数据。
