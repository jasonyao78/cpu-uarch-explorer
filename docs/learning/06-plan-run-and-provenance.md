# 06 · Plan/Run 分离与参数溯源：参考仓用血换来的两条规矩

> 费曼段：一句话——**先把实验计划写在纸上检查一遍，再进实验室；每个参数都要能说出"我是从哪来的"。**

## 概念

### Plan/Run 分离

`plan` 阶段：读 ExperimentSpec + 平台配置 → 展开成**确定性的 case 集合**（控制组 × 参数档位的笛卡尔积）→ 打印出来给人看。不执行、不写盘、零副作用。
`run` 阶段：照着 plan 执行。

为什么值得分？因为参数错误在 plan 期就爆炸，而不是跑到第 40 分钟才炸。`python -m runner.cli plan` 的输出里每个参数都带着来源标注（`buffer_kb=32[experiment-sweep]`），人眼扫一遍就知道对不对。

### 参数溯源（ResolvedValue）

每个参数是 `ResolvedValue{value, source}`：来源四层优先级 CLI > 实验 > 平台默认 > 规格默认。溯源信息直接写进 run-record 的 `params_provenance` 字段。

## 这两条规矩的血缘（GB10 实证缺陷）

1. **64MiB 静默降级**：参考仓配置写 `working-set: 64MiB`，但它的 runner 只认识 `MB/KB` 后缀——`MiB` 不认识，**静默落回默认 1024KB**。DRAM 延迟实验实际跑在 1MB 工作集上，报告却写着 64MiB。→ 本仓对策：未知单位**硬报错**，绝无默认值兜底（`runner/resolve.py`，契约测试守住）。
2. **samples=7 是死参数**：profile 声明重复 7 次，执行器从不读这个配置，每个 case 只跑 1 次且 `sample_index` 恒为 0。→ 本仓对策：repetitions 在 **plan 期**就展开进每个 case（预览即可审计），执行期 `sample_index` 真实递增。

## 派生参数也在 plan 期算好

loads（追逐次数）不是用户参数，是派生参数：`max(min_loads, 每槽位8次)` 且对齐 8 的倍数（探针的展开因子）。在 plan 期计算并标注 `source=derived`——run 期不做参数解释，只做执行。

## 费曼自测

1. 为什么"未知单位报错"比"智能猜测"好？（猜测错了无人知晓；报错把问题暴露在 plan 期、暴露给人）
2. `derived` 来源的参数出了问题怎么查？（plan 预览可见推导结果；记录里有完整输入参数可复算）
3. 如果临时想让重复次数从 5 改成 7，改哪一层最干净？（CLI override 或实验 JSON，平台默认不动）

## 锚点

- `runner/plan.py`、`runner/resolve.py`（实现与防线注释）
- `docs/reviews/2026-09-24-gb10-borrow-review.md`（缺陷实证原文）
- `runner/tests/test_plan.py`（`test_mib_unit_not_silently_downgraded` 等契约测试）
