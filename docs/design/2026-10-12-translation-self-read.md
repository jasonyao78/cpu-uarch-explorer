# 自有进程root descriptor读取能力检查 v1.0（2026-10-12）

## 本次任务的目的（给人类看）

通过最小、短生命期观察器确认root能否直接读取自己探针的页表root descriptor。它回答权限/观测能力，不测TLB容量，也不读其他进程页表。当前目标BTF已确认类型偏移，但masked全局地址使完整安全走表路线仍未知。

## 方法选择与合同

继续间接VA/PFN曲线不能消除descriptor残差；内核模块/全局安全配置修改超出本有限检查；采用短生命期BPF raw sys_enter。首段先过滤getpid syscall=172和当前TGID=本探针PID，任何其它进程/其它syscall在首个kernel-read前返回。再用probe_read_kernel只读current task.tgid/mm、mm.pgd及两个自有prefault VA对应的root项。BTF SHA必须是 `edf0efa6c0a4d661367567ae7386985c58e42d6e4cc700a0903f8eb831c6c6e1`，task.mm1440/tgid1588、mm.pgd56，3级4K页/39VA/48PA；layout或kernel不匹配拒绝，不尝试替代偏移。

reserve 2GiB无物理承诺arena，仅offset0和1GiB两个4K页prefault；两个root索引由实际VA>>30 &511决定。读8-byte root描述符，不沿物理地址盲走下一级；安全direct-map偏置尚不可见，不猜常见RAM起点。叶PTE/CONT/HPA保持UNKNOWN。

一个map，一个GPL raw-tracepoint程序，attach sys_enter；仅FD持有，无pin、无sysctl写/内核写入/tracefs永久配置。程序有限直线控制流；negative controls=自身gettid3次、子进程getpid3次（过滤应无capture），positive=自身getpid3次（capture恰3）；关闭attach/program/map所有FD后才输出。异常也close；进程退出由内核回收FD，无重试至成功。

三fresh进程，串行、每个≤30秒、进程之间固定15秒；无PMU性能扫描。每次技术门为部署SHA/BTF/核/page、CPU7、读回TGID准确、负控0、正控3、read errno0、mm/pgd非零、两owned root项(table d&3==3)。所有三进程通过才 SELF_ROOT_DESCRIPTOR_READ；权限或helper/load/attach拒绝=CAPABILITY_UNAVAILABLE（保留stage/errno/verifier），其它不符=INCONCLUSIVE/技术失败，不输出假成功。不改kptr_restrict或放宽SELinux，不装模块绕过。

## 实现/验证/证据

pure实际指令生成 `probes/diagnostic/translation_self_bpf.h`，native/Android CLI `probes/diagnostic/translation_self_read.c`；实际BPF指令导出使用独立host解释器攻击wrong syscall/PID、每层read失败、成员偏移、root索引和退出/FD合同。`tools/diagnostic/tests/test_translation_self.py`、consumer `tools/diagnostic/translation_self_analysis.py`、driver `tools/diagnostic/run_sm8650_translation_self.py`，测试必须真实plan→writer→loader，synthetic内核读不当设备证据。双NDK27.2/API34/static/O2/Werror并记录recipe/source/binary；冻结launch后设备能力检查，绝对VA/PFN/内核指针和verifier私有，公开仅匿名计数/SHA/门和状态。

参考 [Linux6.1 UAPI](https://raw.githubusercontent.com/torvalds/linux/v6.1/include/uapi/linux/bpf.h)、[tracing helper实现](https://raw.githubusercontent.com/torvalds/linux/v6.1/kernel/trace/bpf_trace.c)、[BTF格式](https://docs.kernel.org/6.1/bpf/btf.html)。通用API支持不是目标权限证明，实际加载结果裁定能力；第三方capacity图不参与。

本检查完成后更新 `docs/open-items.md` / `docs/reviews/2026-10-12-tlb-rob-status.md`；阳性只开放下一owned-leaf观测设计，不回填旧CONT UNKNOWN、不宣告physical TLB/ROB完成。primary独占，branch codex/sm8650-tlb-hierarchy-r2。
