# SM8650 A1 软件合同收口执行计划（2026-10-08）

> 已批准范围：用户“按你的建议继续”；本会话单代理连续执行，设备工作由上板 Agent 承担，不再请求逐批许可。
> 起点：m0b `6f433e3`、r2 `14110db`；约束与反例见 [当前对账](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/reviews/2026-10-08-a1-producer-takeover-fix.md)。

## 设计与边界

- 正式配置 → planner 是完整条件身份与覆盖的权威；按实验 ID、完整 params、control 绑定 case，不以字段存在性或 seed 排序猜层。同身份第二条 record 一律命名拒绝，不隐式合并。
- 每 case 校验全部 10 个 observations、per-round 资格、统计中位和每个实际 realized。每个 process 的 VA 高字段独立保留、独立计算 C×M 预测；有效地址重分配可变化，真实混域/purity/维数/配额违例仍拒绝。
- 两个专用 CALIBRATION 配置：空窗 W0 与 scatter W8，均 r20、10 repetitions；旧 pilot 不自动改名或回填。沿已注册网格/STOP 程序选 on，固定 floor=1、平台比=0.8。
- 冻结产物锚定配置/代码/标定 JSONL、manifest 与 artifacts 文件，以及实际 probe binary SHA、target/regime、run_id/raw 引用；正式入口核验锚点、重算确定性决策并排除标定记录混入。只传 `{frozen: true, on_threshold: ...}` 不再足以放行。
- 本轮没有手机测量、不调整 H 候选数学或正式 128-case 网格、不扩展 A3/ROB/ALU/FPU。

## 执行步骤与提交边界

### 1. 消费守卫：RED → GREEN → 提交

涉及 [A1 入口](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py)、新合同模块 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1_contract.py`、[adapter](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/runner/adapters/ptr_chase.py)、[engine](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/runner/engine.py)、[schema 登记](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/runner/schema/README.md)。

先加入真实配置→run_plan→load_run 的测试，观察以下断言在旧代码上失败：

```python
with self.assertRaisesRegex(TlbError, 'duplicate'):
    run_a1_adjudication(records + [records[0]], frozen)
with self.assertRaisesRegex(TlbError, 'coverage'):
    run_a1_adjudication(records_without_one_W10, frozen)
self.assertTrue(varying_valid_va_record['probe']['realized']['domain_consistent'])
```

补充完整条件变化、伪造中位、缺事件/观测、错误类型/维数/总和/高字段、末个样本跨界与混域负例；再实现身份与最终防线。正例必须仍为完整 128 条，结果与排序 JSON 置换不变。显式 high→low 的 L3 形态保持拒绝；平台统计不得过滤低于 on 的观测造成选择偏差。

### 2. 冻结产物：RED → GREEN → 提交

新配置在 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/configs/experiments/`：`ptr-chase-sm8650-x4-tlb-a1-calibration-floor.json`、`ptr-chase-sm8650-x4-tlb-a1-calibration-scatter.json`。专用冻结/命令入口在 `analysis/sm8650_tlb_a1_freeze.py` 与 `analysis/sm8650_tlb_a1_cli.py`。

接口：

```python
frozen = freeze_a1_from_runs(floor_run, scatter_run)
result = run_a1_adjudication(formal_records, frozen)
```

先测试：专用真实 producer 标定文件可冻结；STOP 可审计且拒绝正式入口；裸字典、标定数据污染、修改配置/代码/输入、不同二进制、篡改阈值并重算摘要、缺失文件均拒绝。实现后让正式 E2E 正例必经同一冻结产物，不保留绕过参数。CLI 写出冻结 JSON 后不得用不同结果覆盖旧冻结文件。

### 3. 文档与验收

修订 r2 [任务书 §5.5](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md)：删除旧入口重复段和未约束的“候选数值复核”措辞，登记角色、实际删失/平台/L3规则、冻结入口与所有新组件的路径。open-items 按原 R3-C/R5-C/R5-D 对账关闭；本机合成证据不作设备数值冻结。

软件检查（在相应工作树执行；现有 Python 在 main 的 `.venv`）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m unittest discover -s runner/tests -t .
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m unittest discover -s analysis/tests -t .
cmake --preset macos-arm64-release
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release
```

保存实际命令、退出码、测试计数与源码/证据 SHA256，确认全部必经门能被负例击中。每批只暂存本会话自己的修改；不包含并行 run 目录或 main 的脏文件。

### 4. m0b → r2 集成与 main 兼容

源代码与文档各自提交后，在干净 r2 合入 m0b；核对 main 已提交图表线/AGENTS 变化并整合，保留 main 未提交内容。冲突按最终软件合同和两端既有功能解决，集成树重跑 Python、CTest、真实 producer/冻结/判定 CLI；旧数据与图表按受影响路径检查。远程暂不处理。

交付明确区分：软件合同/集成通过；设备数值冻结与正式矩阵待上板 Agent。m0b 开发使命可结束；仍有其他 Agent 使用或设备数据未处置时保留 worktree，分支不删除。
