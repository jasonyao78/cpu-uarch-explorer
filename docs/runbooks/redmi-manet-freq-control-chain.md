# Runbook：SM8650 频率控制链——技术原理、已证事实与排障手册

> **定位**：`redmi-k70pro-01`（SM8650/Pineapple，HyperOS 2，KernelSU
> root）上"频率不符合预期"时的权威参考。**自包含**：原始调查文档
> （仓外 `cpu-uarch-ref/`，OI-7，可能散佚）的全部关键证据已内联，
> 不依赖外部材料即可诊断与动手。
> **证据等级**：【实证】= 本机运行时直接验证；【实证-阴性】= 实验
> 有效执行但无变化，"不生效"本身是证据；【静态】= 配置/ELF/文档
> 证据；【推断】= 单一来源推论；【未证】= 开放问题。
> **总边界**：永不停止/抑制 thermal 保护；测量实验的 cpufreq limits
> 只观测、不写入；正 handle、write_ok、单次回读值，三者都不等于
> "生效"。

## 目录

- §1 这份手册解决什么问题
- §2 技术原理（P1–P9）
- §3 分层控制模型与已证事实
- §4 排障手册（决策树与处置）
- §5 调试与取证手段（工具箱）
- §6 案例档案（A：动态 ceiling drift；B：解锁调查）
- §7 未决问题登记
- §8 红线
- §9 出处

---

## 1. 这份手册解决什么问题

三类典型困惑，共用一套定位流程：

1. **频率低于画像值**——实验门禁报 `cpufreq-max-mismatch`，
   `scaling_max_freq` 被压到稳态 cap 之下（本仓 2026-09-28 事件，
   §6.1）。
2. **频率到不了硬件 OPP**——`cpuinfo_max_freq` 是 3302400，
   `scaling_max_freq` 却稳在 2745600（案例 B 的主问题，§6.2）。
3. **写了/调用了但没变化**——sysfs 写返回成功、Perf2 返回正
   handle，目标节点纹丝不动。

三者的共同根因层：**有效频率由多层仲裁产生，你写入的那一层未必
是当前生效的那一层。** 理解这一点需要先理解下面的原理。

---

## 2. 技术原理

### P1. DVFS 与 OPP：频率从来不是孤立旋钮

现代 SoC 按 **OPP（Operating Performance Point，电压-频率对）** 运
行：升频通常必须同时升压才能保证电路时序收敛。动态功耗近似：

```text
P_dynamic ∝ C · V² · f
```

电压随频率上升，所以频率→功耗是**超线性**关系。三个直接推论：

1. 存在一张硬件 OPP 表——`cpuinfo_max_freq` 只是表顶，不代表任何
   工况都能到达；
2. 厂商会在表顶之下设**产品稳态 cap**（功耗、散热、产品定位），
   所以"芯片最高 3.3 GHz"与"日常能稳在 3.3 GHz"是两回事；
3. 一切"锁频"讨论最终都绕不开热——这是 §P9 的物理基础。

### P2. 约束合并：为什么有效值是 min/max 而不是"最后写入者胜"

同一个硬件旋钮有多个利益方：用户（sysfs）、调度器（WALT）、热框
架（cooling device）、厂商性能服务（Perf2）、其他 QoS 请求者。
内核的 **freq-qos** 模式让每个请求者登记一条**约束**（一条上限或
一条下限），然后合并：

```text
F_effective,max = min(所有 max 约束)   ← 最保守者胜，保护硬件
F_effective,min = max(所有 min 约束)   ← 最饥渴者胜，保证响应
```

推论（全部在本机实证过，见 §3）：

- 写 sysfs 是"登记/修改一条约束"，不是"命令硬件"——已有更低约束
  时 `write_ok` 但回读被**截断**；
- "叠加一条更高的 max request 顶掉现存低 cap"在数学上不可能成
  立——除非高票能替换或释放原约束，而这正是厂商仲裁（§P5）管的
  事。

### P3. 为什么 Qualcomm/Android 有这么多层

一台 Android/Qualcomm 手机上至少有四个独立的频率控制层，各自有
来历与职责：

1. **Linux 通用层**：cpufreq + OPP（执行频率切换）、freq-qos（约
   束合并）、kernel thermal framework（热保护，§P4）。
2. **Qualcomm 调度层（WALT）**：任务调度与频率联动；
   `sched_fmax_cap` 是**调度器侧**的频率帽，与 cpufreq 层的帽彼
   此独立又互相取小——所以 WALT 层干净不代表 cpufreq 层干净（本
   仓事件的关键判别，§6.1）。
3. **厂商用户态层（Perf2/MPCTL）**：Android PowerHAL hint 的现代
   形态。系统各处（app 启动、触摸、相机、游戏、电源模式）的性能
   请求统一由 perfd 仲裁。它以用户态服务存在，是因为策略要跨
   CPU/GPU/DDR/总线统一编排，且要按产品区分——同一芯片不同机型
   下发不同 XML（本机配置 Target=`pineapple`）。
4. **Android 框架层**：Power HAL、Doze/DeviceIdle、wakelock 等，
   决定"系统是否在跑"（§P7），间接决定频率语义。

所以一个"频率不对"的问题，至少要按 §4 的顺序查四层，任何单层
证据都不足以定论。

### P4. thermal framework：zone、trip、cdev、state 与 hysteresis

内核热保护的组成模型：

```text
thermal_zone（温度传感器）+ trip points（阈值）
  → governor（如 step_wise：温度 → 冷却强度的映射）
  → cooling_device（cdev：能降温的执行器；state 越大冷却越激进）
  → cdev 把 state 翻译成 QoS 票（对 CPU cdev：一条频率上限约束）
```

- **为什么有 hysteresis**：防止温度在阈值附近抖动时频率来回振荡
  ——升阈值触发、降阈值（更低）才释放，所以"已经不热了"和"热票
  已释放"之间总有滞后。
- **为什么有多个 zone**：保护对象不同——SoC die、PMIC（电源管
  理）、电池、皮肤（skin）、NPU/DSP、相机模组。任一 zone 过热都
  可触发它绑定的 cdev。
