# REV-M0-BATCH：46b1daa 收口请求复核

日期：2026-10-01。范围：作者回执 `46b1daa`，M0-1/2/3/4/6 代码批次及任务书 v1.3；不执行目标板测量，不代修生产代码。

**平台与职责（2026-10-01 用户明确）**：当前聚焦 SM8650 Redmi 手机。目标验证路径为宿主使用 Android NDK 交叉编译生成 Android arm64 可执行探针，再经 `adb push` 部署到手机执行；设备验证由其他 Agent 负责。本评审保留本机软件复核与目标语法检查的证据边界，手机上板验证不由本会话执行。 操作参考 [上板前环境与冒烟清单](../runbooks/2026-10-01-sm8650-tlb-r2-preboard.md) §2；该清单已登记 Android 构建 preset 缺口，§6 的 S6 仍为跳过。本回执中的“未执行/未取得目标证据”限定本会话；其他 Agent 的上板记录保留其独立证据与验收边界。

**裁定：当前 M0 代码侧出口不通过。MB-01/02/04 可以关闭，MB-08 的选择规则口径满足；MB-03 与 MB-07 仍有 P1。** MB-05 所有权子项通过，窗口有效性仍待交付；MB-06 是已登记的后置设计工作，不能写成已经验证的 descriptor 能力。

代码基线：m0b `2d48704`、main `798f774`。作者文档基线 r2 `46b1daa`；复核期间 r2 增加上板清单提交至 `ae8532d`，本轮 replay 记录该 HEAD，分析器源码未随该清单提交变化。本文为评审方独立产出，原作者回执保留。

## 1. 逐项关闭对账

| ID | 裁定 | 本轮独立证据与边界 |
|---|---|---|
| MB-01 | **关闭该读长缺陷** | 生产头文件原文 + 宿主 syscall 注入：1/2/4/16 成员分别返回 32/40/56/152 字节，全部 read_ok=1；syscall 错误、零长、不对齐、短头、nr 不符、截断全部命名拒绝。未执行 Linux 内核。 |
| MB-02 | **关闭该身份映射缺陷** | cycles 打开失败后，spec0 = cycles/failed/-1，spec1 = refill/ok/0，spec2 = walk/ok/1；不越界。当前是固定组位置映射 + spec 身份表，可以采用此实现，但须统一旧注释及任务书的事件 ID 表述。 |
| MB-03 | **未关闭，P1** | 参数进入 case_params 后仍被 adapter 忽略；新形状仍先读取 chase 字段；未知 swept 参数仍获放行。见 §2。 |
| MB-04 | **关闭跨条件聚合缺陷** | K=1/2 的两组保留独立 identity；cohort 与 main 曲线均给命名 TlbError，拒绝聚合。该拒绝方案符合上轮要求。 |
| MB-05 | **部分关闭** | 编译期证明不可复制；move 构造/赋值后原 FD 100 和被替换 FD 101 各关闭一次。snapshot 与 window 的区别、窗口时间差分/有效性仍未实现。 |
| MB-06 | **待交付** | §11 已登记，但 requested→canonical→执行→realized→identity 的纵贯验证尚缺。bool True 与 integer 1 的直接输入仍合并；不同 hypothesis 的直接输入仍合并。不能用于新的条件化正式实验。 |
| MB-07 | **部分修复，仍有 P1** | 缺点 audit、stderr、空系列诊断已修；报告“重判”仅为固定文本，仍沿用固定区间与终态。见 §3。 |
| MB-08 | **口径满足** | v1.3：B1 不合格证据 + B2 正负控/分类器/误判门合格 + pilot 后正式矩阵前冻结，三条件合取，正式数据不参与选择；均失败则 GATE_FAILED。具体阈值及验证证据仍在正式采样前冻结。 |

MB-04 的旧诊断脚本确实没有捕获新拒绝异常。本文的后续脚本逐项捕获该异常并继续，因而同时验证了二次聚合拒绝、旧数据重放及其它反例；一个提前结束的 traceback 本身不能代替整条复核链完成。

## 2. MB-03 [P1]：记录了请求，执行与通用形状仍未成立

### 2.1 不支持的语义参数被记录成实验条件

