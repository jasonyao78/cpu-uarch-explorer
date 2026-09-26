# 任务说明书：环境事务接线 + Xeon 锁频 + capability 核型采集

> 类型：agent 可执行任务书（自包含，无需对话上下文）
> 创建：2026-09-26｜状态：待执行
> 预估规模：3~5 个 commit；runner/environment 接线 + targets/capabilities 扩展 + 一次锁频重跑
> 必读先行：`AGENTS.md`、`docs/design/measurement-framework-design.md`（§4 平台层、§3.2 事务段落见 ptr-chase-pipeline-analysis.md）、`docs/design/ptr-chase-pipeline-analysis.md` §5.4'（Xeon 800MHz 实证）与 §7.2（改进表）、`docs/open-items.md` OI-8/OI-9

## 1. 背景

三个已实证的问题汇成同一个主题——**环境可控性与能力证据链**：

1. **Xeon 频率失控**：首跑的 `freq_snapshot` 显示 governor=powersave 下指针追逐全程锁 800MHz（内存敏感负载不触发升频，ALU 负载可达 2.0GHz）——ns 绝对值不可跨档比较，仅台阶位置可用（已登记在 `configs/platforms/xeon-8481c-01.json` 的 capabilities_note）。解法是把 governor 锁到 performance——但锁频是 host 级状态突变，必须走事务。
2. **事务协调器已实现未接线**：`runner/environment/`（coordinator/journal/controllers，GB10 模型重实现：host 锁 → journal 台账 → apply → verify → 逆序 restore）代码与测试俱在，但 cli/engine 无任何调用路径。
3. **capability 采集器缺核型维度**：`targets/capabilities.py` 只采 cache 拓扑 + cpufreq；ARM64 平台的定义性特征是核型异构（超大/大/小核、多 cluster），核型决定 controls 控制组设计与结果解读。且 M4 Pro 至今没有机器生成的 capability-manifest（`data/public/capabilities/` 只有 Xeon 一份，2026-09-24 的 M4 Pro 实测结论是 v0.3 §2.1 的散文）。

## 2. 目标（验收标准）

1. **事务接线**：runner 支持环境突变——平台/实验可声明 host 级需求（如 `{"cpufreq.governor": "performance"}`），run 时经 `environment/coordinator` 执行 锁→journal→apply→verify→run→逆序 restore；**默认拒绝突变**，须显式 `--allow-mutation` 才执行（GB10 模式的授权门槛）；中断恢复实证：`kill -INT` 中断的 run 在下次运行前被检测并完成 restore（写测试）；
2. **Xeon 锁频重跑**：governor=performance 下重跑 ptr-chase-cache-sweep，`freq_snapshot` 前后值贴近标称区间上限（不再是 800MHz 平线），run 目录入库；与未锁频 run 的对比结论写入报告（报告层现有功能够用就够用，不够注明缺口不强行实现）；
3. **核型采集进 capability**：Linux 侧采集逐核 `cpu_capacity` / `topology/cluster_cpus_list` / `cpufreq/cpuinfo_max_freq` / `regs/identification/midr_el1`（存在性逐个检测，采不到记 `supported:false`，**不许猜**）；macOS 侧采 `hw.nperflevels` + `hw.perflevel*.{name,logicalcpu}` 等 sysctl——产出 capability-manifest 的 `core-topology` 条目；
4. **M4 Pro 清单补登记**：机器生成 `macbook-m4pro-01` 的 capability-manifest 入 `data/public/capabilities/`（核型 + 已有计时器/QoS 结论的引用）；
5. **sudo 边界清晰**：写 cpufreq 需要 root——controller 写操作经 `sudo`（执行器通道内），无免密 sudo 时给结构化 failure（`capability-unsupported` 或 `mutation-unauthorized`），绝不静默跳过；sudoers 配置步骤写进 runbook 由人工完成；
6. 本机全部测试保持绿色 + 新增测试（fake 锁/journal 恢复/中断恢复/核型解析）；records 过 schema 校验；
7. 文档同步：CHANGELOG、OI-8（事务项标注接线完成）、设计文档、runbook 增补锁频流程。

## 3. 非目标（明确不做，对应设计文档 §7.2）

