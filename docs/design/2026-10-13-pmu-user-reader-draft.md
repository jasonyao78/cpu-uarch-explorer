# 逐进程PMU用户读取资格（草案，未实现／冻结／执行写入）

## 本次任务的目的（给人类看）

针对 `docs/reviews/2026-10-13-rob-fenced-issue-results.md` 的短窗校准尾部，优先验证能否在实际核心用自己的perf mmap metadata读取自己的counter，移除每shot enable/disable syscall包络。候选不是猜固定寄存器号，也不是通过PMU绕过读取他人信息。其他路径为独立批量信号放大，不重跑旧N0追门。

## 界面与必须实证的能力

官方Linux arm64 perf用户访问文档 https://www.kernel.org/doc/html/v6.16/arch/arm64/perf.html 描述sysctl perf_user_access、attr.config1 bit1以及metadata seqlock/index；版本仅参考，目标6.1.118-android14实际接口必须实证。2026-10-13只读目标sysctl=0，当前没有启用。若另批准／冻结临时资格任务，需要先写独立恢复事务：baseline0→apply1→验证→自己event4group／mmap→cap_user_rdpmc/index/width实际检查→安全只读MRS→kernel group read一致性／负控→all FDclose→finally恢复0→inspect。任何缺cap/不支持/信号异常命名拒绝，不在无资格时尝试MRS，不猜physical counter index，不沿用旧组ID。

只允许自己的pinned USER-only事件，CPU7／seqlock前后稳定，context switch/metadata change使本窗不可算，width按实际元数据处理，不忽略wrap与offset。普通root不是固件权限，本候选不写PMU原始控制寄存器／内核代码或读取其他进程事件。临时全局sysctl与原baseline不同，不能暗改；异常／未恢复事务阻止后续实验。登记事务恢复命令及其真实exit，不接tail掩盖。

初资格拟用长已知自有LDR/STR loop校验计数增量、两个边界snapshot与原own结果，再接SB结构发射对照。先交actual C/协议/driver复归测试／双NDK／实际ELF及metadata资格，事件open不等于implemented；新读法也不认证ROB单位／供给／容量。组件候选 `probes/diagnostic/pmu_user_reader.c` 尚不存在；主Agent执行，`docs/open-items.md`追踪。
