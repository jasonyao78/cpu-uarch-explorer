# TLB history / 单页反证结果（2026-10-09）

## 本次任务的目的（给人类看）

检验此前 target100 的 W8 整圈高 walk 和 W9 较低现象能否直接解释为容量边界，区分准备历史、访问顺序与窗内试探的影响。执行按[冻结协议 `docs/design/2026-10-09-tlb-history-discrimination.md`](../design/2026-10-09-tlb-history-discrimination.md)，与正式 A1、旧 target100/200 批次分别汇总。

**技术审计通过；持久历史敏感门未通过。** F128/W8 的逆序 history DID 第一圈及 fading 门均通过4/5 epoch，正序仅3/5。epoch4 正序整圈8 walk，与相同准备规则下单页窗口率和1.75并存；这反对将整圈计数直接换算为窗前8页全部不驻留，但不能认证单页驻留概率或唯一替换机制。本轮没有测得或命名精确 ways。

## 覆盖与数据接受

匿名设备 `redmi-k70pro-01`，CPU7，MIDR `0x410fd821`，base4K；固定 target100、seed137、rotate offset、max12，保留本 mapping 的旧 collector prefix9。每个 `(H,W)` 只建链一次；全部 trajectory 与每个 victim 样本先做共同 `[F→history12]×8`，再请求的 `[F→history6/12]×8`。重复准备不是架构 TLB reset。

5进程各38 cells/800窗，共190 cells/4000窗：trajectory 2240、victim 1280、floor 480。全部 round0 保留，没有按大小删窗。每进程878条 JSONL、76个逐cell前后 backing 端点；全4000窗六计数有效、`enabled>0` 且 `running==enabled`。全部380个 backing 端点为4K/AnonHugePages=0。12个环境端点按启动 policy 重算通过，max CPU温度38.4–42.0°C。五组 VA 几何不同；不能据此认证 PFN 独立性。

[`tools/diagnostic/summarize_sm8650_minimal.py`](../../tools/diagnostic/summarize_sm8650_minimal.py) 与 [`tools/diagnostic/tlb_history_analysis.py`](../../tools/diagnostic/tlb_history_analysis.py) 已从 raw 重跑；另按 raw 六计数直接复算配对差、victim率和非零背景窗，结果一致。接受包括冻结 [`plan.json`](evidence/2026-10-09-tlb-history/plan.json) 的物理顺序、完整轮转、旧9页前缀/追加3页、两候选 leaf 排除、source/build/driver/stdout SHA与环境策略绑定。4000窗是相关的观测，不是4000个独立统计样本；门按5个 mapping进程分别判定，不用跨epoch均值救门。

## History 与方向对照

令 A=H1、C=H2。主差 `D=(A_hist12−C_hist12)−(A_hist6−C_hist6)`，同epoch/F/W/direction按步骤相减。下表每格为 **第1步 / 第8步 / 第16步 / 末4步均值**，单位 datawalk/窗口。

| F128 history DID | epoch0 | epoch1 | epoch2 | epoch3 | epoch4 | fading |
|---|---|---|---|---|---|---|
| W8 正序 | 0/0/0/0 | 3/0/0/−0.25 | 0/0/0/0 | 3/0/0/0 | 6/0/0/0 | 3/5，不通过 |
| W8 逆序 | 1/0/0/0 | 2/−1/1/−0.25 | 0/0/0/0 | 2/0/0/0 | 3/0/0/0 | **4/5，通过** |
| W9 正序 | 2/2/2/2 | 5/5/5/5 | 0/0/0/0 | 3/3/3/3 | 0/0/0/0 | 0/5 |
| W9 逆序 | 1/0/0/0 | 0/0/0/1.25 | −1/−1/0/−0.75 | 0/0/0/0 | 2/2/1/1.5 | 1/5 |

fading 原门为同epoch第一步 `|D|≥1` 且末4步 `|D|<0.5`，联合至少4/5；不会把起初无效称为消失。W8逆序通过的epoch为0/1/3/4，初始均为正；epoch2是保留的零效应反例。持久门要求末4步同一符号、各epoch幅度≥1、联合至少4/5，四组均未通过；W9正序仅3/5正向持续。

