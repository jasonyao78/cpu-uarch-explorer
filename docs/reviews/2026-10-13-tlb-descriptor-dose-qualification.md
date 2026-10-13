# 描述符剂量独立资格通过（只N32，不是容量结果）

## 本次任务的目的（给人类看）

在新stride5／515布局下独立验证descriptor-bound ordinal graph和PMU阴性，不能借旧stride3资格；下一固定1536leaf剂量扫另有预注册判据 `docs/design/2026-10-13-tlb-descriptor-dose.md`。

**DOSE_GRAPH_QUALIFIED**：3/3fresh、192/192初始观察、36/36PMU窗；18data窗walk全部0、IR4±.001／I背景门全过。LinuxleafPT pages每process1/32、leaf64B groups20/32、Pmd groups1/4，foreign/wrongVA／sticky逐node gate，observer全FD卸载后计数。20rawSHA、独立原JSONL逐node VA/word/PFN/request与各窗重新核对。表PA是LinuxPA/IPA，CONT只安装时点；资格不能作2048／ways／HPA／sethash认证。

branch `codex/sm8650-tlb-hierarchy-r2`；sourcef997cb7/buildc1256db/实际launch `ac1903f0e3debd456de30799ce99c3c971bc91b3`；binarySHA `00955f97ab0541bb557cdfeaa6518fcb43f23c9e1a35ef40775f17d5ed7b2fa4`。NDK27.2/API34双构建同字节、28actual C layouts、实际ELF四指令核心、BPF102/32 words验证，15项production-chain测试通过（mock外部计数，不当target）。组件 `probes/diagnostic/tlb_descriptor_dose.c`、`tools/diagnostic/tlb_descriptor_dose_analysis.py` / `tlb_descriptor_dose_raw.py` / `run_sm8650_tlb_descriptor_dose.py`。private `data/private/20261013T110007Z-tlb-descriptor-dose-qualification`；public对应evidence/qualification-analysis.json与qualification-independent-check.json。完整674回归尚运行，不先声明通过。

下一正式27process（3×before-floor+7dose+after-floor），324窗64,896安装观察，锁定本三qualification原文件SHA与同二进制；原门与pred169→173不调整。thermal／技术first failure停止留证，不捡数据拼接。环境原样，未产生事务或修改globalsetting。
