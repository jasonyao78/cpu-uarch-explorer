# REV-M0-BATCH 两层回执 · 处置响应与收口请求

> 日期：2026-10-01。响应对象：[两层评审回执](2026-10-01-m0-two-layer-review.md)（MB-01~MB-08 + Q4 裁定 + 出口口径要求）。
> 处置基线：r2 `d105765` / m0b `2d48704` / main `798f774`（三层均已推送 origin）。
> 请求：**五项 P1（MB-01/02/03/04/07）关闭确认 + MB-08 口径确认**，即 M0 **代码侧出口**验收；完整 M0 出口（含 M0-5 设备侧）按评审裁定不在本批次。

## 1. 五项 P1 处置与证据

| 发现 | 处置 | 复核证据 |
|---|---|---|
| **MB-01** GROUP 读长误判 | `read()` 按**实际返回字节**判定：最低长度（≥3 词）/8 字节对齐/nr≤容量/组构成（nr==成功打开数）逐项检查；截断、对齐错、nr 不符、syscall 失败分别给命名 `last_error()`。不再以最大容量判定完整性。 | 合成 harness（注入 syscall 返回，无内核执行）：**n=1/2/4/16 全部 read_ok=1**（修复前 1/2/4 均 false）；`err` 全空。黄金测试 19/19 保持。 |
| **MB-02** 名称错位/越界 | `names_` 在 open 时按**原始 spec 数组全程占位**（失败项也占位）；`value_index_[spec]→values[]` 为唯一值映射；`event_count()/name(i)` 均以 spec 下标为准。头文件契约注释改为"位置映射 + 身份表"，**不再宣称按内核事件 ID 解码**（未用 PERF_FORMAT_ID，如实标注）。 | 合成（cycles 打开失败）：spec0 `failed=1 vidx=-1 name=cycles`；spec1 `vidx=0 refill`；spec2 `vidx=1 walk`——与评审期望表逐行一致；无 out_of_range。 |
| **MB-03** planner 丢语义参数 | ① `_PASSTHROUGH_PARAMS`（与 analyzer `_IDENTITY_PARAM_KEYS` 对齐的四个身份维度）**直通 case_params**——engine 只记录 case_params，此为证据唯一通道，"仅进 ID 不进证据"的命名-执行分裂消除；② 未消费参数 plan 期显式拒绝（**例外**：战役既有的 swept-ID 段机制计为合法消费，其钉桩测试 3 项不变；语义/身份维度必须走直通）；③ 非 ptr_chase 形状 case_id = 全部 case_params 规范化枚举（白名单 + 标量校验），消除主循环对 `buffer_kb/stride` 的隐含形状契约。 | runner 158/158（新增：chains sweep 进 case_params 且进 ID；未消费 fixed 参数 plan 期拒绝）。 |
| **MB-04** 二次聚合合并 K 条件 | 双端拒绝非 legacy 身份（评审允许方案）：m0b `grade_thp_cohorts` 与 main `seed_medians` 对任何非全 None 的 `identity` 给**命名 TlbError**，不做无声合并。条件化 cohort/曲线的显式预注册汇总规则属 MB-06 后续。 | m0b analysis 149/149（新增 cohort 拒绝测试）；main 167/167（新增拒绝测试）。说明：seams 脚本第 87 行对曲线调用未包异常，其 traceback 即"未合并"的命名证据，属脚本按旧行为编写，非缺陷。 |
| **MB-07** 图表静默删点 | main `seed_medians` 的 None 跳过改为**审计清单**：`skipped=[{run,buffer_kb,seed,field}]` 经 `build_figures(audit=)` 透出；CLI 成功路径打印结构化 stderr 披露，报告附"数据局限"段并声明"相关区间按可用点重判"；**空系列错误点名跳过点**（修复 overlay failure 根因——缺指标时错误消息丢失 run 名；退出码 1 断言本就通过）。 | main 167/167（新增两条：部分缺点→可用点照算+清单；非 legacy 身份→拒绝）。全缺与部分缺两种输入均有受控行为。 |

## 2. 同批处置的 P2 与口径项

- **MB-05**：复制构造/赋值删除 + **正确转移语义**（move 构造/赋值，搬迁后源对象清空）——评审"删除或提供正确转移语义"双选项的完整版。余量（snapshot 解码 vs window validity 分离、enabled/running 前后差分）登记任务书 §11-7，Phase B 短窗 pilot 前完成。
- **MB-06**：descriptor 最小证据契约（requested→canonical→realized 链、params 类型规范化、schema README 登记）登记 §11-8，按评审 §4 表格在 Phase B 上线前核验。
- **MB-08**：B1→B2 切换已从 OR 改为**合格门三条件**（① pilot 证明 B1 不合格且门控证据在档；② B2 正控+负控+分类器+误判门全部达标；③ pilot 后正式矩阵前按预注册规则决策，**正式数据不得参与选择**）；两方案均不合格 → `GATE_FAILED`/重新设计。已入任务书 v1.3 §1.2。
- **请求文档措辞**：层 A/层 B 均改为"已有提交、待验收"；出口口径区分**代码侧出口**（本批次）与**完整 M0 出口**（+M0-5 设备侧 pilot/锚点池）。

## 3. 回归基线（三层全绿）

| 层 | 测试 | 结果 |
|---|---|---|
| m0b | analysis / runner / CTest / NDK 27.2 语法 | 149 / 158 / 19 / 通过 |
| main | analysis（含图表 19 项组合） | 167 / 167 |
| r2 | analysis / runner / CTest（REV-M0-BATCH 首层后） | 146 / 154 / 18 |

旧 49 runs 重放一致性由评审脚本在上轮确认（5/5 字节一致），本轮未改动分析语义路径（仅 planner 直通与聚合守卫），无新增漂移面。

## 4. 边界与未决项（诚实声明）

1. 评审方本轮留存的回执文档/复核脚本/证据目录与 `docs/open-items.md` 修改**未代提交**（提交卫生：非本任务产出），以未跟踪状态留在 r2 工作区，归属评审方处置；
2. MB-01/02 的合成验证为**注入式 mock**（无内核/PMU 执行），真实 Linux 行为仍属"代码审查级"证据，随首次上板验证；
3. OI-13 维持"部分关闭"口径（上轮评审裁定）。

## 5. 收口请求

请确认：**MB-01/02/03/04/07 关闭、MB-08 口径满足**——即 M0 **代码侧出口**验收通过。通过后动作：层 B（m0b）合并入 r2 主分支 → main 同步核对 → 进入 Gate 0 与首次上板（冒烟 + M0-5 pilot）。若仍有 P1，请按 REV 格式回执。
