# Wide THP 停止批次审计（2026-10-09）

## 本次任务的目的（给人类看）

审计 256/512 MiB wide THP 尝试的完成前缀和技术失败，保留实际观察，不把不完整矩阵转成资格通过。结论：**批次在 e0/512 MiB 的 initial backing 验收失败后按冻结协议停止。** e0 的热点与 256 MiB 共12窗技术审计通过；没有 e1，不能做完整科学资格裁定，不能进入 N 扫描。

## 来源与工件

- 私有 raw：`data/private/20261009T035527Z-rob-miss-wide-thp/`；manifest SHA256 `2b7a8222e911c486556b28f90055d86910801e6277b36945c568201a9fcfaa16`。
- 启动 commit：`7c19814ee8ecd93747c4111ee0c4b1b5f26dfb68`；二进制 source：`2a37795107163a9c3effd8fc3e25410c0dd75695`；binary SHA256 `afeafad4b9538768efacddf07ee50b5ba6b8795c70fdf5e070b246c5d1f7b161`。同一 binary 已用于 `docs/reviews/2026-10-09-long-load-thp-results.md`。
- 启动 driver：`tools/diagnostic/run_sm8650_minimal.py`，SHA256 `f16b667f5a2fd6bb485f12ed1a34373ffe7765ca1bd2cbfd177bc2fa6ac212bf`；冻结协议：`docs/design/2026-10-09-wide-load-qualification.md`，SHA256 `7fec8c457fdbf4cce4b09be3c65db995e1e93952706979818d36605fda77667a`。
- 构建注册：`docs/reviews/evidence/2026-10-09-long-load-wide/build.json`，SHA256 `08928b5d741df316d28897dda82103d6fafbbef924536febeeef7a9fa9bddf7a`。它由原负责人提交，本次没有改动。
- 脱敏前缀/失败证据：`docs/reviews/evidence/2026-10-09-long-load-wide/attempt.json`，SHA256 `f21ef69205c12569ebac4262995334fd824f7a1816a387a564246d6d2f087bb9`。包含全部12窗整数计数、各窗前后 backing、两个 runtime、512失败原文、完整/缺失矩阵、环境核验及 **22个raw文件全部SHA256**；三个构建源文件的SHA单列在 `build_source_sha256`。

独立重算 saved driver 与启动 commit driver、protocol、build evidence；构建列出的 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`、`probes/common/perf_group_read.h`、`probes/common/rob_backing.h` 在 binary source 和启动 source 中的 SHA 均与注册一致。三个 stdout、六份 P/S 导出生成码也逐一匹配 manifest。没有调用要求 complete 的 `tools/diagnostic/summarize_sm8650_minimal.py` 或 `tools/diagnostic/analyze_long_load.py` 来给本批资格结论，没有伪造缺失窗口或将失败 metrics 填零。

## 停止边界与完成前缀

| 位置 | 结果 | PMU窗 |
|---|---|---:|
| e0/1 MiB，4K热点 | 完成，exit0 | 6 |
| e0/256 MiB，THP长点 | 完成，exit0 | 6 |
| e0/512 MiB，THP长点 | initial backing验收失败，exit1、无timeout | 0 |
| e1/512、256、1 MiB | 未启动 | 0 |

注册矩阵为6进程/36窗，实际仅2进程完成、1进程失败、3进程未启动。manifest status=`stopped`，reason=`STOP probe failure e0-miss-m512-n0`。512 stdout SHA256 `8e5b56a5318a374ad781226ba08c4e0f947cc7cade8f8bd51da92a8caa07811b`；其内容只有 config 和下列 failure，没有 runtime、backing-info 或 round：

```json
{"type":"failure","metrics":{},"failure":{"reason":"chase-backing-not-thp2m"}}
```

stderr SHA256 `8d09cda104a7a0dc94a67e98ab4eb26ca5e347b7a7933e1a8d1c638488c486b4`，原文为 `error[chase-backing-not-thp2m]: Invalid argument`。源码在 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c:271` 的 initial `backing(...)` 复合验收失败后返回该 reason。失败分支未输出具体 smaps/字段/解析子原因，stderr 也不能分型。**不能断言一定 partial THP**，也不能定位成 exact VMA、parser、覆盖或其他 backing 验收子条件中的某一个失败。六份导出生成码都存在，只证明 host export 完成，不证明512运行时 backing 成功。

