# TLB/ROB离最终目标的距离（2026-10-12）

## 本次任务的目的（给人类看）

回答“现在离最终目标达成还差多远”，区分可复现行为画像、物理参数认证、软件集成；不把测试数或采样量当完成百分比。目标仍是给出SM8650/X4上可复核的TLB/ROB结构与容量结论。**整体目标尚未完成。TLB已形成较成熟的条件化行为画像；ROB仍在测量方法校准阶段。**

| 方向 | 已验证的内容 | 距离物理定案的主要缺口 |
|---|---|---|
| TLB | 局部冲突转折、有限低位/高位候选区分、L1 refill曲线和walk并行有效响应；最新同PFN三VA族279窗/270门与330240原始pagemap位核对通过，几何差仍复制 | 分离descriptor/translation预取、stored-pointer识别与硬件聚合等可替代解释；认证物理容量/ways和足够范围内的索引规律 |
| ROB | 真实生成码/PMU/IR/结果链可信；D0/D1独立参考约208/416，chain32约416/832；架构目的XZR控制及同码/同VA反例保留 | 建立稳定、可解释的资源流量控制，独立标定分配单位，并证明被碰到的活跃限制确为ROB；当前不能将NOP数、µOP/IR或第三方384改名entries |
| 工程收口 | m0b已集成进r2并完成使命；414/414诊断回归、NDK构建与producer→raw审计通过 | 科学结果稳定后整合总报告及交付索引，核对main相关变更，完成集成回归/备份；不复活旧不完整正式矩阵 |

## 最新一块对距离判断的影响

`docs/reviews/2026-10-12-rob-retirement-units-results.md`：24进程/192真机窗技术链完整、两chain参考稳定，但ADD+SUB无锚点每轮约42–71cycles，三个epoch波动45–50%，另9取指窗越过冻结门。**资格not-qualified，2352窗扫描未启动。** 双NOP/NOP+ADD稳定不能替代缺失的共同单位标尺，失败批不改门重跑。平均cycle/ns约2.7115–2.7462仅为描述观察，不能认证窗内恒频或唯一归因。

最新同PFN反证 `docs/reviews/2026-10-12-tlb-shared-alias-results.md` 排除“不同data PFN是本新协议几何效应的必要条件”，但还没有唯一排除descriptor、指针值相关预取及聚合。两者都在减少解释空间，仍未达到物理参数命名出口。

因此不能提供可靠的完成百分比或日期；剩余关键工作是**两个科学辨识出口及后续工程收口**，其耗时取决于新对照是否产生可区分结果。当前数据已经支持有限结论，物理未知保持公开登记，不以多跑几轮保证测得。

## 接续动作

1. TLB先冻结同物理页/同访问轨迹的stored-pointer表示与预取事件对照，或可观测descriptor层级干预，明确阳性/阴性各能排除什么；再测必要的局部转折，避免重复全局曲线加密。
2. ROB先对当前供给/执行状态作新的正交干预，补分配单位及活跃约束证据，再启动可解释的容量扫描。本次资格失败保持终态，物理ROB目前仍未测得。
3. 结果逐项纳入 `docs/reviews/2026-10-11-tlb-rob-goal-ledger.md` / `docs/reviews/2026-10-11-tlb-rob-identifiability.md`，所有未竟问题、负责人和触发条件归 `docs/open-items.md`；软件和分支收口随后验证。

当前工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`，分支 `codex/sm8650-tlb-hierarchy-r2`。本次新增代码 `probes/diagnostic/rob_retirement_units.c` / `tools/diagnostic/rob_units_analysis.py` / `tools/diagnostic/run_sm8650_rob_units.py`：source `df2171d`、build `47ff455`、真实launch `f2c99a9`、目标报告 `a0e6243`。本版无main合并或远端推送声明；其他会话.gitignore与旧六run目录原位保留。
