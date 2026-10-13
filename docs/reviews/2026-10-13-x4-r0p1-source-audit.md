# 目标修订匹配的官方TRM核验：规格、实测和未知量分开

## 本次任务的目的（给人类看）

目标MIDR=0x410fd821，对应Arm D82 r0p1。此前本地资料为r0p3；现在找到官方r0p1 Issue04，补上修订匹配，避免重复黑盒识别已公开规格，同时不替代实测和地址映射研究。branch codex/sm8650-tlb-hierarchy-r2；核验起点7a54c9b。资料来源 [Arm官方PDF](https://documentation-service.arm.com/static/6473ef18bae17b773b05d1e8)，证据元数据 `docs/reviews/evidence/2026-10-13-x4-r0p1-source-audit/source.json`。

## 已核对的文档事实

|项目|官方位置（印刷页）|结论／边界|
|---|---|---|
|L2统一TLB|§6.1表6-1，61；表10-32，91|2048项、8路；RAMID0x18，Way0–7、Entry0–255，相互支持256×8组织。RAM地址不是VPN选择函数。|
|L1数据TLB|表6-1，61；表10-7，82|96项全相联，两表一致。|
|L1指令TLB|表6-1，61；表10-4，81|128与Entry0–47相矛盾；保持文档冲突，不选择128或48作为已确认目标值。|
|硬件合并条目|§10.2.3表10-43/44，94–96|IDATA0[6]合并标志，[5:2]四有效位；四页PA低位字段。该格式不是Linux PTE.CONT，不披露分配条件。|
|描述符／walk cache|表6-1，61；表10-45，96|L2可容纳中间描述符PA，IDATA1[46]标记walk-cache entry；2048不是保证全部供leaf占用。|
|文档位宽冲突|表10-44，95|[53:28]与PA[47:14]宽度不等，视觉核对仍如此；不据此推导目标HPA宽度。|
|RAM直接读取|IMP_IDATA0_EL3访问伪代码，372|EL0/1/2未定义，EL3可读。普通root不是EL3；本任务不尝试特权指令或固件修改。|

## 如何更新我们的解释

`docs/reviews/2026-10-13-tlb-observed-reach-scan-results.md` 的18process/52,416安装观察/216PMU窗仍成立：相同data PFN、访存顺序和VPN低8位直方图，N1536 packed近零walk、spaced近1，初始Linux leaf PT pages分别9和1536。新资料说明合并条目和walk-cache占用是必须继续区分的候选；不能仅由CONT0或访存序列不连续排除合并。

公开规格可报告：L2 2048项、256sets×8ways；L1d96全相联。目标黑盒证实、VPN/ASID/descriptor set选择函数、有效leaf容量分配仍未完成。ROB物理容量没有因此获得证据，第三方384继续只作候选。进度采用两张清单：公开L2容量／组织规格2/2有修订匹配依据；独立物理识别三项目标仍0/3，不把规格核验与黑盒测量混算成百分比或承诺剩余天数。

完整PDF9,383,340bytes、1365pages，SHA256=d978da9c87a4ca267b81000b2f2ca4f82d182f0d4b13189e06e6511ba9492802；Poppler全文与上述六页1500px渲染均核对。完整原件仅私人参考缓存 `data/private/references/Arm_Cortex_X4_Core_TRM_102484_0001_04_en.pdf`，不入Git。最初超时的partial PDF和截图cache miss不作证据；没有改cpu-uarch-ref。新增材料索引 `docs/reference-materials.md`。后续合并激励、walk-cache占用、set选择及ROB资格均登记 `docs/open-items.md`。
