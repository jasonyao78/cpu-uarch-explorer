# 实际 THP long-load 资格结果（2026-10-09）

## 本次任务的目的（给人类看）

检验完整 2 MiB backing 能否削弱长随机 load 的翻译干扰，并使其通过既有长锚点资格。独立从 raw 复算结果：**技术验收通过，科学资格不通过。** 长点实际 full THP、walk 降至约 10⁻⁶/iteration，但 64/128 MiB 的 L2 与 LL miss 代理率仍逐轮低于 1.8；64 MiB 另有 headroom、一个 epoch 的稳定性和配对差失败。**不能说只需大页即可合格，不进入 N 扫描，不命名 DRAM 或物理 ROB 容量。**

## 来源与复算

- 私有 raw：`data/private/20261009T033850Z-rob-miss-qualify-thp/`；manifest SHA256 `2b7fdcb1b164239fe669377917598487cb1e578b6b57c32748d0238d0b9f682d`。
- 启动 commit：`ba7b47a931a8d1814399823f46db7d5723262046`；实际二进制 source：`2a37795107163a9c3effd8fc3e25410c0dd75695`；binary SHA256 `afeafad4b9538768efacddf07ee50b5ba6b8795c70fdf5e070b246c5d1f7b161`。二进制来源以构建记录为准，包含窗前 backing 核验。
- 启动协议：`docs/design/2026-10-09-thp-load-qualification.md`，SHA256 `67bfbcdb7a1093383bb55f8e10e7f112981ff4e62510d0edadc5702b29cc7119`；构建证据：`docs/reviews/evidence/2026-10-09-long-load-thp/build.json`，SHA256 `08928b5d741df316d28897dda82103d6fafbbef924536febeeef7a9fa9bddf7a`。
- 科学门来源仍为 `c93e788a31c077f5575ef6139157b8fe3185bc0f` 的 `docs/design/2026-10-09-long-load-qualification.md`，SHA256 `7de293eff7033316c2f46a77025a688c7a26e3b6efe37ebe6f5b16b57a53d943`。没有以 THP 结果修改原门限。
- 脱敏全部 member/round 摘要：`docs/reviews/evidence/2026-10-09-long-load-thp/summary.json`，SHA256 `ff74a2b1242c60ebe0d01a78b92aa13f598f5eb768bbe4e27d75aca039a9a6de`。
- 逐窗原始计数、backing 前后值、SHA/环境绑定和完整逐门结果：`docs/reviews/evidence/2026-10-09-long-load-thp/qualification.json`，SHA256 `5b3da56c3a09e503111d9b0ea34fa73c6d29aa5879394c3535c4e886be193811`。
- 原始审计器：`tools/diagnostic/summarize_sm8650_minimal.py`；资格分析器：`tools/diagnostic/analyze_long_load.py`。独立脚本另从 raw 整数计数逐轮计算每项门，与 CLI 的全部 53 条失败门逐格一致；随后才核对临时摘要，两份 summary 逐值相同，qualification 除输入 summary 路径外逐值相同。保留所有失败窗口。

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/diagnostic/summarize_sm8650_minimal.py \
  data/private/20261009T033850Z-rob-miss-qualify-thp \
  --output docs/reviews/evidence/2026-10-09-long-load-thp/summary.json
PYTHONDONTWRITEBYTECODE=1 python3 tools/diagnostic/analyze_long_load.py \
  docs/reviews/evidence/2026-10-09-long-load-thp/summary.json \
  --mode rob-miss-qualify-thp \
  --raw data/private/20261009T033850Z-rob-miss-qualify-thp \
  --output docs/reviews/evidence/2026-10-09-long-load-thp/qualification.json
