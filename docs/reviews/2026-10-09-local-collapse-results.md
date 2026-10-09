# 局部同步THP合并资格：技术停块回执（2026-10-09）

## 本次任务的目的（给人类看）

独立审计 `data/private/20261009T093842Z-rob-collapse-qualify/` 的完整停止批次，检验单次局部MADV_COLLAPSE请求与原full THP门是否通过。**本批技术不通过：e0/256 MiB的唯一请求返回-1/ENOMEM，前后映射均未满足full THP门，按冻结协议停止。** 仅e0/1 MiB热点6窗完成，两个epoch的长点没有PMU窗口；原c93科学资格不可计算，**不进入N扫描**。没有重复请求或将旧前缀拼入本批。

## 来源与工件

- 启动commit：`68f0991c7b9a54915bea6ee1a3cc95e88f9fe775`；binary source：`3b4e66db0b4804106a277b7ec41dcf9a71e454e9`；binary SHA256 `29d8c8b844183bdfa05288d60fb07f6966bb24174e2310af68866c86cb6dd74a`。
- driver `tools/diagnostic/run_sm8650_minimal.py`，SHA256 `f7bf163ddaf43d1a62ffb3d6741ea6f5cac4292856e4673106963c7efdc7e8af`；协议 `docs/design/2026-10-09-local-collapse-qualification.md`，SHA256 `5790d606f64a095bc03f5faa23ed9656779a9bf5267ff4cf9f702a6fcf4cbd85`。
- 构建注册 `docs/reviews/evidence/2026-10-09-local-collapse/build.json`，SHA256 `ee50de89534286a67e1b07b2a6d3c16748b4eb908e319b731442cb2c4a14365b`；私有manifest SHA256 `b767853cec1bdcc80f70614c026967b4f964ce0096396a1a22a6402045cdc1d9`。
- 脱敏回执 `docs/reviews/evidence/2026-10-09-local-collapse/attempt.json`，SHA256 `37c96dff7c959325ab6b572acd98b269e9f23412229c9e7b5ceaaaafd0687bd5`。保留完整collapse receipt、config、failure、热点6窗全部整数计数及13份backing观察，列出**16个raw文件全部SHA256**。

