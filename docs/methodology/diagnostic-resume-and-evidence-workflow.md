# SM8650有限探针：中断恢复与证据闭环工作流

## 本次任务的目的（给人类看）

把可复用的实质进展留成可恢复方法，减少生产链接缝反复漏网。优先构建能区分解释的小探针；工作流服务科学问题，不以增加门或大矩阵代替机制辨识。

1. **恢复先查现场**：读最新commit/status、有限协议和结果manifest；确认设备所有权/active探针/unfinished journal。已完成批次只复核，不因网络或上下文中断重复采样。别动其他会话文件、失败目录或原raw。
2. **先定义可推翻的判断**：写清作用域、实际干预、相同/变化的量、阳性和阴性能排除什么。负控的激励单独核验；`NOT_EXCITED`时不能把阴性叫因果排除。区间删失、非单调、资格失败有命名终态；不救门、不由官方/第三方数值倒拟合。
3. **验证实际生产链**：实际生成代码/图→独立decode或解释器→driver→写盘→回读→消费入口。覆盖缺失、冲突、重复、乱序、类型True/1、真实默认键及跨回调失败覆盖。独立计算与synthetic测试只证明软件合同，真机能力/性能另外验证。
4. **失败证据不可被成功覆盖**：连续窗口或回调必须保留首次失败与完整状态。`translation_self_bpf.h` 的sticky守卫由实际失败后再次回调反例钉住；末次成功不替代整个尝试。CLI完整stdout/stderr及退出码落盘，不使用tail管道掩盖失败。
5. **观测前先验证能力**：BTF/config存在不代表load/attach/read可用；pagemap可见不代表leaf CONT可见。程序只读自有process/mapping，核对target source/BTF/二进制；短FD生命周期、无pin且每个退出close。先有限能力检查，再决定新实验；不猜内核physical bias或改安全配置追成功。
6. **结果分层入库并及时提交**：source、binary source、build、protocol、actual launch、consumer、raw SHA分列；raw/地址/PFN/标识私有。保留全部signed效应及失败门，公开匿名表/CSV/图和第二算术对账；每项结果独立scope commit，随后同步README/目标账/open-items。
7. **关键结果更新记忆**：记录支撑行动的事实、commit/path、证据级别和未认证边界；可变现场留“恢复需live recheck”。本会话记忆更新按 `/Users/michaelyao/.codex/memories/extensions/ad_hoc/notes/` 写小note，供记忆系统归入MEMORY索引，不直接编辑自动维护registry。

实例：`docs/reviews/2026-10-12-tlb-pfn-association-results.md` 的零邻接reach=(1792,2048]复制但关联主INCONCLUSIVE/自然激励NOT_EXCITED；`docs/reviews/2026-10-12-rob-lifetime-heldout-results.md` 的E2 g+chain=(352,368]预测复制但不命名physical entries；`docs/reviews/2026-10-12-translation-self-read-results.md` 的3/3自有root descriptor能力通过但leaf CONT/HPA未知。这些边界必须随事实一起恢复，不能只记“通过”。

## 已实证的reference残差攻击方法（2026-10-13）

`docs/design/2026-10-13-rob-anchor-order.md` / `docs/reviews/2026-10-13-rob-anchor-order-results.md` 用同进程同code PFN、交换slot、同opcode histogram/输入/result/prefix/tail，只更换两条独立FSQRT链的register schedule；NONE/SERIAL两个layout逐字同码作阴性。12新进程768窗/54SHA全部controls过，k32 blocked/interleaved462/433、DID≈29跨六process复制，k16≈225无同类变化。这样把被模型外推隐藏的reference启动/排程贡献变成可证伪干预。不能由该差唯一推32-entry scheduler或ROB容量；旧433外推不能反过来说“模型从开始就被验证”。更换anchor reference需另案绑定新producer/plan/qualification，不回填旧scan。

## 事件能力与小信号包络（2026-10-13）

事件准入需先查具体core/revision实现表/PMCEID，再做真实架构正控；raw perf open+ID+无MUX只认证采集，不认证事件存在。`docs/reviews/2026-10-13-rob-speculative-marker-results.md` 的0x06是实证反例。单指令差分时统计粒度必须覆盖实际wrapper/供给背景；不能把每窗cache refill自动归到JIT，更不能在看到原门失败后扩大门。新观测原则应另冻，例如own cache state+架构原结果，不依赖缺失的退休tap。

自有cache状态资格进一步见 `docs/reviews/2026-10-13-rob-cache-marker-results.md`：独立冷热cal与架构正负均合格仍不保证错误路径footprint可用。分别跟踪issued、fill-completed、architecturally-retired三个事实；计时miss不能自动判未发射或未分配。保留未通过.90门及全部原值；更换原理/干预须另注册。


2026-10-13发射观察阴性：`docs/reviews/2026-10-13-rob-issue-marker-results.md` 实证训练为taken且架构绕过，仍LD_SPEC/ST_SPEC有8级推测响应；“不退休”和“不发射”不能合并。语义正控成功不保证negative有效；A/B阈值重叠须None及NOT_QUALIFIED，不能令0 eligible冒称0 issue。下一结构性阴性先以pre-tap SB与post-tap SB同错路对照另冻结；独立校准，原计数包络和失败gate保留。


2026-10-13SB结构阴性事实：`docs/reviews/2026-10-13-rob-fenced-issue-results.md` chain16三fresh通过、整体k32远阈值失败；支持pre/post-SB结构干预，不是整资格／capacity通过。当前f2f4f12金样新增“near可算+far不可算→far conditional rate必须None”；guard不只拦TypeError，还必须拦0等伪数值。短窗端点噪声须先换观测方式／放大真实信号，不能改分位门追通过。


2026-10-13own perf metadata实证 `docs/reviews/2026-10-13-pmu-user-metadata-results.md`：cap_user_rdpmc=true但index0、policy0，不可直接MRS。访问资格需policy+实际own index/width+seqlock/offset/wrap+正控全部成立；root/open成功/cap位均不能替代。新临时profile必须另冻恢复事务，原基线和未知状态保存，不猜counter号码，metadata snapshot不复用给后续进程。