- **为什么 PMIC/充电域能钳 CPU**：整机功耗包络是共享的——充电电
  路与 SoC 共处一个狭小机身，PMIC 过热时压 CPU 频率是减少整机
  发热的合法手段。这是"CPU 已凉、限额仍不放"的一个常见候选机
  制（本仓 §6.1 事件中 PMIC 域为候选驱动源【推断】，根因 OPEN）。

### P5. 请求与生效分离：为什么 write_ok / 正 handle 不等于生效

防御性设计的普遍模式：**入口校验通过 ≠ 请求被采纳**。

- 内核驱动对 sysfs 写入：先收进约束表，再与现存约束仲裁
  （§P2）——返回值只描述"接收"，不描述"胜出"。
- Perf HAL 对 Binder 请求：先建 request 生命周期对象（分配
  handle、写记账记录），再过 caller 准入与资源仲裁——handle 只
  证明"生命周期存在"，不证明"进入 effective queue 并被 Apply"。
- 厂商硬化：不受信 caller（例如 root/KSU 下的自编译二进制）可
  以被"给记账、不给生效"，以防任意 root 应用篡改产品性能策略
  （本机实测路径正是如此，§3.6）。

推论：**生效判定必须看目标层的可观测变化**（节点值变化、
tracepoint、目标节点的 open/write syscall），不能看返回值。

### P6. 唤醒 boost 为什么存在（~3 秒）

感知性能：用户触摸/唤醒后的前几百毫秒决定"卡不卡"的主观感受。
厂商在唤醒瞬间短暂抬高频率帽，随后回落稳态。本机 ftrace 实证
（§3.3）：唤醒到上限提升延迟 0.171 s，窗口持续 2.9996 s，PERFD
时间相关 1.1 ms。

对测量的意义：唤醒/亮屏瞬态是**污染源**——实验必须等瞬态结束
再采数（本仓安静态流程中的"等待 display/keyguard 瞬态"步骤，
见 quiet-state runbook）。

### P7. suspend 与 wakelock：灭屏不等于在跑

Android 灭屏后系统可进入 **suspend**：用户态冻结、CPU 落入深度
idle，此时"最高频"只剩配置意义、没有运行意义。要让灭屏下的负
载持续执行，必须持 **partial wakelock**；`dumpsys deviceidle
disable` 关闭的只是 Doze 状态机，不保证系统永不 suspend。

测量协议必须把三个条件拆开：屏幕关闭 / 未 suspend（有
wakelock 或有 adb 等活跃会话）/ 无唤醒瞬态（§P6）。本仓画像的
`wakefulness: Dozing` 指 Doze 态，设备经 adb 保持运行，不等同
suspend。

### P8. 为什么 `scaling_cur_freq` 证明不了真实时钟

- 它可能是**缓存值或采样瞬时值**；fast-switch 路径下，读取值与
  硬件瞬时状态可以有偏差；
- CPU 空闲时即使 min 被抬高也会进 idle（频率掉到很低甚至关
  断）——"policy 锁在最高 OPP"和"CPU 持续执行不 idle"是两回
  事；
- 证明"当时实际跑在什么频率"需要组合证据：
  `cpu_frequency` / `cpu_frequency_limits` tracepoint + 持续负
  载吞吐 + active/idle residency 互证。

本仓纪律：cycles↔ns 换算依赖 cpufreq 报告值时一律标 DERIVED
（见 P0″ 评审残差节）；平台画像 `freq_domains_note` 早已声明
scaling 值不作硬件时钟的独立证明。

### P9. 为什么不能用"禁 thermal"换测量稳定性

- **安全**：P ∝ CV²f（§P1），最高 OPP 长时无热保护运行，在
  emergency shutdown 兜底之前就可能已经造成损伤；
- **科学**：禁 thermal 改变被测对象——测到的不再是这台零售
  机，而是一台理想化机器；且温度上升使硅片漏电流指数增长、功
  耗进一步增大，"稳定"会变成幻觉；
- **纪律**：本仓与原始调查文档共同的安全边界，无例外条款。

---

## 3. 分层控制模型与已证事实

### 3.1 总模型

```text
F_effective,max = min(硬件 OPP, 厂商稳态 cap, WALT sched_fmax_cap,
                      cpufreq QoS 票(thermal/vendor), Perf2 仲裁结果, …)
F_effective,min = max(硬件最低 OPP, 用户 sysfs min, vendor min, …)
```

### 3.2 频率三档（【实证】，kHz）

| policy（核型） | 稳态 cap | 唤醒 boost（~3 s） | 硬件 OPP |
|---|---:|---:|---:|
| 0（A520×2） | 2265600 | — | 2265600 |
| 2（A720×3） | 2707200 | 2956800 | 3148800 |
| 5（A720×2） | 2707200 | 2956800 | 2956800 |
| 7（X4×1） | 2745600 | 3052800 | 3302400 |

要点：稳态 cap 低于硬件 OPP；唤醒 boost 也不是全 SoC 最高状态；
vendor 控制链可动态修改 policy limit（同一 policy 的 max limit 可
变，非熔丝死值）。

### 3.3 唤醒 boost 的 ftrace 实证（【实证】）

窗口一：

```text
3563.667077  KEYCODE_WAKEUP_SENT
3563.838322  policy2/5 max=2956800, policy7 max=3052800   (Δ=0.171245 s)
3566.837884  恢复 policy2/5=2707200, policy7=2745600      (持续 2.999562 s)
```

窗口二：3568.978429 提升 → 3571.988117 恢复（持续 3.009688 s）。
PERFD 相关性：`PERFD-SERVER-1837` 于 3568.977302 活动，
`cpu_frequency_limits` 于 3568.978429 变化（Δ=1.127 ms）——强烈
支持 PERFD 参与执行/仲裁，但不排除 Android Power/Display、Xiaomi
MiPerf、perfservice、PowerKeeper、SystemUI、Camera 等上游请求者。

### 3.4 已证无效的方法（【实证】）

1. **AOSP fixed-performance mode**（`cmd power
   set-fixed-performance-mode-enabled true`）：两次重复实验，四
   policy 的 min/max/governor 全部不变——本 ROM 上不是锁频入
   口。
