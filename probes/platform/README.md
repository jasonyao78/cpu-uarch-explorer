# probes/platform — 平台能力探针（capability discovery）

与 `probes/` 下其他目录不同：这里探测的不是微架构参数，而是**平台本身的能力边界**——计时器、调度控制、计数器接口。结果直接支撑 runner/targets 的 capability discovery 实现（探针代码留在 Probe 层，runner 只负责调用与解释其结果，非一次性实验）。

## 组织规则（重要）

目录按**最窄的平台 API 边界**组织，不按已降级为展示名的 `backend` 复制
实现。`macos-arm64/` 承载 Mach/QoS 这类 Apple ARM64 专用接口；`linux/`
承载 `perf_event_open` 这类跨 ISA 的 Linux UAPI，并可由静态交叉编译产物在
Android/Linux 内核上复用。Android framework/property 专用接口仍应放独立
目录。Runner 的 os/isa/ABI/transport/executor 正交目标描述不由这里重新编码。

判断标准是：路径必须回答“依赖哪一层平台 ABI”，同时避免为 x86-64、
AArch64、未来 RISC-V 复制相同 Linux UAPI 实现。跨 OS 可移植的探针不属于
这里，例如 `probes/cache-mem/ptr_chase.cpp` 仍放在“测什么”的目录。

CMake 按目标系统条件编译（`if(APPLE)`、`CMAKE_SYSTEM_NAME=Linux` 等），
避免 Mach 代码进入 Linux 构建，也不把 Linux UAPI 带入 Darwin。

## 当前探针

- `macos-arm64/timer_resolution` — `mach_absolute_time` 的 timebase、有效分辨率、单次调用开销。
- `macos-arm64/qos_steering` — 延迟链吞吐双峰验证 QoS→P/E cluster 分流（2026-09-24 实测通过，BACKGROUND 即 E-core 调度手段）。
- `linux/pmu_counter_smoke` — 从安全的 sysfs PMU 名解析 type，或在 sysfs
  发现权限与计数权限不一致时显式接收数值 type；经 `perf_event_open` 对单一
  counting event 做 baseline/workload/final 响应性验证。它只用于能力门禁，
  不直接产 cache geometry 结论。SM8650 验收见
  `docs/reviews/2026-09-27-sm8650-llcc-pmu-smoke.md`。

## 新增平台探针时

1. 先判定最窄平台 ABI，复用现有目录或新建明确的 OS/API 目录；
2. 在 `probes/platform/CMakeLists.txt` 增加对应的平台条件；
3. 运行结果（含日期）登记于需求文档 §2.x 与 `docs/open-items.md`。
