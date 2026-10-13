# Gunyah运行接口与TLB物理解释边界（2026-10-13）

## 本次任务的目的（给人类看）

在扩大descriptor-aware容量扫描前，核实目标的虚拟化接口和可观测范围，避免将Linux页表地址直接称machine HPA，或仅根据CONFIG_KVM猜环境。

**实际只读事实**：`/sys/hypervisor/type=gunyah`；`/sys/hypervisor/version/api=1`、variant=81；目标device-tree具有Gunyah兼容项、CONFIG_GUNYAH=y，相关模块与 `/dev/gunyah` 存在。未更改配置、创建VM、发自定义hypercall或读取其它VM。与早期只有KVM配置线索相比，这是已部署Gunyah接口实证；未直接读取HCR_EL2.VM/Stage2页表，不能据此补成具体stage2 granule或HPA identity。

[Qualcomm官方Gunyah说明](https://github.com/quic/gunyah-hypervisor)定义其为独立于guest OS的Type-1 hypervisor；[API中的VMPhysAddr](https://github.com/quic/gunyah-hypervisor/blob/develop/docs/api/gunyah_api.md)属VM物理地址空间，即IPA。公开参考版本与本目标variant81不自动等价：不将81强行命名为文档的Haven48、不从公共source推本目标IPA=HPA。

因此已读的PTE/PMD/PGD child地址与pagemap PFN保持 **Linux guest physical / IPA域** 解释，machine HPA及其stage2映射仍UNKNOWN。`docs/reviews/2026-10-13-tlb-descriptor-graph-results.md` 的同数据PFN、节点闭环、descriptor身份与Linux地址分组仍成立，绝不倒填旧数据；1/32、8/32是Linux地址域的直接关系，不额外认证machine cache着色/连续性。

read-only PMU source清单没有arm_spe，现有SPE/perf物理地址采样入口不可用；这不是硬件永不支持SPE的结论。Cortex-X4 TRM Issue06/r0p3（`../cpu-uarch-ref/docs/Arm_Cortex_X4_Core_TRM_102484_0003_06_en.pdf` §18）对DTLB_WALK/STEP提供总walk/step语义，已查列表未给可直接隔离S1/S2的事件；不伪造S2 counter、不把总步数除常数判stage2页数。内核相关dmesg零匹配可能日志已滚动，不能当hypervisor不存在。

匿名完整事实/原SHA见 `docs/reviews/evidence/2026-10-13-gunyah-observability/read-only-evidence.json`；raw root `data/private/20261013-virtualization-observability/`，唯一capID/地址只private。后续TLB实验继续真实descriptor-aware控制，但需要把组合翻译/descriptor竞争与物理leaf-entry命名分开；取得当前VM合法只读stage2信息是候选路线，未经支持不猜capability ID或修改hypervisor。ROB可继续纯执行/退休方法，参数0/3状态不因接口发现被虚构晋升。owner和触发在 `docs/open-items.md`。
