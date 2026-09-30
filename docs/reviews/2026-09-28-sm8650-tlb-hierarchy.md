# 战役终审：SM8650 Cortex-X4 TLB 层级探测（任务书 2026-09-28，执行 v4.4）

> 本文件是 TLB 层级探测战役的终审裁定（任务书 §10）。执行规范基线 =
> 任务书 v4.4（`docs/tasks/2026-09-28-sm8650-tlb-hierarchy.md`，修订映
> 射 v4.1→v4.4 见其卷首）；实施计划 =
> `docs/superpowers/plans/2026-09-28-sm8650-tlb-hierarchy.md`（M1–M8）。
> 分阶段裁定文档：Gate 0/1 = `docs/reviews/2026-09-29-sm8650-tlb-gate1.md`、
> Phase A/B/C/D = `docs/reviews/2026-09-30-sm8650-tlb-phase-{a,b,c,d}.md`——
> 本文件只汇总终态与跨阶段裁定，细节一律回指。

## 1. 终态总表（§10.2；每 Q 独立）

| Q | 终态 | 结果 |
|---|---|---|
| **Q1** `0x05` 第一有效转折 | **INTERVAL_IDENTIFIED** | **[120, 1024] 页（480 KiB–4 MiB）**——L1 dTLB refill 密度从 ~4/1k（48 页）连续爬升至 ~1400/1k（1024 页），宽饱和区而非锐边；4/4 order_seed × 8/512 环双训练量同区间（§6.2.6 稳定条件成立） |
| **Q2a** `0x34` walk-onset | **INTERVAL_IDENTIFIED** | **[2560, 3072] 页（10–12 MiB）**——≤1024 页全地板（长训练下 0.014–0.029/1k），2560 页起 walk 显形（44–54/1k）；4/4 seed × 双训练量一致 |
| **Q2b** L2 层级辨识 | 降级完成 | `0x2d`（unified refill）QUALIFIED 并入组；`0x2f`（L2 TLB access）**SEMANTICS_UNVERIFIED**（方向反降 + 分布重叠）——层级辨识仅 `0x2d`+G0 承担 |
| **Q2c** 第二级 effective reach | 未授权 | `0x2f` 失败 + 授权门槛未满足（任务书 §3.3/§7）；不结案即OPEN，保持未授权 |
| **Q3** walk 暴露成本 | **MODEL_UNIDENTIFIABLE** | 实测 walk 密度与 cyc/load、latency **反相关**（1024→3584 页 walk 0.19→45.2/1k（2560 页峰值 49.8）时 cyc/load 22.96→17.66、latency 8.36→6.44 ns）——连单调性都不成立，成本型估计在本协议下不可识别；MMUTC 混杂声明保持 |
| **Q4** THP cohort 对照 | **机制方向一致（受限比较级）** | 512 KiB 策略负控成立（`-T` 零变化）；3072 KiB mixed cohort（seed42 比较级 n=5）lat **-12.4%**、R_0x05 **-82%**、R_0x34 地板中性——方向一致性成立；2304 mixed 与 3072 其余 3 seed = **INSUFFICIENT_COHORT**（不追加尝试） |

## 2. 数据与工程清单

- **分支** `codex/sm8650-tlb-hierarchy`：提交数随评审修订变动（以 git
  为准）；全部推送 origin。
- **数据**：本战役 **49 个 run**（正式判定 28——含 Phase B 干净重跑
  块；fail-closed 留档 12；方差表征池 6；偏差佐证 = 被取代的长训
  练偏差重试块 3），共 **291 records + 2959 artifact entries**；全
  部 schema 校验通过、raw 样本 SHA256 逐条复算一致、raw/ 未入库
  （SHA256 manifest 锚定可再生）。
- **质量门**：所有代码/规则改动双评审（规范+质量）通过；M8 全量复
  验：CTest release 18/18 + UBSan 19/19、runner 154、analysis 136、
  46+3 run schema+哈希全过（本文件 §9 退役清单的复验项即此；干净
  重跑块的校验同样通过）。
- **探针**：`ptr_chase` + `vma_base` 字段（本战役唯一探针增量）；
  Xeon 交叉构建 SHA-256 三方一致（`8304ff7a…`）。

## 3. 分 Q 证据与三栏（§10.1）

### Q1 = INTERVAL_IDENTIFIED [120, 1024] 页

- **直接实测**：R_0x05 密度曲线（/1k timed dependent loads）——48 页
  4.3–4.5 → 104 页 93–99 → 112 页 168–171 → 120 页 232–235 → 1024
  页 1388–1445（4 seed 范围；短/长训练一致）；cycles/load 6.2→22–24
  同步爬升（§6.2.2 第三条件的配套证据）。
