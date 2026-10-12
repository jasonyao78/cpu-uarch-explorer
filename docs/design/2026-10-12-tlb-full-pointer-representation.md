# TLB同PFN全位指针表示对照（冻结v1，独立新协议）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-tlb-pointer-representation-results.md` 的333窗高位编码阴性不能排除利用低位的指针识别：mask低48位全0。本新协议把plain、高位XOR和全位XOR放入**同一physical/VA/offset/order图**，询问几何walk差是否对真正改变地址低位的存储表示敏感。旧协议/数据保持原形，不升级旧阴性为DMP排除。

复用同memfd Space；新 `probes/diagnostic/tlb_full_repr_layout.h` / `probes/diagnostic/tlb_full_repr.cpp`。三个mask：plain=0、xor-high=0x00a5000000000000、xor-full=0x9e3779b97f4a7c15。same静态LDR/EOR X17/SUBS/B.NE body；full同时改变39/48/56-bit地址投影及64-byte对齐投影，before/after实际存储字必须逐节点验证此干预，并仍解码为同一需求地址。并非认证内部DMP一定关闭；内部解码、投机、XOR-zero消除和decode资源仍是残余解释。

## 原样复用的合同与变化

CPU7/MIDR0x410fd821/4096页，baseline walt只读、同data PFN/全部raw pagemap位/smaps4KiB/no huge证据，per-cell闭环、六GROUP+ID pinned noMUX事件[0x11,0x08,0x05,0x34,0x8154,0x8155]均沿前一冻结协议。Arm事件来源及目标revision caveat见 `docs/design/2026-10-12-tlb-pointer-representation.md`，tap不是DMP专属或完备观测。

N={1024,1792,2048}、dense/spaced257i/balanced-random、两visit order、三表示相邻配对；55cells（54非空+1floor），每cell3round/同量warmup，load=N*ceil(1048576/N)，三fresh进程顺/逆/顺，**495窗，486背景门，608条JSONL/进程**；固定15秒进程间隔，不改sysfs/THP/内核；异常即停。

## 主判据及辅助判据

技术/背景/pressure/IR4*loads守卫完全沿前冻结合同；full新增实际图39/48/56bit及cacheline对齐低位差证书。背景失败优先INCONCLUSIVE。plain在N≥1792至少一个shape/N六配对全≥.10几何差才有基线复制，否则BASE_GEOMETRY_NOT_REPLICATED。

主：D_full−D_plain，D=对应shape相对dense的3round总walk/总load差。每shape∈{spaced,balanced-random}/N六epoch/order同符号绝对≥.10为复制，任一复制→GEOMETRY_CONTRAST_REPRESENTATION_SENSITIVE；全部|DID|<.10→GEOMETRY_CONTRAST_NOT_CHANGED_AT_DETECTION_SCALE；其余INCONCLUSIVE。辅助原样给D_high−D_plain、D_full−D_high、各表示plain→encoded带符号walk/cycles/tap变化；不看结果改变门/主辅顺序。

阳性只说明完整地址位的存储表示参与现象，不唯一命名DMP；阴性只约束本次编码/检测尺度与直接利用原始地址投影的简单解释。物理descriptor、CONT/HPA、实际entries/ways/hash仍不自动关闭。完整保留所有窗、失败、signed effects和原raw/SHA，不能挑点救门。

consumer `tools/diagnostic/tlb_full_repr_analysis.py`、driver `tools/diagnostic/run_sm8650_tlb_full_repr.py`、tests `tools/diagnostic/tests/test_tlb_full_repr*.py`、evidence `docs/reviews/evidence/2026-10-12-tlb-full-pointer-representation/`；actual plans/layout/shared-FD全部54图、独立低位干预与程序字验证、双NDK、producer→writer→raw反例后上板。不同source/build/launch/report commit；owner=当前primary独占设备，branch `codex/sm8650-tlb-hierarchy-r2`。
