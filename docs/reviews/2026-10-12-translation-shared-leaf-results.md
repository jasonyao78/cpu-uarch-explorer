# Shared-memfd leaf触发资格：NOT_EXCITED（2026-10-12）

## 本次任务的目的（给人类看）

检验匿名COW下已实证的leaf观察入口能否转用于TLB实际shared-memfd alias，防止跨backing暗借能力。

**NOT_EXCITED：计划3进程，首个进程positive hit0后按冻结合同停止，实际只执行1进程；没有重试。** map/load/perf-kprobe attach及读取结果成功，初始/negative/positive map全0，canonical与alias前后两个PFN完全相同、present/not-swapped/unique，部署/BTF/CPU/环境链完整。没有该函数的selected owner/VA capture，故没有leaf descriptor读数；不能把global/config存在当触发成功或把0叫CONT=0。

`probes/diagnostic/translation_shared_leaf.c` / `probes/diagnostic/translation_leaf_bpf.h`；消费 `tools/diagnostic/translation_shared_leaf_analysis.py` / `tools/diagnostic/translation_shared_leaf_raw.py`，driver `tools/diagnostic/run_sm8650_shared_leaf.py`。source2671b5b / buildff87b31 / actual launch8953da2，branch codex/sm8650-tlb-hierarchy-r2；binary SHA `248da08cfdf72b77e2d952a6dea3e51ac96eb33a4dd9c03db089c66bcc8b5b4c`，NDK27.2/API34/static/O2/Werror两build一致，复用45条实际指令，37新旧关联tests通过。

原raw `data/private/20261012T142029Z-translation-shared-leaf/`，10raw SHA、完整stderr与状态保留；匿名 `docs/reviews/evidence/2026-10-12-translation-shared-leaf/validation.json` / `independent-check.json`。第二算术直接raw核对双过滤/实际code、三map全0、两端canonical/alias PFN、完整环境、首不合格停，和消费者一致。所有FD退出回收、无pin/安全设置/内核PTE写；共享数据toy write只属本预注册触发。

这不推翻 `docs/reviews/2026-10-12-translation-self-read-results.md` 的root能力或 `docs/reviews/2026-10-12-translation-self-leaf-results.md` 的匿名COW能力，但限制它们到各自已实证backing/事件。目标共享read→write为何没有capture尚未归因，不能未经反例直接指定HW_AF/DBM为唯一原因。旧TLB/steady CONT/HPA及physical table PA保持UNKNOWN。

下一shared descriptor观察需要新触发/内核入口或安全只读走表证据，先冻结允许读和激励；不能同页重复至出现事件，不因COW已过跳过资格。另推进ROB退休生命周期正交方案 `docs/design/2026-10-12-rob-retirement-drain-next.md`。owner/触发 `docs/open-items.md`；本有限资格结束，整体physical目标未完成。
