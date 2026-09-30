# 执行端微架构探测方案设计（ROB / ALU-FPU / I 侧 TLB）

> 版本：v1.0（2026-09-30）
> 输入：REV-TLB-R2-20260930 评审 §4/§5（R1–R4 + 执行资源方法论）、《ROB 微架构深度分析报告》v0.1（`docs/cpu-uarch-deep-analysis/rob-deep-analysis/`，估计量/混淆/判据 J1–J8 已预注册）、CPUSUIT 参考框架（`cpu-uarch-ref/cpu微架构材料/src/`，Apache-2.0 脚手架 + 无头测量代码——借鉴方法不搬代码）
> 定位：**独立设计文档**，不是 r2 TLB 任务书的章节（ROB/ALU/FPU 属另立项；本文是其任务书的输入）。r2 任务书 §1.3/§11 已预登记 R4 约束与 I 侧立项条件。

## 1. 总序：先能力曲线，后资源拓扑

评审 §5 的核心方法律：**某指令每周期执行 8 条不证明 8 个同质 ALU，4 条 FP 路径不证明四个独立 FPU**。操作支持集 / initiation interval / 旁路 / 共享资源必须分别测量。执行顺序固定四级，前一级是后一级的解释前提：

```text
L0 测量正确性（生成码控制流 + PMU 解码 + 寄存器交集 + 锚点标定）
L1 ALU/FP 能力标定（逐指令形式延迟/吞吐表）
L2 ROB 窗口矩阵（锚点 + 填充类别 + 跨类别约束）
L3 混合流资源共享 + I 侧 TLB 短跳板
```

## 2. L0 正确性门（ROB 骨架 R1–R3 为现例，全部为关闭条件前置）

| 项 | 缺陷（已复核属实） | 设计要求 |
|---|---|---|
| 生成码控制流 | R1：回跳位移多除 4（期望入口 28，实际 316，稳态循环绕过双锚点） | 黄金检查：分支目标/每迭代锚点数/填充数/退出条件逐例断言；`--write-asm` 产物 disasm 自动比对，**不只看 opcode 合法** |
| PMU 组读 | R2：GROUP 布局按 `nr,values[],ena,run` 解码（实际 `nr,ena,run,values[]`），enabled/running 被当事件值 | 按 `read_format` 实际布局解码 + 按事件 ID 映射（不按位置替代）；合成 `[nr,ena,run,values]` 黄金测试；窗口 delta + enabled/running 完整性检查；任一事件失败 = n/a 字段，**不按位置顶替 cycles** |
| 寄存器/锚点 | R3：fsqrt 锚点 d0 未初始化；FADD 填充的 s0 与 d0 寄存器交集打断锚点链 | 锚点输入显式初始化并标定数据相关时延（反复 sqrt 收敛问题）；填充/锚点寄存器分配无交集，机器码依赖图验证 |
| 事件语义 | R4：INST_SPEC（执行 op）/INST_RETIRED（退休指令）比值 ≠ ROB 条目（融合/消除/重执行混入） | 仅作辅助约束；指南 NOP 融合情形（§4.11）的 NOP/消除控制保留 |

## 3. L1 ALU/FP 能力标定

- 官方指南候选拓扑：8 条整数路径（6 单周期 + 2 单/多周期）、4 条 FP/ASIMD issue 路径——**候选，非结论**。
- 测量矩阵：每指令形式单独一行——延迟（单依赖链 producer→consumer）与吞吐（多寄存器独立链，初始链数 `K ≥ latency × target_throughput`，如 ADD 1c/8ipc → ≥8 accumulator）分列；shifted/flags/MUL/DIV 不共用"ALU"标签。
- FP 分 scalar/ASIMD × F16/F32/F64 × FADD/FMUL/FMA/FDIV/FSQRT；FMA accumulator 旁路延迟单独测；稳定正常数 + 记录 FPCR/FPSR，零/NaN/非正规数为独立条件。
- 长延迟单位（UDIV/SDIV/FDIV/FSQRT）注意数据相关提前结束（指南表 3-4 已示）与同流水线阻塞。
- 排歧：前端供给/分支/spill/循环开销/频率——吞吐平台必须过这些检查才归因到执行端口。

## 4. L2 ROB 窗口矩阵

- **估计量**：`W_class` = 长延迟锚点阻止退休时，可容纳多少**特定填充类别**使第二独立 miss 仍可提前发出。先被限制的可能是 ROB/PRF/调度器/load-store buffer/前端供给/融合——命名"ROB 条目数"必须证明填充流占用单位与其它限制均未先触发。
- **384 的定位**：Cardyak 2023 框图标注 "384 Entry ROB" = **第三方候选扫描值**（宽扫至 1024，细扫 256–512），**非目标设备真值**（评审已核：无官方来源）。
- 锚点：miss 锚点（L1/L2-miss chase）与 fsqrt 链锚点双模式；内存 miss 锚点须携带 TLB/cache 状态证据（r2 战役的页审计复用）。
- 填充类别矩阵：NOP / ADD(+INT PRF) / MOVI·MOVR(+rename 消除) / FADD(+FP PRF) / LDR(+load buffer) / STR(+store buffer，SA+SD 2 µOP)；类别混合窗口 knee 跨类别一致性约束。
- 混淆排除：PRF（stuffedcow 已明其与 ROB 测量纠缠）、调度器、前端供给——靠类别矩阵的差异化 knee，不靠单曲线。

## 5. L3 资源共享与 I 侧

- 资源共享：A、B 及比例混合 A+B 流（依赖图不变），退化相对单项吞吐；共享端口只是候选解释，dispatch 类型限制/rename/前端限制先排查。
- I 侧 TLB 短跳板探针（r2 后置项 2 的立项输入）：每页等长数指令跳板 + 页内偏移对照 + `L1I_CACHE_REFILL` 与分支事件剥离；设计同构先例 = CPUSUIT `ifetch_block.S`（页 0 尾 1 nop 跳板 + 页 1 K nop）与我们报告 §5.6；D 侧纪律（页审计/锚点/fail-closed）全继承。

## 6. 工程接入与借鉴边界

- **接管道**：ROB/ALU/FPU 探针经 M0 的 descriptor/adapter 进 runner/schema/锚点管道（评审 §3 架构图："研究算法与判据独立，证据运输共用"）；ROB 独立 CSV 边界届时重开 OI-12(rob) 决策。
- **CPUSUIT 借鉴**：`both/lat/thr` 模式、`port.cc` 混合流列、xbyak 生成构造。**警示**：其 `utils` 存在"假定 ADD 一周期推频率"与 PMU 读数双路径（移植须追踪消费的是哪个周期来源）；SIGILL=-1 占位、FD 错误路径、reciprocal 注释不可原样进新 ABI；`pattern.c` 的 TLB 片段重复加载少数地址（probeCount 是指令数非 distinct 页数），**不能替代本仓集合生成方法**。
- 判据预注册：ROB 报告 v0.1 的 J1–J8 继续有效；本文 L0 四项正确性门作为 J 系判据的**前置门**补入。

## 7. 与 r2 TLB 战役的接口

r2 产出的可复用物：M0-1 共享支撑层（映射/页审计/CPU 身份）、M0-3 PerfWindow（GROUP 原子读）、M0-4 descriptor/几何字段——执行端探针直接消费；r2 的 I 侧后置项（任务书 §11-2）以本文 §5 为设计输入。
