# 目标页表可观测性：类型可读，内核读取未验证（2026-10-12）

## 本次任务的目的（给人类看）

TLB几何/同PFN/全位指针/PFN关联控制仍不能唯一排除descriptor、CONT和聚合，先验证能否直接观察自有探针进程的页表。当前只有只读元数据检查，未加载/附加BPF、未读取PTE、未修改sysctl或内核。

## 实际能力与边界

目标内核6.1.118-android14-11-ga3b9c44908dd-ab13320413，4096页；CONFIG_PGTABLE_LEVELS=3、VA_BITS=39、PA_BITS=48。BPF syscall/events/KPROBES/BTF配置存在，raw_syscalls/sys_enter可见。BTF5629043字节、130435类型，SHA256 `edf0efa6c0a4d661367567ae7386985c58e42d6e4cc700a0903f8eb831c6c6e1`；实际task_struct.mm=1440bytes、tgid=1588bytes，mm_struct.pgd=56bytes（位于匿名嵌套struct，递归解析，不硬按扁平成员查找）。

kptr_restrict=2，所需memstart_addr/kimage_voffset符号地址被掩为零；BTF没有这些全局VAR项。configured KVM=y，活动模式UNKNOWN。root可读BTF不证明具备BPF load/attach或probe_read_kernel权限，更不证明允许读取页表leaf或EL3的HPA控制。

公开匿名证据 `docs/reviews/evidence/2026-10-12-translation-observability/capabilities.json`；原BTF/命令输出私有目录 `data/private/20261012-translation-observability/`。不输出内核指针、绝对PFN/设备标识。

## 接续方案

先验证一个短生命期、owner PID及syscall双过滤的BPF程序，仅读取current task的tgid/mm/pgd及两个自有、已prefault VA对应root descriptor；不根据未观测物理偏置盲走下一层。程序/map/link仅FD持有，始终close且不pin；能力拒绝保留errno/verifier原输出，停止该能力路线，不改安全设置绕过。这个小检查阳性只能叫SELF_ROOT_DESCRIPTOR_READ，leaf CONT/HPA继续UNKNOWN。根descriptor直接读数通过后，是否能取得自有leaf PTE指针/校验安全走表路线需另立方案。

[BTF官方格式](https://docs.kernel.org/6.1/bpf/btf.html)支持类型/成员元数据解析；[Linux6.1 BPF接口](https://raw.githubusercontent.com/torvalds/linux/v6.1/include/uapi/linux/bpf.h)与[trace helper实现](https://raw.githubusercontent.com/torvalds/linux/v6.1/kernel/trace/bpf_trace.c)是下一原型的主来源。上述路径描述是方案，不将通用接口文档当目标设备能力证据。

owner=当前TLB端到端负责人；有限metadata检查结束，实际load/attach/read能力OPEN，归 `docs/open-items.md`。branch `codex/sm8650-tlb-hierarchy-r2`；本报告不重写任何旧PTE/CONT UNKNOWN或物理capacity。