方向差为 `(A_forward−C_forward)−(A_reverse−C_reverse)`；完整负值与零值保留：

| F/W/history | 第1步，epoch0→4 | 末4步，epoch0→4 | fading | 持久同向计数 |
|---|---|---|---|---|
| 128/8/6 | 0,0,0,0,1 | 0,0.25,0,0,0 | 1/5 | 正0/负0 |
| 128/8/12 | −1,1,0,1,4 | 0,0.25,0,0,0 | **4/5** | 正0/负0 |
| 128/9/6 | 0,−1,−1,0,0 | 0,0.25,−1,0,0 | 1/5 | 正0/负1 |
| 128/9/12 | 1,4,0,3,−2 | 2,4,−0.25,3,−1.5 | 0/5 | 正3/负1 |
| 512/8/12 | 0,4,1,−1,3 | 0,0,0,0,0 | **4/5** | 正0/负0 |
| 512/9/12 | 0,5,1,−2,2 | 0,5,−1,−2,2 | 0/5 | 正2/负2 |

两组方向差虽然满足绝对值 fading 门，其初始均为3正1负，未通过同符号≥4/5的复制门。所有方向差的第1/8/16步及末4步同向门均未通过。F0的320个目标窗 datawalk全0，0x2f仅第一步可能为1；它支持本条件下的L1屏蔽，不能否定L2竞争。

完整140条16步曲线见 [`trajectory.png`](evidence/2026-10-09-tlb-history/trajectory.png) / [可缩放SVG](evidence/2026-10-09-tlb-history/trajectory.svg)；图保留全部方向和F512/F0控制，不将混合瞬态均值叫稳态。

## 单页对照：整圈计数不能直接换算初始驻留

下表每格为 **8个victim单页窗口率之和 / 同条件正序trajectory第1步walk**。每页8次重复准备；所有1280个单页窗口的0x34均为0或1，`count>1=0`，因此本批率和恰好也等于逐页平均计数之和。这一数值相等不能把窗口率认证为目标页miss概率。

| epoch | A/history6 | A/history12 | C/history6 | C/history12 |
|---|---|---|---|---|
| 0 | 0.25 / 2 | 1.5 / 2 | 0 / 0 | 0 / 0 |
| 1 | 0.25 / 3 | 1.75 / 6 | 0.125 / 1 | 0.5 / 1 |
| 2 | 1.375 / 2 | 1.25 / 2 | 0 / 0 | 0 / 0 |
| 3 | 0.5 / 2 | 1.5 / 5 | 0 / 0 | 0 / 0 |
| 4 | 0.25 / 2 | **1.75 / 8** | 0 / 0 | 0 / 0 |

最有辨识力的 epoch4/F128/W8：A/history12 正序16步为 `8,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0`，逆序为 `4,0,…,0`；A/history6正/逆首步为2/1，其余均0；C四条均0。

同epoch A/history12 的victim0→7窗口率为 `0,0,0,1,0.375,0.125,0.125,0.125`，和1.75。trial0→7每轮8victim平均计数为 `0.625,0.125,0.25,0.125,0.125,0.125,0.125,0.25`；前4均值0.28125、后4均值0.15625，漂移−0.125。轮转平衡了位置，却没有证明隐藏状态相同或样本独立。

这些观测符合窗内级联、试探扰动或准备残差，使“整圈8walk ⇒ 窗前8页全缺失”的直接解释失去依据；它们没有单独识别替换策略，也未排除descriptor/cache/隐藏索引及snapshot包装的背景。全部20个bundle、1280窗热图及整圈对照见 [`victim.png`](evidence/2026-10-09-tlb-history/victim.png) / [可缩放SVG](evidence/2026-10-09-tlb-history/victim.svg)。

## 非零背景与二进制边界

floor最大datawalk=1，**1/480**个floor窗非零：epoch0 `floor-b0-f0` round0，六计数 `[136,1,1,1,1,0]`。不能写作floor全0。

另有2/2240个trajectory窗的datawalk大于目标页数W，均在epoch1、H1/F512/history12/正序round0：W8为 `[485,11,9,12,9,0]`，W9为 `[522,12,10,13,10,0]`。这些记录完整保留，进一步要求将0x34解释为全窗事件计数，不能机械等同于不同目标页的初始缺失数。