- **派生（DERIVED）**：区间 [120,1024] 由冻结算法产出（§6.2.2 三条
  件在致密点阵上的唯一满足对；`adjudicate_knee`）；生成器三哈希锚
  定致密配置（input `7ca8f4fd…`/rules `80641cda…`/output
  `ecb1759d…`）。
- **解释**：协议限定读法 = "本探针协议下 L1 dTLB refill 活动的有效
  转折区落在 120–1024 页"。**不支持反推物理项数**（§3.3 授权边
  界）；TRM"fully associative"与本区间无逐项映射。>1000/1k 段证
  实 `0x05` 为 event density 而非 miss 概率（§3.2）。

### Q2a = INTERVAL_IDENTIFIED [2560, 3072] 页

- **直接实测**：R_0x34 地板段（64–1024 页）0.05–0.31/1k，2560 页
  46–52/1k，3072 页 45–54/1k，3584 页 35–42/1k；长训练下同区间同
  水平（43.9–53.6/1k）；地板段密度报告标注"含固定开销"（§5.3：
  512K 冷启动 ≈8 walks/窗）。最小点 48 页为冷启动抬高实例
  （0.45–0.55/1k，onset 算法按地板处理——Phase A §3 已登记观察
  项，落 OI-14），不在上示地板范围内。
- **派生（DERIVED）**：onset 区间由 `detect_walk_onset` 产出（两训
  练量各自 INTERVAL_IDENTIFIED 且一致）。
- **解释**：下沿 2560 页位于 MMUTC 容量（2048 项，TRM Table 6-1）
  之上——**MMUTC 耗尽使 walk 显形的机制联想保持假设级**；Q2c
  （L2 TLB effective reach）未授权，不由本区间外推。

### Q3 = MODEL_UNIDENTIFIABLE

- **直接实测**：上表关联数据 + G3 对照（`0x8144` 三点饱和
  ~1001/1k，与 walk 无共变）。
- **派生（DERIVED）**：steps/walk 1.91→1.18→1.07（walk-active 区
  step 短化）；percyc 29.7→1432/1k（walker 活动量随 walk 上升）。
- **解释**：中段（1024 页）L1 refill 风暴（~1400/1k）的成本高于
  onset 后的 walk 服务——translation 各级成本相互抵消，单调性不成
  立；成本型升级须另行冻结模型规格（§7 Phase C 前置条件未满足）。
  固定开销：cycles/dtlb_walk 的绝对密度标注"含固定开销"（§5.3 判
  定，Gate 1 评审 §4）。

### Q4 = 机制方向一致（受限比较级）+ INSUFFICIENT_COHORT

- **直接实测**：转化表（512 `-T`→base 40/40；2304 `-T`→base 35 +
  mixed 5；3072 `-T`→base 25 + mixed 15）；cohort 分级表（见 Phase
  D 文档 §1）。
- **派生（DERIVED）**：3072 mixed（seed42）vs base 的 -12.4% /
  -82% 差值（cross-cohort 比较，布局未配对——进程级对照非逐槽
  位）；跨 seed 合并合法性判定（`grade_thp_cohorts`）。
- **解释**：大页把每 4 KiB 页的 L1 refill 需求压到 1/512，与
  Gate 1 ③（16 MiB `-T` 总 walk 2800× 削减）同机制链；**延迟收
  益不按 refill 削减比例换算**（§7 Phase D 明示）；选择偏差
  （mixed 达成率 12.5%/37.5%）已披露，未比较级 cohort 不进结论。

## 4. 来源三段分标（§2.2）

- **TRM 声称**（Issue 05 逐字核对）：L1 dTLB fully associative、
  miss 路径 L1→L2 TLB→walk、MMUTC=2048 项 8 路 walk 缓存（独立组
  件）、`0x05`/`0x34` 事件语义。**r0p3 未核对**（§11 待办已落
  OI-14）。
- **AArch64-Explore 方法**（commit `9e3d464`，Apple M1 对象；以
  submodule 钉在 main 树的 `third_party/AArch64-Explore`，FF 集成
  后分支读者可达）：
  依赖链/反例构造的方法学参照（§6.5 对照清单）；**其 TLB 数值零
  移植**（对象不同）。
- **本机观测**：全部终态数字来自 redmi-k70pro-01 CPU7 的本战役
  run（上文）；任何与 TRM 叙述的对应均为"机制联想"而非结构证明。

