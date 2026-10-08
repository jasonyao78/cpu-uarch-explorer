# SM8650 TLB 三轴探索：两target、反序复现

## 本次任务的目的（给人类看）

在用户确认单一执行者并授权端到端接管后，用少量有区分力的探针取得可解释的硬件信息，检验是否值得继续TLB确认实验。执行设计见 `docs/runbooks/2026-10-09-sm8650-bit-axes-exploration.md`，研究路线见 `docs/reviews/2026-10-09-probe-first-reassessment.md`。

## 结论

**探索信号与复现通过；正式H*/物理ways/完整索引函数尚未证明。** 两轮、两个target、相反顺序均呈A/B高而C低，与H1（VPN低8位定义冲突分组）的预测方向吻合。在已检验的四个leaf候选中，初步行为证据支持H1；未排除其它在这些地址上等价的函数、共享/中间描述符或窗口背景因素。

单位为每有效轮的0x2d计数，表值为每条件5个独立进程各自均值的中位数：

| 条件 | target200 / 正序 | target100 / 反序 |
|---|---:|---:|
| 空窗 | 0.0 | 0.0 |
| A：中间字段变化 | 6.2 | 7.7 |
| scatter | 0.1 | 0.0 |
| B：高字段变化 | 6.8 | 9.7 |
| C：补偿中间字段 | 0.1 | 0.1 |

两轮A/B共20个观测最小5.1；C/scatter共20个观测最大0.3。该分离是描述性事实，未据本批数据选择on阈值，未调用正式H*分类器。两轮不合并为一个正式矩阵。

## 资格与执行事实

- 两轮均5cases/25进程，合计50个进程、950个有效轮；逐样本19valid、0invalid、0mux，purity=1、节点向量/active与请求一致。第二轮B的一份实际高字段序列跨253/254/255→0…8，仍每区域1节点。
- `runner.plan`→`runner.engine.run_plan`→adapter→原始文件/records→loader完整生产链，非手写record。全部50份stdout+stderr组合SHA256与大小独立回算一致；另一只读审计同时重新解析raw，核对record metrics/realized。
- 两轮保持walt，未变更governor/min/max/热服务；完整状态端点quiet条件通过，policy7上限始终2745600。端点maxCPU第一轮38.0–41.1°C、第二轮38.0–40.9°C；这些不是连续温度或窗口时钟证据。
- 每轮 `run_plan` 合计约23.87/24.65秒，不包含准备和两轮间分析时间。一次完整8-command环境采集实测约2.02秒；尚未完成细分CPU耗时/发热归因。
- NDK27.2.12479018/API34完整独立重编，正确宏 `CPU_UARCH_HAVE_LINUX_PERF=1`。新编/原本机/设备端摘要一致：54d105930b8743e7a3a69c31d7e640cdec1044a0276a5f040efff4b1dc82398c。无需替换已相同的设备产物；runner部署仍核对摘要。
- 采样后复核：walt/min/max与前述基线一致、maxCPU38.0°C、无环境违规、unfinished journal=0、无残留探针进程，设备端二进制摘要不变。

## 所有尝试与数据位置

1. `data/private/20261008T161923Z-sm8650-tlb-bitaxes-exploration/`：仅floor5进程后，探索驱动的输入文件名与ID在后验校验中不符，驱动停止。探针本身产出ok记录；完整输入/日志/原始样本保留，不混入两轮结果。随后将该检查移到运行前并修正文件名。
2. `data/private/20261008T161956Z-sm8650-tlb-bitaxes-exploration/`：target200，floor/A/scatter/B/C，5×5完整通过。
3. `data/private/20261008T162157Z-sm8650-tlb-bitaxes-exploration/`：target100，C/B/scatter/A/floor，5×5完整通过。

总共实际调用55个探针进程，表中包含两轮设计内的50个；没有数值筛选或删除失败尝试。私有目录保留生成的spec、实际platform、驱动源码及摘要、probe源码摘要、完整日志、raw和标准records/artifacts/manifest。公共派生摘要与全量观测在 `docs/reviews/evidence/2026-10-09-bit-axes-exploration/summary.json`；没有提交原始样本或私有输入。

运行时git dirty=true如实保留：第一轮包含他人.gitignore改动，第二轮还包含采样前登记的runbook修改；探针源码未改且独立编译摘要完全一致。不能把它宣称为旧正式clean-source合同通过，也不回填旧冻结工件。

## 下一步优先级

1. 先排查窗口背景：0x2d同时包含指令与数据refill；0x05扣除空窗后部分条件仍超旧±15%目标页计数带，**本轮没有宣称该旧协议门通过**。0x2f扣底约11.8–13次/轮，支持12页访问暴露到L2的量级。后续用可用的数据walk事件/匹配空窗与几何对照验证来源，再估局部W转折，避免直接把6–12次refill叫ways。
2. 只补能推翻解释的控制。若信号仍稳定，固定科学主张后进入独立确认；是否继续既有48/48/32或另注册三轴确认版本再裁定，旧L1不拼接。
3. 同时启动ALU/FPU短探针设计：依赖链延迟、独立链吞吐、混合指令争用；随后利用已验证长延迟源区分ROB、rename/队列和前端瓶颈。TLB完整hash未解不阻塞其它部件。

软件恢复修复 `dc0e72b` 保留；runner203/203、analysis250/250已通过。测试成功与上述真实手机测量分别记账。本轮未推远程、未提交或移动其他Agent的上板目录，未重新开启m0b开发。
