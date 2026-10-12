# 自有leaf PTE指针的有限能力检查 v1.0（2026-10-12）

## 本次任务的目的（给人类看）

上一 `docs/reviews/2026-10-12-translation-self-read-results.md` /64dcbe4只认证root descriptor。下一只验证是否可安全取得自有leaf PTE指针并读取实际descriptor、与pagemap PFN对账，不猜direct-map偏置，不测容量。

## 新方法与有限合同

目标ptep_set_access_flags符号名可见，[Linux6.1 arm64函数](https://raw.githubusercontent.com/torvalds/linux/v6.1/arch/arm64/mm/fault.c)接收(vma,address,ptep,entry,dirty)；[COW reuse调用](https://raw.githubusercontent.com/torvalds/linux/v6.1/mm/memory.c)是事件来源候选，目标实际触发未验证。用perf-kprobe BPF，先helper14过滤owner TGID，再比较pt_regs.x1==一个selected自有VA，所有helper113在双过滤后；只读参数x2的8-byte PTE、记录x3 requested entry。程序不改PTE。

owned anonymous8192B，两页prefault并读取/proc/self/pagemap；fork child对selected页写一次后exit作为foreign PID负控，父对另一页写一次作为wrong VA负控，父最后写selected页作positive。在此协议COW/reuse可能产生hook，也可能硬件AF/DBM或目标实现不触发：没有事件必须记NOT_EXCITED，不能自动当权限失败或重试强迫触发。pagemap before/after非零present/非swap、selected PFN不变才接受，old PTE及requested entry PFN=(word & ((1<<48)-4096))>>12都须等于实际pagemap PFN，descriptor&3==3；错误/不匹配只保留技术失败，不换页追门。

这会主动改变自有mapping的COW/权限状态，所以任何观察到的CONT位只能归本COW协议时点，不能替旧TLB数据回填CONT=0或认证benchmark稳态无HPA/聚合。physical PTE table identity/parent布局和HPA配置仍未知；任何未来性能采样前彻底卸载observer。

一个ARRAY64B map、一个GPL KPROBE程序、CPU7的perf事件FD，type从sysfs读取、config1为函数名、无tracefs永久配置/无pin。FD关闭事件→程序→map，任何出口/进程终止回收；三fresh进程、15秒固定间隔、每进程30秒界限。精确BTF及MIDR/page先核验，kptr_restrict不改；map/load/perf/attach拒绝记CAPABILITY_UNAVAILABLE并停止，不安装模块或绕过安全配置。

每进程初始及负控map全0、positive恰1capture才可判SELF_LEAF_DESCRIPTOR_READ；hit0=NOT_EXCITED，hit>1或readerrno/类型/PFN/cleanup/bytecode漂移=技术失败。三进程全部positive才关闭本能力；任何第一不合格停止且原样归档，不救门。首次read失败锁存不让后续覆盖。

## 组件与验证

`probes/diagnostic/translation_leaf_bpf.h` 实际指令emitter，`probes/diagnostic/translation_self_leaf.c` native plan/Android loader；`tools/diagnostic/tests/test_translation_leaf.py` 用真实C计划与独立BPF VM作PID/VA双过滤、read失败粘滞、跳界反例。consumer `tools/diagnostic/translation_leaf_analysis.py`，driver/raw入口 `tools/diagnostic/run_sm8650_translation_leaf.py` / `tools/diagnostic/translation_leaf_raw.py`。真实计划→driver→落盘→回读、请求/类型/PFN错/覆盖缺失/未激励/权限拒绝留证；NDK两构建/source/actual launch/bytecode/raw SHA分列。模拟kernel读仅software合同，不是目标证据。

owner=primary，branch codex/sm8650-tlb-hierarchy-r2。本有限能力检查不重放既有TLB曲线；结果和未认证physical项归 `docs/open-items.md`。
