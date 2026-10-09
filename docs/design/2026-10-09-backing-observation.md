# ROB backing失败观测（冻结v1）

## 本次任务的目的（给人类看）

512MiB与固定256MiB初始验收均曾输出`chase-backing-not-thp2m`，旧记录无实际smaps值，不能把它猜成同一根因。当前在`codex/sm8650-tlb-hierarchy-r2`补失败观测，然后仅做一次带仪表的256MiB复现。用户授权持续推进，根Agent独占手机；不改变内核THP/defrag/频率，不重复直到成功。

## 变更与有限动作

`probes/common/rob_backing.h`新增生产`rob_backing_inspect`，仍调用原精确VMA解析与同一验收谓词；`docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`的初始/每窗失败使用命名状态，parsed实际字段保留，解析或I/O失败为null。保持旧failure.reason与metrics={}；不回填旧失败，也不改变成功config/runtime/round或JIT指令。

`tools/diagnostic/run_sm8650_minimal.py`显式mode=`rob-backing-observe`：单进程CPU7/type8、256MiB/N0/NOP/seed42/实际THP2MiB、i2097152、同VA paired各3轮、事件0x11/08/03/17/34/37。先固定15秒冷却与环境检查。若初始验收失败，正常技术停块且保存失败状态及实际观察；若通过，保留完整6窗，仅描述该次配置，不晋升成双epoch资格，不拼旧单epoch前缀、不进入N扫描。来源/NDK/binary/driver/protocol/原始SHA按注册绑定。

## 解释边界与后续

`coverage-mismatch`只证明完整字段被解析且原验收谓词失败；逐项比较AnonHugePages、Rss、Swap、no_huge、PMD与Kernel/MMU粒度，不能仅凭状态断言碎片化。`smaps-parse-failed`说明未取得完整精确VMA信息，仍需区分VMA边界与字段错误；`smaps-open/close-failed`分别命名I/O层。公开观察不含VA/PFN/设备标识。

最小回归先RED后GREEN：真实生产helper的部分THP保留huge2048/rss4096，缺字段输出null；实际NDK编译与旧成功JSON/生成码测试。未解决物理ROB与THP可用性继续由当前负责人在`docs/open-items.md`登记；若实际THP不稳定，不靠扩大足迹追资格，改小足迹地址编码/访问次序对照另案冻结。
