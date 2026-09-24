结论：`1826c74` 不需要整体回滚，但不能视为“系统借鉴已完成”。现有分析方向基本正确，却遗漏了参考仓最有价值的软件架构部分，并把数条 GB10 经验写成了跨平台强制规律。建议补一个纠偏提交，而不是继续按当前文档直接实现。

## 对现有结论的裁定

### P0：测量方法学存在过度断言

[measurement-discipline.md](/Users/michaelyao/workspace/cpu-uarch-explorer/docs/methodology/measurement-discipline.md:11) 需要修正：

- `cold-dbl-evict` 不能因为“工作集 ≤ LLC”就称为“真 cold”。容量驱逐、`DC CIVAC`、双重 eviction 都不能独立证明目标数据已离开系统级缓存。应称为“eviction-conditioned first traversal”，并通过工作集曲线、对照组、PMU 等确认。
- hugepage 是减少并重塑 TLB/page-walk 开销，不是“消除 TLB 噪声”。2 MiB 也是 GB10 当前配置，不是 Linux 通用常量。
- `clflush 类指令`不应跨 ISA 合并表述。参考代码实际使用 ARM `DC CIVAC`，且自己明确声明只到 PoC、不保证清出 L3/SLC：[chase_pmu](/Users/michaelyao/gb10-cpu-arch-probe/src/chase_pmu/chase_pmu_v2.7.3.c:67)。
- `median-of-5/7`可作为默认采样策略，不能作为普适置信度证明。还需要独立性、热漂移、异常处理、终止条件。
- `ns 与 cycles 成对记录`必须区分：
  - PMU/硬件计数器直接测得的 cycles；
  - 用频率换算的 derived cycles。
  
  `scaling_cur_freq` 或 `powermetrics` 快照不能当作测量区间的精确频率。
- “违反纪律的数据不得进入 data/ 任何层级”不利于审计。更合理的是允许进入 `raw/quarantine`，但禁止晋升到 `candidate/baseline`。

### P0：参考 Runner 不能照搬

我实测复现了一个严重参数错误：

```text
params= {'page-policy': ('default', 'platform-default'),
         'samples': (7, 'profile'),
         'working-set': ('64MiB', 'platform-default')}
argv= ['1024', '0', '0', '42', '0', '0']
```

配置声明 `64MiB`，但 Runner 只识别 `MB/KB`，最终静默降级为 `1024KB`：[runner.py](/Users/michaelyao/gb10-cpu-arch-probe/arm64_probe/execution/runner.py:440)、[gb10.json](/Users/michaelyao/gb10-cpu-arch-probe/configs/platforms/gb10.json:29)。

此外：

- profile 声明 `samples=7`，Runner 每个 case 只执行一次，永远写 `sample_index=0`：[baseline.json](/Users/michaelyao/gb10-cpu-arch-probe/configs/profiles/baseline.json:7)、[runner.py](/Users/michaelyao/gb10-cpu-arch-probe/arm64_probe/execution/runner.py:319)。
- `journal_tx_ids` 创建后从未追加：[runner.py](/Users/michaelyao/gb10-cpu-arch-probe/arm64_probe/execution/runner.py:131)。
- environment 仍写成 `platform=unknown`：[runner.py](/Users/michaelyao/gb10-cpu-arch-probe/arm64_probe/execution/runner.py:480)。
- CLI 用 `coordinator=None` 构造 Runner：[main.py](/Users/michaelyao/gb10-cpu-arch-probe/arm64_probe/cli/main.py:289)。
- 即使接入 coordinator，Runner 调用也缺少 `backend` 参数，而真实接口要求它：[coordinator.py](/Users/michaelyao/gb10-cpu-arch-probe/arm64_probe/environment/coordinator.py:58)。
- coordinator 异常被宽泛捕获并转成 error sample，可能掩盖环境恢复失败。

所以 OI-9 中“runner 蓝图参考”是对的，但必须明确：

> 借分层、协议和测试方式，不借当前 Runner 实现。

### P1：不应排除环境事务模型

[OI-9](/Users/michaelyao/workspace/cpu-uarch-explorer/docs/open-items.md:27) 以“coordinator=None”为由整体不吸收环境事务子系统，裁定过头。

事务协调器本身已经实现了：

- host-wide lock；
- durable journal；
- inspect → validate → apply → verify；
- 失败后逆序 restore；
- signal 中断恢复；
- 未完成事务阻止下一次运行；
- 显式 restore/recovery。

问题出在 CLI/Runner 接线未闭环，而不是事务模型没有价值。将来控制 Linux governor、hugepage、THP、perf 权限时，这正是应该借鉴的核心模式。

### P1：许可证登记需要标注矛盾

参考仓根 [LICENSE](/Users/michaelyao/gb10-cpu-arch-probe/LICENSE:1) 是 BSD-3-Clause，但 [pyproject.toml](/Users/michaelyao/gb10-cpu-arch-probe/pyproject.toml:7) 明确写着 `Proprietary`。

