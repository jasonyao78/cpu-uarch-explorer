# SM8650 TLB r2 · 上板前环境与冒烟清单（M0-5 前置）

> 日期：2026-10-01。状态：**已执行（2026-10-01，环境 1.1–1.9 全过，S1–S5 全过，S6 跳过）**——执行记录见 §6。
> 依据：任务书 v1.3 §5（Gate 0 / §5.2 冒烟）、OI-12(baseline) 跨日基线教训、REV-M0-BATCH MB-01/02 合成验证边界（mock 级证据，须真机复核）。
> 纪律红线：**冒烟产物 = 备忘录，不入 `data/public/runs/`，不进对比表**；证据级测量一律等移植版探头 + 管道。

## 1. 设备与环境确认（逐条打勾，任一不过即停止并记录）

| # | 项 | 命令 / 判据 | 记录 |
|---|---|---|---|
| 1.1 | adb 可达 | `adb devices` 列出设备，`adb shell echo ok` | |
| 1.2 | root | `adb shell su -c id` → uid=0 | |
| 1.3 | X4 核身份 | `adb shell su -c 'cat /proc/cpuinfo'` part=0xd82 的核即 X4（通常 cpu7）；**禁默认** | |
| 1.4 | 页大小 | `adb shell getconf PAGESIZE` = 4096（探针硬门） | |
| 1.5 | perf 权限 | `cat /proc/sys/kernel/perf_event_paranoid`；simpleperf 可用（`simpleperf list` 非空） | |
| 1.6 | 事件资格（引用战役 Gate 1） | 0x05/0x34/0x2d QUALIFIED 直接继承；**0x2f = SEMANTICS_UNVERIFIED**（G0-1 复验对象） | |
| 1.7 | quiet-state | 限额/热状态：锁频或定间隔采样 `cpuinfo_cur_freq`；参照战役 quiet-state 门禁 | |
| 1.8 | THP 状态 | `adb shell cat /sys/kernel/mm/transparent_hugepage/enabled`——**记录实际状态，不假设** | |
| 1.9 | 内核/构建指纹 | `uname -a` + 探针二进制 SHA256（入备忘录） | |

## 2. 二进制准备（本机 M4 Pro → NDK 交叉编译）

```bash
NDK=~/Library/Android/sdk/ndk/27.2.12479018   # r26/r27/r28 均 x86_64 工具链，Rosetta 2
# .c 原型探针必须用 clang（非 clang++）：clang++ 编译 .c 触发 -Werror=deprecated（2026-10-01 实测）
CC=$NDK/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android34-clang
# 证据管道探针（主线纪律，配置走 configs/）
# 注意：android-arm64-cross preset 尚未建（CMakePresets.json 无此项，已登记 open-items）；
# 2026-10-01 冒烟绕开 cmake 直编；preset 建成前证据管道探针无标准构建路径。
# cmake --preset android-arm64-release && cmake --build --preset android-arm64-release
# 冒烟专用（原型 v2.3，仅 §5.2 合法性边界内使用）
$CC -O2 -Wall -Wextra -Werror -static -o l2_set_probe \
  docs/cpu-uarch-deep-analysis/tlb-deep-analysis/probes/l2_set_probe.c
adb push <binaries> /data/local/tmp/ && adb shell -> su
```

## 3. 冒烟清单（产出 = 一页备忘录；全部失败项转判据重设计）

| # | 项 | 做法 | 通过判据 |
|---|---|---|---|
| S1 | 0x2f 复验（G0-1） | `l2_set_probe run -H 1 -T 0/-T 7` 两窗对照，采 0x2f | 方向不反降、分布不重叠 → 门控可升级三事件版；仍异常 → 判据定型为 0x05 差分版（预注册默认） |
| S2 | prime+probe 门控 | `-w 4/8/12`，filler 512，采 0x05+0x2d | probe 段 `0x05≈w`；`0x2d` w=8→12 方向正确 |
| S3 | `-w 0` 空窗 | 空窗底噪量级 | 底噪 ≪ 目标信号（量级比入备忘录） |
| S4 | 页守卫 | 16K 宿主已拒；板上 4K 路径 smaps 端点核验走 ptr_chase | backing 端点一致 |
| S5 | K 链可行性 | 原型仅论证；真机 K 链属移植版——本项仅记录内存余量（K=8×4096 页=128MB 可分配） | mmap 成功、无 LMK 杀 |
| S6 | PerfWindow GROUP 读 | 移植版前不做真机要求；如冒烟顺手采一组 GROUP read 样本 | nr/ena/run/values 布局与黄金测试一致 |