2. **root 直写 `scaling_max_freq`**：

   ```text
   policy2 request=3148800: write_ok readback=2707200
   policy5 request=2956800: write_ok readback=2707200
   policy7 request=3302400: write_ok readback=2745600
   ```

   写入返回成功、回读立即被截断、后续 10 s 无变化——不是写权限
   失败，也不是 daemon 写回，而是现存更低约束即时生效（§P2）。
   继续轮询写没有价值。
3. **只提高 min 或切换 governor**：请求仍被低 max 截断——解除低
   max 之前，这两样都不是根因方案。

### 3.5 WALT 节点族（【实证】基线与可写性）

- `/proc/sys/walt/sched_fmax_cap`（4 字段）：基线
  `1804800 2707200 2707200 2147483647`——PRIME 域 = INT_MAX，即
  **WALT 层对 X4 不封顶**；字段↔policy 映射【推断】（待单资源刺
  激实验确认）。
- `/proc/sys/walt/sched_max_freq_partial_halt`：基线 `1190400`；
  root 直写 `1190400→1000000→1190400` 成功——节点存在、parser
  接受 raw kHz、KSU 可写、300 ms 内无后台覆盖。证明了"节点可
  写"与"Perf 请求生效"是两回事（§P5）。
- `/proc/sys/walt/sched_asymcap_boost`：基线 `0`；perf 请求
  `0x43C00000,1` 获得正 handle（1534/1535）但节点 50/500/1500
  ms 均不变——Perf2 失效路径的实证样本。

### 3.6 Perf2 通道：系统组成与决定性 syscall 证据（【实证】）

组成：

```text
Perf HAL   PID 1682  /vendor/bin/hw/vendor.qti.hardware.perf2-hal-service
           domain = u:r:vendor_hal_perf_default:s0
PowerOpt   PID 1634  poweropt-service, UID 1000
           domain  = u:r:vendor_hal_poweroptservice_qti:s0
           持长期 direct perf lock（duration=INT_MAX, hint_id=0；
           handle 在 1512/1526/1528 间变化 = 释放并重建循环）
测试 caller /data/local/tmp/perf_lock_resource, UID 0, domain u:r:ksu:s0
```

决定性证据：对 Perf HAL PID 1682 全线程 `strace -ff`（open/
openat/close/write/pwrite64），测试请求（opcode `0x43C00000`、
value 1、duration 3000 ms、handle 1535）期间，Binder worker
TID 1837 **只执行了**：

```text
write(/proc/perflock_records, "type = acquire ... pl_handle = 1535 ...")
write(/proc/perflock_records, "type = release ... pl_handle = 1535 ...")
```

**没有**目标节点的 open/write，**没有** EACCES/EPERM/EINVAL/
ENOENT/EROFS——即请求根本没进入 Apply 路径。由此排除：节点写
失败、写入被快速恢复、采样错过首写、内核 parser 拒绝、ABI 错
误、XML 缺失、节点不存在、KSU 无写权限。残余风险：第一轮
trace 未覆盖 `openat2/writev/ioctl`（建议补齐一轮干净 trace）。
旁证【实证】：Perf HAL 的 FD 全景显示其持有
`/proc/perflock_records`、`/proc/perflock_exception`、
`/sys/kernel/tracing/trace_marker`、`/dev/binderfs/(vnd)binder`
等，但**没有任何** WALT/cpufreq 目标节点 FD——与"没看到 open"
互证（排除"早就开着"）。

正 handle 的真实含义 = request 通过基本校验 + 生命周期对象建立
+ acquire/release 可记账；**不保证**进入 effective queue、赢得
仲裁、handler 有效、目标节点被写入。

根因候选与置信度（详见 §6.2 案例档案）：

| 候选 | 置信度 | 要点 |
|---|---|---|
| caller 准入/硬化（UID/SID/client class 抑制） | 中高 | KSU UID 0 vs PowerOpt UID 1000 差分实验可判 |
| PowerOpt 高优先级/exclusive vote | 中高 | 需先拿到其锁的 resource array |
| resource 运行态 inactive / handler 未绑定 | 中 | feature gate/初始化失败/XML 与实现库不匹配 |
| 普通 min/max 值比较竞争 | 低 | 无法解释高值/低值/boolean 全不生效 |
| SELinux 阻止目标节点写入 | 低–中 | 本次连 open 都没发生，不在写入点 |

### 3.7 Perf 资源地图（【静态】自 OEM XML）

编码关系（【静态】）：`Major base = 0x40000000 + (Major << 22)`，
`Opcode = Major base + (Minor << 14)`；WALT Major = `0xF` → base
`0x43C00000`（如 Minor `0x7` → `0x43C1C000` = `sched_fmax_cap`）。
已测资源（`0x43C00000`、`0x43C20000`、`0x40800000` 及 fmax_cap 族）
均通过 QIndex 校验——"opcode 位域构造错误"已降为极低概率。

| 资源 | opcode | 节点/语义 |
|---|---|---|
| `SCHED_FMAX_CAP_LITTLE/BIG/PRIME/TITANIUM` | `0x43C1C100` / `0x43C1C000` / `0x43C1C200` / `0x43C1C300` | `/proc/sys/walt/sched_fmax_cap`（Major `0xF` Minor `0x7`），**单位 kHz** |
| cluster max freq（LITTLE/BIG/TITANIUM/PRIME） | `0x40804100` / `0x40804000` / `0x40804300` / `0x40804200` | **单位 MHz** |
| cluster min freq（LITTLE/BIG/TITANIUM/PRIME） | `0x40800100` / `0x40800000` / `0x40800300` / `0x40800200` | **单位 MHz** |
| `SCHED_MAX_FREQ_PARTIAL_HALT` | `0x43C20000` | `/proc/sys/walt/sched_max_freq_partial_halt`，kHz |
| Performance mode hint | `0x00001091`（Target=pineapple） | 含 4 组 fmax_cap = `0x7fffffff` + 基础 cluster min（1785/800/1670/1785 MHz） |

陷阱：cluster 资源用 MHz、fmax_cap 用 kHz，不可混用；
`0x43C1C300`（fmax_cap TITANIUM）与 `0x4080C300`（另一类
vendor frequency/adaptive 资源）尾部相似但**不是同一资源**；
`0x7fffffff` 的语义（unlimited / reset / 普通大数 / 特殊值）
【未证】，只能运行时判定。

