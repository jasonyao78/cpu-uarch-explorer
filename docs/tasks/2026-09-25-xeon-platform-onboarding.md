# 任务说明书：Xeon（linux-x86_64）平台接入 runner 并首跑 ptr_chase sweep

> 类型：agent 可执行任务书（自包含，无需对话上下文）
> 创建：2026-09-25｜状态：待执行
> 预估规模：2~4 个 commit；新增/修改约 6~10 个文件
> 必读先行：`AGENTS.md`（硬约定）、`docs/design/measurement-framework-design.md`（框架设计）、`docs/requirements/v0.3.md` §2.2（Xeon 平台画像）

## 1. 背景（为什么做这个任务）

本仓是跨 ISA/OS 的 CPU 微架构测量框架。当前 M4 Pro（macos-arm64）最小骨架已闭环：probe → 统一 JSON 数据 → 自动报告（runner + analysis 两个 Python 包，stdlib 零依赖）。但框架的核心宣称是**跨平台**——目前只有 local 执行器和一个 macOS 平台配置，`transport`/`executor` 字段在 schema 里预留了却从未被真正使用。

本任务把第二个平台（Xeon 8481C 服务器，linux-x86_64）接入 runner 并产出首份实机数据。这同时验证两个未验假设：① Plan/Run/controls 抽象能否零特判地容纳第二个平台；② SSH transport 通道是否成立。

## 2. 目标（验收标准）

全部满足才算完成：

1. `configs/platforms/xeon-8481c-01.json` 平台配置入库，target 五要素齐全（ADR-0006：os/isa/execution_kind/executor/target_id），controls 用 taskset 绑核；
2. runner 支持按平台配置的 `transport` 字段选择执行器（local / ssh），**主流程不出现任何 x86 或主机名特判**；
3. `CMakePresets.json` 新增 `linux-x86_64-release` preset，探针在服务器原生构建；
4. 在 Xeon 上完成 ptr-chase-cache-sweep：14 档 buffer × 5 重复 × ≥1 个控制组，run 目录入库（records.jsonl / artifacts.jsonl / run-manifest.json / report.md / latency.svg，raw/ 按策略不入库）；
5. 全部 records 通过 `runner/schema/run-record.v2.schema.json` 校验；
6. 报告数据呈现合理的 x86 层次结构（参考预期：L1d 48KB / L2 2MB / LLC ≈105MB 共享，台阶应在相应档位附近；**不符预期不得强行解释，如实记录并标注置信度**）；
7. 本机（macOS）全部测试保持绿色：CTest 5 项 + runner 22 项 + analysis 7 项；新增代码带测试（SSH 执行器用 fake/mock，不依赖真机）；
8. 文档同步：CHANGELOG、设计文档 §11/§12（local-only 限制条目更新）、OI-3 标注接入完成。

## 3. 非目标（明确不做）

- gem5 相关的一切（OI-1 剩余项是另一条线）；
- Android 平台、新探针（core/branch/TLB 是后续任务）；
- perf/PMU 采集（本期纯计时法；`perf_event_paranoid=4` 意味着 perf 需 sudo，不碰）；
- 跨 run 汇总对比、报告层功能增强；
- x86 服务器上的 gem5 重建（已验证状态，勿动）。

## 4. 环境事实（已核实，可直接依赖）

- 服务器：Xeon 8481C（Sapphire Rapids），56C/112T 单路单 NUMA，Ubuntu 24.04，内核 7.0.0-30；**SMT sibling 对为 `CPU i` ↔ `CPU i+56`**（如 0↔56）。
- SSH：本机（M4 Pro）到服务器免密已通；**主机映射见 `data/private/hosts.md`**（真实 IP 不入库，仓库内引用一律用该文件）。服务器上仓库位于 `~/cpu-uarch-explorer`。
- 服务器工具链：cmake 3.28（支持 presets v3）、gcc 13、系统 Python 3.12。探针是纯 POSIX C++17，无外部依赖。
- v0.3 §2.2 的 SMT 纪律：单线程 probe 运行时，同物理核的 sibling 必须空闲——CPU 0 跑 probe 时 CPU 56 不得有负载（本期不要求主动隔离 sibling，但**控制组设计必须避开 sibling 对同时占用**，并在记录中如实写明控制口径）。
- 本机 runner 现状：`runner/engine.py` 目前硬编码 `LocalExecutor`；`executor/local.py` 的 `ExecutionResult` 与接口形态可直接复用。

## 5. 约束与坑（全是踩过的坑，别再踩）