位置：m0b `runner/plan.py:341–347`、`runner/adapters/ptr_chase.py:87–122`、`runner/engine.py:237–239`。

现有 ptr_chase 合成 plan 的同 buffer/control、chains=1/2 两个 case，得到：

| 条件 | record.params / case.params | adapter argv |
|---|---|---|
| K=1 | chains=1 | `-b 64 -s 64 -n 4194304 -w 1000` |
| K=2 | chains=2 | `-b 64 -s 64 -n 4194304 -w 1000` |

argv 完全相同；现有 native 探针也没有 K/offset/distribution/span 参数协议。engine 记录 case.params 只能证明请求值被留存，不能证明实际执行几何。它会把相同单链执行标成两个不同条件，属于测量证据错误，不能以“未来实现”放行。

**最低修复**：由当前 shape/adapter 声明真实支持的参数；未实现的非 legacy 条件在 plan 期明确拒绝。保留未来扩展缝无需提前实现所有 K 链探针，但至少验证两条不同的新形状条件走到不同执行入参，并有 realized 自证；未支持条件受控失败。

### 2.2 通用形状 ID 分支不可独立于 chase 几何执行

位置：m0b `runner/plan.py:324–325`，早于 `shape != 'ptr_chase'` 分支（359）。

合成注册 `tlb-set` deriver，输入只 sweep ways={8,9}，返回对应 ways；平台提供该探针映射，没有 buffer/stride。结果仍为 **KeyError('buffer_kb')**。回执所称“消除隐含形状契约”尚未发生。

即使人为补入 chase 几何绕过上述位置，新形状带合法 pmu_events 列表又会在 363–369 被拒绝，因为通用 ID 枚举要求每一个 case_param 都是 int/str。PMU 是当前公共参数协议的一部分，不能因为 ID 生成器而禁止。

**最低修复**：旧 chase ID/派生只在相应 shape 内；通用 planner 接受 descriptor 规范化输出。ID 身份编码与执行参数分开，结构化公共参数采用明确的规范化/签名或避免作为逐字段字符串片段，不要求 PMU 列表变成标量。

### 2.3 “进入 ID = 已消费”仍允许未知参数静默消失

位置：m0b `runner/plan.py:383–418`。

sweep 添加 unsupported_dimension={1,2}：8 个 case 全部放行，字段不在 case.params/record.params，执行也未变化。这是回执明示的兼容例外，仍违反不支持的测量参数应明确拒绝这一语义。

**最低修复**：以 shape 的真实输入契约确定已消费参数；若允许纯元数据标签，单独显式声明，不能对任意 swept 测量参数一概豁免。既有 ID 钉桩测试可以继续验证真正消费的 loads_per_slot 等维度，不应成为接受丢参的依据。

## 3. MB-07 [P1]：已披露缺点，但“重判”没有执行

位置：main `analysis/tlb_figures.py:398`、`409–415`；固定读法/终态常量在 281–327。

本轮两个合成输入：

1. 仅删除 coarse b128K 的两个 seed 的 walk 指标：CLI=0，walk 曲线 20→19 点；stderr 和报告准确披露这两个点。这一披露子项通过。
2. 继续删除 scan 的 4096≤buffer<32768KiB 的 walk 指标，同时保留最大端点以维持绘图范围。剩余 walk 横轴点为 **192、256、384、416、448、480、512、768、1024、1536、2048、3072、32768KiB**，10/12MiB onset 区间无点。CLI 仍为 0，报告仍写 **Q2a INTERVAL_IDENTIFIED [2560,3072] 页、4 seed × 双训练量一致**，同时宣称“相关区间的科学结论按可用点重判”。

build_report 的输入只有 graded THP 与 skipped 清单，没有 knee/walk 的重判结果；它照常插入 `_FIG2_READING` 和 `_FINAL_STATES`。因此问题不再是 None 导致崩溃，而是当前曲线覆盖与结论口径不一致。

**最低修复可二选一**：

- 该附件只重现冻结终审：有相关缺点时受控失败；或明确区分“历史终审引用”与“当前缺点图”，撤掉“已重判”的声明并禁用/标记不再受当前曲线支持的读法和区间提示，避免把历史结论作为本次生成结果。
- 支持缺点重新分析：接入实际判据结果、coverage/seed/训练量资格，按当前数据生成状态/区间及读法；不足时命名降级。

