# runner/schema — 统一数据模型

`record.schema.json` 是统一实验协议（需求 v0.3 §4）的物理载体：一次 probe 运行产生**一条 JSONL 记录**（每行一个 JSON 对象），追加写入 `data/<layer>/runs/<backend>/<date>.jsonl`。

设计原则（ADR-0003）：

- **信封强制**：run_id、timestamp、backend、device_code、probe_git_commit、evidence_level 等元数据字段必填——任何记录必须能回答"何时、在哪台设备、哪版代码、什么参数下测得"。
- **扁平字段**：不嵌套大对象；`params` 与 `metrics` 为小型受控对象，未来 SQLite 汇总层（推迟引入）可无损映射为 child 表。
- **schema 演进**：新增字段不得破坏旧读者；废弃字段保留至少一个基线周期。
- **证据等级**：`MEASURED / DERIVED / SIMULATED / PUBLIC_SOURCE / ASSUMED / UNKNOWN / NDA_RESTRICTED`，与需求 v0.3 §7 一致。

Runner 层实现（targets 适配、采集、落盘）属下一迭代（M4 Pro 最小骨架）范围。
