# SM8650 TLB 三个位字段对照：第一轮探索

## 本次任务的目的（给人类看）

用5个小条件检查真实X4是否出现可区分H1–H4的冲突/分散信号，并量清外围采集成本。不求这一轮确定ways、完整hash或正式H*。用户已确认原上板Agent停止，由当前Agent端到端执行。

## 固定设计与边界

已有 `probes/cache-mem/ptr_chase.cpp`，4KiB页、pool65536、target200、r20（19有效轮）、F512、seed42；每条件5个独立进程，不延长热循环。顺序预先定为 floor→A→scatter→B→C。

| 条件 | H / regions / scope / W / scatter | H1/H2/H3/H4下每set最大目标页数 |
|---|---|---|
| floor | 1 / 4 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| A | 1 / 4 / 0 / 12 / 0 | 12 / 1 / 12 / 1 |
| scatter | 1 / 4 / 0 / 12 / 1 | 1 / 1 / 1 / 1 |
| B | 1 / 12 / −1 / 12 / 0 | 12 / 12 / 1 / 1 |
| C | 2 / 4 / 0 / 12 / 0 | 1 / 12 / 1 / 12 |

分区预测来自 `probes/common/tlb_set_layout.h`、`probes/common/tlb_set_collect.h`，推演及限制见 `docs/reviews/2026-10-09-probe-first-reassessment.md`。表中数字不是PMU计数预测。相关PMU沿用cycles(0x11)、L1 refill(0x05)、L2 refill(0x2d)、L2 access(0x2f)，type8；不在这轮增加事件或改窗口。

本轮为独立的 `exploration-stock-walt-v1` 条件：保持当前walt governor，不切换全簇performance，不改变min/max、不停止热服务；按 `runner/environment/android_state.py` 在case前后采集原有完整状态。沿用charging-thermal的quiet条件和baseline cap检查，但governor期望显式为walt。只证明观测端点状态，不声称窗口内频率恒定；不把本轮ns当作最高频延迟。

## 执行与留痕

1. 确认单设备、没有探针进程、journal全终态；核对root、4096页与cpu7 MIDR。
2. 独立NDK重编并核对本机/设备SHA256。正确宏为 `CPU_UARCH_HAVE_LINUX_PERF=1`，不是 `CPU_UARCH_HAVE_PERF=1`：

```bash
NDK_CC=/Users/michaelyao/Library/Android/sdk/ndk/27.2.12479018/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android34-clang++
"$NDK_CC" -O2 -Wall -Wextra -Werror -static -DCPU_UARCH_HAVE_LINUX_PERF=1 \
  -Iprobes/platform/linux -Iprobes/common probes/cache-mem/ptr_chase.cpp \
  probes/platform/linux/perf_counter.cpp -o /private/tmp/sm8650-ptr-chase-recipe-20261009
```

本次独立重编与原本机/设备产物逐字摘要一致：`54d105930b8743e7a3a69c31d7e640cdec1044a0276a5f040efff4b1dc82398c`。

3. 从既有专用配置生成5份独立探索spec，写入私有实验目录保存完整输入，不修改正式配置。保持实际planner→runner/adapter→raw/record生产链；每份plan为1case/5reps，逐case执行。输入、脚本、代码/二进制摘要、完整stdout/stderr和真实退出状态保存；不接tail管道。
4. 任一case失败/环境变更/无有效轮/mux/geometry或fallback异常即停止，不继续后续点；失败仍留空metrics及结构化原因。成功case逐样本核对realized和窗口，记录L1/L2事件分布及环境。
5. 执行后复核系统状态和journal，原始数据及输入保存在 `data/private/`，不自动提交测量数据，不修改旧run或冻结工件。

当前r2另有他人 `.gitignore` 修改。探索如记录dirty=true，要如实保留；通过独立编译摘要证明实际探针，不宣称满足旧正式clean-source合同。

## 如何解读与下一步

先报告5个条件的5个原始观测值、中位数、有效轮、L1/L2响应与状态，不选择on阈值、不输出正式H*。若三轴未产生预测的方向，优先检查访问是否暴露到L2、filler、页表中间项和窗口背景，而不是增加重复次数。若出现清晰签名，仅称支持某候选的初步行为证据；再用第二target、反序/新epoch和匹配对照尝试推翻。

已有48/48/32 A1合同保持独立。是否继续其正式矩阵或采用新的确认设计，在探索结果后决定；未完成L1不拼接。ALU/FPU探针设计可以并行推进，设备采样仍串行。
