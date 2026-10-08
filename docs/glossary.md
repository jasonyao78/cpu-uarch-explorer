# 术语表（给"隔几天回来的我"的一页解码）

> 用法：回来先扫速查表，够恢复上下文；再细的概念按分类索引查，每条带权威出处。
> 维护：边用边补、不追求一次收全（防漂移）；新词随手加一行即可。首批 2026-10-07 收录 ~40 词；10-08 增补 RPA/cohort 入速查。
> 不改名词本身（ID 稳定 = 评审链可追溯），本表只做解码。

## 速查表

| 词 | 一句话解码 | 出处 |
|---|---|---|
| r2 | TLB 层级探测**第二次战役**（分支 `codex/sm8650-tlb-hierarchy-r2`） | 任务书 v1.6 |
| 战役 | 一次有任务书、有评审、有终态表的完整测量行动 | README 当前状态 |
| 任务书 | 预注册的实验规格：科学问题、判据、顺序、非目标 | `docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md`（v1.6） |
| M0 | 采数前的工程批次：M0-1~M0-6 六项（管道/探头/锚点池），"M0 未完成不得采数" | 任务书 §4 |
| M0-5 | 锚点参照池项，顺序：安全性修正 → **pilot** → 独立校准冻结 → 正式矩阵 | 任务书 §4 M0-5 |
| pilot（标定试点） | 标 `CALIBRATION/PILOT` 的预采集；锚点池**只用 pilot 数据**建，不复用旧长链率；本次 = 2026-10-07 五段 18 record | `docs/runbooks/2026-10-07-sm8650-tlb-pilot-kickoff.md` |
| 冒烟（smoke） | 上板前可行性预检；产物 = **备忘录，永不入库**；原型唯一合法上板场景 | `docs/runbooks/2026-10-01-sm8650-tlb-r2-preboard.md` |
| Gate 0 | 正式矩阵前的事件资格 + 窗口能力门：G0-1（0x2f 复验✅）/G0-2（短窗作用域）/G0-3（开销标定 case） | 任务书 §5 |
| Phase A–D | Gate 0 之后的正式阶段：A=Q-A、B=Q-B/Q-C、C=Q-D、D=终审退役 | 任务书 §7 |
| 锚点 / 锚点参照池 | 漂移检测参照（b512K/b3072K 两 case，块前后各跑一次）；池 = 判据阈值的校准基准 | 任务书 §4 M0-5 |
| 3% 规则 | 跨日/跨 session 基线移动 >3% = **调查触发器，不是数据排除门** | 任务书 §6.2、OI-12(baseline) |
| PerfWindow | 短窗 PMU **GROUP 原子读**组件（一次 read 得 nr/ena/run/values[]），防逐事件读窗口错位 | m0b `probes/common/perf_window.h` |
| ptr_chase | 指针追逐探头（依赖 load 延迟 + PMU 同窗）；TLB set 协议已移植进它 | `probes/cache-mem/ptr_chase.cpp`、m0b `fb746c6` |
| l2_set_probe | `docs/` 下**方法原型** v2.3：算法蓝本，**不可产证据**（冒烟除外） | `docs/cpu-uarch-deep-analysis/tlb-deep-analysis/probes/` |
| tlb-set | set/way 系新探头（规划中）；其 prime+probe 协议先以 ptr_chase 模式落地 | 任务书 §6.1、`probes/tlb/README.md` |
| prime+probe | 协议：filler 页先驱逐 L1 TLB（prime），再访目标页（probe）分阶段计数 | 任务书 §1.2 Q-B |
| filler | 驱逐用页集（按候选哈希**避开目标 set**），512 页 | 原型 v2.3 头注 |
| Q-A~Q-D | 四个科学问题：分布效应 / L2 冲突 / 索引哈希 / 翻译并行占用 | 任务书 §1.2 |
| B1 / B2 | Q-B 的两个并列估计量：B1 同 set 自冲突曲线（默认主）；B2 单 victim 驱逐概率（切换有三条合格门） | 任务书 §1.2 Q-B |
| H1~H4 | VPN→set 哈希候选：位选 / 相邻 XOR / 高位折叠 / 三字段 XOR | 原型头注、任务书 §1.2 Q-C |
| set/way | 组相联结构；L2 TLB = **8 way × 256 set**（X4 TRM 地面真值，不测） | 任务书 §1.2 |
| 0x05 / 0x2d / 0x2f | 三个 TLB 门控事件：L1 refill / L2 refill / L2 lookup；0x2f 于 2026-10-01 复验升级 | `configs/pmu-event-registry.json` |
| 事件资格化 | 事件按**作用域**发资格（QUALIFIED / SEMANTICS_UNVERIFIED），长链有资格 ≠ 短窗有资格 | 任务书 §3.1 |
| 同窗 / mux | 多事件必须同测量窗采；计数槽不足会时分复用（mux），要求 time_running==time_enabled | 战役测量链定论（README） |
| probe_ns | 短窗计时辅证，**不作门控**（实测非单调）；门控 = 0x05 差分 + probe_ns 上界 | 任务书 §1.2 Q-B |
| controlled-baseline | 安静态环境 profile：唯一 mutation = governor→performance，其余只读门禁 | `docs/runbooks/redmi-controlled-quiet-state-v2.md` |
| charging-thermal | 充电态非基线 regime profile：policy0/2/5 被热策略压制属登记非基线；**policy7 被压 = 真阻断** | m0b `31c333a`、kickoff §2 |
| fail-closed | 环境任一项不合格即拒跑/记失败记录，不降级强行通过 | v2 runbook §4 |
| 设备线 / 分析侧 | 分工：设备线执行+现象记录；判读/冻结/锚点池归分析侧 | kickoff 头部、closure review |
| RPA-xx | Phase A 修复包的**复核发现**编号（PA-01..09 修复 → rereview 提出 RPA-01..05）；最新 v2 裁定：**本包不通过**（RPA-04 身份丢失 / RPA-05 标定程序未闭环，2026-10-07） | `docs/reviews/2026-10-07-rpa01-05-v2-review.md` |
| cohort（样本队列） | 分析允许合并统计的最小单位：同实验身份的样本组；≥5 出统计量、<3 = `INSUFFICIENT_COHORT`；跨身份合并被命名拒绝（详见索引·数据模型） | `analysis/sm8650_tlb.py` §7 Phase D |
| 铁律 | `AGENTS.md` 的 0–7 条硬约定（待办不丢/数据纪律/分层/注释/schema/git/提交卫生/分支终点） | `AGENTS.md` |

