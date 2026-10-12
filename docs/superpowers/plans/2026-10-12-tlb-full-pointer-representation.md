# 全位同PFN表示 Implementation Plan

## 本次任务的目的（给人类看）

执行 `docs/design/2026-10-12-tlb-full-pointer-representation.md`，弥补旧高位mask未改变低位的干预边界，保留旧协议代码/数据。

**Goal:** 在同映射内比较plain/high/full的几何walk差，actual低地址位干预必须成立。
**Architecture:** 新独立MODE/文件，复用旧Space与原始pagemap纯解码；新三mask矩阵与图证书；主full/plain、辅助high/plain和full/high分列。
**Tech Stack:** C++17/NDK27.2/API34/Python unittest/Capstone/adb。当前primary串行执行，无第二设备操作者。

- [ ] `tools/diagnostic/tests/test_tlb_full_repr.py` 先RED：新producer缺失；实际110plan/222layout、54共享FD图逐边decode，full mask的39/48/56-bit及cacheline投影变化；所有同PFN/typed/overflow/IR4/graph反例与主/辅数学金样，反例验证后GREEN。
- [ ] 新 `probes/diagnostic/tlb_full_repr_layout.h` / `probes/diagnostic/tlb_full_repr.cpp`，仅三mask/mode/cell数扩展及实际图，保存原文件；`tools/diagnostic/tlb_full_repr_analysis.py` 检查608 raw/进程与新低位证书，495窗/486门，主full/plain与两辅助分列。小步source提交。
- [ ] 双NDK构建并独立ELF/Capstone动态X17四ISA，实际两plan/两layout核对；输出 `docs/reviews/evidence/2026-10-12-tlb-full-pointer-representation/{build,plan,kernel-audit}.json`，完整源/依赖/plan/binary SHA与recipe，source/build分列。
- [ ] `tools/diagnostic/run_sm8650_tlb_full_repr.py` 只读基线、最新全probe ownership与部署SHA；`tools/diagnostic/tests/test_tlb_full_repr_raw.py` 真实producer计划→driver→writer→raw正例、重哈希graph/PFN/mask冲突、旧mode/覆盖/顺序/环境/入口绕过反例。运行新13项及旧表示/alias相关回归，无共享源码更改不重复无关整树检查；后续合并新ROB代码后再整树验收。
- [ ] 串行495目标窗，独立raw复算全部低位投影、PFN图、比例/DID/主辅/gates，交付完整CSV/SHA/报告 `docs/reviews/2026-10-12-tlb-full-pointer-representation-results.md`；更新目标状态/待办，禁止以阴性唯一排除DMP或以曲线命名物理容量。
