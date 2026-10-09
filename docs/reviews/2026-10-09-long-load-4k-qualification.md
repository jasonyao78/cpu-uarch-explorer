# 4K long-load 锚点资格复核（2026-10-09）

## 本次任务的目的（给人类看）

独立复核 64/128 MiB 随机双链 load 能否作为 ROB 后续实验的长延迟锚点，严格应用采数前冻结的逐轮门限。结论：**技术验收通过，科学资格不通过；两个 footprint 均不可进入 N 扫描。** 不将远层 miss 代理命名为 DRAM，不将任何响应量换算为物理 ROB 条目。

## 输入、来源与可复算路径

- 冻结协议：`docs/design/2026-10-09-long-load-qualification.md`，commit `c93e788a31c077f5575ef6139157b8fe3185bc0f`，SHA256 `7de293eff7033316c2f46a77025a688c7a26e3b6efe37ebe6f5b16b57a53d943`。
- 私有完整 raw：`data/private/20261009T004419Z-rob-miss-qualify/`，manifest SHA256 `f859bb9aa570746686b5e0fa365b24e50a945310497b59ddc42df50b78b8b3b8`。raw 不入库。
- 实际启动 source：`c93e788a31c077f5575ef6139157b8fe3185bc0f`；二进制 source：`217e5e37a4fa6ce05cd948c264ceceae4fe36e71`。二进制 SHA256 `7d217b050ec08564e5c46160ae49dfc39ee02135adcefbce7e8f3a40e46af28d`，构建锚点为 `docs/reviews/evidence/2026-10-09-minimal-probes/build.json`。
- 脱敏摘要：`docs/reviews/evidence/2026-10-09-long-load-4k/summary.json`，SHA256 `fe7b7374ba1f3b2433dc03dc2dc679a5376200d1d5acf2ce066cf3d91b18890b`。保留 12 个 member 各 3 轮的全部事件率，未筛掉失败窗口。
- 资格与技术审计：`docs/reviews/evidence/2026-10-09-long-load-4k/qualification.json`。保留逐轮原始计数、enabled/running、生成码与 stdout SHA、环境端点 SHA、全部逐门值和失败门。
- 分析器：`tools/diagnostic/analyze_long_load.py`；测试：`tools/diagnostic/tests/test_long_load.py`。CLI 必须重新审计 raw 并与摘要精确比对，技术失败不写资格文件；科学失败正常写出完整结果。

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/diagnostic/summarize_sm8650_minimal.py \
  data/private/20261009T004419Z-rob-miss-qualify \
  --output docs/reviews/evidence/2026-10-09-long-load-4k/summary.json
