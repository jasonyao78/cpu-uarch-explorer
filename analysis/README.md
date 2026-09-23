# analysis — 报告生成与校准对比

职责（随骨架迭代实现）：

1. **单 run 报告**：JSONL 记录 → 人类可读报告（含 docs/learning 定义的"费曼段"）。
2. **跨 run 对比**：多设备/多日期趋势图；SQLite 汇总层引入后（ADR-0003 触发条件）改为 SQL 查询驱动。
3. **校准对比**：实机 MEASURED vs gem5 SIMULATED，按 ADR-0005 的 T1/T2/T3 目标判定，超差生成"校准差异单"。

状态：待实现。
