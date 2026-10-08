# runner/schema — 统一数据模型

## v2（当前，ADR-0006）

| 文件 | 用途 |
|---|---|
| `experiment.schema.json` | ExperimentSpec：实验语义定义（测什么/参数/前置条件/指标定义） |
| `capability-manifest.schema.json` | 目标能力快照（capability discovery 产物，按 target 引用） |
| `run-record.v2.schema.json` | 运行记录 v2：目标正交分解（os/isa/abi/target_id/cpu_profile/execution_kind/executor/transport，`backend` 仅派生展示名）、运行状态（ok/failed/skipped/unsupported）、统计量（repetitions/median/分位数/raw_samples_ref）、证据来源（evidence.provenance）与访问分类（access_class）分离。metrics 强制随 status 条件化（2026-09-24 评审修订）：`status=ok` 时 ≥1 项数值 metric；`failed/skipped/unsupported` 允许空 metrics 且必填结构化 `failure{reason, detail}`；repetitions/statistics 的强制条件由 ExperimentSpec 决定，不在本 schema 强制 |
| `artifact-manifest.schema.json` | 产物清单：二进制/镜像/checkpoint/原始样本的 SHA256 与构建谱系 |

原则：信封强制（v2 的 required 列表）；`schema_version` 必填；`additionalProperties=true`（新增字段不破坏旧读者，**扩展字段必须登记到本 README**）；证据来源与访问分类是两个正交轴。

### 已登记的 ExperimentSpec 扩展字段

| 字段 | 类型 | 用途 | 登记日期 |
|---|---|---|---|
| `execution.controls` | non-empty unique string array | 按 id 选择 platform `controls` 子集；保持控制定义归平台所有，实验只声明需要哪些控制，未知 id 在 plan 期失败 | 2026-09-28 |
| `execution.params.repetitions` | positive integer | 实验级显式重复数，优先于平台默认；用于 ≥10 次等方法学门禁，计划预览必须显示实际值 | 2026-09-28 |
| `execution.probe_shape` | string | 语义参数派生形状注册键（`_CASE_DERIVERS`）；`ptr_chase`（默认）/ `tlb_set`（M0-4b TLB set prime+probe，同一 ptr_chase 二进制 `--tlb-set-mode` 模式分发）。未注册形状 plan 期拒绝 | 2026-10-01 |
| `execution.params.set_hypothesis` | integer 1..4 | tlb_set 形状：候选 VPN→set 索引假设 H1 位选 / H2 相邻 XOR / H3 高位折叠 / H4 三字段 XOR | 2026-10-01 |
| `execution.params.set_target` / `set_target2` | integer 0..255 | tlb_set 形状：目标 set / T2 对照组 set（可选） | 2026-10-01 |
| `execution.params.set_window` | integer ≥0 | tlb_set 形状：每轮 probe 访问数 W；**0 = 空窗底噪 case（G0-3 标定）** | 2026-10-01 |
| `execution.params.set_rounds` | integer ≥2（默认 20） | tlb_set 形状：轮数；round 0 冷启动剔除 | 2026-10-01 |
| `execution.params.set_pool_pages` | integer ≥1024（默认 65536） | tlb_set 形状：目标地址池总页数（多区域共享） | 2026-10-01 |
| `execution.params.set_filler_pages` | integer ≥0（默认 512） | tlb_set 形状：prime 驱逐链页数（独立映射，按候选 H 过滤目标 set） | 2026-10-01 |
| `execution.params.set_regions` | integer 1..16（默认 4） | tlb_set 形状：F4 多稀疏 VA 区域数（跨 256MiB 边界使 VPN[23:16] 各异）；预约失败回退单区域并输出 `set_domain=single-region-fallback` 命名降级 | 2026-10-01 |
| `execution.params.set_scatter` | 0/1 | tlb_set 形状：无冲突负控（G0-3）——W 页各落不同 set；要求 1≤W≤256 | 2026-10-01 |
| `record.probe descriptor 核验`（非字段） | 契约 | MB-06：adapter `parse_output(stdout, stderr, expected)` 第三参携带 plan case_params；解析形状由**请求**决定——请求 tlb_set 输出 legacy 或反之即 ParseError；tlb_set 自描述字段（hypothesis/target/target2/window/rounds/pool/filler/regions/scatter/region_scope/nsets/seed）与请求不一致或未报告 → ParseError；请求的 PMU 判据事件缺失 → ParseError | 2026-10-07（PA-02 修订） |
| `record.probe.realized` | object | PA-02：tlb_set 探针 realized 自描述域随结构化记录持久化——set_domain / set_active_regions / set_region_nodes（实际激励审计）/ 实验条件字段；requested（params）与 realized 分开；legacy 输出无此键 | 2026-10-07 |
| `execution.params.set_region_scope` | integer -1..15（默认 -1） | tlb_set 形状：-1=全域配额取样；0..K-1=仅该区域收集（A1 隔离对照）；必须 < set_regions | 2026-10-07 |
| `execution.params.set_nsets` | integer 0..256（默认 0=关） | tlb_set 形状 N-set 模式：收集候选 set 0..nsets-1 各 W 页进一条链（A3 整体 translation reach 估计量）；与 set_target2/set_scatter 互斥 | 2026-10-07 |
| `record.metric_contract` / `group.identity` 语义 | 契约 | MB-06：分析器分组键采用类型规范身份——bool True 与 int 1 不可合并，任何 params 差异（类型规范残差）阻止合并；报告面 identity 字典保持 legacy 原值（旧重放逐字一致） | 2026-10-07 |
| `generator` | object | 致密配置生成器审计块（input_run_sha256/rules_sha256/output_sha256 三锚定 + dense_points 来源标注 + quota 核算）；仅由 `analysis/tlb_dense_gen.py` 产出，非手写 | 2026-09-29 |

