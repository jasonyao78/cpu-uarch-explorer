# probes/platform — 平台能力探针（capability discovery）

与 `probes/` 下其他目录不同：这里探测的不是微架构参数，而是**平台本身的能力边界**——计时器、调度控制、计数器接口。结果直接支撑 runner/targets 的 capability discovery 实现（骨架迭代时本目录代码升级为 `runner/targets/macos/` 的正式模块，非一次性实验）。

- `timer_resolution` — `mach_absolute_time` 的 timebase、有效分辨率（相邻调用最小非零间隔、零间隔比例）、单次调用开销。
- `qos_steering` — 用延迟链吞吐的双峰性验证 QoS→P/E cluster 的分流是否生效（USER_INTERACTIVE vs BACKGROUND 应差约 2 倍）。

使用：`./build/probes/platform/<bin>`。运行结果（含日期）登记于需求文档 §2.1 与 `docs/open-items.md`。
