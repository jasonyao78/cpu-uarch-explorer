# 最小 TLB / ROB 探针实施计划

## 本次任务的目的（给人类看）

先获得可信、能被对照推翻的部件响应，再扩大框架。用户已批准延续 `docs/reviews/2026-10-09-rob-probe-critical-reuse.md` 的路线；手机由当前代理独占，TLB 与 ROB 采样串行。工作分支为 `codex/sm8650-tlb-hierarchy-r2`，起点 `d6fe032`。每次交付另列实际 commit 和二进制 SHA256。

## 实施与验证顺序

1. 在 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c` 保留 C mini-JIT。真实生成码测试先复现错误回跳、N=0拒绝及 FP 寄存器冲突，再修复。N 表示每段实际 filler 数，不做 N−2 补偿；循环 A→N→B→N，保留非对称诊断；显式 loop mod64 对齐。
2. 用同一随机排列的 cache-line 节点构造独立 A/B 环；serial 模式重连成 A_i→B_i→A_{i+1}，两模式每迭代实际读取相同地址，串行模式两次 load 共用 x0。检查环完整性，记录实际 line/page 足迹，不预设 DRAM miss。fsqrt 使用稳定 1.0、记录 FPCR、专属 v0；普通 FADD 用 v4..7，避开 ABI 保存集 v8..15。
3. 新增 `probes/common/perf_group_read.h`：C 可用 GROUP+ID 纯解码器，严格长度/事件身份/时间与值单调性检查。ROB 使用同一生产解码器，全部请求事件必须打开，显式 PMU type / kernel-hv scope，组启停；任何失败输出空 metrics 与命名原因。
4. Host 检查生成码、输入边界、decoder；NDK27.2/API34 静态交叉编译；目标机先 N=0 / hot / long / serial 锚点与计数核验，再有限 NOP/ADD/FSQRT 探索。未验证的 ROB 条目分配、融合、PRF/前端影响保留 OPEN。
5. 新增独立 `probes/diagnostic/tlb_local_pair.cpp`，复用 `probes/common/tlb_set_collect.h` 及已验证 PMU 能力；同映射一次按最大 W9 收集，然后仅使用其 prefix8/9。对照 H1/H2、F128/F512、页内 offset0/轮转64B、两种 filler 顺序。保存目标/填充地址和逐轮计数，验证 VPN 不变、嵌套成立；不修改正式 A1 合同或冒充 runner schema。
6. 最小板上预算：先 ROB 软件/锚点合格检查；TLB 固定 32 条件×5独立mapping epoch×19保留轮，另每epoch8个floor；先1个独立冒烟epoch，不入结果池，配对顺序预先交替；ROB 最多 40 条件×2进程×3轮。每条件前后只读检查基线环境、无 mux；失败停止，不补挑样本。不更改 governor、频率范围或热服务。任何未执行项登记 `docs/open-items.md`。
7. 原始日志及生成码放 `data/private/`；脱敏汇总、审计程序和报告进入 `docs/reviews/`。修订原 ROB 报告错误判据，README 状态只指向当前事实。分两次小提交：实现与测试；实测报告与溯源。远端暂不处理。

## 估计量与证据边界

ROB 首先观察每迭代 cycles/ns 与并行/串行差异，报告有效窗口区间；不预置384，不把 NOP/MOP/µOP/ROB entry等同。N=0包含锚点，不能统一扣作底噪。TLB 的 nested W8/9对照用于检验既有局部转折受地址变动、cache行冲突和filler压力影响的程度；即使结果稳定，仍不自动命名物理8-way。
