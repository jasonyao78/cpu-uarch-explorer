# 07 · Probe ABI 与契约测试：探针和框架之间的三条规矩

> 费曼段：一句话——**探针和框架只见三次面：传参数、读输出、看退出码；每次见面都有测试盯着。**

## 概念

### Probe ABI（ADR-0006 §3）

探针（C++）和 runner（Python）是两种语言、两个世界，它们之间的全部约定只有三条：

1. **输出**：stdout 打 `key=value` 行（如 `latency_ns=0.7725`）；
2. **退出码**：0 成功 / 1 输入或环境错误 / 2 能力不支持；
3. **非法输入必须非零退出**——带着 `nan`/`inf` 正常退出是最坏的情况：看起来成功了，实际往数据库里灌了毒。

### 为什么退出码 2 单独存在

有些实验在某些平台上天然做不了（macOS 没有 hugepage）。探针用退出码 2 说"我没这个能力"，runner 记 `status=unsupported`——这是**诚实的无能力声明**，和"坏了"（failed）是两回事，校准时不混为一谈。

### 契约测试：fixture 必须是真的

参考仓的血泪：adapter 的解析器和测试 fixture 都是**手写臆造**的（其复盘文档原话 "invented"），理想化输出和真实探针输出字段名都不一样（`migration_penalty` vs `migrate_penalty`），测试全绿，上线即崩。

本仓对策（`runner/tests/test_ptr_chase_contract.py`）：**用真实编译出来的二进制**跑 adapter 生成的 argv → 真实 stdout/stderr 回给 parser → 断言数值合法。二进制不存在就 skip（不许伪造通过）。OI-9 修订后的纪律：fixture 的真实来源必须由 capture 过程证明，文件存在不算数。

### 双端各自守界

- C++ 侧：`tests/`（CTest）守 ABI 第 3 条——合法输入必须出数值、非法输入必须非零退出（WILL_FAIL）；
- Python 侧：契约测试守"argv 被真实探针接受 + 输出被 parser 正确解析"。

## 费曼自测

1. 为什么"测试全绿"不能证明测量链闭环？（手写 fixture 可以全绿而真实输出早已漂移）
2. 新探针要接入框架，最小要做哪三件事？（遵守 ABI 三条 + 写 adapter 两方法 + 真实二进制契约测试）
3. 退出码 1 和 2 的记录差异？（1→failed 可以重试排查；2→unsupported 是能力声明，证据等级按降级路径处理）

## 锚点

- `docs/adr/ADR-0006` §3（ABI 定义）
- `runner/adapters/base.py`（协议与 `require_finite_number` 防线）
- `tests/CMakeLists.txt`、`runner/tests/test_ptr_chase_contract.py`