policy ↔ 资源组候选映射（【静态】置信度高，未做单资源闭环）：
policy0=LITTLE、policy2=BIG、policy5=TITANIUM、policy7=PRIME/PLUS。

### 3.8 Perf client 调用入口（【静态】+ 风险）

库：`/vendor/lib64/libqti-perfd-client.so`，导出 `perf_hint`、
`perf_hint_renew`、`perf_hint_acq_rel`、`perf_lock_acq`、
`perf_lock_rel`、`perf_event`。ABI 候选（未经反汇编调用方确
认）：

```cpp
int perf_hint(int hint, const char *user_data, int duration_ms, int type);
int perf_lock_acq(int handle, int duration_ms, int list[], int num_args);
int perf_lock_rel(int handle);
```

风险（root 不自动绕过）：`/data/local/tmp` 二进制 `dlopen` vendor
库可能失败于 linker namespace 可见性、依赖库不可见、SELinux 禁
Binder/HIDL/AIDL、Perf HAL 对 UID/PID/域的权限检查。失败时必须
取 `logcat -b all -d` 与 dmesg 并检索 `linker` / `namespace` /
`CANNOT LINK EXECUTABLE` / `dlopen failed` / `avc: denied` /
`perf` / `mpctl`——不得无日志归因于 ABI。

---

## 4. 排障手册（决策树与处置）

### Step 0：先定义"期望"

期望是**稳态 cap**（2265600 / 2707200 / 2707200 / 2745600）还是
**硬件 OPP**（2265600 / 3148800 / 2956800 / 3302400）？测量实验
的画像值是前者；把 OPP 当稳态期望是定位错误的第一来源。

### Step 1：取证快照（只读，约 30 秒）

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
| `sched_fmax_cap` ≠ 基线 | L2 WALT | 调度层在压帽；查谁写的（Perf2 或直写） |
| 某 `cpu-clusterN` cdev state > 0 | L3 热票 | 找最热 zone（**未必是 CPU**——PMIC/NSP/充电域都可能驱动） |
| `perflock_records` 有未配对 acquire | L4 有持锁方 | 按 pid 找 owner；PowerOpt INT_MAX 锁是系统常态 |
| max 稳在 L1 稳态 cap | 正常工况 | 这不是故障；想要 OPP 是案例 B 的课题，不是排障 |
| Android dumpsys 全闲但 kernel cdev 激活 | L3 | dumpsys 只覆盖框架层设备，**以 sysfs cdev 为准** |

### Step 3：分支处置

**动态 ceiling drift（疑似 L3 热票，根因 OPEN）**

- 做：等（时段不可控）；分段矩阵 + 段间限额检查；**拔充电线**
  （PMIC/充电域是常见驱动源；adb-over-USB 会先断，插回即重
  连）；钳制值与最热 zone 入档。
- 不做：写 `scaling_max_freq`（§3.4 已证无效）；停/抑制
  thermal（红线）；用 Perf2 注高票对冲（污染测量基线，§6.3）。

**L4 Perf2 失效（handle 有了，节点没变）**

按 §6.2 的决策树执行，不要跳步：UID 1000/SID 差分 → 补齐
`openat2/writev` 的干净 strace → 可信 caller 正对照 → 确认
PowerOpt 锁 resource array → 二进制 strings/XREF 或 uprobe 定位
ApplyOpt 条件 → 最后才受控释锁。任何一步都不从"正 handle"宣称
生效。

**测量门禁报 `cpufreq-max-mismatch` / `state-drift`**

这是 fail-closed **正常工作**：环境被外部（thermal/vendor/其他
实验）改变时拒绝测量。处置 = 找漂移源（回 Step 2）+ 冷却/等
待/分段；**不要放宽门禁**——它在 2026-09-28 拦下过两次真实热
钳位（§6.1）。

---

## 5. 调试与取证手段（工具箱）

以下手段在案例 A/B 中全部实战使用过。按"证明什么 → 怎么做 →
怎么读"组织；取证层次从无侵入观察到动态探针递进。**没有日志与
快照的归因都是猜测——先取证，再下结论。**

工具选择（原文实战总结）：**strace** 看路径与 write buffer（决
定性）；**ftrace** 低侵入、长窗口交叉验证；**simpleperf** 采样
粗筛（微秒级关键路径会漏，须 ≥1 kHz + 重复请求）；**uprobe**
做函数命中终验；**logcat/dmesg** 做归因旁证；**sysfs 采样** 与
**dumpsys** 做环境基线。任何单一工具的"没看到"都不构成结论。

### 5.1 ftrace / tracepoint：内核事件的硬时间线

- **证明什么**：频率帽变化的确切时刻与持续时长（唤醒 boost 窗
  口）、与 PERFD 活动的时间相关性。
- **怎么做**（配方源自操作手册 §32–35）：先查能力——
  `available_tracers`、按 `syscalls:` / `binder:` / `power:` /
  `thermal:` grep `available_events`；然后按需二选一：
  - *系统事件*（`power/cpu_frequency`、`power/cpu_idle`、
    `thermal/thermal_temperature`）：清 trace → 逐项
    `echo 1 > events/<E>/enable` → 触发 → 停 → 读 trace → 逐项
    关回；
  - *指定进程 syscall*（如 Perf HAL 全线程）：把
    `/proc/<pid>/task/*` 的 TID 逐个写进 `set_event_pid`，
    enable `syscalls/sys_enter|exit_(openat|openat2|write|writev|
    pwrite64)` 后 `tracing_on=1`，事后清空 `set_event_pid`。
  限制：新建 TID 不在初始 `set_event_pid` 列表；syscall
  tracepoint 通常看不到 write buffer（buffer 取证靠 §5.2）；
  **不要全局开 `sched_switch`**（数据量爆炸，需要时短窗口 +
  filter）。§3.3 的唤醒 boost 证据来自灭屏专题会话的
  `cpu_frequency_limits` 捕获。
- **怎么读**：同类事件时间戳相减得窗口时长；与 perfd 线程活动
  行的时间差只给出"相关"，不等于"唯一上游"（上游还可能是
  Power/Display、MiPerf、PowerKeeper、SystemUI、Camera 等）。
- **案例**：§3.3 的两个 ~3 s 窗口与 1.1 ms PERFD 相关。