## 分类索引（速查之外的补充）

**战役流程**：上板 = 真机执行（相对本机/模拟器）。kickoff = 给上板 agent 的一页执行包。preboard = 上板前清单。收口 = 评审缺陷的修复-回执-复核循环。

**工程组件**：planner = runner 的 case 展开器（M0-4 后退化为通用控制）。deriver = 探头形状参数派生器。descriptor = 探头描述（requested→canonical→realized 链，MB-06 契约）。probe_common = 共享探头支撑层（页策略等，M0-1）。

**科学符号**：空窗 = W=0 测协议底噪（G0-3 强制）。正控/负控 = 制造/排除目标效应的对照（B1：同 set 集中 = 正控，打散 scatter=1 = 负控）。跳变 = refill 在阈值 W 处的抬升（实测提前至 W=8，按"总竞争条目数"口径解读）。F4/采样域等价 = 单一 256MiB 池内 H1≡H3、H2≡H4 不可区分，需多稀疏 VA 区域激励；终态 `HYPOTHESES_EQUIVALENT_ON_TEST_DOMAIN`。终态词汇：`INTERVAL_IDENTIFIED`（区间可识别）/`MODEL_UNIDENTIFIABLE`（模型不可识别）/`GATE_FAILED`（门控失败）/`QUALIFIED`/`CONFLICT_CURVE_IDENTIFIED` 等，定义见任务书各问。

**事件与测量**：0x11 = CPU_CYCLES（归一/共变）；0x34 = DTLB_WALK；0x8128 = DTLB_WALK_PERC。事件率 ≠ 概率（R_0x05 >1000/1k 已证，战役纪律）。G0-2 = 0x11/0x8128 的短窗/K 链作用域验证。raw/ = 逐样本原始输出，**不入库**（SHA256 manifest 锚定可再生）。

**环境治理**：quiet-state = 安静态门禁（v2 runbook）。mutation = profile 对设备的显式改动（每次 run 需 `--allow-mutation` 授权）；transaction/journal = mutation 的应用/恢复记账（逆序精确恢复，禁止"全部写回 walt"）。nonbaseline / accepted-nonbaseline = 登记的显式非基线条件，随 record 入档。

**评审治理**：REV-* = 外部评审批次；MB-01~08 = REV-M0-BATCH 缺陷编号；C1~C7 = 首层评审条件；F1~F9/R1~R4 = 第一性原理评审发现；OI-* = `docs/open-items.md` 编号（OI-12 有两个：baseline=跨日基线、rob=ROB 项目）；P0/P1/P2 = 评审严重度。双评审 = 两名独立评审方；回执 = 作者对评审的逐条处置文档。提交卫生 = 只提交本任务自己的文件（铁律 6）。

**数据模型**：records.jsonl = run 的记录主文件（schema v2：experiment/capability/run-record/artifact 四类，ADR-0006）。realized geometry = 实际执行几何（与 requested 请求参数分字段入 record，M0-4）。identity/probe_shape = 样本身份维度，**禁止跨条件合并**。cohort（样本队列）= 分析允许合并统计的最小单位：同实验身份（buffer×实际 backing×分布/offset/K 等）的样本组；≥5 有效样本出 median[p25,p75]（比较级）、3–4 只报原始观测（描述级）、<3 终态 `INSUFFICIENT_COHORT`；跨身份合并被命名拒绝（MB-04 修复）——出处 `analysis/sm8650_tlb.py` §7 Phase D。access_class = 数据分层（public 可入库 / private、restricted 永不入库）。

## 易混对照（回来最容易搞反的）

- **冒烟 vs pilot**：冒烟 = 备忘录级预检（原型可上板，产物不入库）；pilot = CALIBRATION 级采集（管道+移植探头，raw 留存建池）。
- **锚点 vs 锚点池**：锚点 = 单 run 的漂移参照 case；锚点池 = 判据阈值的校准基准集合（只用 pilot 数据建）。
- **0x2d 跳变提前 ≠ 异常**：W=8 即抬升是登记过的已知形态（SMOKE-20261001），判据按总竞争条目数口径写。
- **3% ≠ 排除线**：是调查触发器；触发调查，不淘汰数据。
- **计时不作门控**：短窗 probe_ns 只作上界辅证；门控靠事件计数。