- 适配器注册表改造（§7.2 #3，属新探针任务）；
- SSH 会话复用（#4）、跨 run 汇总报告（#7）、GB10 回传演练（#8）；
- 测量期多次频率采样 / powermetrics 并发采样（#5 的完整形态，本期锁频即可，采样增强另行立项）；
- p95/p99 尾部统计（#6，repetitions 未到 20 无意义）；
- gem5 一切、Android 一切、新探针。

## 4. 环境事实（已核实）

- 事务三件套：`runner/environment/coordinator.py`（锁+journal+恢复流）、`journal.py`、`controllers.py`（controller 注册点）——先通读再接线，**不要重写**；
- Xeon：governor 可写路径 `/sys/devices/system/cpu/cpuN/cpufreq/scaling_governor`（需 root；per-policy 写 `/sys/devices/system/cpu/policy*/` 亦可）；当前 powersave；`perf_event_paranoid=4` 与本期无关；
- 频率证据样例：`data/public/runs/20260924T184842Z-ptr-chase-cache-sweep-hp2m/`（800MHz 平线记录）；
- capability 采集器：`runner/targets/capabilities.py`（cache 拓扑 + cpufreq，经执行器通道跨 transport 同码）；
- M4 Pro 已实测能力（v0.3 §2.1，MEASURED）：perflevel0=Performance 10 核、perflevel1=Efficiency 4 核、计时器 41.67ns、QoS 双峰——本期转为机器生成清单；
- sudo：Xeon 用户 michael 有 sudo（v0.3 §2.2）；免密配置属人工步骤（升级路径 §8）。

## 5. 约束与坑

1. 通用约束沿用前两份任务书（不编造数字、注释纪律、单位严格、commit 粒度、服务器不提交 git）；
2. **恢复可靠性是第一优先级**：锁频失败可以容忍（记 failure），恢复失败不可容忍——中断恢复必须有测试（模拟 SIGINT 中断 + 下次运行前检测未完成 journal 并完成 restore）；SIGKILL 无法捕获，靠"未完成事务阻塞下次运行 + 启动时恢复"兜底；
3. **journal 与锁在目标机**：ssh 平台的事务状态在远端（coordinator 现有实现已支持经执行器通道——若不完整，补在 coordinator 内，不改引擎语义）；
4. 锁频范围最小化：只写实验用核所在 policy 的 governor（Xeon 单插槽通常单 policy），不碰其他 sysfs；
5. turbo 不等于固定频率：governor=performance 后仍有 turbo/热漂移——记录仍带 freq_snapshot，报告口径写"已锁 performance 档，实测频率见快照"，不宣称"频率已固定"；
6. `runner/schema/README.md` 登记所有新增扩展字段（host_requirements / capability 的 core-topology 等）。

## 6. 建议实施步骤

1. 通读必读文件与 `runner/environment/` 三件套；跑通现有测试；
2. controllers 落地 cpufreq governor controller（读原值/写新值/验证/还原四方法）+ fake 测试；
3. 接线：平台/实验声明 host_requirements → cli/engine 在 run 外围包事务（默认拒绝 + `--allow-mutation`）；
4. 中断恢复测试（SIGINT 与"上次未完成"两条路径）；
5. capability 核型采集（Linux sysfs + macOS sysctl）+ 解析测试；
6. Xeon：sudoers 人工配置（或人工 sudo 执行）→ 锁频重跑 sweep → 数据入库与对比结论；
7. M4 Pro 清单生成入库；
8. 文档与提交（粒度：controller+接线 / capability / Xeon 数据 / 文档）。

## 7. 交付物清单

- `runner/environment/` 接线（含 cpufreq controller）与测试；`--allow-mutation` 门槛；
- `targets/capabilities.py` 核型采集 + 测试；
- `data/public/capabilities/`：Xeon 更新版 + `macbook-m4pro-01` 首份机器清单；
- `data/public/runs/<时间戳>-ptr-chase-cache-sweep/`（锁频后 Xeon 数据，含报告）；
- runbook 增补（sudoers 配置、锁频运行流程）；文档更新（§2.7）。

## 8. 升级路径（停下来问人）

- 无免密 sudo 且用户无法配置 sudoers（改为人工 sudo 执行或降级为只读方案，先问）；
- 中断恢复测试暴露出 coordinator 的模型级缺陷（不是接线问题）——回到 OI-9 讨论；
- 锁频后频率仍不稳定（可能是热限制或 RAPL 功耗墙）——如实记录并停止，不继续调参；
- 需要改 run-record schema 结构（非扩展字段）才能表达事务信息。