### 5.2 strace 服务端取证：把"没生效"证明成"没执行"

- **证明什么**：区分"请求被拒绝执行"与"执行了但无效"——案例
  B 的决定性证据。
- **怎么做**（逐字配方；基础版本机已实证 attach 48 线程）：

```bash
adb shell 'su -c "
PID=\$(pidof vendor.qti.hardware.perf2-hal-service)
OUT=/data/local/tmp/perf_hal_strace.txt
rm -f \${OUT}*      # -ff 产生 OUT.<TID> 系列，必须通配删除
strace -ff -p \$PID -s 256 -tt -T -yy \
  -e trace=openat,open,close,write,pwrite64 -o \$OUT
"'
```

  增强版追加 `openat2,writev`（`-s 512`，本机待跑）。提取顺
  序：先 grep 目标节点名（应**零命中**），再 grep
  `EACCES|EPERM|EINVAL|ENOENT|EROFS`（应零命中），最后 grep
  `write(|pwrite64(|writev(` 并去掉 trace_marker——只剩
  perflock_records 记账写 = 未进 Apply。判读表：只有 records →
  未进文件 Apply；EACCES/EPERM → 节点权限；EINVAL →
  formatter/parser 不匹配；写后被还原 → 被 restore/更高 vote
  覆盖；无目标 syscall 但 uprobe 命中 ApplyOpt → alternate
  backend 或提前返回。
- **怎么读**：服务端只有 `/proc/perflock_records` 的记账写、
  没有目标节点 open/write → 请求未进 Apply 路径；同时确认无
  EACCES/EPERM/EINVAL/ENOENT/EROFS，才能说"不是写失败"。
- **配套**：`/proc/<pid>/fd` 快照——确认 daemon 没有长期持有
  目标节点 FD（否则"没看到 open"可能只是早就开着）。
- **案例**：§3.6 handle 1535 的 records-only 证据。

### 5.3 /proc 文件系统取证

- `/proc/<pid>/maps`：取 daemon 加载的 vendor 库清单 → 反汇
  编对象列表（§6.2 P2）。
- `/proc/perflock_records`：perf 锁 acquire/release 生命周期；
  未配对 acquire = 有持锁方，按 pid 追 owner（注意 PowerOpt
  INT_MAX 锁是系统常态，见 §3.6）。
- `/proc/perflock_exception`：perf 锁异常记录（与 records 互
  补；异常为空本身也是证据）。
- `/proc/sys/walt/*`：WALT 层节点基线与变化（§3.5）。
- `su <uid> -c id`：验证差分身份构造（如 uid=1000(system) +
  gid=0 + context=ksu）。

### 5.4 ELF / 二进制静态分析

- **证明什么**：二进制的实现结构（类/函数/字符串）→ 定位仲裁
  与 Apply 条件的候选位置。
- **怎么做**：`nm -D` / `readelf -sW` 看导出符号（如 perf
  client 的 `perf_lock_acq` 等）；`strings -a` 检索
  `Request::Process` / `ResourceQueue` / `ApplyOpt` / `pending`
  / `priority` / `caller` / `hardening` / `whitelist` /
  `no optimizations` / `invalid request`；`objdump -d` 或
  Ghidra/IDA 做 XREF。
- **怎么读**：符号表只证明"符号存在"，**不证明参数原型**——
  ABI 候选必须经真实调用方反汇编或有限时调用验证；stripped
  库退化为字符串 + 导入表分析。
- **案例**：§3.8 client 库导出表；§6.2 P2 检索词表。

### 5.5 OEM XML 考古

- **证明什么**：厂商资源的静态地图（hint id、opcode、target
  匹配、资源值）。
- **怎么做**：`grep -rn` 检索 `/vendor/etc/` 下的
  `perfboostsconfig.xml` / `commonresourceconfigs.xml` 等；按
  `Id="0x00001091"` / `Target="pineapple"` / `sched_fmax_cap`
  等关键字定位。
- **怎么读**：XML 存在 ≠ 运行态启用（可能有 feature gate 或
  初始化失败）；注意单位陷阱（cluster 资源 MHz vs fmax_cap
  kHz）与尾部相似的 opcode（§3.7）。
- **案例**：§3.7 资源全图。

### 5.6 动态函数级探针（uprobe / simpleperf / 断点）

- **证明什么**：把根因从"高概率推断"升级为"代码条件实锤"——
  对函数入口/出口计数并按 caller 分类。
- **怎么做**（配方就绪，本机【未实操】）：
  - *支持检查*：`ls \$TR/uprobe_events \$TR/events/uprobes`、
    `grep -i uprobe /proc/kallsyms`、`zcat /proc/config.gz |
    grep -i uprobe`（若有 config.gz）、能力普查见 §5.12；
  - *函数偏移*：非 stripped 库 `readelf -Ws <lib>` 取符号地
    址；stripped 退化为反汇编定位；
  - *挂点*：`Request::Process` entry/exit、
    `ResourceQueue::Add/Pend`、`ApplyOpt`、`ResetOpt`、
    node-write wrapper；三类 caller（KSU-UID0 / KSU-UID1000 /
    可信 caller）对照计数；
  - *采样粗筛*（simpleperf）：`simpleperf record -p \$PID -g
    --duration 10 -f 1000 -o <out>` 后 `simpleperf report --sort
    comm,pid,tid,dso,symbol`——微秒级关键路径纯采样会漏，须
    ≥1 kHz + 重复请求，**命中确认仍用 uprobe**。
- **怎么读**：请求在 entry 出现而 ApplyOpt 不触发 → 抑制点在
  两者之间；与 §5.2 的 syscall 证据互相闭环（无目标 write 但
  ApplyOpt 命中 = alternate backend 或提前返回）。

### 5.7 差分实验设计（一次只改一个身份字段）

- **UID 差分**：`su 1000 -c <binary>`（已验证可造
  uid=1000(system) + gid=0 + context=ksu）。判读矩阵：节点生
  效 → 强烈支持 UID 准入；handle 变失败 → UID 影响入口准入；
  正 handle 但不生效 → 排除简单 UID-only gate。
