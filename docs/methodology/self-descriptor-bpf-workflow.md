# 自有descriptor BPF指令工作流（已验证方法）

## 本次任务的目的（给人类看）

保存一条真机验证过的直接观测路线及字节码验证方法。当前能力是只读自有root descriptor，不是通用任意内存读工具，也不是leaf CONT/HPA/ROB容量证书。

## 可复用的78指令结构

实际emitter `probes/diagnostic/translation_self_bpf.h`，loader `probes/diagnostic/translation_self_read.c`，78指令冻结plan `docs/reviews/evidence/2026-10-12-translation-self-read/plan.json`。计划PID/root索引/map FD为固定测试值；真机按实际owned VA/PID/FD导出并从binary_source源码重编复生，不能只比较固定plan SHA。

| 阶段 | 实际BPF动作 | 保证/限制 |
|---|---|---|
| 前置双过滤 | `LDX_DW r0,[r1+8]`读raw sys_enter arg1；JNE syscall172返回。helper14取pid_tgid，`RSH64 32`取TGID，JNE owner返回 | 过滤在所有helper113之前。foreign PID和wrong syscall不能读task/mm/PTE；raw context布局仅适用于本hook/目标API |
| 取得结果buffer | 初始化stack-64的u32 key0；`LD_DW_IMM`伪map FD占两个指令槽，src=1；helper1 lookup，空指针返回；map指针留r6 | map为64-byte ARRAY一项；输出是观测buffer，未写kernel页表。跳转偏移以8-byte指令槽计，LD64第二槽也占PC |
| 首错锁存 | hits非零时检查stage==6且read_errno==0，任一不符返回；之后hits+1 | 任一捕获不完整即不能被下一次成功覆盖。最终stage6/hits3需三个捕获全部完成；实际VM反例验证旧实现会覆盖 |
| 三个identity读 | helper35取得current task→r7；helper113只读task.tgid4B、task.mm8B、mm.pgd8B；TGID再与owner比，null返回；pgd留r8 | helper调用会破坏r1..r5，r6..r9留跨helper状态。读前stage递增，读后保存signed errno，错误退出 |
| 两个root读 | helper113读pgd+8*((owned VA>>30)&511)各8B；两个owned VA相差1GiB | 只走已获得的内核root指针，不从PA推未观测direct-map偏置；两项d&3==3仅认证table类型 |
| 收尾 | 完成stage6；所有出口`MOV r0,0; EXIT`。loader关闭link→program→map后输出 | 无pin，无全局安全/sysfs/内核写。异常及进程终止也回收FD；CPU/环境/BTF/部署身份在driver核验 |

本接口helper数字14/1/35/113由 [Linux6.1 UAPI](https://raw.githubusercontent.com/torvalds/linux/v6.1/include/uapi/linux/bpf.h) 核验；kernel-read helper权限可能被lockdown拒绝，见 [tracing实现](https://raw.githubusercontent.com/torvalds/linux/v6.1/kernel/trace/bpf_trace.c)。源配置/符号存在不代替真实load/attach/read，不能复制参数去另一台机器默认成功。

## BTF与页表布局

目标BTF SHA `edf0efa6c0a4d661367567ae7386985c58e42d6e4cc700a0903f8eb831c6c6e1`；task.mm1440、tgid1588、mm.pgd56字节，后者属于匿名嵌套struct，要递归成员偏移。4K页/三层/VA39/PA48。BTF/config不匹配停止，不猜常见offset。kptr_restrict2且global地址masked，没有改变；root可读不能推出leaf CONT已读。

## 验证链与实际证据

`tools/diagnostic/tests/test_translation_self.py` 编译实际C并独立解释实际导出字节码；模拟内存只证明控制流。覆盖正读、wrong PID/syscall、map null、五层helper各自失败、TGID错、跳界、首次失败后再次回调；解释器不能另写一份抽象伪程序替代producer。

`tools/diagnostic/tests/test_translation_self_raw.py` 与 `tools/diagnostic/tests/test_translation_self_driver.py` 锁真实生产计划/registered driver→writer→loader。`tools/diagnostic/translation_self_raw.py` 从binary_source不可变源码重编动态计划，检查原stdout SHA及source/build/protocol/launch、完整negative/positive状态、环境和退出码；重哈希损坏数据仍应拒绝。源码源7224957/build30e6082/launch21c3034/result64dcbe4，branch codex/sm8650-tlb-hierarchy-r2；15新测试/495全量diagnostic通过。

真实目标3/3进程，每进程wrong syscall/foreign child负控0、自身getpid正控3、两个root table读数和20 raw SHA独立核验；结果 `docs/reviews/2026-10-12-translation-self-read-results.md`。此方法打开owned root descriptor观察能力；下一leaf指针仍需新合同和pagemap身份检查，不能由正控推“任意内核读取”“CONT=0”或physical capacity。

## 第二条实际路线：owned leaf pointer（已真机验证）

`probes/diagnostic/translation_leaf_bpf.h` 45实际指令先保存pt_regs context到r9，helper14过滤owner TGID，再用64-bit LD_IMM+JNE_REG比较x1(address)与selected VA，之后才helper1 lookup与helper113读取x2(ptep)的8-byte word；x3(requested entry)仅记录。r6 map/r7 source跨helper保留；first failure sticky，错误/重复/零事件分别处理，0事件NOT_EXCITED不能当因果阴性。

`probes/diagnostic/translation_self_leaf.c` 用CPU7 perf-kprobe，type由sysfs读取，config1=ptep_set_access_flags，event→program→map退出回收。两个owned匿名页COW/reuse触发：foreign child和wrong VA负控0、parent selected正控1。三进程实际old/requested PTE page/PFN与两端pagemap一致，source0e8cd63/build49c7123/launchd235ce3/result77a3293，20 raw SHA已独立对账。实际ABI/BTF/PMU类型/计划/source绑定，完整28关联与508诊断通过。COW入口CONT0只属于该时点；shared-memfd alias适用性尚待验证，steady CONT/HPA不回填。后续性能窗口先卸载observer，观测对descriptor/cache准备的影响必须对称控制，页表物理PA仍未直接读取。

## 必须保留的适用性反例

`docs/reviews/2026-10-12-translation-shared-leaf-results.md` /f330dff：同45字节码/shared memfd canonical−alias PFN身份通过，首进程没有selected capture，NOT_EXCITED按合同停止（实际1/计划3）。单纯双映射/PFN相同不保证ptep_set_access_flags事件产生。root/匿名COW的成功不能跳过另一backing的能力/激励门；不循环写同页追事件，不将0capture改成CONT0或hardware aggregation阴性。为什么没触发仍未唯一归因，需新入口的有限方案。最新517完整diagnostic通过。
