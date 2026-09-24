# 05 · 数据模型：四类记录与"不许编数"的实现

> 费曼段：一句话——**实验记录单上，"没测成"必须能原样写下来，而不是逼你填一个数。**

## 概念

### 四类记录各管一件事

| 记录 | 大白话 | 回答的问题 |
|---|---|---|
| ExperimentSpec | 实验方案书 | 测什么、参数范围、指标定义 |
| capability-manifest | 体检报告 | 这台机器能怎么测（计时器多细？能绑核吗？有 PMU 吗？） |
| run-record | 实验记录单 | 这一次测出了什么、什么条件下测的 |
| artifact-manifest | 物证清单 | 二进制和原始输出的 SHA256 指纹 |

### 证据等级：每个数字的"出身"

`MEASURED`（实测）/ `DERIVED`（换算）/ `SIMULATED`（仿真）/ `PUBLIC_SOURCE` / `ASSUMED` / `UNKNOWN`。为什么需要？因为未来实机数据和 gem5 仿真数据要进同一个库做校准——不标出身，校准就是在拿苹果比对苹果汁。注意它和**访问分类**（PUBLIC/PRIVATE/RESTRICTED）是两个正交轴：一个说"这数哪来的"，一个说"这数谁能看"，v1 把它们混在一起是设计错误，v2 拆开了。

### "不许编数"是怎么变成强制的

评审发现 v2 初版的 schema 有缺陷：`metrics` 无条件必填且至少一项数值。那一条**失败的**记录怎么办？只能编个数字塞进去才能通过校验——schema 在逼着人造假。

修复（2026-09-24，`0b2d70e`）：用 JSON Schema 的 `if/then` 条件化——`status=ok` 才强制 ≥1 项数值指标；`failed/skipped/unsupported` 允许空 metrics 但**必须**带结构化 `failure{reason, detail}`（机器可读原因码如 `probe-exit-1`）。规则从"文档里的道德要求"变成了"schema 里的物理强制"。

### JSONL 先行（ADR-0003）

原始层用 JSONL：每行一条记录、追加写、流式可读、C++/Python 零依赖。SQLite 推迟到首次跨 run 分析需要时再引入（YAGNI），schema 按可无损迁移设计。

## 费曼自测

1. 为什么 `additionalProperties=true`？（新增字段不破坏旧读者；扩展登记到 README 即可演进）
2. 证据等级和置信度是一回事吗？（不是：证据等级标数据来源，置信度评测量过程质量，§4 两轴不互相替代）
3. 一条 `unsupported` 记录长什么样？（空 metrics + failure.reason=`capability-unsupported`——macOS 无 hugepage 就该这么记）

## 锚点

- `runner/schema/`（四个 schema + README 登记规则）
- `docs/adr/ADR-0003`（JSONL）、`docs/adr/ADR-0006`（v2 演进）
- 第三轮评审修订记录（`docs/requirements/CHANGELOG.md`）
