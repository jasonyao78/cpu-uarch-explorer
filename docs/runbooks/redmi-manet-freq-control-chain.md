# Runbook：SM8650（Redmi K70 Pro）频率控制链排障手册

> **定位**：本手册是"频率不符合预期"时的分层定位流程与处置边界，适用
> 于 `redmi-k70pro-01`（SM8650/Pineapple，HyperOS 2，KernelSU root）。
> 它综合两个方向的实证：向上解锁硬件 OPP 的调查（仓外只读参考
> `cpu-uarch-ref/`，OI-7，不入库）与本仓测量实验被热票钳制的事件
> （`docs/reviews/2026-09-28-sm8650-x4-p0prime.md` §5）。
> **证据等级标注**：【实证】= 本机运行时直接验证；【静态】= 配置/ELF/
> 文档证据；【推断】= 单一来源推论；【未证】= 开放问题。
>
> **总边界**：永不停止/抑制 thermal 保护；测量实验的 cpufreq limits 只
> 观测、不写入（平台画像 `environment_control_note`）；正 handle、
> write_ok、回读值，三者都不等于"生效"。

## 1. 这份手册解决什么问题

三类典型困惑，共用一套定位流程：

1. **频率低于画像值**——实验门禁报 `cpufreq-max-mismatch`，
   `scaling_max_freq` 被压到稳态 cap 之下（本仓 2026-09-28 事件）。
2. **频率到不了硬件 OPP**——`cpuinfo_max_freq` 是 3302400，
   `scaling_max_freq` 却稳在 2745600（仓外文档的主问题）。
3. **写了/调用了但没变化**——sysfs 写返回成功、Perf2 返回正 handle，
   但目标节点纹丝不动。

三者的共同根因层：**有效频率由多层仲裁产生，你写入的那一层未必是
当前生效的那一层。**

## 2. 分层控制模型（核心心智图）

```text
F_effective,max = min(硬件 OPP, 厂商稳态 cap, WALT sched_fmax_cap,
                      cpufreq QoS 票(thermal/perf), Perf2 资源仲裁结果, ...)
F_effective,min = max(硬件最低 OPP, 用户 sysfs min, vendor min, ...)
```

| 层 | 机制 | 观测点 | 已证事实（等级） |
|---|---|---|---|
| L0 硬件 OPP | `cpuinfo_max_freq` | sysfs | policy0/2/5/7 = 2265.6 / 3148.8 / 2956.8 / 3302.4 MHz【实证】 |
| L1 厂商稳态 cap | vendor 控制链（PERFD 参与执行） | `scaling_max_freq`、`cpu_frequency_limits` trace | 稳态 cap = 2265.6 / 2707.2 / 2707.2 / 2745.6 MHz；唤醒后存在 ~3.0 s boost 窗口（2956.8 / 3052.8 MHz），PERFD 时间相关 ~1.1 ms【实证】 |
| L2 WALT 调度层 | `/proc/sys/walt/sched_fmax_cap`（4 字段） | proc sysctl | 基线 `1804800 2707200 2707200 2147483647`；PRIME 域 = INT_MAX（WALT 层不封頂）【实证】；字段↔policy 映射【推断】 |
| L3 cpufreq QoS 票 | kernel thermal zone → `cpu-clusterN` cooling device | `cooling_device*/cur_state`、`thermal_zone*` | 热票激活时逐级压 OPP（本仓事件：cpu-cluster3 state 3/34 ↔ policy7 2745600→2688000）【实证】 |
| L4 Perf2/MPCTL 通道 | `vendor.qti.hardware.perf2-hal-service` 仲裁 | `/proc/perflock_records`、strace | **正 handle ≠ 生效**：合法请求可只记账不落节点；存在 caller 准入/优先级仲裁【实证（失效路径）】；PowerOpt 持 INT_MAX 长期锁【实证】；生效路径【未证】 |
| L5 用户 sysfs | `scaling_max_freq` 直接写 | write/readback | root 写入返回成功，回读立即被现存更低 cap 截断【实证】 |

**关键认知**：

