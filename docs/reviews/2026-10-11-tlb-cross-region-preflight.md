# TLB 四域反证的软件出口

## 本次任务的目的（给人类看）

冻结 `docs/design/2026-10-11-tlb-cross-region.md` v1：跨四个256MiB域，用共同victim的I/G1/G3区分有限低位与高位折叠候选。本文只验软件与来源出口，尚不代表34560窗设备结果通过。工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`、branch `codex/sm8650-tlb-hierarchy-r2`，main/远端未操作。

## 已验证事实

- source `7ed6434d846fd49e609097f396a5cdac2cd1161d`；consumer/build `8bd0588a5544936b71891516b395e812749c23b0`。`probes/diagnostic/tlb_cross_region.cpp` / `probes/diagnostic/tlb_cross_region_layout.h` 直接复用原闭合walk，旧组件合同/默认参数未改；全部48cell及顺逆计划、六族几何、四种不对齐/高字节边界host基址、共同victim、4候选的[1,12,1,12]/[1,3,4,12]/[4,12,1,3]数学预测、四域3/3/3/3、PTE项组VA代理与F128真实闭合环均核验。host实际mapped harness按本机16KiB guard对齐，选址仍为4KiB；不会声称它执行了Android backing/PMU路径。
- NDK27.2.12479018/API34静态O2/Werror双构建同SHA `2ac083ee8e7905925cb8f20097c329a7fced2786e784056797b2004a28124a95`。`docs/reviews/evidence/2026-10-11-tlb-cross-region/` 登记全部source依赖、完整真实plan/build与measured-window反汇编。实际末次F之后只有既得寄存器/读snapshot/沿竞争或victim指针加载；准备metadata与target prefault在窗外，包装背景仍以W1门处理，不声称零开销。
- 消费 `tools/diagnostic/tlb_region_analysis.py`、驱动 `tools/diagnostic/run_sm8650_region.py`：真实C++计划/几何→已提交driver→writer→raw回读5进程/34560窗软件正例通过，21类重哈希/身份/来源/几何/窗口/环境损坏拒绝；首坏geometry只执行1进程，故意绕过audit_process会被回归抓住。外部执行/PMU明确模拟，不能当本机Linux或设备证据。路径 `tools/diagnostic/tests/test_tlb_region.py`、`tools/diagnostic/tests/test_tlb_region_raw.py`。
- 10项新测试、fresh完整diagnostic **317/317（148.045s）**。日志 `/tmp/tlb-region-targeted-full.log`、`/tmp/tlb-region-full-regression.log`。同本轮未改的runner203/203、正式analysis250/250、CTest21/21已fresh通过（`/tmp/rob-resident-*-regression.log` / `ctest.log`）；新增独立探针无formal schema/CMake接入，不冒称其Linux路径被macOS CTest覆盖。
- 反例曾只降低16个重复中的一条，仍在预注册平均激励范围内；已改为真正越过该均值门的整pass低激励，不改阈值救门。原字节维护ROB有限批已经结束，TLB driver会在新启动时重新核独占设备/unfinished journal/环境、逐步先审计再推进、完整stderr/退出码落盘；科学不合格不补样，端点不证明窗内恒频。

代码/软件出口通过；设备结论须随后五个完整新mapping和直接第二算术。PTE/CONT/PFN未实读，页表项组只为匹配代理，禁止升级为唯一hardware hash或物理ways。
