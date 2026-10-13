# 实际TLB地址链与descriptor布局连接资格（2026-10-13）

## 本次任务的目的（给人类看）

把已经验证的单页BPF观察能力绑定到真正共享物理数据页的两条地址链，为容量/set-way下一步提供直接descriptor身份，而不是只按VA猜父项。

**DESCRIPTOR_GRAPH_BOUND，通过3/3新进程、192/192逐节点capture。** 每capture foreign child与wrong VA负控0、entry1/return1，installed leaf PFN匹配canonical/node及两端pagemap；两个布局的32-data-PFN及stored ordinal/physical visit order完全相同，固定4ISA LDR/MADD/SUBS/B.NE、每layout512loads闭环。observer全部FD关闭后才执行链核验，不采PMU或宣称小N容量。

实际parent/leaf descriptor的Linux PA分组如下，三进程均复制：

| 布局 | data PFN | leaf table pages | leaf descriptor64B lines | PMD table pages | PMD descriptor64B lines |
|---|---:|---:|---:|---:|---:|
| packed | 32（两布局相同） | 1 | 8 | 1 | 1 |
| spaced | 32（两布局相同） | 32 | 32 | 1 | 4 |

root kernel virtual line同一、mm/pgd与两个层级地址关系一致；不由关系反推未观测的PGD物理PA。192节点初始安装CONT均按原字段保存，三进程各布局值见完整证据；不回填steady CONT/旧数据。Linux descriptor PA不是machine DRAM/EL2 HPA证书。

branch codex/sm8650-tlb-hierarchy-r2，source73dbc19/buildf7e0d93/actual launch84b8568；binary `8981924d443d36025a8976b805d9dfce3053043fb415466587a903356f9f2fd6`，NDK27.2/API34/static/C11/O2/Werror两次构建一致；实际binary固定kernel4words已独立decode，exact-VA entry99/return32原emitter不改。代码 `probes/diagnostic/tlb_descriptor_graph.c` / `probes/diagnostic/translation_install_bpf.h`，严格消费 `tools/diagnostic/descriptor_graph_analysis.py` / `descriptor_graph_raw.py`，driver `tools/diagnostic/run_sm8650_descriptor_graph.py`，冻结 `docs/design/2026-10-13-tlb-descriptor-graph.md`。

15项新producer/consumer/driver测试与46关联回归通过（23.428s），实际producer纯门函数经host动态库攻击确保首坏停止；真实plan→BPF emitted VM→registered driver→writer→immutable source重编原计划及rehashed损坏拒绝，software模拟不当目标证据。初始SUBS元数据误值和缺失首坏C门在上板前被失败测试挡住并修复，不记录成硬件异常。

private raw `data/private/20261013T015456Z-tlb-descriptor-graph/`，所有绝对kernel VA/PFN与逐节点计划保留，公开 `docs/reviews/evidence/2026-10-13-tlb-descriptor-graph/validation.json` / `independent-check.json` 仅匿名谓词/计数/SHA；20raw文件SHA、192个capture、所有链闭环及页表PA分组由第二算术直接读取原值核对，三owner PID不同，和consumer一致。

距离目标：descriptor可读→同实际链身份绑定这项必要连接已完成，但TLB物理capacity/set-way和ROB capacity最终参数仍0/3定案。下一另冻结large-N转折及固定VA/data-PFN、改变实际PTE-table PA关联的干预；只有真实layout激励/工作集与control通过才比较。原高位/全位pointer阴性、PFN关联NOT_EXCITED、old reach/proxy/ROB终态不覆盖。本小N资格不产生capacity/ways/hash数字，owner/触发 `docs/open-items.md`。
