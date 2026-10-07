# SM8650 TLB M0-5 pilot 上板执行包（给上板 agent 的一页 kickoff）

> 日期：2026-10-07。执行对象：Redmi K70 Pro（SM8650，dc4ad7d1，已 root/KernelSU）。
> 你的角色：**执行 + 现象记录**。判读、校准冻结、锚点池判定一律不在你的范围——异常即停、回传，不要扩参、不要改代码、不要自行重试变体。

## 1. 代码基线与目录

- 分支 `codex/sm8650-tlb-r2-m0b` @ **`31c333a`**（含充电态协议；worktree `~/workspace/cpu-uarch-explorer-tlb-r2-m0b` 若已存在，先 `git pull --ff-only` 到该提交；若新开，clone 后 checkout）。
- venv 用主树：`.venv/bin/python`（在 m0b worktree 内跑 runner 时用 `/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python`）。

## 2. 环境确认（跑数据前必过，任一不过即停并回传）

按 [上板前清单](../runbooks/2026-10-01-sm8650-tlb-r2-preboard.md) §1 执行 1.1–1.9 快扫。已知基线（2026-10-01 实测，需复验而非照抄）：CPU7=0xd82(X4)、4096 页、paranoid=-1、THP=`[always]`（S4 已证 MADV_NOHUGEPAGE 守得住）、quiet-state 门禁合规、governor=walt idle 恒 672MHz。设备状态跨 6 天可能漂移，**逐项重新读值**。

**充电态（2026-10-07 增补）**：USB 充电是**必须行为**，不等待拔充电器。若 preflight 报 `cpufreq-max-mismatch:policy0/2/5`（热策略压制小核/中核簇 scaling_max，充电态 PMIC 温度驱动），这已是登记的**显式非基线条件**——按第 4 节用 `charging-thermal` profile 执行，告警会随 record 入档；若报 `policy7` 被压，**才是真阻断，停并回传**。不写 sysfs、不改平台期望的纪律不变。

## 3. 构建（recipe 已验证，2026-10-07，产物 sha256 前缀 `1e03a658`）

```bash
NDK=~/Library/Android/sdk/ndk/27.2.12479018
CXX=$NDK/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android34-clang++
mkdir -p build/linux-aarch64-cross/release/probes/cache-mem
$CXX -O2 -Wall -Wextra -Werror -static -DCPU_UARCH_HAVE_LINUX_PERF=1 \
  -Iprobes/common -Iprobes/platform/linux \
  probes/cache-mem/ptr_chase.cpp probes/platform/linux/perf_counter.cpp \
  -o build/linux-aarch64-cross/release/probes/cache-mem/ptr_chase
```

- 平台配置约定二进制就在该路径（`configs/platforms/redmi-k70pro-01.json` probes.local），不要改平台配置。
- 编译失败：**完整错误回传，不要自行改代码/降 -Werror/去掉 -static**。
- 产物 `file` 应为 `ELF 64-bit ARM aarch64 statically linked`；sha256 记入备忘录。

## 4. 执行序列（顺序有意义：标定先于主曲线，锚点夹块）

```bash
PY=/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python
PLAT=configs/platforms/redmi-k70pro-01.json
ENV="--environment-profile charging-thermal --allow-mutation"
cd ~/workspace/cpu-uarch-explorer-tlb-r2-m0b

# 0) 块前锚点（战役纪律：块主体 run 前后各一次；充电态锚点与主体同 regime）
$PY -m runner.cli plan --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-anchor.json --platform $PLAT $ENV   # 先预览
$PY -m runner.cli run  --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-anchor.json --platform $PLAT $ENV

# 1) G0-3 空窗底噪（1 case）
$PY -m runner.cli run  --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-pilot-g03-empty.json --platform $PLAT $ENV

# 2) G0-3 无冲突同长度窗 + 重复尺度（4 cases）
$PY -m runner.cli run  --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-pilot-g03-noconflict.json --platform $PLAT $ENV

# 3) B1 自冲突曲线（9 cases）
$PY -m runner.cli run  --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-pilot-b1.json --platform $PLAT $ENV

# 4) 块后锚点（同 0）
$PY -m runner.cli run  --experiment configs/experiments/ptr-chase-sm8650-x4-tlb-anchor.json --platform $PLAT $ENV
```

每个 `run` 前先 `plan` 预览：case 数应为锚点 2 / 空窗 1 / noconflict 4 / b1 9，不符即停。每步之间留设备散热间隙（b1 块跑完 idle 30s 再跑锚点）。

## 5. 预期与快速核验（不是判读，是"跑没跑对"的门槛）

- 每条 record `status=ok`；`window_mux_rounds` 应小（≥3 即在备忘录醒目标注）。
- record 的 `policy_result.accepted_nonbaseline` 含 `accepted-nonbaseline:cpufreq-max-mismatch:policy0`（充电态预期，**不是异常**）；若出现 policy7 相关条目或 `violations` 非空 → 停并回传。
- b1 输出形态：W=8 附近 `pmu.l2d_tlb_refill.count` 已抬升（**跳变提前是已知形态**，SMOKE-20261001 登记过，W=8 达 ~1.0/access 属预期，不要当异常停）。
- `set_domain=multi-region` 预期；若出现 `single-region-fallback`，照常跑完并在备忘录标注（F4 降级，不阻塞）。
- 单 case 跑飞/超时/非零退出：停、记录、回传——**不要**自行调 pool/regions 重试。

## 6. 回传物清单

1. `data/public/runs/` 下本次全部 run 目录（锚点×2 + 空窗 + noconflict + b1）：records.jsonl、raw/、artifact-manifest 全量——runner 已自动落盘，原样保留勿裁剪；
2. 一页备忘录：环境 9 项实际读值、二进制 sha256、每 run 的 case 数/ok 数/mux 异常点/single-region-fallback 出现情况、与第 5 节门槛的偏差；
3. `git status` 输出（证明未改仓内文件）。

## 7. 红线汇总

- 不 `git commit`/不推分支；不动他人会话文件（worktree 里 `docs/reviews/`、`docs/open-items.md` 的他人改动原样保留）。
- 不改任何配置/代码/参数；不改判据；判读问题回传，由分析侧处置。
- 产物纪律：备忘录与原始日志留工作区；设备侧 `/data/local/tmp` 探针可留。