- **可信 caller 正对照**：选**可恢复**的系统行为（电源模式/
  省电模式/刷新率切换），同步 strace Perf HAL——可信 caller
  触发目标写 = caller 身份问题；只触发其他资源写 = 该资源运
  行态/仲裁问题；全部无写 = Perf HAL 可能只记账、另有 apply
  后端。
- **纪律**：一次只改一个变量；不向 PowerOpt 进程注入；受控释
  锁只在拿到锁明细 + 确认自动重建 + 备好超时回滚之后（§6.2
  P3）。

### 5.8 节点直写验证（证明"路是通的"）

- **trap-restore 直写 idiom**（原文 §13 配方，partial-halt 已
  【实证】）：

```bash
adb shell 'su -c "
NODE=/proc/sys/walt/sched_max_freq_partial_halt
OLD=\$(cat \$NODE)
restore(){ echo \$OLD >\$NODE; }
trap restore EXIT INT TERM HUP
echo 1000000 >\$NODE; cat \$NODE; sleep 0.3; restore; cat \$NODE
trap - EXIT INT TERM HUP
"'
```

  证明：节点存在 + parser 接受 raw kHz + 权限够 + 无后台秒级覆
  盖；**trap 保证中断也必恢复**。**不证明** daemon 域也能写
  （§3.6）。多字段向量节点（`sched_fmax_cap`）在确认
  formatter/映射前**禁止**直写。
- **证明的是**：节点存在 + parser 接受 + 权限够 + 无后台秒级
  覆盖。**不证明** daemon 域（vendor_hal_perf_default）也能
  写——那是另一条证据链。
- **用途**：把"节点不可写"从嫌疑列表划掉，火力集中到服务路
  径（§3.5、§3.6）。

### 5.9 日志取证（logcat + dmesg）

- **触发**：dlopen/Binder/hint 调用失败的归因；thermal/perf
  异常的背景排查。
- **怎么做**：先 `adb logcat -b all -c` 清**全部** buffer
  （只 `-c` 会漏其他 buffer，后续 `-b all` 读取时混入历史）；
  `logcat -b all -v threadtime` **窄过滤**（`ANDR-PERF|PerfGlue|
  PerfModule|perflock|Qindx|applyopt|hardening|whitelist|caller|
  avc:|denied`）做 Perf 内部归因；宽过滤（`resource|request|
  apply|write|uid`）只适合做系统时间线；dmesg 侧 grep
  `avc:.*denied|vendor_hal_perf_default|ksu`。
- **陷阱**：无 AVC **不能**完全排除 SELinux（`dontaudit` 可能
  隐藏拒绝；初始化失败可能在服务启动阶段）；`AIBinder_
  linkToDeath` 类警告在 Binder/handle/release 全成功时不是根因。
- **归因顺序（不许跳步）**：linker namespace → 依赖库缺失 →
  SELinux → Perf HAL 权限 → ABI → hint id/type。
- **案例**：§3.8 风险清单的配套手段。

### 5.10 sysfs 周期采样与 dumpsys（环境状态）

- **频率基线**：周期读 `scaling_max/min/cur_freq` 建立稳态/
  瞬态图景——单次读取不足为证（§P8）。
- **dumpsys**：`thermalservice`（thermal status、传感器）、
  `battery`（充电状态）、`deviceidle`（Doze）、`power`
  （wakefulness）。
- **陷阱（本仓实战）**：dumpsys 只覆盖 Android 框架层冷却设
  备；**kernel cdev 激活状态以 sysfs 为准**——案例 A 中
  dumpsys 全闲而 `cpu-cluster3` cdev state=3/34（§6.1）。
- **cached 温度陷阱**：`dumpsys thermalservice` 输出里的
  cached 温度字段**不是实时值**（实测：cached 显示 CPU7
  89.9 °C / NSP ~55 °C 时，Current HAL 温度只有 CPU7 31.9 °C
  / NSP ~31 °C）——判读温度必须区分 cached 与 Current HAL，
  详见 §6.1 第 5 条。

### 5.11 受控状态迁移杠杆（亮灭屏 / WiFi / 飞行模式）

三层价值：测量卫生（三者都是已知扰动源）、可复现刺激源（验证
控制链在动）、**仪器阳性对照**——先用"亮屏必现 ~3 s boost
窗"证明 ftrace/采样链路是通的，再用它测未知（同 P0 正向控制
思想）。命令源自操作手册 §28–30（原文标 TODO；键码/服务均为
Android 标准接口，本机现场验证后再升【实证】）。

**亮灭屏**（用确定性键码，**不用**状态翻转的 `input keyevent
26`）：

```bash
adb shell 'su -c "
input keyevent 223   # KEYCODE_SLEEP 灭屏（确定性）
sleep 2
dumpsys power | grep -iE \"Wakefulness|mWakefulness|mInteractive\"
input keyevent 224   # KEYCODE_WAKEUP 亮屏
sleep 2
dumpsys power | grep -iE \"Wakefulness|mWakefulness|mInteractive\"
"'
```

判读：亮屏后 ~0.17 s 内 `cpu_frequency_limits` 应出现 boost 上
限、~3.0 s 后回落（§3.3）——看不到这个已知响应，先怀疑仪器
而不是怀疑设备。锁屏界面可用 `wm dismiss-keyguard`；**不要自
动输入设备密码**。

**WiFi**（异步过程，先存状态、三处确认、按快照恢复）：

```bash
WIFI_OLD=$(adb shell settings get global wifi_on | tr -d '\r')
adb shell 'su -c "
svc wifi disable; sleep 4
settings get global wifi_on
dumpsys wifi | grep -iE \"Wi-Fi is|WifiState|mWifiEnabled\" | head -5
svc wifi enable; sleep 6
settings get global wifi_on
"'
# 结束按 WIFI_OLD 恢复
```

`settings`、`dumpsys wifi`、驱动稳定状态三处对齐才算迁移完
成——单次读取不算数。

**飞行模式**（首选 `cmd connectivity`，回退 settings +
broadcast；**只能 USB adb**——WiFi adb 必死）：

```bash
AIR_OLD=$(adb shell settings get global airplane_mode_on | tr -d '\r')
adb shell 'su -c "
cmd connectivity airplane-mode enable; sleep 5
settings get global airplane_mode_on
cmd connectivity airplane-mode disable; sleep 5
settings get global airplane_mode_on
"'
# cmd 不可用时回退：
# settings put global airplane_mode_on 1|0
# am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true|false
```

