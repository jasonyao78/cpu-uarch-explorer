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
- **评审修订（2026-09-24，第二轮）**：ptr_chase 输入校验/无偏洗牌/退出码修复 + 首批 CTest（含 UBSan 目标）；§4「同一份源码」措辞修订为 ExperimentSpec 语义一致性；新增 ADR-0006（目标正交分解 / ExperimentSpec / Probe ABI）与 schema v2 四类记录（run / capability / artifact / experiment，证据来源与访问分类分离）。
- **借鉴迁移（2026-09-24）**：登记 arm64-uarch-probe（GB10 项目，BSD-3 本人作品，在手且活跃）为借鉴模式（OI-9）；新增 `docs/methodology/measurement-discipline.md`（测量方法学纪律：温度语义 / 页策略 / 统计 / 置信度 / 修正留痕 / 报告模板）；ptr_chase 改进 backlog 入 `probes/cache-mem/README.md`；Python 工具链定为 uv（ADR-0007）。
- **gem5 构建验证通过（2026-09-24）**：Xeon 系统 scons 构建成功（`build/ARM/gem5.opt` 954MB）；ARM64 SE 冒烟仿真通过（`Exiting @ tick`，退出码 0）。据此修订 ADR-0007 与 runbook——gem5 构建用系统工具链（uv 驱动会导致 gem5py 崩溃，Error 134），uv 职责收缩为本仓依赖管理；OI-1 剩余 intake 梳理与 SE 模式精简配置。
- **外部评审纠偏（2026-09-24，第三轮）**：评审核实 GB10 参考 Runner 六处实现缺陷（working-set 单位静默降级、samples 配置死参数、journal_tx_ids 不追加、environment 硬编码 unknown、coordinator 接线未闭环等），OI-9 相应修订为"借分层/协议/测试方式，不借当前 Runner 实现"；环境事务子系统裁定改为"借模型、重新实现接线"；measurement-discipline 六条措辞纠偏（真 cold 需佐证 / hugepage 非消除 / 驱逐指令按 ISA 分述 / median-of-N 非置信度证明 / cycles 区分实测与换算 / 违反纪律数据改 quarantine 制）；reference-materials 标注 GB10 许可证矛盾（根 LICENSE BSD-3-Clause vs pyproject Proprietary）；run-record.v2 的 metrics 强制随 status 条件化，新增结构化 failure 字段。
- **Runner 最小纵向闭环落地（2026-09-24，OI-8 第一阶段）**：`runner/` Python 包实现 Plan → repeated execution → adapter → raw artifact → parser → statistics → atomic record 全链（stdlib 零依赖）；`configs/` 新增 ExperimentSpec（ptr-chase-cache-sweep）与 platform 配置（macbook-m4pro-01，QoS 双控制）；22 项测试含真实二进制契约测试；首份实机数据 28 case × 5 重复全 ok 并通过 schema v2 校验（`data/public/runs/`）。M4 Pro 最小骨架的"probe → 统一 JSON 数据"段打通，剩余报告层（analysis/）。
- **仓库布局修订（2026-09-24，ADR-0008）**：构建目录收敛为单一 `build/` 树（CMakePresets.json 驱动，`<target-triple>/<profile>` 分层），`.gitignore` 一行全覆盖；评审原文归档 `docs/reviews/`、参考仓源码副本删除（许可证矛盾未决不入库）；删除 gem5 本机死构建残留（~1.5G，elf.h 阻塞残骸）；`configs/` 与测试按语言分家正式入册（§5）；rsync runbook 排除规则同步简化。
- **数据策略与代码纪律（2026-09-24）**：runs 目录入库范围收敛为 records/manifests（`raw/` 原始样本为可再生中间产物，gitignore，SHA256 manifest 锚定完整性，§7 已登记）；新增 `docs/methodology/comment-discipline.md` 注释纪律（模块锚点 / 契约 docstring / 决策留依据 / 反模式锚点），runner 存量代码已按此补齐注释。
- **gem5 增量树最小集修剪（2026-09-24，OI-1）**：blob 哈希普查定位增量树真实基线为 v25.0.0.1（873/1008 吻合）；删除 873 个纯旧版携带文件（消除 overlay 静默回退 v25.1 的隐性风险），保留 135 个有意 delta（O3/内存模型本体 27 改 + D9300 配置与 NPU 资产等 108 新）；Xeon 重建 + SE 冒烟为验证门（runbook 附4），通过前不算完成。
- **gem5 改钉 v25.0.0.1（2026-09-25，ADR-0004 修订）**：修剪后钉 v25.1 的重建暴露结构性冲突（失败 #1：`m5.internal` 引用失效——已按 port 修复 SConscript；失败 #2：v25.1 O3 重构拆出 IQUnit 与 v25.0 增量不兼容）；裁定 submodule 改钉增量原生基线 v25.0.0.1，零移植还原原项目已验证状态；`apply_patchset.sh` 增加基线断言与预存脏树检测（OI-8 overlay 加固两项落地）；v25.1 移植（746 行有意改动 + O3 重构适配）入 backlog。
