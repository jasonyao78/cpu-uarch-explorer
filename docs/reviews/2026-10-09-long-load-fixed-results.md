# 固定256 MiB长load资格：技术停块回执（2026-10-09）

## 本次任务的目的（给人类看）

独立核验 `data/private/20261009T090043Z-rob-miss-fixed-thp/` 的完整停止批次，区分已完成热点的技术事实与未能计算的长load科学资格。**本批技术不通过：e0/256 MiB在initial backing验收失败后按协议停止。** 只完成e0/1 MiB热点6窗；两个epoch的256 MiB均没有PMU窗口，不能给资格结论，**不进入N扫描**。

## 来源与公开工件

- 启动commit：`c2a44d2115103c39f66df2415fb22a31b04af7e0`；冻结协议 `docs/design/2026-10-09-fixed-load-qualification.md`，SHA256 `221e49b0165fa57efd9a86c4132c61ca87ed199d65c3cad8853f10fdab07cd89`。
- binary source：`2a37795107163a9c3effd8fc3e25410c0dd75695`；binary SHA256 `afeafad4b9538768efacddf07ee50b5ba6b8795c70fdf5e070b246c5d1f7b161`；构建注册 `docs/reviews/evidence/2026-10-09-long-load-fixed/build.json`，SHA256 `08928b5d741df316d28897dda82103d6fafbbef924536febeeef7a9fa9bddf7a`。
- driver `tools/diagnostic/run_sm8650_minimal.py`，SHA256 `662e49775be5909919fd809200668a56397967723f11a8bc7dd8f872d3437272`；私有manifest SHA256 `73783b49552f6020a3430850173cf9c2740b9d98bb96da3a3a6e670192b816c0`。
- 脱敏回执 `docs/reviews/evidence/2026-10-09-long-load-fixed/attempt.json`，SHA256 `b3dd736bd1ea1d2221d49a3e055e64a82be1180ab29ed2ccafce58e83cf84c7b`；保留全部6窗整数计数、config/runtime、13份成功backing观察、失败记录、5个环境端点核验及**16个raw文件全部SHA256**。

重算saved driver与启动commit、protocol、build的SHA；build列出的 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`、`probes/common/perf_group_read.h`、`probes/common/rob_backing.h` 在binary source和启动commit中的SHA均匹配注册。binary绑定依据构建注册、manifest及已冻结driver的部署SHA检查；本raw目录不保留binary副本，本次无设备操作，不能另称已在运行后重新hash设备binary。

## 停止位置与完整热点

| 注册位置 | 实际结果 | PMU窗 |
|---|---|---:|
| e0/1 MiB，4K热点 | 完成，exit0 | 6 |
| e0/256 MiB，THP长点 | initial backing失败，exit1，无timeout | 0 |
| e1/256、1 MiB | 未启动 | 0 |

注册4进程/24窗，实际1进程完成、1失败、2未启动。manifest status=`stopped`，reason=`STOP probe failure e0-miss-m256-n0`。失败stdout SHA256 `833bba3a7605b4e108c63022389e82fe4d1ff375c5986e6ef46dc791448c150e`；只有config和下列failure，无runtime、round或实际backing字段：

```json
{"type":"failure","metrics":{},"failure":{"reason":"chase-backing-not-thp2m"}}
```

stderr为 `error[chase-backing-not-thp2m]: Invalid argument`，SHA256 `8d09cda104a7a0dc94a67e98ab4eb26ca5e347b7a7933e1a8d1c638488c486b4`。与 `data/private/20261009T035527Z-rob-miss-wide-thp/` 的512 MiB **failure对象、stderr逐字相同，binary相同**；config/足迹不同，所以stdout整体SHA不同。相同reason不能证明相同根因，也不能断言partial THP。

两次失败都发生在binary source的 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c:271`：映射、HUGEPAGE请求和环初始化之后，PMU setup之前。其 `backing()` 在同文件168–174行合并smaps打开/解析、exact VMA、字段验收及close结果；`probes/common/rob_backing.h:42` 的parser和77行的matches均可使它失败。当前失败分支没有输出解析子原因、实际字段或smaps，不能区分精确VMA未命中、字段/读取失败、Rss/Swap/nh/THP覆盖验收失败等条件。此前wide的256 MiB成功前缀不能补本轮缺失观测，也不能当成本轮已通过。

