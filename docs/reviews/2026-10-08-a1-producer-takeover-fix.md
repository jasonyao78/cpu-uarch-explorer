# A1 生产链接手修复与验收（2026-10-08）

**结论：本轮 R7-A 生产归层及 R9 无效正例问题通过，可以关闭；RV2-02 整体与 Phase A 正式冻结仍不通过。** 后者保留的是已登记的最终审计/完整条件身份和冻结产物合同，没有追加新的科学判据，也不要求本次执行手机标定。

## 1. 目的、授权与提交

用户要求在本轮仍不通过时直接接手修复，避免继续只转交意见。本次在 m0b 实际修改代码并验证，不代提交原作者未提交文件。

- 修复前：`codex/sm8650-tlb-r2-m0b` @ `b0f287f12829819f1e6f5acbf3c9fdd53ff36c71`。
- 修复后：同分支 **`0a27eba1a185618855a4081cd27dc21245e97e35`**，`fix(runner): persist experiment identity and verify A1 producer chain`。
- 对照：[第九轮复核](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/reviews/2026-10-08-r9-review.md)。旧报告保留为对应旧快照的历史，不回写旧结论。
- 仅本地提交；未推送、合并、回收 worktree 或删除分支。m0b 并行产生的设备 run 目录保持原样，未纳入提交。

打包期间另一 Agent 独立提交 `6f433e3`（raw 文件名及写入失败处理），位于本次修复之后。本次没有代写或代提交它；在该 HEAD 上补跑 analysis **191/191**、runner **197/197** 及同一生产链诊断，均通过。本次自身修复与验收基线仍为 `0a27eba`，不把并行提交记为本次产出。

## 2. 已落地修复与关闭对账

| 关闭条件 | 实现与证据 | 裁定 |
|---|---|---|
| 实际 producer 持久化层来源 | [runner/engine.py](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/runner/engine.py:215) 在每条记录写盘前赋值 `record.experiment_id = plan.experiment_id`，与 manifest 同源，覆盖全部 status；[schema 登记](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/runner/schema/README.md:36) 为可选扩展，旧记录不回填 | **关闭 R7-A** |
| 成功集合不能为空 | [runner 回归](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/runner/tests/test_engine_experiment_identity.py) 先断言 32 ok / 0 failed，再逐条核 ID、请求参数、节点总和与 10 次 observations；畸形/缺 cycles 输出分别必须产生 32 failed，失败记录同样核 ID | **关闭 R9 证据缺口** |
| 全量真实软件生产链正例 | [A1 生产链测试](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/tests/test_sm8650_tlb_a1.py:249) 实际展开三配置，经 `run_plan → _run_case → adapter → writer → load_run → run_a1_adjudication`；不手拼 record、不手写 JSONL、不在读回后补 ID | **通过本轮关闭条件** |
| 输入置换与准确覆盖 | 完整 128 条结果对象及排序紧凑 JSON 均置换相等；在执行前将请求 target 200→201、W 8/12→100/200，真实 producer 均产出合法记录，消费者分别命名拒绝 | 既有 L3 关闭维持 |

同步修正 [A1 入口 docstring](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:284) 的旧 sharp/onset 描述，使其与已接受的 L3 两点规则一致；把 `unittest.main()` 移至测试文件末尾，直接模块执行也覆盖全部 A1 测试。未改变分类器数学、阈值选择程序或生产 C++ 探针。

## 3. 验证事实与证据等级

先更新测试、保持旧 engine 不变：两个目标测试均因 `experiment_id` 缺失失败（[RED 日志](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/reviews/evidence/2026-10-08-a1-producer-takeover/red.log)）。补入生产接线后通过，避免把“新测试本来就能绿”误当回归保护。