saved driver与启动commit、protocol、build blob的SHA独立复算匹配。build的 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`、`probes/common/perf_group_read.h`、`probes/common/rob_backing.h` 在binary source和启动commit中均匹配注册SHA。binary绑定依据build、manifest和冻结driver的部署SHA检查；raw无binary副本，本审计未操作设备，不能另称运行后重新hash了设备binary。

## 停止位置与唯一请求

| 注册位置 | 实际结果 | PMU窗 |
|---|---|---:|
| e0/1 MiB，4K热点，无collapse | 完成，exit0 | 6 |
| e0/256 MiB，THP+collapse | 单次请求失败，exit1，无timeout | 0 |
| e1/256、1 MiB | 未启动 | 0 |

注册4进程/24窗，实际1进程完成、1失败、2未启动。manifest status=`stopped`，reason=`STOP probe failure e0-miss-m256-n0`。失败stdout SHA256 `7576236a5c4a188b13893fadb36edcb23bc1f5d947eef2d524b3de28ba5fee00`；恰好config、backing-collapse、failure三行，无runtime或round。config明确 `collapse_requested=true`，N0/NOP/miss、seed42、chain8、alignment0、iterations2097152、3轮paired、CPU7/type8、事件0x11/08/03/17/34/37，与注册请求逐项相符。

完整receipt记录请求memory_bytes=268435456、PMD bytes=2097152、return_code=-1、errno=12；before_status和after_status均为coverage-mismatch。失败记录仍为空metrics：

```json
{"type":"failure","metrics":{},"failure":{"reason":"collapse-syscall"}}
```

stderr为 `error[collapse-syscall]: Out of memory`，SHA256 `14880b4f2035a7d939a02c9a16d67081162654b9e8014a28b10aec67fd9f4681`。host记录该次调用wall=0.211432秒，是整次探针调用耗时，不是collapse阶段计时。已绑定的probe source仅在环初始化后、初始验收/PMU之前对自身映射调用一次常量25的madvise；保存call errno后采集post，随后以原errno返回failure。raw中唯一receipt的位置与该顺序一致，没有后续P/S测量或重试。

| 已解析字段 | 请求前 | 请求后 |
|---|---:|---:|
| Rss | 262144 kB=256 MiB | 262144 kB=256 MiB |
| AnonHugePages | 227328 kB=222 MiB | 243712 kB=238 MiB |
| Rss减AnonHugePages | 34 MiB | 18 MiB |
| AnonHugePages/Rss | 86.71875% | 92.96875% |
| Swap / no_huge | 0 / false | 0 / false |
| Kernel/MMUPageSize | 4/4 kB | 4/4 kB |

两次观察均完成exact-VMA解析，其他原backing字段符合门，但AnonHugePages都小于映射256 MiB；post不能替代成功返回，也没有通过覆盖门。前后AnonHugePages增加16 MiB是本次观察，不能命名为整个请求成功、完整大页建立或全局内存耗尽的证明。ENOMEM也不能独自定位物理碎片化、目标内核具体分配失败路径或缺口页的精确位置；原始smaps段未保留，证据为完整脱敏receipt及stdout SHA。旧未带仪表的256/512失败和先前单次observer属于其他批次，不能回填为本次collapse-syscall根因。

## 热点、生成码与环境

热点stdout SHA256 `14e5a1dffe305611f53a508a2e7870dc29ada185a8dc7b12e09aa92db8321e4d`。hot config无collapse请求；runtime CPU7、FPCR0、actual loop mod64=0，6个事件ID唯一，ring_nodes=distinct_lines_per_call=16384，iterations131072。13份initial/pre/post观察均actual4K：Rss1024kB、AnonHugePages0、Swap0、nh=true、Kernel/MMU4k。六窗enabled=running>0，无mux，退休数均524545；减去生成内核期望524305，残差均240，符合既有容差。

热点的round0/1/2描述值为：

| member | cycles/iteration | L2 refill/iteration | LL miss/iteration | walk/iteration |
|---|---|---|---|---|
| P | 14.620430,14.510643,14.525909 | 0.016747,0.015800,0.016357 | 0.000053406,0.000007629,0.000007629 | 0.000007629,0,0 |
| S | 28.853127,28.735100,28.549187 | 0.021049,0.018280,0.016747 | 0,0,0 | 0,0,0 |

热点S/P为1.973480、1.980277、1.965398，P/S中位cycles14.525909/28.735100，range/median0.007558/0.010577，LL最大率0.000053406。它们不替代缺失长点，也不与旧binary的绝对周期作因果配对。全部六事件的原始整数计数与派生率保存在attempt。

四份host导出码均84字节，config逐项绑定各actual config；每份完整word验证初始化、alignment padding、两load、循环分支和RET。P SHA `a4b0acfd3d5425d45570d0fe2a16116f276ed18df193c7303bd27eca820b22ce`，S SHA `bc4e1aff0023d06ac0b163f57a40493501a0d8f6068a9839c6ef51ea83031568`；hot/long及旧N0均相同。成功导出不证明长点runtime mapping或PMU测量成功。

initial/final、hot pre/post及256 pre共5端点完整保留，失败后缺post符合停块路径。saved policy与启动commit的 `configs/platforms/redmi-k70pro-01.json` charging-thermal profile加既有walt override一致；独立重算preconditions和相对initial稳定字段通过，warnings/violations全部为空。端点max CPU温度38.4–41.5°C，final41.5°C。环境端点不是内存分配根因或窗内状态的证明。

## 科学裁定与后续边界

完整summarizer和analysis CLI均在complete/full-result-count guard以exit1拒绝本批，未写summary或qualification。analysis拒绝测试只使用临时、明确不完整的真实热点前缀，已删除；纯qualifier也拒绝1进程覆盖。原科学门 `c93e788a31c077f5575ef6139157b8fe3185bc0f` / `docs/design/2026-10-09-long-load-qualification.md` 没有被评估或修改。

**结论：本批技术停块，科学资格不可计算，N扫描进入条件未满足。** 单次局部同步请求未形成可接受的256 MiB长load锚点，不能用请求前后增加的AnonHugePages、旧成功256单epoch或热点窗口救资格；没有DRAM主导或物理ROB结论。

按本轮冻结边界不再启动相同矩阵追门，不改sysfs/全局defrag、不降低full THP或原c93门。后续应转独立设计的小足迹地址编码/访问次序对照，并在 `docs/open-items.md` 跟踪局部collapse可用性与长load激励未资格的问题；当前raw及失败receipt保持封存。新设计需以它自身完整注册的技术与科学契约判定，不能把本批事后改名为合格样本。
