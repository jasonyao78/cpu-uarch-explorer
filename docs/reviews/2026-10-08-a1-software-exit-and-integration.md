# A1 软件出口与 r2 集成验收（2026-10-08）

## 本次任务的目的（给人类看）

一次完成真实 producer 的成功/缺失/冲突/重复/乱序验收、最终消费守卫和冻结工件，并将 m0b 合入 r2、同步 main 已提交图表线。向用户交付明确裁定和可直接执行的上板交接；不再把软件接缝余项交回原行动方。

**裁定：本轮软件出口与 r2 集成验收通过；RV2-02 剩余软件 P1 可关闭，任务书 v1.9 的程序/合同冻结通过。现在可由上板 Agent 开始交叉编译、部署与设备验证。目标板事件/几何资格和实际数值冻结尚未由本轮完成，正式矩阵仍须先过独立标定门。**

这是当前 Agent 的实现、反例复核和集成自验结论；本轮未另行邀请第二位独立评审，不声称新增一次双独立评审通过，也不声称整个 r2 战役或完整设备出口完成。历史不通过结论继续对应各自快照。

## 1. 可复核基线

| 项 | 已提交快照/动作 |
|---|---|
| 最终消费守卫 | m0b `113ab3d` |
| 锚定冻结工件与专用标定 | m0b `a98c598` |
| m0b→r2 | `95987b9`，保留父历史的 merge；a98c598 为祖先 |
| main 已提交线→r2 | `3c95aeb`，同步 main `6062e20`（含图表 `2fa8d5d`）；6062e20 为祖先 |
| 本轮完整验证基线 | **r2 `0e20534`**，任务书 v1.9 + 交接 + 集成回归；验证时 tracked 树干净 |

当前证据归档提交位于验证基线之后，只加入本报告、台账/索引及证据，不改变已验证代码。未把 r2 反向合入 main；未推送远程。main 的他人未提交文档/runner 草稿未吸收、未修改、未代提交。m0b 的并行设备 run 目录保留，不改名不补写不提交。

## 2. 关闭条件与事实

| 合同/风险 | 实际处置与证据 | 裁定 |
|---|---|---|
| R3-C/R5-C 条件身份、完整覆盖 | 最终入口从三份真实配置展开128个完整 case；精确 experiment_id/params/control/target/protocol；缺H/scope/W/seed/target、额外残差/类型漂移、重复case/ID/raw引用命名拒绝 | 关闭 |
| 有效统计与单位 | 每case10进程、索引0..9、全部有限、单位/引用对齐、中位重算、轮数守恒与事件有效轮逐样本核验；缺obs/事件/坏统计负例被拒 | 关闭 |
| requested→realized / 实际VA | descriptor精确类型/值、向量维数/节点总和/active/scope/purity/实际高字段全部检查；允许合法VA重分配，逐case逐进程保留 C×M预测。末进程才违规也拒绝，首样本不能掩盖 | 关闭 |
| R5-D 阈值与谱系 | 专用floor/scatter真实producer文件→freeze工件→正式入口；配置/代码/标定文件SHA、binary/source/regime、记录/raw隔离必经核验；独立重算决策。裸frozen、篡改后重算SHA、漂移、STOP均拒绝；实际冻结2/3影响分类 | 关闭软件合同；设备数值待标定 |
| 旧平台选择偏差 / L3 falling | 平台采用全部后续点；不筛掉低于on值；falling独立拒绝标签；删失/弱平台/覆盖既有关闭维持 | P2本范围已修 |
| OI-13 图表集成余量 | 同步 main nullable/身份/披露修复；局部缺事件经loader→analyzer→CLI成功且点名，onset整段缺失披露历史结论不受本数据支持；空系列仍受控拒绝 | 图表余量关闭 |
| 旧数据与图表漂移 | 51runs/295records，去除新增identity元数据后统计51/51相等；cohort不规范化直接51/51相等；真实四SVG+report与main已提交输出5/5字节相等 | 集成通过 |

OI-13 的一般 extras 派生/消费语义 PA-06 不借本次图表通过扩大关闭：首次正式新事件组使用前完成或独立登记，沿原触发条件。A1 专用入口对自身四事件逐项验证，不依赖旧容量分析器猜测 extras 含义。A3、ROB与其余已登记后置项保持原归属和触发，不作为本次软件出口新增条件。

## 3. 最终验证结果

在 r2 `0e20534` 执行，逐命令真实退出码均0：

| 检查 | 结果 |
|---|---:|
| analysis 全量（含main图表与新增两项集成回归、末进程负例） | **249/249** |
| runner 全量 | **198/198** |
| macOS preset CTest | **20/20** |
| 实际三配置→plan→run_plan→adapter/统计→写盘→load_run→冻结核验→A1 | **48/48/32 条成功记录；1280 个合成进程观测** |
| 专用两标定配置经同一producer | **2条记录 / 20个合成进程观测** |
| 完整case_audit与canonical JSON置换 | **1280个进程审计 / 相等** |
| 缺失、条件冲突、重复 | **命名TlbError** |
| 旧战役重放 | **51runs / 295records / 统计与cohort均51/51相等** |
| 真实四图+报告生成 | **5/5与main已提交文件字节相等** |
| 历史R7接手脚本适配当前冻结合同 | **退出0** |

外部执行、系统/环境状态采集、二进制登记和Git来源为合成传输；planner、engine、环境policy判定、adapter、统计、写盘、loader、freeze/adjudication保持真实。**这些不是1280次手机调用，不构成目标板PMU/地址映射实测，也没有部署验证。** 本轮未执行Android/NDK编译、adb、手机探针或perf。

r2首次runner测试曾调用旧build中的ptr_chase而失败；标准preset重建后通过，最终验证用重建产物。macOS不能执行Linux专属VMA/PerfWindow路径，证据等级不提升。

证据目录：`docs/reviews/evidence/2026-10-08-a1-software-exit/`。`verification-manifest.json`给出源码/测试/配置/文档与证据SHA；`commands.json`给出命令/工作目录/实际退出码；`diagnostics.json`保留完整旧run名单与摘要、生产成功数及负例拒绝、图表摘要。RED日志保留旧实现确实放行裸frozen和旧合同缺口的反证；RED的失败是预期诊断，不计入最终通过数。

复现（r2根目录，Python用已有环境）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m unittest discover -s analysis/tests -t .
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m unittest discover -s runner/tests -t .
cmake --preset macos-arm64-release
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python scripts/verify_a1_software_exit_20261008.py --tree . --out /tmp/a1-software-exit.json
```

## 4. 接下来由谁做、何时开始

软件工作已由当前 Agent 收口，无需再派回原行动方逐点修复。上板 Agent **现在可从r2开始**：NDK完整Android arm64构建→核对实际部署SHA/设备身份/权限/环境→新几何和Linux窗口首验→专用floor/scatter独立标定→`freeze`→正式L1/L2/L3→`adjudicate`。STOP或输入错误应停块调查；不能直接从软件合成H*=1跳到正式结论。

可执行交接：[2026-10-08-sm8650-a1-integrated-handoff.md](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/runbooks/2026-10-08-sm8650-a1-integrated-handoff.md)。规则与部件索引：[任务书v1.9 §5.5](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md:154)。

m0b开发使命已结束；仍有并行会话/数据依赖，因此分支和worktree保留。worktree回收与分支删除继续分步，删除须main集成+完整测试+推送；r2战役任务继续，H*未唯一化不妨碍以后按预注册科学终态收口。
