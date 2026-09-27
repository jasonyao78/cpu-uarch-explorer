# Redmi K70 Pro 受控安静态 v2

> 适用平台：`redmi-k70pro-01`（SM8650 / Android 15 / KernelSU Root）
> 目的：为 cache/memory 微基准建立可审计、可恢复的环境边界
> 非目标：制造所谓“纯净系统”、停用热保护，或由一次延迟曲线裁定 cache 容量

## 1. profile 的实际语义

`controlled-baseline` 必须由操作者显式选择，不是平台隐式默认值。它只执行
一项 host 级 mutation：把所有 cpufreq policy 的 governor 临时设为
`performance`。Runner 在 apply 前逐 policy 保存 governor/min/max，结束后
恢复保存的实际值，不假设系统默认一定是 `walt`。

以下状态只读采集并作为门禁，不由 profile 改写：

- wakefulness、screen、电源与 DeviceIdle；
- 飞行模式；
- `Active Camera Clients` 当前区块；
- `mi_thermald` 服务状态；
- 每个 cpufreq policy 的 governor/min/max/current；
- CPU thermal sensors、thermal status 和 loadavg。

默认 profile 明确不执行：停止 thermal/perf 服务、`force-idle`、切换飞行
模式、盲发 `KEYCODE_POWER`、`am kill-all`、硬编码 force-stop 应用、
`drop_caches`、修改 scaling min/max。

## 2. 只读 preflight

先确认 adb 与 Root：

```bash
adb get-state
adb shell su -c id
```

再运行只读检查：

```bash
python3 -m runner.cli env \
  --platform configs/platforms/redmi-k70pro-01.json \
  --environment-profile controlled-baseline inspect
```

`policy_result.ready_for_transaction=true` 才能进入实验。正常待机状态的四个
`cpufreq-governor-mismatch:*` 会列在 `covered_by_mutation`，因为正式事务会
切换 governor；它们不算 preflight 阻塞项。

以下任一项出现在 `violations` 都必须停下处理，不能降低门槛强行通过：

- `thermal-over-limit`：CPU 最高温度超过 90°C；保持 thermal 运行并等待冷却；
- `camera-active`：活动客户端区块非 `[]`；关闭实际占用方后重新检查；
- `service-mismatch:mi_thermald`：先恢复 thermal 服务；
- screen、wakefulness 或 force-idle 不符合 profile；
- 任一 `cpufreq-max-mismatch:*`：记录当前热/性能策略原因，不直接写 sysfs
  冒充正常基线。

相机历史事件日志中的 `CONNECT`、HAL device dump 中的 `Camera ID` 不代表
当前占用；Runner 只解析 `Active Camera Clients` 到 `Allowed user IDs` 之间
的区块。

## 3. 预览与正式运行

所有正式运行先 plan：

```bash
python3 -m runner.cli plan \
  --experiment configs/experiments/ptr-chase-cache-sweep.json \
  --platform configs/platforms/redmi-k70pro-01.json \
  --environment-profile controlled-baseline
```

确认 case、repetitions、warmup 和唯一 mutation 后才能 run：

```bash
python3 -m runner.cli run \
  --experiment configs/experiments/ptr-chase-cache-sweep.json \
  --platform configs/platforms/redmi-k70pro-01.json \
  --environment-profile controlled-baseline \
  --allow-mutation
```

`--allow-mutation` 是每次显式授权门。缺失时 Runner 在触碰设备前退出。
profile 声明和额外 `--env` 若请求同一 controller 的不同值，也会在触碰设备
前拒绝。

## 4. 运行中的证据与失效规则

每个 case 的 `environment.state_snapshot` 保存 before/after 和
`policy_result`：

- before 不合格：不执行 probe，记录
  `failure.reason=environment-precondition-failed`；
- required snapshot 采集/解析失败：不允许静默省略，记录
  `environment-snapshot-failed`；
- after 超温、出现相机客户端、服务/频率限制/飞行模式等发生漂移：原始
  stdout/stderr 可保留审计，但 run-record 必须为空 metrics，并标记
  `environment-postcondition-failed`。

`scaling_cur_freq` 仍只是 cpufreq 报告值，不升级为实际硬件周期证据。
通过本 profile 只证明环境控制链可审计，不证明 L2/L3/LLCC 容量或机理。

## 5. 中断与恢复

环境事务在每个 apply 前持久化 before 和 apply intent。后续 controller
失败时，已开始的 mutation 按逆序恢复；恢复失败的 journal 保持 unfinished，
阻止下一次实验。

查看状态：

```bash
python3 -m runner.cli env \
  --platform configs/platforms/redmi-k70pro-01.json status
```

人工重放恢复：

```bash
python3 -m runner.cli env \
  --platform configs/platforms/redmi-k70pro-01.json \
  restore --tx <tx-id>
```

恢复后再次运行只读 inspect，并逐 policy 确认 governor/min/max 回到事务前
快照。不得用“全部写回 walt”代替精确恢复。

## 6. 非 baseline 条件

以下条件必须另建 profile、另写设计和验收，不能追加到
`controlled-baseline`：

- `mi_thermald=stopped`；
- `deviceidle force-idle`；
- 飞行模式开/关 A/B；
- 相机、GPU、NPU、ISP 等异构 master 干扰；
- perf service 抑制或 boost/perf lock；
- scaling min/max 改写。

尤其是停 thermal：只能用于分钟级独立实验，必须预先定义温度中止线、证明
服务确实保持 stopped，并验证恢复成功。量产机上的长跑 benchmark 禁止停热
保护。

## 7. 2026-09-27 control-path 验收

本节只验收环境控制与恢复链，不把单点延迟纳入 cache 容量证据：

1. 提交 `0895270` 的第一次 4 MiB 临时 smoke 正确失败：Android 将默认匿名
   映射与邻接 VMA 合并，`/proc/self/smaps` 的 VMA 级 `AnonHugePages` 无法
   精确归属于目标 buffer。probe 退出 1，run-record `metrics=[]`，事务
   `6f8b56dd6564` 仍完成精确恢复。这里没有为了“跑通”而放宽归属规则。
2. 提交 `d405460` 为 Linux 普通匿名映射增加两侧 `PROT_NONE` guard page，
   使目标 RW 区间具有精确 VMA 边界；本地 Release 11/11、UBSan 12/12、
   Runner 116/116、Analysis 7/7，以及 Linux x86 default/THP 实测均通过。
3. 同一临时 case 重跑成功：run id
   `63c94b7b-8b4a-4eb1-9c5a-17374eb01bfd`，AArch64 artifact SHA-256
   `2b2728f82ebcb31f556442ec3a32750886e5b117bf607ef9a3a57e415fa6111e`。
   before/after 的四个 governor 均为 `performance`，min/max 未漂移，
   `mi_thermald=running`、相机无 active client、policy 无 violation；事务
   `323d65a25ace` 状态为 `restored`。
4. 恢复后只读检查确认四个 policy 的 governor/min/max 与事务前逐项一致：
   governor 全部回到 `walt`，max 分别为 2265600/2707200/2707200/2745600
   kHz，min 分别为 556800/614400/499200/672000 kHz；unfinished journal=0。

smoke 报出的 7.3997 ns 只证明 probe 在受控事务内完成，**不证明**任何 L2、
L3 或 LLCC 容量。临时 run、journal、交叉编译产物和设备端 smoke 二进制在
验收后删除，不进入 `data/`。
