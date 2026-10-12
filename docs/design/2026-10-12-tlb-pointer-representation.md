# TLB同物理页指针表示对照（冻结v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-tlb-shared-alias-results.md` 已显示同data PFN下VA几何仍改变walk。下一只干预内存存储表示：保持同一进程/物理节点/VA集合/offset/访问顺序，将next指针存为`next XOR mask`；同一条LDR/EOR/SUBS/B.NE循环使用mask=0或0x00a5000000000000。询问**几何walk对比是否随存储表示改变**，不将阳性唯一归因DMP，也不以阴性排除全部预取。

备选：直接PTE/descriptor属性观测需要额外系统接口；无指针算术轨迹改变依赖链与需求访存控制。先选择可逆进程内XOR对照；0-mask可能被内部消除、非零mask增加依赖或改变投机，均为残余解释。TBI与“数据看起来像地址”的内部判定未认证，不声称mask一定关闭DMP。旧3ISA alias数据不晋升本4ISA协议。

## 激励、实际证据与有限预算

复用 `probes/diagnostic/tlb_shared_alias_layout.h` 的同memfd三arena2560节点映射，不修改其旧契约。新 `probes/diagnostic/tlb_pointer_repr_layout.h` / `probes/diagnostic/tlb_pointer_repr.cpp`：dense/spaced257i/balanced-random，N={1024,1792,2048}，两独立随机visit order，plain/xor相邻配对，37cells（36非空+1空窗），3round/每cell，三个fresh进程顺/逆/顺，**333目标窗**。每cell load=N*ceil(1048576/N)，等量warmup；同PFN/head/全部stored words及解码后的完整闭环链在before/after核验。canonical和alias原始pagemap位、PFN、smaps四区4KiB/zero huge指标全量保留，绝对地址/PFN仅private。未访问的预留页不是激励。

CPU7/4096/MIDR0x410fd821，baseline walt只读环境，不改sysfs、THP、内核。每进程间15秒固定间隔，异常即停保全raw。一次安装的静态解码循环，两表示仅X17值不同；NDK反汇编必须看到相同4ISA body且EOR使用寄存器mask，不能被编译成两个循环。常规JSONL诊断形状，不冒充正式schema-v2。

六事件固定为cycles0x11、IR0x08、L1D_TLB_REFILL0x05、DTLB_WALK0x34、L1D_CACHE_HWPRF0x8154、L2D_CACHE_HWPRF0x8155；GROUP+ID pinned/user-only/noMUX/noRESET。Arm TRM 102484_0003_06/r0p3及官方文档 https://documentation-service.arm.com/static/6473ef18bae17b773b05d1e8 支持事件名称；目标r0p1差异保留，既有P0″正控见 `docs/superpowers/plans/2026-09-28-sm8650-x4-p0prime-demand-prefetch.md`。这两tap不是全部translation prefetch/DMP流量的完备观测；本次若未激励，命名NO_PREFETCH_COUNTS_IN_MATRIX，不能当预取关闭证据。

## 判据预注册

技术硬门：actual计划/事件/kernel IDs、每窗口实际head回到原位、完整stored-word解码图及before/after PFN一致、IR约4*loads（误差max1000/1%）、enabled=running>0。任一失败不得进统计。非空窗背景门：空窗中位cycles≤.01*本窗cycles；L1refill/walk空窗中位≤.001*loads；本窗L1refill/loads在[.75,1.25]。预取背景独立检查≤.001*loads，未过只降级辅助tap，不删除walk结果。

每epoch/order/N/representation计算3round总walk/总load；在每shape∈{spaced,balanced-random}与dense之间取几何差D。plain在N≥1792至少一个shape/N须六个epoch/order对比全≥.10，否则主状态BASE_GEOMETRY_NOT_REPLICATED。对每shape/N取差分之差`D_xor-D_plain`：全六≥.10或全六≤-.10定义复制的表示敏感几何差；任一复制则主GEOMETRY_CONTRAST_REPRESENTATION_SENSITIVE。若全部比较绝对值<.10则GEOMETRY_CONTRAST_NOT_CHANGED_AT_DETECTION_SCALE；其余INCONCLUSIVE。背景失败优先INCONCLUSIVE，不以平均值洗掉失败。

辅助给出同shape/N plain→xor的walk/cycles/tap变化及全部带符号差；all round原样保留，tap可以>1，不强行解释为概率或demand分解。物理entries/ways/hash、actual CONT、HPA、DMP唯一归因均保持未认证。读者能看见技术/科学结果分别通过与否；不修改门、不因本次阴性再追同协议。

## 文件、实现与闭环

consumer `tools/diagnostic/tlb_repr_analysis.py`、driver `tools/diagnostic/run_sm8650_tlb_repr.py`、tests `tools/diagnostic/tests/test_tlb_repr*.py`、build/plan/code audit与结果 `docs/reviews/evidence/2026-10-12-tlb-pointer-representation/`。先真实native producer/host共享FD图，再独立oracle、双NDK、producer→driver→写盘→raw合成负例及整树回归；外部PMU mock不当手机证据。source/build/launch/report各有commit/SHA。owner=当前primary独占设备，branch `codex/sm8650-tlb-hierarchy-r2`；未竟归 `docs/open-items.md`。