- 写入入口（L5 sysfs、L4 perf_lock）与生效层（L1/L2/L3 的 min/max
  仲裁）是分离的。定位问题的第一步永远是"现在哪一层在出最低票"，
  而不是"再写一次"。
- 稳态 cap（L1）本身低于硬件 OPP（L0）——把 OPP 当成"稳态期望值"
  是定位错误的第一来源。
- 热票（L3）与 Perf2 通道（L4）是两条独立的限制路径：热票来自
  kernel thermal framework，Perf2 来自 vendor 用户态仲裁；排查时
  不要混用证据。

## 3. 两个方向相反的实证案例

### 案例 A：测量实验被热票钳制（本仓，2026-09-28）

时间线（详见 P0″ 评审 §5）：

1. 长训练矩阵（512 圈 × 多 case）中段，后置门禁捕获
   `policy2/5 max 2707200→2630400、policy7 2745600→2688000`
   （CPU 峰值 52.6 °C）；runner fail-closed 中止后续 29 case 并恢复
   governor。数分钟后限额自行恢复。
2. 补全段拆分（r2a/r2b + 段间冷却检查）顺利完成。
3. 下一组前置门禁再遇钳制（CPU 46.9 °C），随后 **≥40 分钟空载限额
   不恢复**：thermal status=0、电池 28.9–32.2 °C、Android 层冷却设
   备空闲——但 **kernel 侧 `cpu-cluster3` cdev 激活（state 3/34）**，
   最热区域是 **PMIC/充电域 `pm8550b_lite_tz`（54.4 °C）**，CPU 已
   凉（32–38 °C）。一组 NSP 传感器读数 40 分钟冻结在 54–61 °C
   （【推断】陈旧读数，来源未确定）。

判别与处置：

- **WALT 层干净**（`sched_fmax_cap` = 基线、PRIME=INT_MAX）而
  **cpufreq 层被钳** → 卡点是 L3 热票，不是 L2/L4。【实证】
- 驱动源不是 CPU 温度，而是 PMIC/充电域——**插着充电时被动降温极
  慢，释放时间不可预测**。【实证】
- 正确处置：分段矩阵、冷却检查点、等/拔充、门禁保持 fail-closed。
  错误处置：写 sysfs 抬上限（L5 已被证无效）、抑制 thermal（红线）、
  走 Perf2 通道注高票（污染测量基线，见 §4 对照）。

### 案例 B：向上解锁硬件 OPP（仓外文档，2026-09-28，进行中）

目标：解除 L1 稳态 cap，达到 L0 OPP。已证与未证（原文照录等级）：

- 已证：L1 cap 阶梯与 ~3 s 唤醒 boost 窗；L5 sysfs 写被截断；Perf2
  正 handle 只代表 request 生命周期（服务端 strace 只有
  `perflock_records` 记账写，无目标节点 open/write）；PowerOpt 持
  INT_MAX 锁（handle 会变 = 释放重建循环）；目标内核节点存在、可
  读、root 可直写、parser 正常。
- 未证：`0x1091`（Performance mode hint）对现存低 cap 的仲裁效
  果；`0x7fffffff` 的语义；低 cap 的唯一 owner；仲裁是"同资源值比
  较"还是"client 优先级分层"。
- 他们的严格实验顺序（值得作为所有 L4 实验的模板）：静态映射 →
  调用通路（dlopen/namespace/SELinux）→ 有限时单 hint → 单资源刺
  激建映射 → 可信 caller 正对照 → 确认 PowerOpt 锁内容 → 最后才
  考虑受控释锁；全程不禁 thermal、一次只改一个变量、不叠加高
  request。

### A/B 对照（为什么不能合并解决）

| 维度 | A（恢复稳态） | B（解锁 OPP） |
|---|---|---|
| 目标 | 回到已知的 L1 稳态 | 越过 L1 到 L0 |
| 机制方向 | 等 L3 热票撤掉（被动） | 往 L4 注入更高票（主动） |
| 正确解法 | 等/拔充/分段实验/门禁不动 | 严格顺序的单变量实验 |
| 错误解法 | 写 sysfs、压 thermal、注高票 | 叠加高 request、停全部 perf 服务、禁 thermal |
| 对测量的影响 | 恢复即恢复基线 | **会改变被测工况**（须另立 profile 与锚点） |

