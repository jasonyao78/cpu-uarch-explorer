# SM8650 TLB：反证对照与局部转折

## 本次任务的目的（给人类看）

尝试推翻 `docs/reviews/2026-10-09-sm8650-bit-axes-exploration-results.md` 的初步解释：当前低 VPN 字段集中条件的高 L2 refill 来自目标数据翻译冲突。先分离指令/数据来源、区域页表 footprint 与 filler 暴露条件，成立后才扫局部转折。用户已授权当前 Agent 独占手机端到端执行；ROB 仅并行软件研究。

## 固定条件与取舍

复用 `probes/cache-mem/ptr_chase.cpp`，不改生成码、窗口或正式 A1 配置。CPU7 X4、4KiB base 页、pool65536、seed42、r20（19有效轮），每条件5个新进程。保留 stock walt，不改 governor/min/max/服务；沿用 `docs/runbooks/2026-10-09-sm8650-bit-axes-exploration.md` 的 profile 与前后环境审计。短条件逐个真实 plan→run_plan→raw/record→load_audited_run→validate_record，全部输入及脚本保存私有目录。

原四事件 cycles(0x11)、L1D_TLB_REFILL(0x05)、L2D_TLB_REFILL(0x2d)、L2D_TLB(0x2f) 加 DTLB_WALK(0x34)、ITLB_WALK(0x35)，type8；六事件同窗，无 mux 才保留。Arm 官方定义 0x2d 包含指令与数据来源，0x34/35 分别对数据/指令导致的 refill 计数，见 https://raw.githubusercontent.com/ARM-software/data/master/pmu/cortex-x4.json 。事件名 l2d 不代表只统计数据。

## 第一段：采数前固定的反证包

target200、W12（floor 为0）。顺序如下；A/C 末尾复测检查时间方向。每一行单独保存，绝不拼进正式 48/48/32 合同。

| 顺序 | 条件 | C / K / scope / F | 要推翻的解释 |
|---|---|---|---|
| 1 | floor-k4 | 1 / 4 / 0 / 512 | 窗口背景已足以产生高 walk |
| 2–3 | A512 / C512 | 1或2 / 4 / 0 / 512 | 高 refill 主要来自指令翻译，而非数据翻译 |
| 4–6 | A0 / C0 / floor0 | 1或2 / 4 / 0 / 0 | 对 filler 的依赖；L1 不暴露时低 walk 不能作为 H1 反证 |
| 7–8 | C128 / A128 | 2或1 / 4 / 0 / 128 | 换较轻 filler 后签名反转；须联看0x05/0x2f确认L2暴露 |
| 9–11 | B / D / floor-k12 | 1或3 / 12 / -1 / 512 | B 高仅因12个区域的页表 footprint |
| 12–13 | C512-end / A512-end | 2或1 / 4 / 0 / 512 | 时间、热或进程顺序决定了高低分组 |

A/C 在 H1 模型下最大目标占位分别12/1。B/D 均每区域1页：H1 下12/1，H3 下1/12；生产 `probes/common/tlb_set_layout.h` 与 `probes/common/tlb_set_collect.h` 的纯整数检验覆盖 target100/200、256个起始高字段、raw页偏移0/1/65535，共1536布局：B/D 的每区域 VA>>21 相同。D 的其它模型占位随实际高字段变，不声称固定四模型签名。target200 的 A/C 在计划的局部W点上逐地址 VA>>21 也匹配；target100 后续重复只保证相同leaf-table页数，部分页前缀不同，不能称逐页完全匹配。这控制常规4KiB页表的 leaf-table 页前缀数量，未控制所有物理 cache 状态或页表中间项替换。

本段是反证筛选而非统计显著性检验。只有 A512 首尾及 B 的数据 walk 最小值分别高于配对 C/D 最大值至少3 events/轮、floor/C/D 的数据 walk 最大值≤0.5，且 A/B 的中位 DTLB_WALK 至少解释中位0x2d的80%，才继续当前解释下的局部扫描。否则先报告是哪条预测失败，不改阈值挽救。F0/F128 对照单独报告，包括0x05/0x2f；F128不够暴露L2不会否定F512，也不把 F0 低读数解释为无冲突。全部正反例都保留。

## 第二段：局部扫描（第一段满足后执行）

先用 target200、F512，A/C 成对 W={6,8,10,12} 各5进程，共40进程；顺序 W8(C,A)→W12(A,C)→W6(C,A)→W10(A,C)，不单调升压。W12相当于新epoch正负控。初步响应仅定义为 A 的数据 walk 中位≥2.0 且 C中位≤0.5；2.0只是本次探索夹界规则，不是复用正式 frozen 工件，也不给 sharp/H*。

若相邻采样点夹住响应变化，补其中整数点（6/8→7，8/10→9，10/12→11）；若W6已响应，补W4/5；若W12仍未响应，不向高处无限扩展，记右侧未定位。随后 target100 在同一局部点集合按相反顺序做A/C独立重复；须重新保留W12正负控和W0地板。只报告转折区间、样本分布和非单调性。不同target不合并估计“精确ways”；跨seed/轮数/填充压力稳健性留待该段结果后决定并登记 `docs/open-items.md`。

## 停止、审计与命名

任何 failed/unsupported、窗口无效或mux、geometry/fallback异常、环境前后门失败立即停止后续条件；保留失败文件，不重复挑选。先核 journal 全终态/单设备/无探针，再核二进制 SHA256 `54d105930b8743e7a3a69c31d7e640cdec1044a0276a5f040efff4b1dc82398c`。六事件首次 floor 即为可用性冒烟，失败不自动删事件降配。

输出先叫“特定构造下的数据翻译冲突响应与有效转折”。即便支持 H1 型等价类，也不等于发现完整hash、物理set编号、精确8ways或完整TLB层级。窗口包含 clock_gettime/读计数器边界和程序自身数据翻译；地板扣除不能逐事件归属到每条目标load。原正式 ±15% L1 refill 协议此前未通过，本次不宣称修复或晋升其资格。

## 局部补点执行登记（粗扫完成后，补点前）

target200 粗扫 A 的 DTLB_WALK 中位数 W6/8/10/12=0.1/1.3/5.9/12.0，C=0.0/0.1/0.0/0.1；因此按既定规则仅补 W9 A/C。第二target100按完整第一轮W顺序反转：9→10→6→12→8，每点反转A/C先后；之前/之后各W0，末尾再W12 C/A，5新进程/条件。合计16条件/80进程，条件清单在私有目录随输入保存；生成前清单 SHA256=af66e920923352dfde567c164b5fb627521d7fc12f27938d3eb77bf55295451e（以文件复核为准；不满足时停止核对，不猜测）。本段仍只用原2.0/0.5探索规则，不按观测调整阈值或重复次数。