### A1 最终消费与逐进程 realized 合同（2026-10-08）

- `record.probe.realized` 完整保存 tlb_set 整数 descriptor（含 `set_pool_pages` / `set_filler_pages` / `scatter`）。adapter 验证输出，A1 consumer 再按正式 plan 验证完整请求身份与实际几何，不依赖首样本标签。
- 若各进程 realized 不同，`record.probe.realized.samples[]` 保存 `{sample_index, raw_sample_ref, realized}` 并保留公共字段；`domain_consistent` 只表示 mode/domain/page/region/scope/nsets 一致。域内 VA 重分配不等于混域；每个进程的 purity/配额/实际高字段分别核验，任一不合格即命名拒绝。
- 正式 consumer 只接受登记的完整 128-case 计划，各 case 恰一条成功记录、plan 指定的 10 observations。重复 record 拒绝；不隐式合并，不按最后一条覆盖。每 metric 的有限值/单位/中位、sample indices/raw 引用及事件/窗口有效轮守恒均校验。
- 以上为新增 A1 入口合同；旧通用分析器、历史 records 与 schema required 不变。扩展保持 `additionalProperties=true`。

### 已登记的 run-record 扩展字段

| 字段 | 类型 | 用途 | 登记日期 |
|---|---|---|---|
| `experiment_id` | string | `runner/engine.py:run_plan` 在每条 record 写盘前持久化 `Plan.experiment_id`，与 `run-manifest.json` 同源，覆盖 ok/failed/skipped/unsupported。供独立记录消费及 A1 L1/L2/L3 归层；旧记录允许缺省，不回填历史数据，不新增 schema required，不改变 schema_version，旧读者可忽略此扩展 | 2026-10-08 |

### 已登记的 target 扩展字段

| 字段 | 类型 | 用途 | 登记日期 |
|---|---|---|---|
| `ssh_host` | string | transport=ssh 时的 ssh config 别名（如 `xeon-8481c-01`）；真实地址禁止入库，映射在 `data/private/hosts.md` 与本机 `~/.ssh/config` | 2026-09-25 |
| `ssh_remote_root` | string | 远端仓库根目录；SshExecutor 执行前 cd 的目标（默认 `~`） | 2026-09-25 |
| `adb_workdir` | string | AdbExecutor 的设备侧工作目录（默认 `/data/local/tmp`）；cd 容错（目录未建时退回默认目录，采集脚本全绝对路径不受影响） | 2026-09-27 |
| `environment.freq_snapshot` | object | 每 case 前后 `scaling_cur_freq` 瞬时值 `{before_hz, after_hz}`（measurement-discipline §5 落地：锁频前的频率证据；macOS 无此接口则省略，不编造） | 2026-09-25 |
| `environment.aux_snapshots` | object | 平台配置 `aux_snapshots` 声明的只读采集命令快照 `{name: {before, after}}`（GB10 §5.4：GPU 利用率等；命令失败则该 name 省略） | 2026-09-25 |
| `probes.<name>` 的 dict 形态 | `{local, remote}` | deploy 模式（交叉编译产物推送目标机，Android 预演课题）——非 GB10 自驱模式 | 2026-09-25 |
| `host_requirements`（平台配置顶层键） | object | 声明式 host 级需求 `{"cpufreq.governor": "performance"}`：run 时经环境事务执行，**默认拒绝、须 `--allow-mutation`**；启动前自动 reconcile 中断残留事务（2026-09-26 接线任务） | 2026-09-26 |
| `environment_profiles.<name>`（平台配置） | object | 显式选择的测量环境 profile：把可恢复的 `host_requirements` 与只读 `measurement_environment` 门禁绑定；不选择 profile 时不隐式改变设备状态 | 2026-09-27 |
| capability `core-topology` 条目 | object | 核型事实：linux-sysfs 逐核 `{capacity, max_freq_khz, midr_el1, cluster_cpus_list}`（缺失维度=null 不猜）或 macos-sysctl `perflevels[]` | 2026-09-26 |