完成前缀的 config 为 N0/NOP/miss、seed42、CPU7/type8、完整六事件、paired三轮。每进程 P/S 顺序为 P/S、S/P、P/S；runtime CPU7、FPCR0、实际 loop mod64=0，各六个事件ID唯一。全部12窗 enabled=running>0，无mux，retired相对生成内核残差均239条，符合既有计数容差。

热点 iterations=131072，ring_nodes=distinct_lines=16384，实际4K、AnonHugePages=0、Rss=1024kB、Swap0、nh=true。256 MiB iterations=2097152，ring_nodes=distinct_lines=4194304，即2i覆盖整个ring；actual page bytes=2097152，initial及全部pre/post均 Rss=AnonHugePages=262144kB、Swap0、nh=false、Kernel/MMUPageSize=4k。共核验26份完成前缀 backing 观察，256长点13份均 full THP；512无对应实测观察。

实际存在的7个环境端点为 initial/final、两个完成进程各pre/post及512的pre。立即停止发生在512的post之前，不能把final当成512的backing诊断。保存策略与启动 commit 的 `configs/platforms/redmi-k70pro-01.json` charging-thermal profile 加既有 governor=walt override 精确一致；重新计算 preconditions/稳定字段通过。所有 warnings/violations为空，max CPU温度端点范围38.0–40.7°C，final为39.9°C。final环境干净不解释此次backing失败。

## 256 MiB 单epoch描述，不作资格判定

以下三元组按round0/1/2，计数率均为事件数/iteration；所有窗口均保留。数字可与既有门作描述性比较，但不能替代完整双epoch注册矩阵。

| member | cycles | L1 refill | L2 refill | LL read-miss proxy | datawalk（×10⁻⁶） |
|---|---|---|---|---|---|
| P | 299.331600,299.693715,300.862088 | 2.000017,1.999991,1.999990 | 1.903977,1.907617,1.915188 | 1.903342,1.906898,1.914394 | 0.476837,0.953674,0.476837 |
| S | 595.149930,595.922251,595.420318 | 1.999831,1.999833,1.999826 | 1.910890,1.912720,1.910748 | 1.910348,1.912266,1.910272 | 1.430511,1.430511,0.953674 |

S/P 三对为 **1.988263、1.988438、1.979047**；P/S cycles range/median分别为0.005106841/0.001297103。P/S的L2、LL均值相对差分别为0.001322114/0.001440310，分母为两个均值的平均。同epoch热点P中位cycles=15.229790，参考下限max(4hot,171)=171；256的P中位cycles=299.693715。热点P/S各轮LL最大值为0.000038147。描述值显示256值得在新完整矩阵中复验，**不表示本批256已通过科学资格**。

## 下一步边界

不重试512，不改全局defrag/THP策略，不向这次stopped批次追加e1来补救。下一轮优先将256固定为唯一长点，独立预注册 `rob-miss-fixed-thp`：两epoch顺序1/256和256/1、同binary4K热点、实际256 full THP、各3轮同VA P/S，共 **4进程/24窗**；重新采集完整批次。原逐轮率、walk、稳定性、配对差、同epoch热点/headroom和两epoch均通过才eligible的科学标准保持不变，旧wide前缀仅作描述，不能晋升或拼入新批。

若后续完整256资格仍失败，可独立设计固定footprint的编码地址/访问次序对照，以区分地址相关预测或命中残差；此类新对照需单独冻结，不能把随机指针当成已排除预取，也不能改动既有资格门来救结果。当前可命名量只限上述实际256观测；没有DRAM主导或物理ROB容量结论。
