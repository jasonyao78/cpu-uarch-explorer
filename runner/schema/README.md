# runner/schema — 统一数据模型

## v2（当前，ADR-0006）

| 文件 | 用途 |
|---|---|
| `experiment.schema.json` | ExperimentSpec：实验语义定义（测什么/参数/前置条件/指标定义） |
| `capability-manifest.schema.json` | 目标能力快照（capability discovery 产物，按 target 引用） |
| `run-record.v2.schema.json` | 运行记录 v2：目标正交分解（os/isa/abi/target_id/cpu_profile/execution_kind/executor/transport，`backend` 仅派生展示名）、运行状态（ok/failed/skipped/unsupported）、统计量（repetitions/median/分位数/raw_samples_ref）、证据来源（evidence.provenance）与访问分类（access_class）分离。metrics 强制随 status 条件化（2026-09-24 评审修订）：`status=ok` 时 ≥1 项数值 metric；`failed/skipped/unsupported` 允许空 metrics 且必填结构化 `failure{reason, detail}`；repetitions/statistics 的强制条件由 ExperimentSpec 决定，不在本 schema 强制 |
| `artifact-manifest.schema.json` | 产物清单：二进制/镜像/checkpoint/原始样本的 SHA256 与构建谱系 |

原则：信封强制（v2 的 required 列表）；`schema_version` 必填；`additionalProperties=true`（新增字段不破坏旧读者，**扩展字段必须登记到本 README**）；证据来源与访问分类是两个正交轴。

### 已登记的 target 扩展字段

| 字段 | 类型 | 用途 | 登记日期 |
|---|---|---|---|
| `ssh_host` | string | transport=ssh 时的 ssh config 别名（如 `xeon-8481c-01`）；真实地址禁止入库，映射在 `data/private/hosts.md` 与本机 `~/.ssh/config` | 2026-09-25 |
| `ssh_remote_root` | string | 远端仓库根目录；SshExecutor 执行前 cd 的目标（默认 `~`） | 2026-09-25 |
| `environment.freq_snapshot` | object | 每 case 前后 `scaling_cur_freq` 瞬时值 `{before_hz, after_hz}`（measurement-discipline §5 落地：锁频前的频率证据；macOS 无此接口则省略，不编造） | 2026-09-25 |

## v1（归档）

`record.schema.json`（v1，2026-09-23 基线）：已被 v2 取代，保留作历史参考，新记录一律用 v2。

Runner 层实现（targets 适配、采集、落盘）按 ADR-0006 的组合式结构落地（BuildProfile/Transport/Executor/PlatformControl/Collector/Parser，见 OI-8）。