```

## 技术完整性与实际 backing：通过

6 进程、36 窗口全部完成，exit=0、无 timeout、stderr 为空。e0 footprint 顺序为 1/64/128 MiB，e1 反序；每进程 round0=P/S、round1=S/P、round2=P/S。全部成员使用同一新 binary；1 MiB 热点显式 4K，长点显式 thp2m。N0/NOP、seed42、CPU7、PMU type8、exclude_kernel/hv 和六事件集合均与启动参数一致。每进程前固定 15 秒暂停来自启动 driver；raw 没有独立 elapsed 暂停计时。

重新计算 saved driver、启动 commit 中 driver/protocol/build、构建记录中三个源文件在 binary source 与启动 source 中的 SHA、6 个 stdout、12 份生成码 SHA，均一致。P/S 生成码 SHA 分别为 `a4b0acfd3d5425d45570d0fe2a16116f276ed18df193c7303bd27eca820b22ce` / `bc4e1aff0023d06ac0b163f57a40493501a0d8f6068a9839c6ef51ea83031568`，与既有 N0 JIT 循环一致；运行时对齐 mod64=0、FPCR0。每进程六个事件 ID 唯一，全部窗口 enabled=running>0；retired 相对生成内核的残差均为 239 条，通过原计数容差。

| footprint | iterations/member/round | ring nodes=distinct lines/call | 请求/实测 backing | initial及所有pre/post观察 |
|---|---:|---:|---|---|
| 1 MiB | 131072 | 16384 | 4K/4096 bytes | Rss=1024kB，AnonHugePages=0，Swap=0，nh=true |
| 64 MiB | 524288 | 1048576 | thp2m/2097152 bytes | Rss=AnonHugePages=65536kB，Swap=0，nh=false |
| 128 MiB | 1048576 | 2097152 | thp2m/2097152 bytes | Rss=AnonHugePages=131072kB，Swap=0，nh=false |

共检查 **78 份 backing 观察**：6 份 runtime initial 和 36 窗口各前/后；其中长点 52 份均 full THP，热点 26 份均真 4K。精确单 VMA 的实际 Rss/AnonHugePages 全覆盖是验收依据，未把 MADV_HUGEPAGE 成功充当 backing 成功。所有记录的 KernelPageSize/MMUPageSize 都为 4k，与本协议 full THP 验收并不矛盾；`probes/common/rob_backing.h` 同时核验真实 PMD 大小与全量 AnonHugePages。端点验证不能证明窗口中从未短暂拆页。

14 份环境端点完整且 warnings/violations 为空。保存策略与启动 commit 中 `configs/platforms/redmi-k70pro-01.json` 的 charging-thermal profile 加既有 governor=walt override 精确一致；重新计算 preconditions 和稳定字段均通过。max CPU 温度端点范围 **37.6–42.6°C**；约定频率上下限、governor、屏幕、idle/service 等稳定字段无漂移。

## 冻结资格逐轮结果：不通过

原门逐项保留：长点 P/S 每轮 L1/L2/LL 均在 `[1.8,2.2]`/iteration，walk≤0.02；各 member cycles range/median≤0.10；所有配对 S/P 在 `[1.6,2.4]`；L2 与 LL 的 P/S 均值差除以两均值的平均≤0.10；P cycles 中位数≥max(同 epoch 热 P 中位数×4,171)；热点 P/S 每轮 LL≤0.1。64/128 分别要求两 epoch 通过，任何 epoch/member/round 的通过都不救另一失败单元。

以下三元组为 round0/1/2，计数率单位为事件数/iteration。展示值四舍五入，门限计算使用全精度 JSON。

| epoch/footprint/member | L1 refill | L2 refill | LL read-miss proxy | datawalk（×10⁻⁶） |
|---|---|---|---|---|
| e0/64/P | 2.000040,2.000031,2.000034 | 1.275051,1.156431,1.200804 | 1.132469,1.031340,1.073736 | 1.907349,1.907349,1.907349 |
| e0/64/S | 1.999943,1.999928,1.999947 | 1.082972,1.082310,1.088341 | 0.953749,0.954399,0.956108 | 1.907349,1.907349,3.814697 |
| e0/128/P | 2.000007,1.999996,2.000043 | 1.712734,1.635741,1.638153 | 1.709079,1.631802,1.635659 | 0.953674,0.953674,0.953674 |
| e0/128/S | 1.999856,1.999856,1.999835 | 1.661111,1.677352,1.678080 | 1.658647,1.675593,1.675284 | 0.953674,0.953674,1.907349 |
| e1/64/P | 2.000040,2.000021,2.000055 | 1.224777,1.221207,1.226868 | 1.088100,1.085211,1.099556 | 1.907349,1.907349,1.907349 |
| e1/64/S | 1.999926,1.999933,1.999935 | 1.158289,1.160461,1.156019 | 1.027121,1.023954,1.016665 | 1.907349,1.907349,1.907349 |
| e1/128/P | 2.000005,2.000016,1.999923 | 1.713025,1.691779,1.698432 | 1.711527,1.689581,1.696376 | 2.861023,0.953674,0.953674 |
| e1/128/S | 1.999846,1.999849,1.999838 | 1.716189,1.697101,1.733662 | 1.714530,1.695914,1.732227 | 0.953674,0.953674,0.953674 |

| epoch/footprint | P cycles三轮 | S cycles三轮 | S/P三轮 | P/S稳定性（range/median） | L2/LL均值相对差 |
|---|---|---|---|---|---|
| e0/64 | 171.775539,154.671528,161.956360 | 300.980387,300.845711,301.986540 | 1.752173,1.945062,1.864617 | **0.105609** / 0.003790 | **0.109982 / 0.122354** |
| e0/128 | 265.820630,253.944185,254.788873 | 514.755795,519.337859,518.603268 | 1.936478,2.045087,2.035424 | 0.046613 / 0.008835 | 0.005981 / 0.006606 |
| e1/64 | 161.574930,160.703312,162.100929 | 323.303150,322.232212,320.676987 | 2.000949,2.005137,1.978255 | 0.008650 / 0.008150 | 0.055426 / 0.064703 |
| e1/128 | 266.484733,263.047444,264.140209 | 530.420278,527.879097,536.270118 | 1.990434,2.006783,2.030248 | 0.013013 / 0.015820 | 0.008530 / 0.008826 |

热点 e0/e1 P cycles 中位数为 14.727921/14.495361，故长点 headroom 下限均为 171。64 MiB P 中位数为 **161.956360/161.574930**，两个 epoch 都失败；e0/64 的 round0 超过 171 不能替代中位数门。128 MiB P 中位数 254.788873/264.140209 通过。热点 P/S 所有轮 LL 最大值为 e0=0.000022888、e1=0.000007629，均通过。

| 独立单元 | 完整失败门 | 失败门数量 |
|---|---|---:|
| e0/64 MiB | P/S各3轮 L2、LL<1.8；P稳定性>0.10；L2与LL配对均值差>0.10；P中位cycles<171 | 16 |
| e0/128 MiB | P/S各3轮 L2、LL<1.8 | 12 |
| e1/64 MiB | P/S各3轮 L2、LL<1.8；P中位cycles<171 | 13 |
| e1/128 MiB | P/S各3轮 L2、LL<1.8 | 12 |

共 **53 条科学失败门**。所有长点 L1、walk、S/P ratio 通过；其余失败项如上，未因 full THP 而豁免。

## 可命名边界与下一反证

本批确证了**实际 full THP 下翻译 walk 率很低，但远层 miss 主导的双长 load 锚点仍未达到既有工程资格门**。相对 `docs/reviews/2026-10-09-long-load-4k-qualification.md` 的旧 4K walk 约 0.96–1.65/iteration，本批约 0.95–3.81×10⁻⁶/iteration，与削弱翻译干扰的方向一致；不能把本批 LL 率低于 2 自动解释成某一个缓存容量、预取器或预测机制。0x37 的远层 miss 代理身份仍不等于 DRAM。

新 source 在每窗 warmup 后、PMU enable 前读取 smaps；旧 4K binary 没有相同窗前步骤。即使 N0 JIT 字节一致，窗前 wrapper 也会改变 cache/TLB 状态。**旧 4K 与本批绝对 cycles 不构成同 binary、同流程因果配对**，不能用两批周期差宣称 THP 性能收益，也不能将 walk 的量级差外推成 ROB 容量结论。

下一轮尚未冻结，建议按可反证的问题选择最小控制：

1. **足迹残差优先：** 当前 128 MiB 的 L2/LL 约 1.63–1.73，明显高于 64 MiB 的约 0.95–1.28，但仍低于资格下限。用同 binary、实际 THP 扩大至 256/512 MiB，完整 ring iterations 分别至少 2097152/4194304；保留同 binary 的 1 MiB 4K 热点、两 epoch 反序、各3轮同 VA P/S和全部原科学门。该反证检验残留命中/请求比例是否随 footprint 改变，不预设它能排除访问预测。现有 `-m` 上限为512、`-i`足够，无需修改生成内核；下一协议必须显式注册新 footprint/身份及实际 backing/内存前置条件，当前分析器的64/128矩阵不能被绕过来接收新数据。
2. **更小的访问次序敏感性诊断：** 现有 `--seed` 可在固定128 MiB/full THP上做 seed42/137、两 epoch 反序的有限对照，不需新探针编码。它比扩大 footprint 更直接检验结果对地址访问次序是否敏感，但各进程重新 allocation，且 warmup/measurement 仍重复相同 ring；有差异也不能单独归因预取，无差异更不能证明随机指针已排除预取或已学会的预测。需单独预注册诊断身份，不能直接复用当前 seed42 资格消费者。
3. **更直接的代理分母诊断：** 若目标已确证支持并明确语义，可在单独非资格窗口利用既有 `-e` 配置，用 LL 读访问事件替换一个事件槽，与0x37一起观察远层请求数和 miss 数。这样可区分“到达远层的请求不足”与“远层请求中的 miss 比例不足”的不同预测，比继续扩大 footprint 更直接审查代理解释；事件 open 成功仍不等于语义确证，也不能据此识别预取单因。替换计数器的窗口缺原六事件集合，只能作诊断，原资格仍须完整事件和原门逐项通过。

当前最有依据的下一资格候选是同 binary 的更大实际 THP footprint；更小控制分别回答访问次序敏感性和代理分母问题，不能冒充关闭预取的直接反事实。本批失败记录保持公开脱敏审计，不晋升 baseline，不凭反复增大 footprint 或改门限保证得到 ROB 数字。
