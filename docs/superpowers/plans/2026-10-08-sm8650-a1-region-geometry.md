# SM8650 A1 区域几何修复与交接更新计划

## 本次任务的目的（给人类看）

解除真机 pilot 暴露的“生产区域跨 256MiB 窗口、正式入口拒绝 purity=0”阻塞；保留旧数据审计，交付可验证的软件几何与新的设备交接。用户已在会话批准此前的预约内对齐方案并要求连续完成；本轮单代理，不连接手机，不推远程。

**Goal:** 使 A1 默认四个 64MiB 区域不随 mmap 页偏移跨高位窗口，并保持现有 H/target/scope 配额和正式判据。

**Architecture:** `probes/common/tlb_set_layout.h` 提供纯整数预约尺寸/布局函数；预约留一个窗口的对齐余量，在自有映射内部取 256MiB 对齐起点，保留区域 k 的 k×256MiB+k×8页相对偏移。`probes/cache-mem/ptr_chase.cpp` 与 C++ 黄金测试共享该函数。正式消费不放宽 purity 或谱系门；冻结代码摘要覆盖新头文件。

**Tech Stack:** C++17/POSIX mmap、CMake/CTest、Python unittest、真实 runner planner/adapter/writer/loader（外部 I/O 合成）。

## 执行清单

- [x] 在 `scripts/reproduce_tlb_region_boundary_20261008.py` 提取生产区域预约块，替换系统映射为确定性地址，重现接近窗口尾部的跨窗 RED；只模拟映射返回地址，不模拟布局算法。
- [x] 新增 `probes/common/tlb_set_layout.h`：检查区域数/池大小/地址和尺寸溢出；预约内对齐；每区域末页与起点位于相同窗口，保留余数分配。不满足尺寸合同返回 false；所有映射与回收仍由调用方负责。
- [x] `probes/cache-mem/ptr_chase.cpp` 调用共享布局，所有 mprotect 位于拥有的预约内；失败仍命名，保留 fallback 披露与消费者拒绝。更新 purity 注释。
- [x] 新增 `probes/tests/tlb_set_layout_golden.cpp`，检查全部 65536 种 4KiB 页偏移、2/4/16 区域、极限池/溢出/短预约、真实宿主 PROT_NONE 预约及 H×target×scope 采集；在 `tests/CMakeLists.txt` 注册。`probes/tests/tlb_set_collect_golden.cpp` 的布局改为同源实现，完整长度 munmap。
- [x] `analysis/sm8650_tlb_a1_freeze.py` 的 CODE_PATHS 纳入新头；`analysis/tests/test_sm8650_tlb_a1_freeze.py` 钉住存在及该头漂移拒绝。
- [x] 新增 `configs/experiments/ptr-chase-sm8650-x4-tlb-a1-geometry-smoke.json`：H{1,2,3,4}×scope{-1,0,1}×W12，12 cases×2 reps；只做设备几何资格，不当正式样本或标定。
- [x] 更新 `docs/runbooks/2026-10-08-sm8650-a1-integrated-handoff.md`：pilot 证据与限制、先几何资格再独立标定、48/48/32含义、工具执行与人为调参责任。旧 `docs/runbooks/2026-10-07-sm8650-tlb-pilot-kickoff.md` 仅加历史替代提示。
- [x] 同步 `docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md` 几何合同/部件索引；`docs/open-items.md` 登记设备尚待验收；新 `docs/reviews/2026-10-08-a1-geometry-and-pilot-audit.md` 留事实与验证范围。不代提交 m0b run 数据。
- [x] 执行 `cmake --preset macos-arm64-release`、`cmake --build --preset macos-arm64-release`、`ctest --preset macos-arm64-release`，runner/analysis 全量；`scripts/verify_a1_software_exit_20261008.py` 验证完整合成 producer、51旧runs与5图表字节一致；对新 smoke 做真实 plan 预览。每项保存退出码与必要摘要。
- [x] 复核差异/暂存名单，只提交自有文件到 r2；保持 m0b/main 他人数据与改动，远程不操作。设备实际构建部署、Linux PMU 与几何资格仍交上板 Agent。

## 验收与边界

RED 必须来自生产预约块的跨窗断言，修复后同一反例 GREEN；共享几何金样不得依赖 mmap 随机碰巧不跨窗。纯整数/宿主 mmap 验证不能晋升为 Android/SM8650 测量。对齐变更使旧二进制及数值标定不可继承，正式128case仍只消费专用两块标定生成的有效冻结工件。
