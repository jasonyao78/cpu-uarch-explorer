# docs/learning — 个人学习笔记（费曼工作流）

> **定位**：这是 Michael 的**个人学习工作流**，不是项目的交付物。仓库转公开时可**整目录删除**，删除不影响任何代码与报告（零依赖设计）。评审或引用其中内容前请注意此定位。

## 方法论

费曼学习法的操作化：**讲不清楚 = 没懂**。本目录把"理解"变成可检查的产物：

1. **报告"费曼段"（强制，嵌入每份探测报告）**：
   - 一句话结论（<= 40 字）；
   - 机制解释（<= 200 字，目标读者：学过计算机组成原理的本科生）；
   - 关键数据（带单位与证据等级）；
   - **讲不清楚就打回重测**——解释缺口即知识缺口。
2. **三段式知识页（本目录的页面格式）**：
   - `## 概念`：通俗版原理；
   - `## 测量`：我们平台测到的数据（引用 data/public 与报告）；
   - `## 模型`：gem5 中对应的参数/结构（接入后补）。
3. **校准差异单联动**：measured vs simulated 超阈值时（ADR-0005），差异解释写进对应知识页；解释不了的在 `docs/open-items.md` 登记为知识缺口。

## 页面索引

**框架与工程**（架构设计 × 代码细节）：

- `00-why-this-framework.md` — 问题本质：没有纪律的测量产生数字不是知识
- `04-layered-architecture.md` — 四层架构：probe/runner/数据/报告为什么分开
- `05-data-model.md` — 四类记录、证据等级、"不许编数"的 schema 强制
- `06-plan-run-and-provenance.md` — Plan/Run 分离与参数溯源（GB10 血泪）
- `07-probe-abi-contract-tests.md` — Probe ABI 三条规矩与真实二进制契约测试
- `08-persistence-reliability.md` — fsync/原子替换/JSONL 追加/raw 不入库
- `09-gem5-overlay-minimal-delta.md` — blob 哈希普查破案：1008→134 与三次构建失败
- `10-frequency-and-env-transactions.md` — 频率能力分级与环境事务模型
- `11-cross-platform-abstraction.md` — target 正交分解、controls 收敛、三机管线

**微架构概念**（三段式：概念/测量/模型）：

- `01-pointer-chase.md` — 指针追逐与 MLP=1：测"单次依赖 load 的真实延迟"
- `02-timing-and-statistics.md` — 41.67ns 的尺子量 1ns：区间平均 + median-of-5
- `03-qos-steering.md` — QoS 分流：macOS 无绑核下的 E 核测量手段
- `12-tlb-hierarchy.md` — TLB 层次：翻译也是一层 cache（X4 结构 × 两战役实测）

（后续随实验进展添加：分支预测、SMT 干扰、cache 一致性……每页一个概念，测量栏引用 data/public 与报告，模型栏待 gem5 校准启动后补。）