与本仓 quiet-state 流程的关系：这三项就是安静态 profile 管理
的对象（screen_on=false、airplane 观测、唤醒瞬态等待）——实
验前确认迁移完成 + 瞬态结束，实验后按快照恢复。

### 5.12 调试能力普查（动手前的清单）

新设备/新会话先跑一轮能力普查，不假设工具存在（原文 §10 配
方）：

```bash
adb shell 'su -c "
for T in strace simpleperf perf atrace perfetto trace-cmd bpftool \
         gdbserver lsof toybox strings readelf objdump nm; do
  printf \"%-12s: \" \$T; command -v \$T 2>/dev/null || echo MISSING
done
for D in /sys/kernel/tracing /sys/kernel/debug/tracing; do
  [ -d \$D ] && echo \"tracefs: \$D\"
done
for F in /proc/sys/kernel/perf_event_paranoid \
         /proc/sys/kernel/kptr_restrict \
         /proc/sys/kernel/yama/ptrace_scope; do
  [ -e \$F ] && { printf \"%s=\" \$F; cat \$F; }
done
ls /proc/kallsyms /sys/kernel/btf/vmlinux 2>/dev/null
"'
```

本机已知【实证】：`/system/bin/strace`、`su`、`run-as` 存在；
`setpriv` 不存在；core PMU `type=8` 可 shell 计数、LLCC
`type=9` 需 root（本仓平台画像）。其余按普查结果登记。

---

## 6. 案例档案

### 6.1 案例 A：测量实验遭遇动态 cpufreq ceiling drift（本仓，2026-09-28；根因 OPEN）

背景：P0″ demand/prefetch 复测，长训练矩阵（512 圈 × 56 case，
controlled-baseline，governor=performance）。

时间线：

1. **drift #1（02:44–02:46Z）**：long-base 在 b1024K-seed20260928
   后置门禁失败：`policy2/5 max 2707200→2630400、policy7
   2745600→2688000`，CPU 峰值 52.6 °C。runner fail-closed 中止
   后续 25 case 并恢复 governor（结构化失败记录在
   `20260928T024353Z` run）；数分钟后限额自行恢复。前置 31
   case 门禁在各自测量时刻有效，数据保留。**事发时未采集
   cooling-device 状态（取证缺口）**。
2. **应对**：长训练矩阵拆为 r2a（16 case）+ r2b（12 case）两
   段，段间冷却检查；两段 100% ok 完成。
3. **drift #2（02:52Z）**：short-thp 前置门禁失败
   （`policy2/5=2572800、policy7=2630400`，CPU 46.9 °C），8
   case 未产生测量；governor 恢复成功。
4. **持续 drift（≥40 分钟空载）**：`scaling_max_freq` 未回画像
   值。thermal status=0、冷却设备（Android 层）空闲、电池
   28.9–32.2 °C；但 kernel 侧 `cpu-cluster3` cdev 激活
   （state 3/34），GPU cdev 激活（4/11）；最热 zone =
   `pm8550b_lite_tz`（PMIC/充电域，54.4 °C），CPU 已凉
   （32–38 °C）。
5. **cached 温度陷阱（复审更正）**：本文原记"一组 NSP 传感器
   40 分钟冻结在 54–61 °C"——那是 `dumpsys thermalservice` 的
   **cached 字段**（复审实测：cached 显示 CPU7 89.9 °C / NSP
   ~55 °C 时，Current HAL 温度只有 CPU7 31.9 °C / NSP ~31
   °C）。cached 不可当实时值；**NSP 因果关系不定案**。

判别与处置（§4 流程的实战）：

- `sched_fmax_cap` = 基线（PRIME=INT_MAX）→ **L2 干净**【实证】；
  cpufreq max 被动态下调 + 事后 ~40 min 观察到 cpu-cluster3
  cdev state=3/34 与 PMIC 域 54.4 °C → **疑似 L3 热票**【推断】；
  但事发时未采集 cooling-device 状态，且 NSP/cached 读数不可
  靠——**根因保持 OPEN【未证】**。
- 插着充电时被动降温慢、释放时间不可预测（运维观察，与驱动
  源无关的实操结论）。【实证】
- 正确处置：分段矩阵、冷却检查点、等/拔充、门禁保持
  fail-closed、THP 段登记触发条件推迟（限额回画像值且稳定
  ≥5 分钟）。
- 未做的事及原因：写 sysfs（§3.4 已证无效）、抑制 thermal
  （红线）、Perf2 注高票（§6.3）。

### 6.2 案例 B：向上解锁硬件 OPP（外部调查，2026-09-28，进行中）

目标：解除 L1 稳态 cap 达到 L0 OPP。当前进度（原文照录）：
Binder/ABI/参数 95%、opcode/映射 95%、节点可写性 90%、
acquire/release 生命周期 100%、ApplyOpt 未执行 90%、根因大类
70–80%、精确代码条件 45–60%。

已证（§3.2–3.8 已内联）：三层频率状态；唤醒 boost ftrace；
AOSP 模式/sysfs/min-only 三路径无效；Perf2 资源地图与 client
ABI 候选；正 handle 只记账；节点可直写；PowerOpt INT_MAX 锁
存在。

未证：`0x1091` 对现存低 cap 的仲裁效果；`0x7fffffff` 语义；
低 cap 唯一 owner；仲裁模型（值比较 vs client 优先级分层）；
`/data/local/tmp` 进程经 namespace/SELinux 调 vendor 库的可行
性；灭屏长时锁频稳定性。

后续实验计划（P0–P3，严格顺序）：

1. **P0 UID 差分**：同一 binary/SID，仅 UID 0→1000（`su 1000
   -c`，已验证构造可行）。节点生效→强烈支持 UID 准入；正
   handle 但不生效→排除简单 UID-only gate。同步补
   `openat2/writev` 干净 strace。
2. **P1 可信 caller 正对照**：选可恢复的系统行为（电源模式/
   省电模式/刷新率切换），strace Perf HAL，看可信 caller 是否
   触发目标节点写。区分"caller 身份问题"与"resource 本身问
   题"。
