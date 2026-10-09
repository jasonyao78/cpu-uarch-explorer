# ROB 局部同步THP合并与完整资格（冻结v1）

## 本次任务的目的（给人类看）

`docs/design/2026-10-09-backing-observation.md`的一次仪表复现已取得完整smaps字段：256MiB中224MiB为AnonHugePages，Rss256MiB、Swap0。因此该次初始失败属于完整THP覆盖谓词，不是打开/解析失败；这并不追溯证明旧256/512失败同根因。现检验对探针自身映射调用一次`MADV_COLLAPSE`能否稳定建立完整大页，然后复算原长load资格。根Agent独占手机、用户持续授权，TLB/ROB串行。

## 第一性原理与来源

TLB翻译本身不能成为ROB长load锚点的主要混杂，因此仍需实际大页与低walk，而不仅是MADV请求。Linux6.1的[UAPI常量25](https://raw.githubusercontent.com/torvalds/linux/v6.1/include/uapi/asm-generic/mman-common.h)与[madvise实现](https://raw.githubusercontent.com/torvalds/linux/v6.1/mm/madvise.c)提供同步合并操作；只对调用进程已有匿名范围生效，返回成功不替代smaps验收。目标Android6.1分支是否实现、是否能分配由实际返回值与观察决定，不能从版本号假定。此操作可能涉及局部内存整理；不写任何THP/defrag/频率sysfs。

## 软件与有限矩阵

`docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`新增显式`--collapse`，仅允许miss+thp2m。在环初始化之后、初始验收与任何PMU窗之前，对整个映射**固定仅调用一次**MADV_COLLAPSE。输出`backing-collapse`的pre/post状态与可解析实际字段、请求bytes、return_code和errno。调用失败或post覆盖不合格立即结构化失败，metrics={}；不继续尝试、不静默回退、不更改原backing谓词/JIT。成功config仅在本flag下增加collapse_requested=true，旧配置输出保持兼容。

`tools/diagnostic/run_sm8650_minimal.py`新mode=`rob-collapse-qualify`，独立完整4进程24窗：e0热1MiB4K→256MiBTHP+collapse；e1逆序。N0/NOP/seed42/alignment0、i=max(131072,MiB×8192)、三轮sameVA paired P/S、CPU7/type8；事件0x11/08/03/17/34/37。每进程固定15秒冷却再检查原环境。初始失败停整块；全部实际THP/退休/无mux/环境/SHA门与原资格矩阵相同。旧单epoch与stopped批次不拼入。

消费路径必须核验collapse_requested贯穿请求→config→summary→qualifier，并审核collapse唯一记录与PMU前位置、return_code/errno及post与initial_info一致。`tools/diagnostic/analyze_long_load.py`显式接受新mode，仍逐epoch/member/round使用`c93e788`原科学门，256在两epoch独立通过才允许有限N扫描。技术停块与科学门失败分开；若失败不反复启动该矩阵来追门，转小足迹地址编码/访问次序对照。

## 命名与工件

即使资格通过，仅称低翻译干扰、远层miss主导的双长load候选；不是DRAM或物理ROB条目证明。分支`codex/sm8650-tlb-hierarchy-r2`；源码、启动、binary、build/protocol/driver及raw SHA分开登记到`docs/reviews/evidence/2026-10-09-local-collapse/`，raw仍仅私有。失败保留所有实际值；未识别根因/物理ROB归属与触发记录`docs/open-items.md`。
