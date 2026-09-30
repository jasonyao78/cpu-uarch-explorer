# M0 两层批次复审回执

> 编号：REV-M0-BATCH-20260930；复审日期：2026-10-01。
> 请求：`docs/reviews/2026-09-30-m0-batch-review-request.md`，原 r2 `3b86f61`。
> 原快照：`m0-review-snapshot^{}` = `adaac4d`；原层 B：`5a07722`。
> 复审期间更新后，再验输入：r2 `3e539c6`、m0b `154679b`、main `dd4e46a`。M0-3 重放为 `d811248`，M0-4 重放为 `154679b`。
> 结论：**要求修改。原层 A 多数异常已修；当前确认五项 P1（MB-01/02/03/04/07）。代码侧 M0 尚未完成验收。**
> 范围：两层代码与请求文档；不连接设备，不修改生产实现，不合并或提交 Git，不充当第二位独立评审。

## 1. 请求文档需要先校正的事实

五部分组织方式适用，但请求正文应纳入已经取得的证据，不能让外部评审重新从“未验证”开始。

| 当前说法 | 核验结果 | 应改成 |
|---|---|---|
| 代码侧五项完成 | 原 M0-1/2 已修多数异常，但 M0-3/4 仍有新缺陷，图表仍有静默删点 | 五项已有提交，待验收；子项完成情况分别列明 |
| 旧 49 runs 重放未验 | 上轮已复核 49 runs/291 records：42 个原可处理 runs 不变，7 个为预期接纳扩展；本轮 m0b 对快照 49/49 不变（删除新增空 identity 后） | 给出重放范围、结果及科学结论重裁/raw 审计的边界 |
| main 图表兼容性未验 | 完整旧数据四图及报告不变；更新后组合测试 18 通过、1 failure/0 error，另有部分缺值静默删点 | 分别列出正常路径、已修异常、剩余语义回归 |
| Linux 零执行覆盖，等待证据裁定 | 原两处编译错误已修，最新 NDK 语法检查通过；syscall 注入仍复现 PerfWindow 缺陷 | 编译、纯函数、模拟 syscall、真实 Linux、真实目标分别列明 |
| r2 干净待审 | `git status` 有上轮本会话产生的 open-items 修改、报告、证据与脚本 | Git 提交状态与 worktree 状态分开；这些材料尚未入提交 |
| M0 出口不包含 M0-5 | 任务书列了六子项，pilot/池属完整 M0 | 区分“代码侧可集成”出口与“完整 M0”出口，后者包含 M0-5 |

层 A 表格有八行，包括 a104dbf 起点；`a104dbf..adaac4d` 是七个新增提交。r2 从战役基线到原 3b86f61 共九个提交；两种计数并不矛盾。最新修复提交另外计数，不改变快照内容。

上轮回执是 `docs/reviews/2026-09-30-sm8650-tlb-r2-m0-review.md`，其中消费点守卫表继续适用。本次 MB 编号只登记层 B 新发现，避免把继承缺陷误计成修复或重新发现。

## 2. 层 A 的修复复核（3e539c6）

| 上轮 ID | P1 内容 | 本轮状态 |
|---|---|---|
| C1 | PageBackingClass 命名空间导致目标编译失败 | **已修**，两处限定；最新 NDK 检查通过，非真实目标运行 |
| C2 | 分字段滤 None，指标样本集合静默分离 | **group 层已修**：缺失集进键，完整/降级记录分组；二次聚合仍须约束，见 MB-04/07 |
| C3 | knee floor 先比较；walk_samples 部分缺值绕过守卫 | **原异常已修**：公开入口给 INCOMPUTABLE；148 项分析测试包含新增覆盖 |
| C4 | 锚点消费依赖没有必要字段守卫 | **已修**：缺 cycles/refill/walk→BLOCK_FAILED；缺 mem_rd→ANCHORS_OK，本轮矩阵复核 |
| C5 | Markdown/main 图表 nullable 回归；bimodal=None 误写 no | **原 TypeError/误显已修**；展示端仍会静默删点，见 MB-07；组合测试还未全通过 |

