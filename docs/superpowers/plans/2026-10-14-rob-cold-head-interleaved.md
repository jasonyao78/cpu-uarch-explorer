# 同映射冷热与真实head偏移实施计划

## 本次任务的目的（给人类看）

执行已冻结 `docs/design/2026-10-14-rob-cold-head-interleaved.md`，用同进程hot/cold与offset0/1024反证v1缓存剂量模型，资格通过后另冻capacity实验。

用户指定primary单代理内联执行，无常规审批；使用executing-plans/TDD/verification。固定r2分支，不操作main/remote。

- [ ] 原生RED：新producer生成512state schedule、两head真实地址链；packet decode512并保留256；冲突state/重复/缺窗必须拒绝。
- [ ] producer `probes/diagnostic/rob_cold_head_interleaved.c`：复用原短ROI ISA与FD包络，member16轮转/分块反序；head地址统一从mapbase+offset计算，munmap mapbase；state写入warm/formal/invalid/rejected。
- [ ] consumer `tools/diagnostic/rob_cold_head_interleaved_analysis.py`：actual native plans逐词比对、current index、LinuxPFN/地址/内容链、512完整度、same-trial state冷热配对；offset1024原资格主门、offset0全列，所有资源键含state。
- [ ] controller `tools/diagnostic/run_sm8650_rob_cold_head_interleaved.py`：复用独占/环境/双journal与durable finally恢复，16process固定8192formal/32768warm。
- [ ] 运行 `.venv/bin/python -m unittest tools.diagnostic.tests.test_rob_cold_head_interleaved tools.diagnostic.tests.test_owned_roi_packets`；旧consumer重读v1真实raw保持原失败。提交仅本任务source。
- [ ] NDK27.2.12479018/API34静态双构建SHA相同；实际native两套index每组合plan逐词一致并解码AArch64 words；build.json/plan.json绑定source commit与全依赖SHA，再小步提交。
- [ ] 上板：controller严格查已提交source/build/plan、13旧事务restored/runner unfinished空/target idle/perf0；记录launch HEAD、binary/raw SHA。期间串行，无补样或retry。
- [ ] 核验全部8192/32768窗口、每条PMU算术/FD包含、双epoch/offset所有原门与signed差、restore/readback0；报告通过/不通过及物理ROB UNKNOWN。更新README/open-items/工作流及授权memory补充。