**结论**：B 对 A 的参考价值在方法论（分层模型 + 单变量实验纪律），
不在解法。A 不等 B 解决，B 也解决不了 A（min() 下热票照样优先）。

## 4. 排障决策树（动手顺序）

### Step 0：先定义"期望"

- 期望是**稳态 cap**（2265600 / 2707200 / 2707200 / 2745600）还是
  **硬件 OPP**（2265600 / 3148800 / 2956800 / 3302400）？测量实验
  的画像值是前者；不要拿后者当前者用。

### Step 1：取证快照（只读，30 秒）

```bash
adb shell 'su -c "
for p in 0 2 5 7; do echo \"policy\$p: gov=\$(cat /sys/devices/system/cpu/cpufreq/policy\$p/scaling_governor) min=\$(cat /sys/devices/system/cpu/cpufreq/policy\$p/scaling_min_freq) max=\$(cat /sys/devices/system/cpu/cpufreq/policy\$p/scaling_max_freq)\"; done
echo \"-- sched_fmax_cap: \$(cat /proc/sys/walt/sched_fmax_cap)\"
echo \"-- perflock tail:\"; tail -4 /proc/perflock_records
echo \"-- active cdevs:\";
found=0; for f in /sys/class/thermal/cooling_device*/cur_state; do
  s=\$(cat \$f); [ \"\$s\" != \"0\" ] && { echo \"  \$f=\$s type=\$(cat \${f%/*}/type)\"; found=1; };
done; [ \$found -eq 0 ] && echo \"  (none)\"
echo \"-- hottest zones:\";
for z in /sys/class/thermal/thermal_zone*; do echo \"\$(cat \$z/temp) \$(cat \$z/type)\"; done | sort -rn | head -5
"'
```

### Step 2：按层判别

| 观测 | 结论层 | 读法 |
|---|---|---|
| `sched_fmax_cap` ≠ 基线 | L2 WALT | WALT 调度层在压帽；查谁写的（L4 或直写） |
| 某 `cpu-clusterN` cdev state > 0 | L3 热票 | 找最热 zone（**未必是 CPU**——PMIC/NSP/充电域都可能驱动） |
| `perflock_records` 有未配对 acquire | L4 有持锁方 | 按 pid 找 owner；注意 PowerOpt INT_MAX 锁是系统常态 |
| max 稳在 L1 稳态 cap | 正常工况 | 这不是故障；想要 OPP 是案例 B 的课题，不是排障 |
| Android dumpsys 全闲但 kernel cdev 激活 | L3 | dumpsys 只覆盖框架层设备，**以 sysfs cdev 为准** |

### Step 3：分支处置

**L3 热票（测量实验被钳）**

- 做：等（时段不可控）；分段矩阵 + 段间限额检查；**拔充电线**
  （PMIC/充电域是常见驱动源，拔线即去热源；adb-over-USB 会先断，
  明天插回重连即可）；记录钳制值与最热 zone 入档。
- 不做：写 `scaling_max_freq`（L5 截断，已证无效）；停/抑制
  thermal（红线）；用 L4 注高票对冲（污染基线）。

**L4 Perf2 失效（handle 有了，节点没变）**

按仓外文档的决策树执行（不要跳步）：UID 1000/SID 差分 → 补齐
`openat2/writev` 的干净 strace → 可信 caller 正对照 → 确认
PowerOpt 锁 resource array → 二进制 strings/XREF 或 uprobe 定位
ApplyOpt 条件 → 最后才受控释锁。任何一步都不从"正 handle"宣称
生效。

**测量门禁报 `cpufreq-max-mismatch` / `state-drift`**

这是 fail-closed **正常工作**：环境被外部（thermal/vendor/其他实
验）改变时拒绝测量。处置 = 找漂移源（回本手册 Step 2）+ 冷却/等
待/分段；**不要放宽门禁**——它昨天刚拦下过两次真实热钳位。

