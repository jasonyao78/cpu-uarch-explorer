# runner/schema — 统一数据模型

## v2（当前，ADR-0006）

| 文件 | 用途 |
|---|---|
| `experiment.schema.json` | ExperimentSpec：实验语义定义（测什么/参数/前置条件/指标定义） |
| `capability-manifest.schema.json` | 目标能力快照（capability discovery 产物，按 target 引用） |
| `run-record.v2.schema.json` | 运行记录 v2：目标正交分解（os/isa/abi/target_id/cpu_profile/execution_kind/executor/transport，`backend` 仅派生展示名）、运行状态（ok/failed/skipped/unsupported）、统计量（repetitions/median/分位数/raw_samples_ref）、证据来源（evidence.provenance）与访问分类（access_class）分离 |
| `artifact-manifest.schema.json` | 产物清单：二进制/镜像/checkpoint/原始样本的 SHA256 与构建谱系 |

原则：信封强制（v2 的 required 列表）；`schema_version` 必填；`additionalProperties=true`（新增字段不破坏旧读者，**扩展字段必须登记到本 README**）；证据来源与访问分类是两个正交轴。

## v1（归档）

`record.schema.json`（v1，2026-09-23 基线）：已被 v2 取代，保留作历史参考，新记录一律用 v2。

Runner 层实现（targets 适配、采集、落盘）按 ADR-0006 的组合式结构落地（BuildProfile/Transport/Executor/PlatformControl/Collector/Parser，见 OI-8）。
