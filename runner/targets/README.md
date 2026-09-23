# runner/targets — backend 适配层

每个 backend 一个适配模块，职责：

1. **capability discovery**：可用计数器接口（perf_event / KPC / 无）、绑核或 QoS 手段、锁频/thermal 控制、计时器精度与开销；结果随 run 记录（schema 的 `affinity` 等字段）。
2. **部署与执行**：本地编译/交叉编译、推送（adb/ssh）、运行、回收原始输出。
3. **后处理**：原始输出 → `record.schema.json` 兼容的 JSONL 记录。

实现随 M4 Pro 最小骨架迭代落地；当前各 backend 均只完成了 v0.3 §2 的画像级信息。