PYTHONDONTWRITEBYTECODE=1 python3 tools/diagnostic/analyze_long_load.py \
  docs/reviews/evidence/2026-10-09-long-load-4k/summary.json \
  --raw data/private/20261009T004419Z-rob-miss-qualify \
  --output docs/reviews/evidence/2026-10-09-long-load-4k/qualification.json
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.diagnostic.tests.test_long_load -v
```

## 技术验收：通过

6 个进程按 e0=`1,64,128 MiB`、e1=`128,64,1 MiB` 顺序完成，exit=0、无 timeout、stderr 为空；每进程 3 轮 P/S，共 **36 个 PMU 窗口**。每进程的配对执行次序均为 round0=P/S、round1=S/P、round2=P/S。没有跨 epoch、footprint 或 member 合并来替换门限判定。

复算了 saved driver、启动 commit 中 driver/protocol/build evidence、构建记录列出的源文件、6 个 stdout 和 12 份导出生成码的 SHA。实际 config 均为 N=0/NOP/miss、paired、seed42、CPU7、PMU type8、exclude_kernel/hv，事件为 cycles/retired/L1D refill/L2D refill/datawalk/LL read-miss proxy。运行时 CPU7、FPCR0、loop address mod64=0，6 个事件 ID 在每进程内唯一。P/S 导出循环均 84 bytes、每迭代 4 条指令，两个 load 的串/并行依赖及后跳编码与 source 契约一致；P/S 同 VA 的地址序列契约来自该 source 的同 allocation 重链接构造，而非从 PMU 计数反推。

| footprint | iterations/member/round | ring nodes（每节点64B） | distinct lines/call | 覆盖 |
|---|---:|---:|---:|---|
| 1 MiB | 131072 | 16384 | 16384 | 全 ring，重复访问 |
| 64 MiB | 524288 | 1048576 | 1048576 | 全 ring，2i=nodes |
| 128 MiB | 1048576 | 2097152 | 2097152 | 全 ring，2i=nodes |

全部 runtime 报告 `mapping_4k_verified=true`。36 窗口 enabled=running>0，无 multiplex；retired 相对生成内核的残差为 238–246 条，均通过预注册计数容差，不能将调用框架也视为循环内指令。

14 个环境端点（初/终及每进程前/后）完整，原始 warnings/violations 均空；保存的 `environment-policy.json` 与启动 commit 中 `configs/platforms/redmi-k70pro-01.json` 的 charging-thermal profile 加 driver 唯一 governor=walt override 精确一致，重新计算 preconditions 和相对初始端点的稳定字段也均通过。max CPU 温度端点范围为 **39.2–46.7°C**，walt governor、各 policy min/max、screen/idle/service 等约定稳定字段无漂移。端点证据不代表窗口内连续监控。冻结 driver 在每进程前调用固定 15 秒暂停，raw 未另存 requested/elapsed 暂停时长，故这里只核验其静态执行策略，不声称有独立的暂停计时审计。

## 冻结资格门与逐轮结果

门限完全来自上述 c93e788 协议：长点 P、S **每轮** L1/L2/LL 率均在闭区间 `[1.8,2.2]`，每轮 walk≤0.02；各 member 三轮 cycles 的 range/median≤0.10；三对 S/P 均在 `[1.6,2.4]`；P/S 的 L2 与 LL 均值相对差≤0.10，分母为两个均值的平均；P 的 cycles 中位数≥max(同 epoch 热点 P 中位数×4,171)；热点 P/S 每轮 LL≤0.1。以下三元组依次为 round0/1/2，单位均为事件数/iteration，展示值四舍五入，判定使用 JSON 全精度。

| epoch/footprint/member | L1 refill | L2 refill | datawalk | LL read-miss proxy |
|---|---|---|---|---|
| e0/64/P | 1.999977,1.999973,1.999987 | 1.565674,1.469175,1.562225 | 0.970236,0.970392,1.044802 | 1.124277,1.116674,1.173885 |
| e0/64/S | 1.999968,1.999960,1.999962 | 1.454374,1.466244,1.425560 | 1.009014,0.995058,1.008472 | 1.036819,1.023762,1.025406 |
| e0/128/P | 1.999928,1.999931,1.999934 | 2.348103,2.326650,2.356265 | 1.554932,1.543859,1.549923 | 1.696710,1.681843,1.695523 |
| e0/128/S | 1.999880,1.999896,1.999900 | 2.345835,2.351001,2.308293 | 1.594462,1.594215,1.588066 | 1.695488,1.689718,1.678694 |
| e1/64/P | 1.999962,1.999962,1.999979 | 1.696066,1.717804,1.673504 | 0.979898,0.960506,0.962934 | 1.146461,1.109741,1.102980 |
| e1/64/S | 1.999939,1.999947,1.999945 | 1.631960,1.692211,1.650017 | 1.005686,1.051104,1.003798 | 1.039875,1.110479,1.033846 |
| e1/128/P | 1.999897,1.999887,1.999907 | 2.558327,2.481249,2.537983 | 1.613644,1.573753,1.605932 | 1.763128,1.712829,1.744240 |
| e1/128/S | 1.999880,1.999877,1.999880 | 2.522344,2.544724,2.501656 | 1.630115,1.647247,1.626175 | 1.727058,1.756310,1.720479 |

| epoch/footprint | P cycles三轮 | S cycles三轮 | S/P三轮 | P/S稳定性（range/median） | L2/LL均值相对差 |
|---|---|---|---|---|---|
| e0/64 | 197.159960,194.992813,208.945528 | 373.975447,369.837072,370.346182 | 1.896812,1.896670,1.772453 | 0.070769 / 0.011174 | 0.056109 / **0.101172** |
| e0/128 | 306.983602,306.153065,307.733301 | 610.336782,611.235643,607.505479 | 1.988174,1.996503,1.974130 | 0.005148 / 0.006112 | 0.003689 / 0.002007 |
| e1/64 | 202.135046,196.099289,195.301683 | 378.354616,402.653954,376.244164 | 1.871791,2.053317,1.926477 | 0.034846 / 0.069802 | 0.022499 / 0.053484 |
| e1/128 | 319.904988,311.774397,318.862913 | 628.290260,636.340954,626.319042 | 1.963990,2.041030,1.964227 | 0.025499 / 0.015951 | 0.001167 / 0.003137 |

热点 1 MiB 的 e0/e1 P cycles 中位数分别为 14.891533/14.484985，故长点下限均为 171 cycles；P/S 所有热点轮的 LL 最大值分别为 0.000015259/0.000022888。热点与 headroom 门均通过。L1 逐轮率、所有配对 S/P 和所有 member 稳定性门也均通过。

| 独立资格单元 | 不通过的冻结门 | 判定 |
|---|---|---|
| e0/64 MiB | P、S各3轮 L2<1.8、LL<1.8、walk>0.02；另 LL 均值差 **0.10117172646571425>0.10** | 不通过（19条失败门） |
| e1/64 MiB | P、S各3轮 L2<1.8、LL<1.8、walk>0.02 | 不通过（18条失败门） |
| e0/128 MiB | P、S各3轮 L2>2.2、LL<1.8、walk>0.02 | 不通过（18条失败门） |
| e1/128 MiB | P、S各3轮 L2>2.2、LL<1.8、walk>0.02 | 不通过（18条失败门） |

共 73 条科学失败门。**不能仅归为“翻译门失败”**：全部长窗口还违反 L2/LL 率门，e0/64 MiB 另违反 P/S LL 均值差门。尤其 128 MiB 的 L2>2/iteration 不能当作“两次需求 load 均必 miss”的证明；与高 walk 并存表明计数存在翻译活动等混杂，不能据本批归因到单一资源。

## 可命名结论与后续边界

最高可命名结论为：**4K 随机双链出现远层 miss 代理响应和约两倍串行 cycles；低翻译干扰、远层 miss 主导的双长 load 锚点资格未通过。** 0x37 是远层读 miss 代理，不能据此宣布 DRAM 延迟或 DRAM 主导，也不能估计物理 ROB 条目数。raw 技术有效、科学门失败，按冻结协议保留和公开脱敏审计，不删除失败记录或晋升合格锚点。

`docs/design/2026-10-09-long-load-qualification.md` 指定的显式 THP/2MiB 对照属于下一步诊断候选；本批同时失败的 miss 率及配对差门必须保留，THP 对照也需重新逐门合格后才能进入 N 扫描。`tools/diagnostic/analyze_long_load.py` 为 `rob-miss-qualify-thp` 提供显式 mode 入口并固定旧协议的 rates/阈值；未来原始 THP backing 必须先通过其生产 raw auditor 的 exact-VMA、真实 hpage size、前后 AnonHugePages 全覆盖检查，本文件的 mode 入口本身不证明 THP 成功。

软件验证为 **20 项 synthetic/隔离契约测试通过**，守护逐轮门、闭区间、同 epoch 热点、独立 footprint/epoch、P/S 比率方向、均值差分母、身份/非有限值、环境策略来源/快照漂移和技术失败不写出。它们不作为设备测量证据；设备事实仅来自上述 6 进程/36 窗口 raw 重放。扩大检查 `tools/diagnostic/tests` 时，唯一未通过项为并行实现中的 `test_minimal_audit.HistoryMatrix.test_only_registered_target_and_epoch_order`（当时 driver 尚未登记 `tlb-history`），已交主代理协调，未修改其文件。
