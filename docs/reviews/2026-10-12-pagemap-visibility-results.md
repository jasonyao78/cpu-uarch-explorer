# SM8650 pagemap能力检查：通过（2026-10-12）

**通过：三个进程均visible-stable。** 每个47个自有4KiB页、两快照；282条metadata观察全部present/not-swapped，47个PFN非零/unique、前后PFN相等。独立直接raw位运算与18文件SHA全部一致。只证明本权限/本批映射的PFN可见与端点一致，不证明CONT/HPA、窗内无迁移、旧映射PFN或容量。

目的/冻结：`docs/design/2026-10-12-pagemap-visibility.md`。生产者 `probes/diagnostic/pagemap_visibility.cpp` 只读 `/proc/self/pagemap`，不读他人进程，不改系统环境/PTE。三地址族前16页union47页payload188KiB，4GiB只是reserve；MADV_NOHUGEPAGE、AnonHugePages前后0，无PMU测量。absolute PFN及VA均留private；公开结果只含计数与source/raw SHA，见 `docs/reviews/evidence/2026-10-12-pagemap-visibility/capability-result.json` 和独立核对文件。

[Linux官方pagemap文档](https://www.kernel.org/doc/html/latest/admin-guide/mm/pagemap.html)说明权限不足可能使PFN清零；本次用实际非零输出确认能力，未将root或零域冒充可见证书。零域/换出/partial/端点变化均有命名路径和真实producer→driver→writer→raw反例测试。

| 角色 | branch `codex/sm8650-tlb-hierarchy-r2` 的commit / 路径 |
|---|---|
| source | `849f1456dfc865c0d37e4d6c0803632b910ed87f` / `probes/diagnostic/pagemap_visibility.cpp`、`probes/common/pagemap_decode.h` |
| build / consumer | `b16d2e4` / `tools/diagnostic/pagemap_visibility_analysis.py`、`tools/diagnostic/run_sm8650_pagemap_visibility.py` |
| actual launch | `9e42d6a028bab152177e4e71390e2106f4745f07` |
| binary SHA256 | `7ac9d5e1b31c645561977c4a011af44847590d8f751160d81e81fd498128750e` |

raw私有目录 `20261012T024216Z-pagemap-visibility`；两个NDK27.2/API34/O2/Werror/static构建字节一致，native实际plan/纯decode与6项软件测试、3项实际写盘回读测试通过；不把mock当上板。工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`，没有main/remote合并。

**下一行动**：同一memfd backing逐页alias到不同VA集合，核验canonical与各alias的PFN身份/实际offset/order，让数据页物理访问轨迹配对。先冻结后实现/采数；页表descriptor本身的物理布局及指针值引发的预取仍是边界，不把“同PFN”夸成全部cache流量相同。旧PFN/HPA/CONT=UNKNOWN不回填。当前能力结果只打通新实验条件，TLB/ROB总体物理参数仍未全部测得。