M0-6 的角色声明仍可接受。M0-1 当前仅页策略提取子项，不等于任务书所列 RAII、合法地址池、timer、CPU/MIDR 均完成。OI-13 继续保持未关闭，任务书 v1.2 已收紧 extras 的交付口径。

offset 的独立节点地址策略已补入 v1.2，可作为设计输入。B1/B2 也补了默认值和 pilot 时点，但切换条件仍需修订，见 MB-08。

## 3. 层 B 新发现

### MB-01 [P1] PerfWindow 将正常的小事件组读误判为失败

位置：m0b `probes/common/perf_window.h:132–135`。

当前无 ID 的 GROUP 格式是 `nr, enabled, running, values[nr]`，有效载荷长度为 `(3+nr)*8`，取决于实际打开成功的事件数，而非缓冲容量。这个布局来自 [Linux perf_event_open(2) 手册](https://man7.org/linux/man-pages/man2/perf_event_open.2.html)。代码提供 152 字节容量，却要求 `read()` 返回值也必须等于 152；于是 1–15 个成功事件的合法返回都被拒绝。

包含原生产头文件、仅注入 syscall 返回的合成测试结果：

| 成功事件数 | 合法返回字节 | 当前 read_ok |
|---:|---:|---:|
| 1 | 32 | false |
| 2 | 40 | false |
| 4 | 56 | false |
| 16 | 152 | true |

成员打开失败后组会缩小，仍落入此缺陷。应按实际 read 字节数检查最低长度、对齐、nr、期望组构成，再把实际 word 数传给 decoder；不能用最大容量判定完整性。截断、nr 不符和系统调用失败应保留明确失败原因。

这是类逻辑与 ABI 的确定性错误，合成测试不等于真实内核或 PMU 执行。现有黄金测试只测试 decoder，因此全部通过也查不到 read 包装错误。

### MB-02 [P1] 部分事件打开失败会让名称错位并越界

位置：m0b `probes/common/perf_window.h:91–114`、`:147–151`。

`failed_`、`value_index_` 按原始 spec 数组索引；`names_` 却只 push 成功打开的项。`event_count()` 返回原始数量，`name(i)` 访问压缩数组。输入 specs=[cycles,refill,walk]，模拟 cycles 打开失败：

| spec_i | failed | value_index | name(spec_i) |
|---:|---|---:|---|
| 0 | true | -1 | refill |
| 1 | false | 0 | walk |
| 2 | false | 1 | out_of_range |

因此除了异常，还可能把 refill 的值标成 walk。元数据必须永久以原始 spec 身份存储，失败项也占位；实际 FD/读值位置另行映射。当前也没有 `PERF_FORMAT_ID` 或 `PERF_EVENT_IOC_ID`，与任务书按事件 ID 解码的交付要求不同。若保留位置映射，需明确契约与组序依据，不能宣称已经按内核事件 ID 映射。

### MB-03 [P1] planner 扩展缝仍会丢弃实验语义参数

位置：m0b `runner/plan.py:156–235`、`:287`、`:315–335`、`:357–373`；record 来源见 `runner/engine.py:237–238`。

把 `chains=[1,2]` 加入合法 sweep 后，生成不同 case ID（分别有 chains1/2），但两个 case.params 都没有 chains，engine 因而不会把它记录到 params。`chain_distribution`、`node_offset_policy`、`mapping_span_kb` 同样没有通过现有 deriver 保留。结果是“命名不同实验、执行/证据却没有该维度”。新增分析身份键从 params 取值，根本接不到 planner 丢掉的数据。

对当前 ptr_chase 不支持的字段，正确做法是 plan 阶段显式拒绝，而不是仅把名称放进 ID 后忽略。对注册的新 probe，则 descriptor 必须规范化并完整保留所有有效参数，由 adapter 明确执行。

另一个扩展证据：注入 tlb-set deriver 返回其自身的 `{ways:8}` 后，主循环仍取 `case_params['buffer_kb']`/stride，报 KeyError。这个合成注册测试说明扩展缝仍有隐含 ptr_chase 形状契约，不是完整的通用 planner。

不需要立即构造庞大的通用框架，但必须定义 descriptor 的返回契约与通用 case-ID 构造；所有未消费参数应被拒绝。仅验证“未知 probe_shape 会报错”不足以证明已注册新形状可贯通。

### MB-04 [P1] identity 在 analyze_records 生效，随后又被 cohort/图表合并

位置：m0b `analysis/sm8650_tlb.py:812–860` 及 `:1107` 的 `(buffer,backing,seed)` 聚合；main `analysis/tlb_figures.py:75–90`。

合成 K=1/K=2、相同 buffer/seed/backing 的两条记录：analyze_records 正确给两组，cycles/load 中位数分别约 0.03128 与 100。但 main 的 seed_medians 只按 `(buffer,seed)` 合并，画出约 50.01564 的一个点；grade_thp_cohorts 则把两个条件的各两样本拼成 n=4。

因此“分组键加了 identity”不等于“禁止跨条件合并”已经实现。所有二次聚合、报告及判据行转换必须保留估计量的条件身份；固定战役图表最小修复可以拒绝非 legacy identity，而不是无声聚合。对未来多条件图，应明确按哪个维度分系列，跨维度汇总只能经显式、预注册的规则。

以上数值是软件合成输入，不是目标设备观察。

### MB-05 [P2] PerfWindow 尚未交付窗口完整性与所有权契约

位置：m0b `probes/common/perf_window.h:77–81`、`:122–144`。

当前 read 返回累计 snapshot，缺少窗口起止差分、计数/时间倒退处理、正式窗口有效运行检查和 phase/CPU 等证据。模拟 nr=16、enabled=running=0 时 read 返回 true、mux=false。零值 snapshot 可以是合法基线，但不能被称为“有效测量窗”；应将 snapshot 解码成功与 window validity 分开。仅 RESET 计数也不能重置 enabled/running 的累积时间，需前后差分。[perf_event_open(2)](https://man7.org/linux/man-pages/man2/perf_event_open.2.html)

删除 copy constructor 没有删除 copy assignment。`copy=owner` 当前可编译；两对象 close_all 对同一合成 FD 100 各调用一次 close。应明确单一资源所有权，删除复制赋值或提供正确转移语义。非 Linux 桩也应保持足够一致的公开接口，让跨平台使用者不靠遗漏调用掩盖 Linux 专属编译缺陷。

未要求为了短窗加入所有采样功能；这里只要求原任务书已经承诺的窗口/身份/失败语义。`PERF_EVENT_IOC_SET_OUTPUT` 控制采样通知输出，不能替代 GROUP 计数组读，当前忽略该 ioctl 返回也不构成身份保证。

补充准确边界：leader enable/disable 的 flag=0 **不是本轮确认的缺陷**。Linux 手册明确 leader 开关约束整个组；不要因缺 `PERF_IOC_FLAG_GROUP` 就认定只有 leader 计数。

### MB-06 [P2] 四个未经规范化的 params 键不够描述 set 探针

位置：m0b `analysis/sm8650_tlb.py:140–145`、`:814`；schema README 未登记 probe_shape 或新身份维度。

目前只定义 distribution/offset/chains/span，未定义 H、目标/控制集合、页集合身份、phase/pair/分配 epoch 等条件；requested 和 realized geometry 没有贯通。不同 hypothesis 仍归一组。params 未做类型规范化，`chains=True` 与 `chains=1` 因 Python 相等关系也被归一组；list/dict 类 policy 则会使 tuple 不可哈希。

旧记录缺键→None 的兼容策略可以保留。新协议须定义版本、类型、合法值和 canonical identity，并在 schema 扩展登记中落位；不能靠分析端临时读取任意 params。

### MB-07 [P1] main 的 nullable 修复会静默删除部分正式曲线点

位置：main `dd4e46a` 的 `analysis/tlb_figures.py:83–88`。

None 检查已消除原 TypeError，但直接 `continue` 没有带出 run/buffer/seed/field 的缺值审计。合成完整四-run 数据集，只删除粗扫 128 KiB 两个 seed 的 walk 指标：CLI 返回 0、stderr 为空、walk 图从预期 20 点变成 19 点。报告仍生成，未披露缺失点。这不是命名降级。

正式固定数据集应校验每个必需指标的网格与 coverage；缺必要字段给带 run/点位的受控失败。若研究报告允许缺点，则输出结构化缺点清单、图中标记和报告局限，并按可用区间重判，不沿用原完整网格的科学结论。

当前 overlay 19 项为 18 通过、1 failure、0 error。该 failure 的**真实原因**是缺指标时的错误消息只写空系列，丢失了预期 run 名；退出码 1 的断言已通过。不能把它解释成“新契约把退出 1 改为降级”的预期差异而豁免。全缺产生空系列，部分缺会成功删点，这两种输入需同时验收。

### MB-08 [P2] v1.2 的 B1→B2 切换用了不充分的 OR 条件

任务书写“B1 无 L2 暴露 **或** B2 分类器误判率完成校准”即可切换。这样 B1 失败但 B2 未验证也能切换，或仅完成校准就切换，不管校准是否合格。应先规定 B2 的正/负控、分类器与误判门全部达标，再按预注册的选择规则切换；任何方案均不合格时进入 GATE_FAILED/重新设计，不能进入正式矩阵。校准门与预算可在独立 pilot 后冻结，但正式数据不得参与选择。

## 4. Q4：足够的最小 descriptor/证据契约

无需在本阶段实现覆盖所有 ROB/ALU/FPU 的巨型 schema，但 Phase B 上线前，下面这条链必须可核验：requested → canonical plan → adapter/kernel → realized observation → identity-aware analysis。

| 分类 | 最小信息（按 probe 适用性要求） | 获取/校验位置 |
|---|---|---|
| 协议与实现 | probe 名、protocol/implementation/descriptor 版本 | descriptor、record；新旧协议可区分 |
| 请求条件 | distribution、page-set/order seed、offset policy、K、目标/对照协议、H 与目标 set、请求页策略 | plan 规范化；禁止丢参；未支持项受控拒绝 |
| 实际几何 | distinct pages/node count、VA span、每页节点/实际 offset 策略、实际 K、total/per-chain timed loads | 探针/adapter 自证；requested 与 realized 分字段 |
| 样本身份 | session/allocation epoch、round、phase、pair ID、实现的访问/页集合身份 | per-observation，支撑配对与聚类；不靠 case ID 猜测 |
| 事件与窗口 | type/config/事件 ID 与标签、scope、window/phase、delta counts/enabled/running、失败原因、执行 CPU 证据 | PerfWindow + adapter；入同一 observation 帧 |
| 页 backing | requested/actual、端点审计及 page size | 复用现有守卫/页审计；不把请求成功当实际 backing |
| 分析条件 | 规范化条件身份、每估计量必需事件与联合 coverage | analyzer、判据、二次聚合和展示层贯通 |

allocation/session 等是独立性、配对与聚类的依据，不必一律当作主曲线分组键。H/offset/K 等实验条件却不能被 cohort 或绘图随意合并。哪些维度允许汇总由估计量定义，不由展示器省字段决定。

最小集成验证应同时含两条不同条件的新形状 case：计划值不同→执行入参不同→record 自证不同→统计保持两条件。配上一个不支持形状/字段的受控失败 case，比只测试纯 deriver 或手工在 record.params 加字段更有证明力。

## 5. 五个引导问题的裁定

1. **守卫覆盖**：层 A 原异常已修；group 契约分组与公开守卫可接受，二次聚合与展示端的剩余问题不能因原 TypeError 消失就关闭。
2. **main 图表**：完整旧数据兼容；新增 identity 仍造成 MB-04，nullable 的静默删点造成 MB-07。合并前覆盖缺值与多条件两类输入。
3. **Linux 证据等级**：最新目标语法检查已通过；syscall 包装缺陷仍必须先清零。普通 Linux 集成验证可先跑软件事件组检查读长度/身份/窗口，但当前 EventSpec 硬编码 RAW，不支持该测试。SM8650 事件资格/短窗开销最终仍需目标板确认，相关未验证项可独立标明，不能替代源码正确性门。
4. **descriptor**：只有派分缝与四维 identity 不够；按 §4 做最小纵贯契约即可，不要求先完成所有未来执行端探针。
5. **B1/B2、offset**：offset 设计路线已补；B1/B2 仍须处理 MB-08，并在正式采样前冻结合格门与选择规则。

## 6. 本轮证据

| 检查 | 结果 | 边界 |
|---|---|---|
| m0b macOS preset build | 成功 | 当前源码、非 Linux 路径 |
| 原 5a07722 analysis/runner/CTest | 142/156/19 全通过 | 未覆盖包装 read、失败身份、planner 到 record、二次聚合 |
| 更新后 154679b analysis/runner/CTest | 148/156/19 | 包含层 A 新回归；M0-3/4 的上述缺口仍复现 |
| NDK 编译 perf_window_golden | 通过 | Linux 类代码可编译；没有执行 syscall |
| NDK 编译 ptr_chase + perf 宏 | 最新通过 | C1 已修；未链接/执行 |
| PerfWindow syscall 注入 | MB-01/02/05 复现 | 包含生产头文件原文；模拟 UAPI/系统调用返回，没有内核/硬件测量 |
| planner/identity 合成链路 | MB-03/04/06 复现 | 手工软件输入，没有实际新探针执行 |
| 原 m0b 对 adaac4d；最新 m0b 对 3e539c6 | 均 49/49、291 records 相同 | 仅移除新增且全 None 的 identity；非空 identity 会拒绝该归一 |
| 更新后 r2 对 a104dbf | 42 个旧可处理 runs 不变，7 个预期扩展 | 原始数值/报告/派生判定不变；锚点 evidence 新增契约 checks |
| main 图表搭配更新后 r2 | 18 通过、1 failure/0 error；完整旧数据四图报告不变 | 失败是 run 名诊断丢失；另复现部分缺值成功删点 |

复核脚本与输出：`scripts/review_m0b_perf_window.py`、`scripts/review_m0b_seams.py`、`docs/reviews/evidence/2026-10-01-m0-batch/`。这两个脚本是诊断复核，不是证明实现通过的测试。

复现示例（r2 保存脚本，输入指向 m0b，输出到临时目录）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python \
  scripts/review_m0b_perf_window.py \
  --source-tree /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b \
  --out /private/tmp/m0b-perf-review.json

PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python \
  scripts/review_m0b_seams.py \
  --tree /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b \
  --main /Users/michaelyao/workspace/cpu-uarch-explorer \
  --baseline 3e539c6 --out /private/tmp/m0b-seams-review.json
```

## 7. 推荐出口与提交边界

软件侧可集成出口：当前 MB-01–04/07 清零；MB-05/06 的窗口/descriptor 最小交付明确定型并验证；两层合并后 main 图表/身份/缺项回归通过；目标源码可构建。完整 M0 出口另需 M0-5 的 pilot→独立校准冻结→池及任务书要求的设备证据。MB-08 在 Phase B 正式测量前关闭。

不因测试全绿接受命名错位、丢参或跨条件混合；也不因尚未连接 SM8650 而推迟可在本机证明的源码/接口问题。M0-5 的环境准备可以独立推进，但当前软件侧仍有不依赖设备的修复和集成验证工作。

本轮回执和证据尚未提交 Git；原 3b86f61 请求文档保留不动，供作者依本回执更新。修订请求时应引用两份回执与明确证据，而不把提出的问题当作已关闭。
