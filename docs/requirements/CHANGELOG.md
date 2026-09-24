# 需求基线 CHANGELOG

## v0.3 — 2026-09-23（首次落盘基线，tag `req-v0.3`）

相对此前口头/文档版本的修正：

- **Android 设备合并为一台**：此前提到的红米设备与高通平板确认为同一台（已 root 的红米高通手机）。
- **平台画像补全**：M4 Pro（14C/48GB/macOS 26.5.1）与 Xeon 8481C（56C/112T/单 NUMA/125 GiB）的硬件、权限、角色与约束完整入册。
- **D9300 实机入册**：设备在手，定位为 gem5 D9300 模型的严格校准对象；型号/root 待补，后置启用（新增 §2.5、平台矩阵新增 `android-arm64-d9300-phys`）。
- **§4 系统架构**：四层架构（Probe/Runner/数据报告/校准）+ 统一实验协议 + capability discovery 机制。
- **§5 目录结构**：按实际仓库结构补全。
- **§7 开源约束**：许可证定为 Apache-2.0；新增 mem-lat.c 来源审计结论引用（ADR-0002）；新增"私有转公开历史全量可见"提醒。
- **§9 校准误差目标**（新增）：T1 ±1 cycle / ±5~10%，T2 ±10%，T3 ±10~15%；校准顺序与"microbenchmark 校准、综合分只验证"铁律。
- **过程管理决策入册**：trunk-based Git 策略（ADR-0001）、JSONL 数据模型（ADR-0003）、submodule 统一 third_party/（ADR-0004）、费曼工作流定位。

## v0.3 后修订（2026-09-24，未升版）

- **x86 服务器画像回填**（§2.2）：Ubuntu 24.04.4 LTS / kernel 7.0.0-30 / perf 7.0.12 / paranoid=4（sudo 可用）/ SPR 完整 PMU（PEBS + 32-deep LBR + RAPL）。OI-3 仅剩脚本评审。
- **M4 Pro PMU 能力实测**（§2.1）：拓扑（10P+4E、cpufamily 399882554）与 powermetrics 采样器清单为 MEASURED；xctrace PMC 与 QoS 分流验证仍待办（OI-5 部分关闭）。
- **OI-5 关闭（2026-09-24 当日补充）**：计时器（41.67ns 分辨率、4.06ns 开销）与 QoS 分流（双峰 3.8×，BACKGROUND=E-core 手段）实测完毕；PMC 转为"装 Xcode 后验证"的环境决策。能力探针落 `probes/platform/`。
- **gem5 基线源码就位**（§2.4）：上游 stable v25.1.0.1 @ f5c5a6e390；**未发现 D9300 修改**——D9300 模型工作需定位或决策自建（OI-1 更新，见 docs/gem5-d9300-intake.md）。
- 个人参考材料移至仓库外 `../cpu-uarch-ref/`（只读），新增受跟踪索引 `docs/reference-materials.md`。
- **gem5 D9300 模型集成（当日追加）**：模型工作定位（overlay 增量树，`arm_multicore_d9300.py` + CoralNPU/NDP/Gemmini）；上游转正式 submodule 钉 `f5c5a6e390`；集成哲学修订为 overlay（ADR-0004 修订）；基线兼容性 scons 构建验证进行中（详见 OI-1 与 `docs/gem5-d9300-intake.md`）。