热点stdout SHA256 `7df0383bb747ce02f7e4df6a39852a6764db663b580f8067f97e74ff48032167`。config为N0/NOP/miss、seed42、chain8、CPU7/type8、alignment0、3轮paired；runtime CPU7、FPCR0、实际loop mod64=0，6个事件ID唯一。每窗enabled=running>0，退休计数均524544；减去生成内核期望524305，残差均239，符合既有容差。initial和全部pre/post共13份观察均actual4K：Rss=1024kB、AnonHugePages=0、Swap=0、nh=true、Kernel/MMUPageSize=4k；ring_nodes=distinct_lines_per_call=16384，iterations=131072。4份host导出生成码均84字节，逐word验证寄存器初始化、对齐padding、两load、循环分支和RET；P/S唯一差异为第二load依赖x1或x0。导出成功不证明失败256的runtime backing成功。

热点的描述值如下，顺序为round0/1/2；全部整数事件计数另存attempt，不用于代替长点资格。

| member | cycles/iteration | L2 refill/iteration | LL miss/iteration | walk/iteration |
|---|---|---|---|---|
| P | 15.479797,14.433281,14.379845 | 0.040382,0.011292,0.008911 | 0.000007629,0,0 | 0.000061035,0.000038147,0.000030518 |
| S | 28.866455,29.874603,29.248184 | 0.020004,0.038956,0.027847 | 0.000015259,0,0 | 0.000015259,0.000030518,0.000007629 |

热点S/P为1.864782、2.069841、2.033971，P/S中位cycles为14.433281/29.248184，range/median为0.076209/0.034469。热点LL最大率0.000015259，小于原热点上限0.1；没有长点可与其计算同epoch headroom。

实际存在initial/final、热点pre/post及256 pre共5个环境端点，缺少失败256 post符合立即停止路径。saved policy与启动commit的 `configs/platforms/redmi-k70pro-01.json` charging-thermal profile加既有walt override完全一致；重新计算preconditions和相对initial稳定字段通过。warnings/violations全部为空，端点max CPU温度38.0–41.1°C，final为41.1°C。环境通过不能解释backing失败；final环境不是失败映射的smaps观察。

## 科学判定与观测缺口

`tools/diagnostic/summarize_sm8650_minimal.py` 完整CLI在complete/full-result-count guard拒绝本批，exit1且未写summary。`tools/diagnostic/analyze_long_load.py` CLI以临时、明确标记不完整的真实热点前缀作为拒绝测试输入，仍在raw同一guard拒绝，exit1且未写qualification；临时输入已删除，未产出伪完整summary。纯qualifier也以`qualification mode/process mismatch`拒绝1进程前缀。三条拒绝均在科学门之前，详见attempt的 `complete_consumers_rejection`。

原科学门来源仍是 `c93e788a31c077f5575ef6139157b8fe3185bc0f` 的 `docs/design/2026-10-09-long-load-qualification.md`，本批不修改、不评估长点逐轮门。结论为 **技术停块；科学资格不可计算；N扫描进入条件未满足**，不是“原科学门失败”，更不能命名DRAM主导或物理ROB容量。

观测缺口应在 `docs/open-items.md` 的ROB探针问题下明确登记为：**256和512的initial backing失败缺解析/验收分型及失败smaps，不同足迹相同reason尚不能定位原因**。下一次最小软件修补应保留失败stage、打开/读取/close errno、parser是否匹配exact VMA、缺失/重复字段mask及可解析的实际Rss/AnonHugePages/Swap/Kernel/MMUPageSize/nh与各验收predicate；缺字段用null，不用零冒充实测。失败时私有保存对应smaps片段及SHA，公开脱敏相对边界/长度和字段；解析失败也要留下诊断，不能仅补成功路径。该修补只增加观测，不放宽full THP门，不改全局defrag，不重试512来救批。新source/binary/协议需重新绑定后另开完整批次；当前停止批次保持封存。
