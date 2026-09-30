# SM8650 TLB r2 · 上板前环境与冒烟清单（M0-5 前置）

> 日期：2026-10-01。状态：**待执行**（M0 代码侧收口后首板上板用）。
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
CXX=$NDK/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android34-clang++
# 证据管道探针（主线纪律，配置走 configs/）
cmake --preset android-arm64-release && cmake --build --preset android-arm64-release
# 冒烟专用（原型 v2.3，仅 §5.2 合法性边界内使用）
$CXX -O2 -Wall -Wextra -Werror -static -o l2_set_probe \
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
