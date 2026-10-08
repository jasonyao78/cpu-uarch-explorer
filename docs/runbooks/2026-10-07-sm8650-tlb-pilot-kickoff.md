# SM8650 TLB 上板执行包 v2（标定先行 + 正式矩阵）

> 日期：2026-10-08（v2 取代 2026-10-07 pilot 版；pilot 已成功，本版面向 Phase A）。
> 你的角色：**执行 + 现象记录**。判读、阈值冻结、H* 判定一律不在你的范围——异常即停、回传，不要扩参、不要改代码、不要自行重试变体。

## 0. 本次任务的目的（给人类看）

**第一段（标定先行，评审清零后立即可跑）**：在 SM8650 X4 真机上复测 G0-3 标定块（空窗底噪 + 无冲突同窗），产出**阈值冻结程序的输入数据**——这是 Phase A 正式矩阵的前置：`freeze_thresholds` 决策表需要 10 进程空窗底噪样本 + 无冲突 scatter 中位，这些数据只能来自设备。

**第二段（等评审清零授权后追加）**：执行 Phase A A1 三层正式矩阵（128 cases / 1280 进程），产出 **H1–H4 哈希假设裁决的原始数据**——这是"X4 L2 TLB set/way 结构"终点的直接输入。

一句话：第一段给判据"定标尺"，第二段给科学问题"采证据"。

## 1. 代码基线与构建

**两个 worktree 都要同步（各管一件事，缺一不可）**：

| worktree                                      | 分支                              | 同步到                | 作用                                                                                                                     |
| --------------------------------------------- | --------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `~/workspace/cpu-uarch-explorer-tlb-r2-m0b` | `codex/sm8650-tlb-r2-m0b`       | **`b0f287f`** | **执行在这里**——R9 修复（runner 逐 record 写 `experiment_id`，判据归层依赖该字段）。旧代码产出的数据入口直接拒 |
| `~/workspace/cpu-uarch-explorer-tlb-r2`     | `codex/sm8650-tlb-hierarchy-r2` | **`dbd8ca1`** | 本 kickoff 文档住这里——同步后读到的才是当前基线说明                                                                    |

```bash
cd ~/workspace/cpu-uarch-explorer-tlb-r2-m0b && git pull --ff-only   # 代码 → 6f433e3（R10 raw 文件名修复，noconflict 必需）
cd ~/workspace/cpu-uarch-explorer-tlb-r2 && git pull --ff-only       # 文档 → dbd8ca1
```

- **record 级 `experiment_id`**：从该提交起 runner 逐 record 写入——判据入口归层依赖它，**回传前必须抽查一条 record 含此字段**。
- **二进制必须与 `b0f287f` 源码同代**（R9 教训：descriptor 契约在 `4655dd3`/`c8b3cec`/`d0ff946` 三度扩展探针输出，旧二进制缺字段会被 fail-closed 拒绝）。**哈希以现行源码重编实测为准**（2026-10-08 实测前缀 `36aa9228`；`1e03a658` 是 10-07 旧源码产物，已过时）——不要核对历史哈希，直接 §3 recipe 重编并记录新哈希入备忘录。
- venv 用主树：`.venv/bin/python`。

## 2. 环境确认（跑数据前必过，任一不过即停并回传）

按 [上板前清单](2026-10-01-sm8650-tlb-r2-preboard.md) §1 执行 1.1–1.9 快扫，**逐项重新读值**（设备状态会漂移）。**充电态**：USB 充电为必须行为，preflight 报 `cpufreq-max-mismatch:policy0/2/5` 是登记的显式非基线条件（预期内）；`policy7` 被压才是真阻断。

## 3. 执行序列

```bash
PY=/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python
PLAT=configs/platforms/redmi-k70pro-01.json
ENV="--environment-profile charging-thermal --allow-mutation"
cd ~/workspace/cpu-uarch-explorer-tlb-r2-m0b

# === 第一段：标定块（评审对"标定先行"无异议即可跑）===
# 0) 块前锚点（2 cases）
$PY -m runner.cli run --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-anchor.json --platform $PLAT $ENV
# 1) G0-3 空窗（1 case）→ freeze_thresholds 的 floor 输入
$PY -m runner.cli run --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-pilot-g03-empty.json --platform $PLAT $ENV
# 2) G0-3 无冲突同窗 + 重复尺度（4 cases）→ scatter 中位输入
$PY -m runner.cli run --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-pilot-g03-noconflict.json --platform $PLAT $ENV
# 3) 块后锚点
$PY -m runner.cli run --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-anchor.json --platform $PLAT $ENV

# === 第二段：A1 正式三层（须评审清零授权后追加）===
# L1 主判定 48 cases / L2 复现 48 / L3 target 一致性 32
for cfg in a1-l1-main a1-l2-repro a1-l3-target; do
  $PY -m runner.cli run --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-$cfg.json --platform $PLAT $ENV
done
```

case 数核对：标定段 2+1+4+2 = **9 cases / 90 进程**；正式段三层各 48/48/32 = **128 cases / 1280 进程**。不符即停。`--allow-mutation` 只是 run 的授权门，`plan` 预览不要带它。

## 4. 快速核验门槛（不是判读）

- 每条 record `status=ok`；抽查 ≥1 条 record **含 `experiment_id` 字段**；
- `window_mux_rounds` 应小（≥3 醒目标注备忘录）；`accepted_nonbaseline` 仅 policy0/2/5 类（出现 policy7 → 停）；
- 混域：record 的 `probe.realized.domain_consistent` 为 false 或逐样本列表 → 照常跑完并醒目标注（这是命名状态，数据不丢）；
- `single-region-fallback` / `vpn-hi-impure` 出现 → 照常跑完 + 备忘录标注。

## 5. 回传物

1. 全部 run 目录原样（records.jsonl / raw / manifest 全量，勿裁剪）；
2. 一页备忘录：环境 9 项实际读值、二进制 sha256、case 数/ok 数、mux/降级/混域/fallback 出现清单、experiment_id 抽查结果；
3. `git status`（证明未改仓内文件）。

## 6. 红线

- 不 `git commit` / 不推送；不动他人会话文件；
- 不改任何配置/代码/参数；判读问题回传，分析侧处置；
- 设备侧 `/data/local/tmp` 探针可留；冒烟/备忘录留工作区。
