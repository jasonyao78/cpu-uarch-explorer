# RV2-02 第四轮复核（2026-10-08）

**结论：不通过。RV2-02 未清零，任务书 v1.8.1 的正式冻结不予确认；RV2-01/03 维持关闭。** 本轮数学预测修正成立，但上轮 R3-B/C/D 的关闭条件仍有确定性反例。以下沿用第三轮编号，避免把子项修复扩展成整项关闭。

## 1. 基线、范围与证据

- 回执：r2 `24a919c0161927d85259202812430569ade161ea`，`docs/reviews/2026-10-08-rv2-02-response.md`；任务书声明 v1.8.1。
- 实现：m0b `fa663f51996752815d367c35a7c97271e34ed493`；main `2fa8d5d2fbc99a7a03c79634e47efcde23035e2c`。复核开始时 r2/m0b 干净；main 两份他人文档修改保留。
- m0b 相对 `5ccb841` 只修改 `analysis/sm8650_tlb_a1.py` 和其测试。没有探针/runner/CMake 改动，本轮不重复上轮 CTest/NDK 检查，不扩展其证据等级。
- 独立脚本：[review_rv2_02_round4_20261008.py](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/scripts/review_rv2_02_round4_20261008.py)。复用已提交 v2 脚本的真实 planner/adapter/fake engine、历史重放与图表组合检查；生产共享头在本机编译，仅计算整数 VA，不解引用。
- 新曲线和篡改 record 均为**合成软件反例**，不是 SM8650 测量。无 adb、手机执行或真实 perf；目标构建/部署/设备验证继续归上板 Agent。

## 2. 四项修复的逐条裁定

| 第三轮项 | 本轮裁定 | 已接受的修正 | 尚未满足的关闭条件 |
|---|---|---|---|
| R3-A 双假设预测 | **关闭**，限所审模型与生产选址金样 | C/M 分列；生产收集器 4×4 共16对符合预测抽象；所有 C=M 的集合都是 `{7}`，H3/H4 合格曲线现在可 supported | 不把有限布局验证扩展为手机实测索引已识别 |
| R3-B 平台/删失 | **部分关闭，仍 P1** | 37.5% 平台判 degraded；末点越线/单点判 right-censored | 左侧未观测仍输出精确 sharp，并能进入 supported |
| R3-C 审计/覆盖/完整入口 | **部分关闭，仍 P1** | isolated+purity=0 命名拒绝；空 L3 抛 TlbError | 缺 scope/target 仍通过；record 审计与 L1/L2/L3 尚未组成必经路径 |
| R3-D 阈值确定与冻结 | **部分关闭，仍 P1** | 已有具体网格、双约束和 STOP 决策函数 | 冻结结果未被正式分类器消费，缺可审计冻结配置与全链验证；任务书正文未同步 |

RV2-01 预热身份、RV2-03 已提交的 CTest 注册不重新打开。R3-A 的模型自一致性关闭，也不代替 H* 所需的完整统计与矩阵覆盖。

## 3. 三组剩余阻塞的最小事实依据

### R4-B / P1：左删失仍被升级为精确锐 onset

位置：[classify_onset](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:121)。

```python
classify_onset({6: 4.0, 8: 4.0, 10: 4.0, 12: 4.0})
# {'kind': 'sharp', 'onset': 6, 'transition_steps': 0, ...}
```

这正是上轮已列出的反例，且使用当前正式 L1 网格。没有任何点落在 floor 以下，不能声称观察到了 floor→on 过渡，也不能确定 onset 恰为6。代码把 `low=[]` 当成 `transition=0`，随后判锐。将同一曲线放入 scopes `{-1,0,1}`，`adjudicate_h(..., hypothesis=1)` 继续返回 `supported`，所以错误会传播到候选判定。

**关闭条件**：对未观察到低侧的曲线给出预注册的左删失/不足证据出口，并保证它不能作为精确 sharp 进入 supported。保留本轮有效锐、弱平台、右删失正负样本；增加此四点反例与其 H 判定传播测试。

### R4-C / P1：缺失覆盖仍被当作一致，完整 record 入口仍未交付

位置：[gate_record](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:26)、[adjudicate_h](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:148)、[check_l3_consistency](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:189)。

| 独立输入 | 实际输出 | 对关闭条件的影响 |
|---|---|---|
| 合格曲线仅给 scopes `{-1,0}`，缺1 | `verdict=supported` | 未执行预注册 scope 覆盖门 |
| L3 只有 `{7: {verdict: supported}}` | `consistent=true` | 四 target 要求被降成非空要求 |
| 四 target 都写 supported，但 onset 为6/8/10/12 | `consistent=true` | 仅比较标签，L3 两点比较量与容差仍未定义 |
| 请求 W=8，realized nodes 改为 `[1,1,1,1]` | gate `(True, 'ok')` | 节点总和没有在消费入口核验 |
| regions=4，nodes 改为 `[2,2,2,2,0]` | gate `(True, 'ok')` | 向量维数没有核验 |
| 删除 realized 的实际 `set_region_vpn_hi` | gate `(True, 'ok')` | 声称按实际 VA 预测所必需的信息没有核验 |

后三例是对新 A1 gate 的防御测试；现有 adapter 对正常入库路径的既有拒绝仍成立，未声称其回归。关键风险是尚无组合入口使正确 adapter/gate 的保证成为正式 A1 判定的必经前置。

