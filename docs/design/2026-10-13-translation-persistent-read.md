# 自有页表persistent observer v1.0（有限能力冻结）

## 本次任务的目的（给人类看）

先证明一个不重复load/attach/fork的观察器能按逐次登记的exact owned VA获取真实descriptor，为large-N及固定VA/dataPFN的PTE-table关联干预降低准备开销。此前32图绑定成功 `docs/reviews/2026-10-13-tlb-descriptor-graph-results.md`；本协议只有8节点×3fresh，不计PMU/不命名容量。

选项：逐node现有entry99/return32保真但开销随大N；一次跨kernel全局读扩大权限不可取；采用private未pin array map新增一个request VA word，PID仍编译常量，exactVA匹配后才读own fault/mm/pgd/PTE。root index由已匹配selectedVA算((VA>>30)&511)*8，不猜PA-to-VA。单pair程序/单map在8节点期间持有、完成即全close，性能窗口另程序且必须先卸observer。

## 代码与输入生命周期

`probes/diagnostic/translation_persistent_bpf.h` 与 `translation_persistent_read.c`，map136B=原16结果word+requestVA。helper14先过滤TGID，helper1 lookup private map后仅读取ctx.requested VA，与map.word16比较；不符则退出、无helper113。匹配后原六stage entry/单stage return读取不变；root offset为实际selectedVA动态算术。return只接受stage11、entry1、非零PTE；失败/sticky/duplicate stage99不会被另一次call覆盖。每次更新request仅在上一次完整gate通过之后；所有原始read/首次坏节点保留，禁止回填/跳坏节点。

8个shared memfd canonical pages，alias每页guard，storedword=0x12340000+node。child exactVA负控仅在第一node做一次（PID常量及程序不再变化），每node parent wrongVA负控（fileoff=node^1，guard避免fault-around）。initial/request/negative/positive/raw before-after canonical及alias PFN、parent类型/index/两级关系/同mm/pgd必须通过。全部观察器FD关闭并记录最终pagemap；无pin、无全局security/频率/THP写入，页表变化只由正常owned fault产生。

## finite门与停止

每process8captures，共3fresh/24；15秒间隔，120秒每process；BTF/MIDR/page/cpu7/环境端点现合同。实际emitted字节+immutable host plan+32/39-bit动态VA算术VM正负/故障锁存/重复/pair测试，再两NDK与正式driver/raw链后上板。首次技术/环境失败或NOT_EXCITED停，不重试新VA追门；3/3完整才 OWNED_PERSISTENT_DESCRIPTOR_READ。任何一项过不认证machine HPA/steady CONT/ways/capacity，也不回填旧32图或其它raw。

后续把这个已验证emitter连接到large-N实际graph，逐节点参数与实际计划/字节身份绑定，观察器卸载后才测统一PMU循环；fixedVA/dataPFN的allocation-order实验另冻。追踪 `docs/open-items.md`，branch codex/sm8650-tlb-hierarchy-r2，primary独占。
