# 同PFN指针表示 Implementation Plan

## 本次任务的目的（给人类看）

实现 `docs/design/2026-10-12-tlb-pointer-representation.md` 的可推翻对照；当前primary在已存在r2 worktree串行完成，不派第二设备操作者，用户持续授权替代例行人工检查点。

**Goal:** 判断相同物理需求轨迹的几何walk差是否随存储指针表示改变。
**Architecture:** 复用旧Space/pagemap/GROUP解码纯能力，新cell矩阵与严格图证书；新consumer独立从原始数据验证实际解码图，再统计差分之差。
**Tech Stack:** C++17、NDK27.2/API34、Python unittest、Capstone、adb。

- [x] 写 `tools/diagnostic/tests/test_tlb_repr.py`：真实C++计划/layout与oracle一致；host页粒度共享FD上全部36图实际链路；任意stored word/PFN/mask/IR/order/缺失/重复冲突拒绝；敏感/小差/混合/空窗失败/基线不复制金样。运行 `.venv/bin/python -m unittest discover -s tools/diagnostic/tests -p 'test_tlb_repr.py'`，新增组件缺失先RED。
- [x] 实现 `probes/diagnostic/tlb_pointer_repr_layout.h`：Cell(trace, representation,mask)，`next^mask`写入同一Space，native实际decode图必须回head。实现 `probes/diagnostic/tlb_pointer_repr.cpp`：动态X17且同一4ISA body，per-cell全部图/页面证书before+after、三窗计数与头闭合；失败空metrics+结构化reason。旧alias源码不变。
- [x] 实现 `tools/diagnostic/tlb_repr_analysis.py`：严格类型身份、410行raw/进程、before/after stored图独立decode、相对metadata；333窗/324背景门，plain基线复制后才DID主判，prefetch gate单独命名。完成真实码形与数学GREEN，source小步提交。
- [x] 双NDK静态构建，两个actual plan/layout独立oracle比对，反汇编核验LDR/EOR-register/SUBS/B.NE及参数传入；source/hash/plan/recipe记录 `docs/reviews/evidence/2026-10-12-tlb-pointer-representation/{build,plan}.json`，source/build分列。
- [x] 实现 `tools/diagnostic/run_sm8650_tlb_repr.py`，复用只读基线/所有已知probe ownership/部署哈希，complete/stopped raw原样落盘；`tools/diagnostic/tests/test_tlb_repr_raw.py` 必经真实producer→driver→写盘→audit原始形状，mock仅外部counter和adb。包含绕过消费入口、改完SHA仍图冲突、顺序/身份/环境/模式/源码绑定反例，运行两文件测试后整树diagnostic回归并提交launch基线。
- [x] 上板333窗，所有异常停止，不修数据。直接raw第二算术复算全部D/DID/ratio/gates/图PFN身份；完整匿名CSV、raw SHA、图与 `docs/reviews/2026-10-12-tlb-pointer-representation-results.md`。更新README/goal ledger/open-items；阴性和不合格均有限终态，物理参数未知不得改名完成。按结果推进下一正交研究。