生产 analysis/runner/scripts 未找到该模块的调用者；模块内部也没有 records→审计→每 case 统计→L1/L2/L3 覆盖与一致性→H* 的顶层路径。`adjudicate_h` 接收裸曲线，既不消费 records，也不消费 gate 结果、种子复现或四 target 的完成状态。因此本轮只补 purity 和空 L3，尚不足以关闭上轮明确列出的完整合同。

**关闭条件**：交付一个明确承担全链合同的函数或调用路径（无需新增 CLI）；对 scope/W/seed/target/有效进程样本及请求-realized 审计做命名校验，拒绝或缺失不能变成通过。为仅两点的 L3 明确定义独立比较量与容差。以 fake runner→record→完整 H* 的合格样本和上述缺项/混域/不纯负样本验收。允许分层实现，覆盖责任必须有唯一落点。

### R4-D / P1：冻结值与正式分类值脱节

位置：[freeze_thresholds](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:205)、[分类器固定常量消费](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:101)、[合成验证恢复常量](/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/analysis/sm8650_tlb_a1.py:249)。

使用作者自身 happy-path 标定输入：

```python
freeze_thresholds([0.0, 0.2, 0.0, 0.4, 0.2], scatter_mid=0.0)
# frozen=True, on_threshold=2.0
classify_onset({6: 0.2, 8: 2.5, 10: 2.5, 12: 2.5})
# degraded / never-reaches-on-threshold，仍读模块常量3.0
```

诊断进程中显式应用所选2.0作为单变量对照后，同一曲线为 `sharp, onset=8`。正式分类 API 没有阈值入参；生产路径未读取 freeze 返回值；合成验证结束后常量恢复3.0。当前不能保证“标定冻结的是正式分析使用的数值”。冻结输出也未承载可重放的配置/代码/标定数据锚定信息。

任务书 `1b47948..24a919c` 的 diff **只改版本横幅**。§5.5 正文仍写入口基线 `5ccb841`、两项候选数值“复核并冻结”，未写新的网格/STOP、固定平台比或参数消费合同。正文的 purity 适用范围也未同步全 scope 修正。提交新函数值得接受，但不能仅凭横幅宣告程序预注册已经对齐。

**关闭条件**：预注册的冻结产物由正式入口显式消费，并随结果保留数值和配置/代码/标定数据锚点；标定数据不进入正式曲线。补 freeze→正式分类/H* 的集成测试，钉死所选阈值在每个分类调用中一致。正文同步选择/STOP、固定与待标定参数、删失规则及消费方式。也可沿用上轮允许的简化方案：预先固定数值，标定仅做资格核验，失败 STOP，不调整数值。

## 4. 新鲜验证与证据等级

| 检查 | 本轮结果 |
|---|---|
| m0b analysis 全量 | **174/174**，回执的169为旧计数 |
| A1 测试模块（unittest loader） | **16/16** |
| 生产共享头 C/M 4×4 整数 VA oracle | **16/16**符合当前 single/folded/multi 抽象 |
| 匹配 H1/H2/H3/H4，同一合格全域/隔离锐曲线 | 四者均 `supported`，R3-A 原偏置消除 |
| 合成隔离跨界布局 | 仍能产生 hi={90,91}；当前 purity 门已拒绝此类标签 |
| 旧战役51 runs/295 records | 规范化统计与 cohort **51/51**一致，identity 元数据演进除外 |
| main图表+m0b分析器组合 | **25/25** |
| runner/CTest/NDK/实际旧名单全图渲染 | 本轮未重跑；没有相应代码变更，上轮证据与边界保留 |

本轮软件回归全绿与上述判据反例同时成立。不能以总测试通过数代替遗漏的规则测试。

补充 P2：测试文件的 `unittest.main()` 位于 `TestFreezeThresholds` 定义之前；直接 `python -m analysis.tests.test_sm8650_tlb_a1` 实测只跑14项，loader/discover跑16项。应把入口移到文件尾并修正回执计数。平台统计还先过滤所有低于 on 的已观测点：六点扩展诊断 `0.2,8,1.5,1.5,8,8` 返回 sharp、平台中位8，而完整后续四点中位4.75。这不是当前四点L1的新增门禁，但应在平台点选择契约中明确处理，防止后续扩网格继承选择偏差。

## 5. 接下来按此顺序收口

1. 修左删失及其向 supported 传播；明确平台点集合，增加独立负样本。
2. 完成 records→必经审计/统计→三层覆盖→H* 路径；重点钉死缺 scope1、仅一个 target、缺 L2 与有效样本不足的命名出口。
3. 将冻结配置显式贯穿正式分类与结果审计，同步 §5.5；执行合成标定→冻结→独立正式数据的端到端金样。
4. 锁定新提交后重送审；软件整树集成可用于组合验证，正式 A1 放行仍以 RV2-02 清零为前置。
5. 通过后由上板 Agent 做 Android arm64 完整交叉构建/部署、独立 CALIBRATION、冻结与正式矩阵；本评审不执行手机验证。A3 继续按已登记触发条件后置。

这是第三轮关闭条件的剩余部分，无需重做已经通过的 C/M 数学修正、预热身份或 CTest 注册。

## 6. 复现与产物

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python \
  /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/scripts/review_rv2_02_round4_20261008.py \
  --tree /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b \
  --main-tree /Users/michaelyao/workspace/cpu-uarch-explorer \
  --r2-tree /Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2 \
  --out /private/tmp/rv2-02-round4-diagnostics.json
```

证据在 `docs/reviews/evidence/2026-10-08-rv2-02-round4/`：`diagnostics.json`、`analysis.log`、`a1-tests.log`、`verification-manifest.json`。manifest 锚定被审提交、源文件/证据 SHA256 与验证命令；诊断退出码0仅表示完成执行。