1. **rsync 必须带 `--delete`**（配 `--exclude 'build/' --exclude '.DS_Store'`）——不带删除会导致本机已删文件在服务器残留（因此出过幽灵构建错误）。
2. **单位解析不许静默降级**：`runner/resolve.py` 只认 KiB/MiB/GiB/KB/MB/GB/B（1024 进制），未知单位硬报错是对的，不要"宽容"。
3. **失败记录不编造数字**：status≠ok 时空 metrics + 结构化 failure（schema v2 强制，jsonschema 会拦）。
4. **注释纪律**（`docs/methodology/comment-discipline.md`）：模块锚点 + 契约 docstring + 决策留出处。
5. **服务器 gem5 目录不要碰**：`third_party/gem5/build/` 是已验证的构建产物；你的构建只在 `build/linux-x86_64/release/`。
6. **服务器仓库的 git 状态**：rsync 会带上本机 .git；在服务器侧不要 commit（提交统一在本机做，服务器只是执行环境）。
7. 长时间远程操作用 `nohup ... &` + 轮询（SSH 会话有超时）；探针 sweep 预计 1~3 分钟，无需后台。
8. macOS 的 `qos` 控制在 Linux 上没有对应物——**不要试图映射**，Linux 控制组用 `taskset -c <cpu>`，mechanism 写 `taskset`（run-record v2 的 `environment.control.mechanism` 枚举含 taskset）。

## 6. 建议实施步骤（可按实际情况调整顺序）

1. **通读**：`AGENTS.md`、设计文档 §4（平台层）§5（Runner 层）、`runner/engine.py` / `executor/local.py` / `configs/platforms/macbook-m4pro-01.json`。
2. **执行器抽象**：在 `runner/executor/` 新增 `ssh.py`（SshExecutor：与 LocalExecutor 相同的 `execute(argv, command_prefix)` 签名，内部 `ssh -o BatchMode=yes <host> '<cmd>'`，注意 argv 的 shell 引用与 stdout/stderr/returncode 语义对齐）；`engine.py` 改为按 `platform["target"]["transport"]` 选择执行器（"local"→LocalExecutor，"ssh"→SshExecutor），选择逻辑集中在一处。
3. **平台配置**：`configs/platforms/xeon-8481c-01.json`——参考 macbook 配置；`probes.ptr_chase` 指向服务器侧路径（如 `build/linux-x86_64/release/probes/cache-mem/ptr_chase`，相对服务器仓库根）；controls 至少一组 `{"id":"core0","control":{"mechanism":"taskset","value":"0"},"command_prefix":["taskset","-c","0"]}`；platform 需要携带 ssh host 字段（放 `target` 对象的扩展字段，schema 是 additionalProperties=true——**登记到 runner/schema/README.md**）。
4. **构建 preset**：`CMakePresets.json` 加 `linux-x86_64-release`（binaryDir `build/linux-x86_64/release`，仅设 Release）。
5. **服务器构建**：rsync（带 --delete）→ 服务器上 `cmake --preset linux-x86_64-release && cmake --build --preset linux-x86_64-release`。
6. **plan 预览**：本机跑 `runner.cli plan --platform xeon-8481c-01.json ...`，确认 case 展开正确（控制组、参数溯源）。
7. **实跑 + 报告**：`runner.cli run` → `analysis.cli report`；jsonschema 校验全部 records（命令见设计文档 §9）。
8. **测试**：SSH 执行器的单测用 fake（subprocess 拦截或假 transport），不依赖真机；plan 对 ssh 平台的展开测试。
9. **文档与提交**：CHANGELOG、设计文档 §11/§12、OI-3、（如有新约定）AGENTS.md；本机提交，粒度按功能切分（执行器 / 配置+preset / 数据 / 文档）。

## 7. 交付物清单

- `runner/executor/ssh.py` + engine 的 transport 选择 + 测试；
- `configs/platforms/xeon-8481c-01.json`；`CMakePresets.json` 新 preset；
- `data/public/runs/<时间戳>-ptr-chase-cache-sweep/`（Xeon 首份数据，含报告，无 raw/）；
- 文档更新（见 §2.8）；git log 干净、commit 信息符合 `type(scope): summary` 格式。

## 8. 升级路径（遇到这些情况停下来问）

- 需要改 run-record schema 结构（不是加扩展字段）才能完成接入；
- 服务器环境与 §4 描述不符（cmake 版本、编译失败等）；
- sweep 数据形态与 §2.6 预期严重不符且原因不明；
- 发现需要 sudo 才能完成本期目标。
