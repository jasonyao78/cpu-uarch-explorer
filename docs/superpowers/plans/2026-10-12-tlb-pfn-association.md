# 同VA与同物理需求轨迹的PFN关联控制 Implementation Plan

## 本次任务的目的（给人类看）

执行 `docs/design/2026-10-12-tlb-pfn-association.md`，用实际0物理邻接的配对干预和有限局部reach检验连续PA解释，保留虚拟顺序残余。

**Goal:** 真实297窗，负控激励单独裁定，不能回填physical entries。
**Architecture:** 独立布局/C++producer、consumer与driver；π保留mod64并单调移除bad边；复用纯GROUP与四ISA，不改变旧协议。
**Tech Stack:** C++17/NDK27.2/API34/Capstone/Python unittest/adb；单primary串行设备。

- [x] 在 `tools/diagnostic/tests/test_tlb_association_layout.py` 写RED：布局文件缺失；C++实际输出π，N8点、连续/逆序/乱序/带gap/边界u64 PFN，断言bijection/mod64/全部0adj，重复/不可见/越界拒绝。
- [x] 新 `probes/diagnostic/tlb_pfn_association_layout.h` 实现该纯布局契约，真实host memfd映射用π对应同VA line集合/物理图；GREEN后只提交本任务source。
- [x] 新producer `probes/diagnostic/tlb_pfn_association.cpp` / 实际映射 `probes/diagnostic/tlb_pfn_association_space.h` 与 `tools/diagnostic/tests/test_tlb_association.py`：真实plan/graph/PFN前后/smaps/kernel入口，统计主差与删失/非单调金样，缺/重/typed/错IR硬拒绝，完整private raw观测、public匿名计数。
- [x] 新 `tools/diagnostic/tlb_association_analysis.py` / `tools/diagnostic/run_sm8650_tlb_association.py` 生产链；`tools/diagnostic/tests/test_tlb_association_raw.py` 实际plan→driver→写盘→raw，重哈希反例/别名PFN/mapping不一致/未激励阴性命名；不绕过消费者。
- [x] 双NDK/独立反汇编+真实图审计，recipe/binary/source/plan绑定；运行新测试及相关旧reader回归，冻结launch后等ROB设备块结束再串行297窗。
- [ ] 独立raw第二算术校验每窗/每gate/π/主判定/全部reach曲线，保存完整SHA/CSV/图/报告；更新README、ledger、open-items与授权记忆，原失败和physical未知不晋升。