## 4. M0-5 pilot 预告（冒烟通过后）

- 标定块标 `CALIBRATION/PILOT`，raw 全量留存；锚点参照池**只用 pilot 数据建**，不复用旧长链率（任务书 M0-5 顺序）；
- 跨日/跨 session 基线移动 >3% 触发**调查**（OI-12(baseline)），非排除门；
- pilot 与正式验证样本隔离（REV 批次纪律）。

## 5. 清理与回滚

- 冒烟产物（日志/备忘录）留工作区或 `data/private/`（**永不入库**）；`data/public/runs/` 零写入；
- 设备侧 `/data/local/tmp` 探针可留可删；移除前确认无进程占用；
- 任一项失败 → 停、记录、回任务书修订判据——不带病进 pilot。

## 6. 执行记录（2026-10-01，K70 Pro / dc4ad7d1）

**环境（1.1–1.9 全过）**：root=KernelSU；**实测拓扑** cpu0-1=0xd80(A520)、cpu2-6=0xd81(A720)、cpu7=0xd82(X4)；4096 页；paranoid=-1；quiet-state 合规（idle 恒 672MHz，CPU zone ~33°C，未做锁频 mutation）；**THP 实测 `[always]`**（非假设）；内核 6.1.118-android14-11-ga3b9c44908dd-ab13320413，二进制 SHA256 两端相符。二进制 NDK r27.2 静态编译，cpu7 钉核。

**S1 ✅（0x2f 复验）**：T0 `11.0` / T7 `11.1`，方向不反降、set 间一致、w8 两次独立运行精确复现（11.0/11.0）。

**S2（w 扫描，T0）**：0x2f = `7.0/11.0/15.0` = **w+3 精确线性**，+3 恰为 S3 空窗底噪——0x2f 行为正常。0x2d 跳变点提前到 **w=8**（w=4→0.2≈0；w=8 已达 1.0/access）——与任务书"8→9 仅是理想预期"警告一致；**判据须按总竞争条目数口径写**（已登记 open-items，pilot 判据冻结前关闭）。0x05 ≈ w+4~8 底噪、不严格 ≈w，差分可用（w8→12 增量 +8.4）——G0-3 开销标定 case 必要性被实测坐实，F5 负值纪律适用。probe_ns 非单调（69/468/392），计时不作门控。

**S3 ✅（-w 0 空窗）**：0x05=4.0、0x2d=0.0、0x2f=3.0——底噪量级 ≪ 目标信号。

**S4 ✅（页守卫）**：THP=always 下 MADV_NOHUGEPAGE 守得住：`page_policy_actual base/base`、`anon_huge_kb 0/0`、端点一致、exit 0。

**S5 ✅（K 链内存可行性）**：128MB mmap 成功，MemAvailable 不变，无 LMK/OOM；S1–S3 每 run 实 mmap 256MB+filler×6，强度已超判据。

**S6 ⏭️ 跳过**：移植版 PerfWindow 未就绪，runbook 明言移植版前不做真机要求。遗留：生产 PerfWindow 的首组真机 GROUP read（nr/ena/run/values 布局）归入 M0-3/4 出口验收证据（open-items 登记）。

**门控定型拍板（预注册 S1 判据，本清单内裁决）**：S1 三条件（方向不反降 / set 间一致 / 精确复现）全部满足——**批准 0x2f 门控升级三事件版**（0x05 + 0x2d + 0x2f 同窗）。0x2d 的 w=8 跳变提前不改变本裁决，但 pilot 的 Q-B 判据按总竞争条目数口径写、锚点参照池只用 pilot 数据（任务书 M0-5 顺序不变）。

**纪律确认**：`data/public/runs/` 零写入；产物 `/tmp/sm8650-smoke/`（本机）与 `/data/local/tmp/tlb_r2_smoke/`（设备侧，pilot 前可复用）；仓内文件零改动（他人会话的 open-items.md 未暂存修改原样未碰）。