因此当前 [reference-materials.md](/Users/michaelyao/workspace/cpu-uarch-explorer/docs/reference-materials.md:15) 不应无保留地写“BSD-3-Clause”，建议改为：

> 根 LICENSE 为 BSD-3-Clause；包元数据仍标为 Proprietary，待参考仓统一后再复制代码。当前仅借鉴设计和方法。

### P1：“真实捕获 fixture”不是已确认事实

参考仓自己的复盘明确承认原 fixture 曾是手写、不是实际 probe 输出：[error-patterns-and-prevention.md](/Users/michaelyao/gb10-cpu-arch-probe/docs/superpowers/handoffs/2026-06-16-error-patterns-and-prevention.md:194)。

现在新增了真实二进制契约测试，这是非常值得借鉴的；但本机测试中 ARM Linux 二进制相关的 7 项均因未编译而跳过。因此 OI-9 应写成：

> 吸收“真实二进制→argv→stdout/stderr→parser”的契约测试纪律；fixture 的真实来源必须由 capture manifest/命令证明，不能因文件存在就默认真实。

## 真正值得优先借鉴的设计

| 优先级 | 借鉴项 | 裁定 |
|---|---|---|
| P0 | Experiment / Profile / Platform 三分离 | 强烈借鉴；避免把平台默认值写进实验定义 |
| P0 | `ResolvedValue(value, source)` | 强烈借鉴；参数来源可追溯到平台/profile/CLI |
| P0 | Plan 与 Run 分离 | 强烈借鉴；先得到确定性 case 集合和 unsupported/blocked 状态 |
| P0 | Adapter 与真实二进制契约测试 | 强烈借鉴；包括 argv、退出码、stdout+stderr、parser |
| P0 | 非成功记录允许没有测量值 | 应立即借鉴；当前 v2 schema 对 failed/skipped 仍强制 numeric metric |
| P1 | 环境事务、journal、恢复 | 借模型并重新实现接线；不要整体排除 |
| P1 | 原子结果写入与 case signature | 借鉴 `fsync → replace → parent fsync` 和 resume 兼容检查 |
| P1 | legacy evidence manifest | 很值得用于历史数据及 gem5 overlay：完整 commit、blob digest、inventory、路径逃逸防御 |
| P1 | requested/actual 双重记录 | hugepage、CPU affinity、频率、温控必须记录“请求值”和“观测值” |
| P2 | `chase_migrate` 实验范式 | 借实验设计，但不能称为纯“迁移延迟” |
| P2 | `evict_slc` 随机 read+write + sequential control | 可借对照方法，不能把执行成功等价成 SLC 已完全清空 |

## 不值得照搬的部分

- ARM64 绑定的 backend 选择器会直接拒绝 x86/RISC-V：[select.py](/Users/michaelyao/gb10-cpu-arch-probe/arm64_probe/backends/select.py:14)。
- Makefile 只按宿主 OS 分支，没有 target triple/build profile：[Makefile](/Users/michaelyao/gb10-cpu-arch-probe/Makefile:16)。
- Runner 通过 scenario 字符串匹配 probe，新增实验仍会改主流程。
- 只有本地 subprocess，没有 SSH/ADB/gem5 Transport/Executor 分层。
- `chase_pmu` hugepage 失败后静默 fallback，输出仍打印请求的 `hugepage=1`，没有可靠报告实际页策略：[chase_pmu](/Users/michaelyao/gb10-cpu-arch-probe/src/chase_pmu/chase_pmu_v2.7.3.c:121)。
- 精确固定 Python `==3.13.13`有利于单仓复现，但不适合作为本仓长期跨平台兼容要求。
- 大量 phase/spec/handoff 文档并存且 README 状态滞后，不适合作为目录模板。

## 对本仓的建议顺序

1. 补一个 `1826c74` 的纠偏提交：修正方法学绝对化措辞、许可证矛盾、fixture 来源和环境事务裁定。
2. 修正 `run-record.v2`：
   - `status=ok` 才强制至少一个数值 metric；
   - failed/skipped/unsupported 允许空 metrics，并使用结构化 failure/reason；
   - repetitions/statistics 的强制条件由 ExperimentSpec 决定。
3. 把 OI-9 的蓝图输入并入 OI-8，但明确当前 ADR-0006 的正交目标模型优先于参考仓的 ARM64 backend 模型。
4. Phase C 首先实现最小纵向闭环：Plan → repeated execution → adapter → raw artifact → parser → statistics → atomic record。
5. `chase_migrate` 若落地，建议命名为“affinity switch 后同链首次访问惩罚”或“remote-warm-chain penalty”，避免误解为调度器迁移开销或纯互连 hop latency。

验证结果：参考仓 HEAD `f0b4013` 的完整 Python 套件在正常 uv 权限环境下运行了 452 项，全部通过、7 项跳过；legacy manifest 17 个文件验证通过。但上述 Runner 缺陷仍可由源码和定向复现实证确认，说明“测试全绿”不能等价于端到端测量链闭环。两个仓均未被本次评审修改。