## 5. 竞争解释与未排除项

- **Q1 宽饱和区**：①L1 dTLB 有效项数的渐进冲突饱和；②translation
  预取/路径缓存覆盖率渐进退化；③4 KiB base 页 PFN 着色 + PIPT 哈
  希的冲突 refill（cache 战役已证布局影响巨大）。本战役未在区间内
  排他——报告区间不报告成因；路线 B（可控 VA 布局）已登记 OI-14
  备选。
- **Q2a onset**：MMUTC 2048 项耗尽 vs L2 TLB 容量 vs walker 队列阈
  值——`0x2f` 失效使 access 侧交叉验证缺席；onset 区间成立，归
  因开放。
- **Q3 反相关**：refill 风暴成本 > walk 服务成本的抵消读法与数
  据一致，但不排除其他构成（如 MMUTC hit 时的快速 walk 服务）；
  成本型估计未授权故无结论可翻。
- **Q4**：mixed cohort 的 huge 区位置随进程变、逐槽位归属不可测
  （§1.2 既有边界）；`AnonHugePages` 为聚合分类依据。

## 6. 过程纪律记录（战役方法学遗产）

1. **限额 drift 与重启**：采集前限额 drift 3.5h 未愈；22:28"恢复
   画像值"经 uptime 证据更正为**重启事件**（Gate 1 评审已补记）。
   全部判定数据在该次启动后画像值窗口内采集（quiet-state 门禁逐
   case 通过；raw 环境快照在档）。
2. **锚点判据校准链（v4.2→v4.4）**：2048 环参照制度失配（v4.2）
   → 地板量化指标改计数容差（v4.3）→ 方差表征池化 + 带形判据
   （v4.4）——每次修订均由实测触发、用户裁定、双评审通过、修订
   映射留痕；**无一次是为了让数据通过而改判据**（v4.2/v4.3/v4.4 改的
   是参照系与判据形式，方向不偏好任何科学结论；v4.4 后的块仍发生一
   次真实瞬态 fail-closed 与一次边际 fail-closed，证明门禁保留拒
   收能力）。
3. **fail-closed 块**：Phase A 两块（校准前）+ Phase B 长训练首块
   （真实瞬态）+ Phase D -B 首块（边际）——全部留档入库，重试按
   §6.2.5/§7 规则各占额一次。**偏差事件**：Phase B 长训练的偏差
   重试（冷却静置不足，~3 分钟）经评审抓获后由用户裁定干净重跑
   摘除（首块失败约 4 小时后，满足 §7 字面要求）；判定腿已换源为
   干净块（Phase B §4 完整披露，运行记录 `b5ab6dc`）。
4. **事件资格**：Gate 1 新增 4 QUALIFIED + 2 SEMANTICS_UNVERIFIED
   （原始数据保留审计，不续试新事件——有限终点遵守）。
5. **新登记缺口**：OI-12（跨日基线移动）、OI-13（分析器非 G0 适
   用性）——均含触发条件与证据锚。

## 7. 预算核算（§6.2.7；case 与 record 一一对应）

- Gate 0/1 + 开销扫描：37（Gate 0 = 2；Gate 1 = 11，含 16 MiB 辨识
  点 1；开销 24）；
- Phase A：3 块 × 30 = 90（2 次重跑占额）+ 方差研究 12；
- Phase B：短块 36 + 长块 48（首块 16 瞬态 fail-closed 作废 + 偏差
  重试 16 + **用户裁定后的干净重跑 16**——长训练设计行 12 case/
  块 × 3 次尝试，§6.2.5/§7 重试占额规则下如实入账）；
- Phase C：两块 20；
- Phase D：三块 48（含 -B 一次重试 16）；
- **合计 291 case**（= records 总数）；纯执行时间约 1.5 小时（漂
  移/重启等待与校准讨论不计）。

## 8. 后置项落位（铁律 0）

任务书 §11 全部条目 + 战役衍生项已落 `docs/open-items.md`（OI-12、
OI-13、OI-14 战役段）；**无"现在不做"的口头决定留在外部**。

## 9. 退役条件核对（铁律 7 / §10.3）

- [x] 预注册任务完成（四个 Q 各自终态；Q2c 未授权保持 OPEN——
  OPEN 不阻碍退役）；
- [x] 未竟项全部转 open-items；
- [ ] 正式评审（本文档 + 分阶段文档）；
- [ ] FF 集成 main + main 全量复验 + 推送 origin（推送须用户确认）；
- [ ] worktree 回收与分支删除分别满足各自条件。