### 已登记的 environment 扩展字段

| 字段 | 类型 | 用途 | 登记日期 |
|---|---|---|---|
| `environment.state_snapshot` | object | case 前后 Android 状态证据及 `policy_result`；含 cpufreq 各 policy、wakefulness、DeviceIdle、airplane、活动相机、thermal、服务和 loadavg。前置失败不执行 probe，后置漂移保留 raw 但输出空 metrics | 2026-09-27 |

### 已登记的通用 metric 扩展字段

| 字段 | 类型 | 用途 | 登记日期 |
|---|---|---|---|
| `metrics[].observations` | array | 每个 repetition 的 `{sample_index, value, raw_sample_ref, ...样本级字段}`；解决聚合记录只保留首样本附加证据的问题。metric 顶层只复制所有 repetition 完全一致的附加字段 | 2026-09-28 |

### 已登记的 ptr_chase metric 扩展字段

| 字段 | 类型 | 用途 | 登记日期 |
|---|---|---|---|
| `warmup_loads` | non-negative integer | 实际执行的精确 warmup load 数；新协议由 `warmup_passes × slots` 派生，legacy 可为任意非负值 | 2026-09-27 |
| `warmup_passes_effective` | non-negative number | `warmup_loads / slots`，审计 legacy 非整数遍历与完整环覆盖率 | 2026-09-27 |
| `warmup_state` | `warm` or `cold-warm0` | 明确 `-w 0` 只是零预热，不冒充真正 cold | 2026-09-27 |
| `page_policy_requested` | string | `default` / `base-madvise` / `hugetlb-fallback` / `hugetlb-strict` / `thp-madvise` 请求语义 | 2026-09-27（2026-09-28 增补 base） |
| `page_policy_actual` | string | `platform-default` / `base` / `thp` / `mixed` / `hugetlb-2m` 实际 backing | 2026-09-27 |
| `anon_huge_kb` | non-negative integer | Linux `/proc/self/smaps` 对目标 VMA 观测到的 `AnonHugePages` 总量 | 2026-09-27 |
| `page_policy_actual_before`, `page_policy_actual_after` | string | warmup 后/测量前与 timed/PMU 窗后的实际 backing 端点；取值同 `page_policy_actual` | 2026-09-28 |
| `anon_huge_kb_before`, `anon_huge_kb_after` | non-negative integer | 两个端点对目标 VMA 观测到的 `AnonHugePages`；不一致时 probe fail-closed | 2026-09-28 |
| `page_backing_endpoints_equal` | integer `1` | 成功输出的两个 backing 端点相同；离散端点相等不声称排除窗内瞬态变化 | 2026-09-28 |
| `page_policy`, `page_kb` | string, non-negative integer | 兼容既有 reader 的摘要；新判断必须优先使用 requested/actual 字段 | 2026-09-27 |
| `pmu_type`, `pmu_config` | non-negative integer | `pmu.<label>.count` 的 Linux perf PMU type/config；来自 ExperimentSpec 的显式事件描述 | 2026-09-28 |
| `time_enabled_ns`, `time_running_ns` | non-negative integer | 每个 PMU observation 的 perf enabled/running delta；零 running 拒绝，multiplex 判定由二者比值审计 | 2026-09-28 |
| `vma_base` | string (hex) | 建链缓冲区起始 VA（ASLR，布局观测，路线 A） | 2026-09-29 |

ExperimentSpec 的可选固定参数 `pmu_events` 登记为
`[{"name": <安全小写标签>, "type": <uint32>, "config": <uint64/base-0 string>}]`；
Runner 在 plan 期归一化为整数，probe 以重复的
`--pmu-event label:type:config` 接收。旧 spec 不声明该参数时执行路径不变。

## v1（归档）

`record.schema.json`（v1，2026-09-23 基线）：已被 v2 取代，保留作历史参考，新记录一律用 v2。

Runner 层实现（targets 适配、采集、落盘）按 ADR-0006 的组合式结构落地（BuildProfile/Transport/Executor/PlatformControl/Collector/Parser，见 OI-8）。
