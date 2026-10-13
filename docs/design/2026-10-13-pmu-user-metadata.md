# Own perf用户读取接口只读元数据资格 v1.0（第一步，不执行MRS）

## 本次任务的目的（给人类看）

落实 `docs/design/2026-10-13-pmu-user-reader-draft.md` 的最小能力检查：先看目标内核是否接受config1用户访问请求、自己事件mmap实际cap/index/width/seqlock，不预设Linux参考接口与Android内核完全相同。**该producer不执行任何PMU MRS，也不修改perf_user_access**，不能声明counter read、发射或ROB容量资格。

`probes/diagnostic/pmu_user_reader.c` 第一阶段仅metadata-only，API --plan/--run --config1{2,3}。两flags分别user-access和user-access+long64请求，events[0x11,0x08,0x70,0x71]自己pid0/thread、CPU7、RAWtype8、pinned USER-only GROUP+ID+time。只读取sysctl0/1；own mmap只读，完整索引／width／cap／两sequence披露，不猜物理counter号。group own IDs读回核验、所有FD／map最后关闭，首failure保留stage/errno/empty metrics，不降flag0或重试追权限。metadata cap即使为true也不是安全MRS证书：policy、seq、index/width/offset/wrap及actual正控仍须后续证明。

后续driver先active-probe/unfinished-journal/环境/MIDR/SHA，三fresh每flag轮换（6process），first capability拒绝就停；actual plan/双NDK/raw source绑定完成前不执行。当前TLB正式dose独占手机，metadata不得并发争PMU。public仅匿名摘要，raw private；source/build/launch提交分列。目标只读sysctl=0已知，不在本阶段暗开；任何未来临时写另冻结恢复事务。参考接口官方 https://www.kernel.org/doc/html/v6.16/arch/arm64/perf.html （版本差异待目标实证），TRM匹配r0p1见 `docs/reviews/2026-10-13-x4-r0p1-source-audit.md`。

测试 `tools/diagnostic/tests/test_pmu_user_metadata.py` 钉实际plan、无寄存器读取、未知flag及host执行拒绝。FD生命周期不是physical counter观察。本阶段不修复／回救原SB1536-window完整资格失败，`docs/reviews/2026-10-13-rob-fenced-issue-results.md`保持终态。