3. **P1 确认 PowerOpt 锁内容**：dumpsys 接口 → vendor debug 节
   点 → PowerOpt 配置 → 动态跟踪其换锁的 Binder 调用 → 解析
   resource 数组。当前不建议直接 `perf_lock_rel(1528)` 或杀
   poweropt-service。
4. **P2 定位实现库**：`/proc/1682/maps` 取 vendor 库，strings/
   readelf/nm/objdump/Ghidra XREF 检索 `Request::Process` /
   `ResourceQueue` / `ApplyOpt` / `pending` / `priority` /
   `caller` / `hardening` / `whitelist`；回答 handle 在哪步分
   配、caller 检查在哪步、ApplyOpt 触发条件、priority 来源。
5. **P2 动态函数级探针**：uprobe/simpleperf/断点对
   `Request::Process`、`ResourceQueue::Add/Pend`、`ApplyOpt`、
   `ResetOpt` 计数，比较 KSU-UID0 / KSU-UID1000 / 可信 caller
   三类——把根因从推断提升为代码条件实锤。
6. **P3 受控移除 PowerOpt 锁**：仅在已取锁明细、确认自动重建、
   备好恢复动作与超时回滚后执行；移除后 KSU request 开始落
   节点 = priority/exclusive ownership 实锤。

成功判据（任一即闭环）：caller admission（改单一身份字段 →
no-write 变 write）；priority（确认 PowerOpt 持同资源 + 降其
vote → 原请求进入 Apply）；resource inactive（定位并修复
feature gate → write 出现）；实现缺陷（定位代码条件/空
handler → 修复后节点按预期变化）。

### 6.3 A/B 对照（为什么不能合并解决）

| 维度 | A（恢复稳态） | B（解锁 OPP） |
|---|---|---|
| 目标 | 回到已知的 L1 稳态 | 越过 L1 到 L0 |
| 机制方向 | 等 ceiling drift 释放（被动） | 往 L4 注入更高票（主动） |
| 正确解法 | 等/拔充/分段实验/门禁不动 | 严格顺序的单变量实验（§6.2 P0–P3） |
| 错误解法 | 写 sysfs、压 thermal、注高票 | 叠加高 request、停全部 perf 服务、禁 thermal |
| 对测量的影响 | 恢复即恢复基线 | 会改变被测工况（须另立 profile 与锚点） |

**结论**：B 对 A 的参考价值在方法论（分层模型 + 单变量实验纪
律），不在解法。A 不等 B 解决；B 也解决不了 A（min() 下热票
照样优先，§P2）。

---

## 7. 未决问题登记（触发条件 → 下一步）

1. `0x1091` 对现存低 cap 的仲裁效果 → 案例 B 阶段三有限时实
   验（外部项目；调用链与取证配方已就绪，尚未执行）。
2. PowerOpt INT_MAX 锁的 resource array → §6.2 P1（按 pid 过滤
   records 的取证命令已就绪；锁内容确认未做）。
3. Perf2 仲裁模型（值比较 vs 优先级分层）→ §6.2 P1/P2（双向
   value 夹逼已排除单纯 comparator 方向【实证-阴性】；strace
   增强版 `openat2/writev` 与 UID-1000 完整实验均待跑——UID
   1000 身份构造已【实证】可行）。
4. `sched_fmax_cap` 四字段 ↔ policy 映射 → 单资源刺激实验
   （该节点为多字段向量，确认 formatter/映射前**禁止**直写）。
5. ceiling drift 的驱动域（PMIC/充电域为候选【推断】）精确阈
   值与 hysteresis → 本仓 THP 补跑前后，以 Current HAL 温度 +
   cooling-device 状态 + 限额联动采样补齐（运维观察；cached
   字段禁用）。
6. ~~NSP 传感器读数来源~~ → 已由 cached 温度陷阱解释（§6.1
   第 5 条）：`dumpsys thermalservice` 的 cached 字段不可当实
   时值，NSP 因果不定案【实证-阴性】。
7. adb-over-WiFi 作为"拔充实验"的传输 → 需要时立项（改传输
   须用户批准 + 更新 `data/private/hosts.md`）。
8. 灭屏长时锁频稳定性（partial wakelock + Perf 资源 + 无
   suspend）→ 案例 B 阶段六灭屏闭环（外部项目）。

---

## 8. 红线（两边合并）

- 永不停止/抑制 thermal HAL、thermal-engine、PMIC/电池/充电器
  保护、emergency shutdown。
- 测量实验的 cpufreq limits 只观测不写入；unlock 类实验（案例
  B）必须与测量实验时间错开，且 release 干净（本仓门禁
  fail-closed 会兜底拦污染）。
- 不叠加高 max request 硬顶低 cap；不一次停多个 perf 服务（无
  法归因，可能留下未释放 request）。
- 不从正 handle / write_ok / 单次回读宣称"已生效"；生效判定
  必须见 §4 Step 2 的多层证据。
- 不把 OPP 解锁工况混入既有测量基线（锚点全部作废的代价）。

---

## 9. 出处

- 原始调查文档（已按原文归档入本仓 `docs/reference-materials/`，
  仓外 `cpu-uarch-ref/` 为原件；全部关键证据已内联于本文）：
  `Android灭屏最高频锁定实验与证据链.md`（v1.1）、`Qualcomm
  Perf2 Resource Apply Failure - Root Cause Investigation.md`、
  `Qualcomm Perf2 HAL 资源不生效根因分析与手工调试完整手册.md`
  （Final Consolidated Edition）——均 2026-09-28、进行中状态；
  其状态标记（VERIFIED / VERIFIED-NEGATIVE / TODO /
  RECONSTRUCTED）与本文证据等级的对应：VERIFIED→【实证】、
  VERIFIED-NEGATIVE→【实证-阴性】、TODO→【未证】、
  RECONSTRUCTED→【静态/推断】。
- 本仓：`docs/reviews/2026-09-28-sm8650-x4-p0prime.md`（§5 热
  钳位事件）、`configs/platforms/redmi-k70pro-01.json`
  （`freq_domains`/`environment_control_note`）、
  `docs/runbooks/redmi-controlled-quiet-state-v2.md`（安静态门
  禁）、`docs/runbooks/redmi-manet-kernelsu-root.md`（root 通
  道）。
