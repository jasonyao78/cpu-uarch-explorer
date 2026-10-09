# 独立 A64 有效窗口探针 v0.2

## 本次任务的目的（给人类看）

验证长依赖锚点能否让年轻填充流积累成可观察的窗口限制。先测软件构造和并行/串行收益；不把指令数直接叫物理ROB容量。当前实施依据 `docs/design/2026-10-09-minimal-tlb-rob-probes.md`，旧骨架审计 `docs/reviews/2026-10-09-rob-probe-critical-reuse.md`。

## 构建与检查（从仓库根目录）

```sh
clang -O2 -Wall -Wextra -Werror -I probes/common \
  docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c \
  -o /private/tmp/rob-window-exporter
python3 docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/tests/test_rob_probe.py
# Android: NDK27.2.12479018，API34；使用 SDK 内 aarch64-linux-android34-clang
$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android34-clang \
  -O2 -Wall -Wextra -Werror -static -I probes/common \
  docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c \
  -o /private/tmp/rob-window-android
```

Host仅支持导出/契约检查，拒绝测量；不伪造macOS PMU。独立原型暂不接runner/schema/CMake，相关后续见 `docs/open-items.md` 的 OI-ROB-PROBE-20261009。

## 精确行为

- 函数参数 x0/x1 = chase头，x2 = hot缓冲，x3 = iterations；入口每次重装常量与 FP seed。
- 默认循环 `A → N filler → B → N filler → subs/b.ne`；N=0合法，每轮实际2N filler，无−2补偿。`--asymmetric`仅诊断旧布局。
- `--paired`在**同一allocation、同一随机排列**内重连独立双环/串行交替环，逐load地址相同；每轮交替模式先后。`--serial`单独运行时只能保证相对布局相同，跨进程VA/PFN不同。
- 每node一条64B cache line。全环链接检查，报告实际distinct lines、4K backing核验；不声称每次DRAM缺失。默认16MiB/131072迭代使一次调用覆盖全部节点。
- fsqrt锚点为d0，稳定operand=1.0；`--chain k`每侧k条，默认每轮16条。FADD目的d4..7，源d16/17；不覆盖v0、ABI保存v8..15或x18/x19..29。FPCR非0拒绝，以免隐式继承FZ/舍入配置。
- `--align 0|16|32|48`实际改变loop mod64；无伪入口jitter。`--write-asm file`输出全部生成字节及JSON config，不运行。
- PMU必传`--pin 7 --pmu-type 8`；默认cycles0x11/INST_RETIRED0x08，可追加事件。全部事件打开成功才测；GROUP+ID严格解析、共同启停、时间和counter增量，无效/缺失/mux直接命名失败。纯decoder位于 `probes/common/perf_group_read.h`。
- stdout为config/runtime/round JSONL；逐轮保存ns、完整整数counts、enabled/running、模式/顺序。失败为empty metrics + failure且非0退出。`--rawlog`可额外保存round原文，不作为runner record。

## 板上复现

当前单设备授权由本会话持有，其他会话运行前须确认所有者。统一驱动 `tools/diagnostic/run_sm8650_minimal.py`，只读环境、保存源码branch/HEAD、binary及生成码SHA；不会调governor/频率或停热服务：

```sh
.venv/bin/python tools/diagnostic/run_sm8650_minimal.py rob-qualify \
  --binary /private/tmp/rob-window-android --host-exporter /private/tmp/rob-window-exporter
# 资格核对后才运行rob-window；全部raw进入data/private/<timestamp>-<mode>/。
```

N=0包含锚点真实耗时；无锚点和hot控制保留独立曲线，不统一扣底噪。NOP融合、PRF/LSQ、前端供给及锚点长度敏感性未闭合前，仅报告有效窗口响应。384为第三方候选，不作验收条件。

## Single-shot小型冷line机制（2026-10-09）

循环64/128MiB的无编码/高位编码/bit20编码均未满足长load资格，完整报告 `docs/reviews/2026-10-09-canonical-load-results.md`。新机制单列 `probes/diagnostic/rob_cold_pair.c`，不重写本文件旧循环producer。协议与实施计划 `docs/design/2026-10-09-cold-pair-qualification.md`，driver `tools/diagnostic/run_sm8650_cold_pair.py`，consumer `tools/diagnostic/analyze_cold_pair.py`。

8KiB对齐自有两页、guard/实际4K；同映射mask0/4096的raw互链/自指，解码后同两line，冷/热和P/S/E三个角色。内部CNTVCT计时有完成屏障，whole-PMU wrapper不硬扣；不认证timer/cache维护原生执行、DRAM或物理ROB。先2mapping/3072窗只N0资格，成功后才另注册有限N扫描。host topology支持本机16KiB页，不能充当Android4KiB证据；target严格拒绝非4KiB。source与launchcommit分开记录在 `docs/reviews/evidence/2026-10-09-cold-pair/build.json` 和私有manifest，分支 `codex/sm8650-tlb-hierarchy-r2`。

```sh
clang -O2 -Wall -Wextra -Werror -Iprobes/common \
  probes/diagnostic/rob_cold_pair.c -o /private/tmp/rob-cold-pair-exporter
# 同NDK27.2/API34/静态/-Werror flags编译相对source路径，可重复构建核SHA。
.venv/bin/python -m unittest tools.diagnostic.tests.test_cold_pair_producer \
  tools.diagnostic.tests.test_cold_pair_driver tools.diagnostic.tests.test_cold_pair_analysis
# protocol/source/build/plan/consumer全部提交与独立审查后，根单操作者才执行：
.venv/bin/python tools/diagnostic/run_sm8650_cold_pair.py \
  --binary /private/tmp/rob-cold-pair-android --host-exporter /private/tmp/rob-cold-pair-exporter
```