ITLB最大=1，共 **5/4000**个非零窗，均为1；以下round/trial均从0起。全部窗口都满足 `0x2d=0x34+0x35`，这是本批计数一致性，不是逐load归因证明。

| epoch | cell | round/trial | trial_position / victim | 六计数（0x11,05,2d,2f,34,35） |
|---|---|---:|---|---|
| 0 | trace-h1-w9-f128-hist6-d0 | 0 | 0 / −1 | 376,14,4,16,3,1 |
| 1 | floor-b0-f0 | 0 | 0 / −1 | 95,0,1,2,0,1 |
| 2 | trace-h1-w9-f128-hist12-d1 | 15 | 0 / −1 | 466,14,4,23,3,1 |
| 3 | trace-h2-w9-f512-hist12-d1 | 8 | 0 / −1 | 350,13,1,22,0,1 |
| 3 | victim-h1-w8-f128-hist6-d0 | 0 | 0 / 0 | 141,4,1,6,0,1 |

已核对独立NDK27.2反汇编 [`binary-window-audit.txt`](evidence/2026-10-09-tlb-history/binary-window-audit.txt) 及绑定 [`binary-window-audit.json`](evidence/2026-10-09-tlb-history/binary-window-audit.json)：snapshot调用边界为 `0x244164→0x244210`，kind2唯一目标页指针读为 `0x244200`。窗内还有pages元数据读取、分支和snapshot用户态包装，因此只能称一次目标页probe，不能称整个计数窗只有一条load。源代码位置为 [`probes/diagnostic/tlb_history.cpp`](../../probes/diagnostic/tlb_history.cpp) 的measurement段及 [`probes/common/perf_window.h`](../../probes/common/perf_window.h) 的snapshot实现。

## 来源锚点与再生成

原始目录 `data/private/20261009T034442Z-tlb-history/` 保留，不入库；公开逐窗六计数、trial位置及条件见 [`summary.json`](evidence/2026-10-09-tlb-history/summary.json)，逐epoch门与诊断见 [`analysis.json`](evidence/2026-10-09-tlb-history/analysis.json)。

| 锚点 | 值 |
|---|---|
| binary源码commit | `2a37795107163a9c3effd8fc3e25410c0dd75695` |
| 启动commit | `8938afc302817598b9ec913b2379cc3887d77437` |
| binary SHA256 | `8d046bfb68370ccfd21b144864aa77d48f061398a694cae5e4d45732a884c22e` |
| 原始manifest SHA256 | `21f60c1782fd793f0b1eabbd46892ae5e3912a73acfc617757740040b18e138e` |
| 冻结plan SHA256 | `bb5e5ccd72874bfa2027c59d5f87c31bba0783fce32abf3fe91e898f554b0b23` |
| protocol SHA256 | `3a3ddf06e6245e71a1d83b8c6be6b4eeccc81c24a23afadf2ad9583c4ea306c8` |

[`build.json`](evidence/2026-10-09-tlb-history/build.json) 保存NDK/API/flags、source文件SHA和独立字节一致重建证据；auditor同时校验binary源码与启动commit处的这些文件。`analysis.json.input_sha256` 绑定精确公开summary字节。使用 [`plot.py`](evidence/2026-10-09-tlb-history/plot.py) 可从公开文件再生成两组PNG/SVG：

```bash
python3 -B tools/diagnostic/summarize_sm8650_minimal.py \
  data/private/20261009T034442Z-tlb-history \
  --output docs/reviews/evidence/2026-10-09-tlb-history/summary.json
python3 -B tools/diagnostic/tlb_history_analysis.py \
  docs/reviews/evidence/2026-10-09-tlb-history/summary.json \
  --output docs/reviews/evidence/2026-10-09-tlb-history/analysis.json
python3 docs/reviews/evidence/2026-10-09-tlb-history/plot.py  # requires matplotlib
```

本轮完成的是有限准备历史和整圈归因的局部反证。准备分布、descriptor竞争、物理cache/索引和有效容量仍需另案受控实验；不能从这4000窗直接命名8路或任何其他精确容量。