## 5. 已证事实速查

频率阶梯（kHz）：

| policy | 稳态 cap | 唤醒 boost（~3 s） | 硬件 OPP |
|---|---:|---:|---:|
| 0 (A520×2) | 2265600 | — | 2265600 |
| 2 (A720×3) | 2707200 | 2956800 | 3148800 |
| 5 (A720×2) | 2707200 | 2956800 | 2956800 |
| 7 (X4×1) | 2745600 | 3052800 | 3302400 |

Perf2 资源地图（【静态】自 OEM XML；映射置信度见仓外文档 §6）：

| 资源 | opcode | 节点/语义 |
|---|---|---|
| `SCHED_FMAX_CAP_LITTLE/BIG/PRIME/TITANIUM` | `0x43C1C100` / `0x43C1C000` / `0x43C1C200` / `0x43C1C300` | `/proc/sys/walt/sched_fmax_cap`，单位 kHz |
| cluster max freq（LITTLE/BIG/TITANIUM/PRIME） | `0x40804100` / `0x40804000` / `0x40804300` / `0x40804200` | 单位 MHz |
| cluster min freq（LITTLE/BIG/TITANIUM/PRIME） | `0x40800100` / `0x40800000` / `0x40800300` / `0x40800200` | 单位 MHz；与 sched_fmax_cap 的 kHz 不可混用 |
| Performance mode hint | `0x00001091`（Target=pineapple） | 含 4 组 fmax_cap = `0x7fffffff`（语义【未证】）+ 基础 cluster min |

## 6. 未决问题登记（触发条件 → 下一步）

1. `0x1091` 对现存低 cap 的仲裁效果 → 案例 B 阶段三有限时实验
   （仓外项目，本仓不依赖）。
2. PowerOpt INT_MAX 锁的 resource array → 案例 B P1（dumpsys/动态
   跟踪/解析 Binder 参数）。
3. L4 仲裁模型（值比较 vs 优先级分层）→ 案例 B P1/P2。
4. `sched_fmax_cap` 四字段 ↔ policy 映射 → 单资源刺激实验（案例
   B 阶段四）。
5. PMIC/充电域热票的精确阈值与 hysteresis → 本仓 THP 补跑前后，
   以 `pm8550b_lite_tz` 与限额联动采样补齐（运维观察，不立项）。
6. NSP 传感器冻结读数（54–61 °C 40 分钟不变）来源 → 与 5 同期观
   察；若确认为陈旧读数，登记为平台画像注意事项。
7. adb-over-WiFi 作为"拔充实验"的传输 → 需要时立项（改传输须用户
   批准 + 更新 `data/private/hosts.md`）。

## 7. 红线（两边合并）

- 永不停止/抑制 thermal HAL、thermal-engine、PMIC/电池/充电器保
  护、emergency shutdown。
- 测量实验的 cpufreq limits 只观测不写入；unlock 类实验（案例 B）
  必须与测量实验时间错开，且 release 干净（本仓门禁 fail-closed
  会兜底拦污染）。
- 不叠加高 max request 硬顶低 cap；不一次停多个 perf 服务（无法归
  因，可能留下未释放 request）。
- 不从正 handle / write_ok / 单次回读宣称"已生效"；生效判定必须见
  §4 Step 2 的多层证据。
- 不把 OPP 解锁工况混入既有测量基线（锚点全部作废的代价）。

## 8. 出处

- 仓外只读参考（OI-7，不入库）：`cpu-uarch-ref/Android灭屏最高频锁
  定实验与证据链.md`、`cpu-uarch-ref/Qualcomm Perf2 Resource Apply
  Failure - Root Cause Investigation.md`（2026-09-28，进行中）。
- 本仓：`docs/reviews/2026-09-28-sm8650-x4-p0prime.md`（§5 热钳位
  事件）、`configs/platforms/redmi-k70pro-01.json`
  （`freq_domains`/`environment_control_note`）、
  `docs/runbooks/redmi-controlled-quiet-state-v2.md`（安静态门禁）、
  `docs/runbooks/redmi-manet-kernelsu-root.md`（root 通道）。