不要求图表模块新建一套统计判据；复用既有分析器或收紧附件输入边界即可。验收必须包含“只剩远端点、onset 区间缺失”的输入，断言不能同时得到未变的有效区间与虚假的重判声明。

## 4. 回归与重放证据

| 检查 | 本轮结果 | 解释 |
|---|---|---|
| m0b analysis / runner | **149/149、158/158** | runner 首次受沙箱测试锁写入阻挡；获准在该 worktree 重跑后全通过。不是产品测试失败。 |
| m0b preset configure/build + CTest | **成功、19/19** | 当前源码，macOS 非 Linux 分支。 |
| main analysis | **167/167** | 当前 main 图表及其他分析测试。 |
| main 图表 + r2 analyzer overlay | **21/21** | 19 原有 + 2 新项，0 failure/0 error。 |
| NDK 27.2 Linux/Android 目标语法检查 | **通过** | ptr_chase 启用 Linux perf 宏 + perf_window_golden；未链接/执行。 |
| PerfWindow 生产头文件 syscall 注入 | §1 全部符合 | 模拟 UAPI/返回，不是 Linux 内核或 SM8650 执行。 |
| m0b 对修复基线 3e539c6 | **49/49 runs、291 records 相同** | 只移除新增且全 None 的 identity；非空 identity 不允许归一掉。analyze_records 规范化输出及 cohort 成功/命名拒绝结果均49/49一致；包括最新聚合守卫修改后重放。 |
| r2 对 a104dbf | **42 原可处理 runs 不变，7 原拒绝 runs 预期接纳** | 指标契约修订的接受集合变化不能称为49/49旧终态完全相同。 |
| 完整旧数据 main 四图 + report | **5/5 文件字节一致** | 这是五个渲染文件，不是49个 runs 的重放计数。 |

作者回执 §3 的“旧49 runs（5/5字节一致）”混淆了两种证据；“仅聚合守卫、无分析语义改动”也不准确，拒绝非 legacy identity 正是有意改变分析接纳语义。本轮已重新验证 legacy 重放，建议直接写本表的基线、归一规则及两个独立计数。

全部合成输入仅用于软件复核，未取得新 PMU 或硬件测量。Linux 守卫 VMA、真实 perf syscall、SM8650 事件资格、短窗开销及 M0-5 仍无本轮目标执行证据。

## 5. 出口与下一轮最小包

本批次仍应先修 MB-03/07，再执行两层集成及 main 组合验证。MB-05/06 后置可以分阶段推进，但任务书 M0-3 的“短窗能力”、M0-4 的“实际几何 descriptor”不能因此整体标为完成；当前更准确的交付名是组件/扩展缝子批次。短窗 delta/有效性在首个短窗 pilot 前完成，descriptor 最小契约在首个依赖该新条件的 Phase A/K 链/Phase B 采样前完成，不应统一拖到 Phase B。

MB-02 尚有口径残留：头文件第8行“按身份（非位置）”、第13行“窗口 delta”，与新增17–19行位置映射说明及尚未实现的窗口 API 相互矛盾；任务书 M0-3 的“按事件 ID 映射”也未同步。实现可以采用已验证的 spec→组位置映射，但文档应准确声明已经实现的层次。

复核脚本：`scripts/review_m0_closure_perf.py`、`scripts/review_m0_closure_seams.py`。输出与回归日志：`docs/reviews/evidence/2026-10-01-m0-closure/`。这两份脚本在原诊断基础上保留反例和命名拒绝证据，不将预期拒绝混写成通过所有功能。

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python \
  scripts/review_m0_closure_perf.py \
  --source-tree /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b \
  --out /private/tmp/m0-closure-perf.json

PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python \
  scripts/review_m0_closure_seams.py \
  --tree /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b \
  --main /Users/michaelyao/workspace/cpu-uarch-explorer \
  --baseline 3e539c6 --out /private/tmp/m0-closure-seams.json
```

本提交归档本会话的三轮评审文档、复核脚本、证据和评审方 open-items 更新；其它会话的工作区改动保留各自提交边界。
