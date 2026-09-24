# probes/platform — 平台能力探针（capability discovery）

与 `probes/` 下其他目录不同：这里探测的不是微架构参数，而是**平台本身的能力边界**——计时器、调度控制、计数器接口。结果直接支撑 runner/targets 的 capability discovery 实现（探针代码留在 Probe 层，runner 只负责调用与解释其结果，非一次性实验）。

## 组织规则（重要）

**目录名 = backend id**，与 `runner/schema/record.schema.json` 的 `backend` 枚举一一对应（`macos-arm64`、`linux-x86_64`、`android-arm64`……）。判断标准：**不看文件内容，路径本身就能回答"它跑在哪个平台"**——用了 mach API、sched_setaffinity、安卓属性等平台特定接口的代码，必须放进对应 backend id 的子目录；跨平台可移植的探针则不属于这里（如 `probes/cache-mem/ptr_chase.cpp` 是纯 POSIX，放"测什么"的目录）。

CMake 按宿主平台条件编译（`if(APPLE)` 等），避免 mach 代码进入 Linux/Android 交叉构建。

## 当前探针

- `macos-arm64/timer_resolution` — `mach_absolute_time` 的 timebase、有效分辨率、单次调用开销。
- `macos-arm64/qos_steering` — 延迟链吞吐双峰验证 QoS→P/E cluster 分流（2026-09-24 实测通过，BACKGROUND 即 E-core 调度手段）。

## 新增平台探针时

1. 建 `probes/platform/<backend-id>/`，探针放其中；
2. 在 `probes/platform/CMakeLists.txt` 增加对应的平台条件；
3. 运行结果（含日期）登记于需求文档 §2.x 与 `docs/open-items.md`。