| 检查 | 本轮实测 |
|---|---:|
| analysis 全量 | **191/191** |
| runner 全量 | **195/195** |
| A1 直接模块执行 | **33/33** |
| 并行 6f433e3 兼容回归 | **analysis 191/191、runner 197/197** |
| L1/L2/L3 成功记录 | **48 / 48 / 32** |
| record 含正确 ID | **128/128** |
| 三配置合成 probe 调用 | **1280** |
| 每 case 的有效进程 observations | **10** |
| 完整判定与 canonical JSON 置换一致 | **是 / 是** |

[传输夹具](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/runner/tests/tlb_set_fixtures.py) 仅替换外部执行/系统信息、二进制登记与 Git 来源。stdout 按每个真实 case 的完整请求生成 descriptor、区域配额和全部 PMU 事件，20 轮请求报告排除冷轮后的 19 个有效轮。planner、adapter、统计、序列化、写盘和读盘保持真实；不依赖本机已有 NDK 二进制。

**1280 是合成传输调用，不是手机进程或 PMU 测量；合成 H*=1 仅检验软件消费链。** 二进制登记被 mock，不能称部署验证。未执行 adb、手机探针、perf、NDK 构建、CTest、旧战役重放或 main 整树集成。生产差分不涉及 C++，本轮针对改变的 Python 链完成全量回归。

复现（工作目录为 m0b；运行中的 `.venv` 路径按本机现有环境）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m unittest discover -s runner/tests -t .
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m unittest discover -s analysis/tests -t .
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/scripts/verify_r7a_takeover_20261008.py --tree /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b --out /tmp/a1-producer-check.json
```

完整证据：[diagnostics.json](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/reviews/evidence/2026-10-08-a1-producer-takeover/diagnostics.json)、[命令/退出码/源码及证据 SHA256](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/reviews/evidence/2026-10-08-a1-producer-takeover/verification-manifest.json)。脚本退出 0 的范围仅为本轮软件检查，不表示整个 Phase A 已获准正式采样。

## 4. 整体出口仍未通过的已登记条件

本次没有用“两项已修”覆盖历史 P1；以下沿 [open-items](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/open-items.md) 原归属与触发条件，均须在正式矩阵前收口：

1. **R3-C/R5-C 最终消费合同**：完整 W/层角色/条件身份、有效 observations、请求与 realized 的维数/总和/类型/实际高字段，以及重复记录处理。当前 [gate_record](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:26) 与 [组合入口](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:284) 的剩余守卫没有因本次 ID 修复而补齐。**这是软件工作，不转移给上板 Agent。**
2. **R5-D 冻结产物合同**：配置/代码/专用标定数据锚定、与正式数据隔离及核验；[任务书 §5.5](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md:174) 中重复入口段和旧 3.0 候选数值措辞须对齐实际网格/STOP/消费规则。程序与审计产物的准备属软件工作，实际数值冻结待上板 Agent 的独立标定。
3. **整树集成验收**：上述软件条件闭合后，再按 m0b→r2→main 路径核对图表/其他开发线并运行集成回归。本次未执行 merge，不能凭 m0b 单树全绿宣布集成出口完成。

既有 RV2-01/03、R3-A、R4-B、R5-T、R6-C、L3 子项的关闭保留。A3 和其他已登记后置项维持原触发条件，不混入本次修复。

## 5. 专业判断与推进建议

接手修复是合适的：R7-A 只有一处缺失的生产赋值，反复未落入指定分支；原测试又把失败产物当成功证据，属于确定性的软件集成与验收缺陷，无需等待新的架构结论或手机数据。本次用 RED→GREEN 及真实保存/加载链给出了可复核的关闭证据。

后续应固定一个软件实现负责人，沿现有关闭条件先完成最终消费守卫与冻结审计产物，再一次核验完整软件出口；独立复核按相同快照和证据对账，避免继续只修一个函数就转交下一轮。软件验收/集成后，Android arm64 完整交叉构建、adb 部署、独立标定和正式矩阵继续由上板 Agent 承担。m0b 的开发终点按软件使命验收和 r2 集成决定，不等待 H* 科学结论。
