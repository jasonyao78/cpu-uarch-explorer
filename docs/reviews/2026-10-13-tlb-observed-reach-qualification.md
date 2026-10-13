# 实际descriptor/PMU连接N0：通过（2026-10-13）

## 本次任务的目的（给人类看）

确认actual graph/descriptor/PMU生产链，资格通过再扩大N。合同 `docs/design/2026-10-13-tlb-observed-reach.md` v1.0。

**OBSERVED_GRAPH_QUALIFIED**：3fresh/192捕获/36窗口/20raw SHA直接JSONL第二路径精确；两shape所有datawalk0、IR约4/load、原取指门均过。实际same32-dataPFN/storedordinal/order，3/515page奇步长；leaf-table-pages1/32、Linux leaf64B groups12/32、PMD64B groups1/4，安装CONT全部0，仅时点证据。observer卸载后固定15秒冷却、warm在counter外。pagemap端点不认证中途迁移/steady PTE状态；Linux PA/IPA不认证HPA/物理容量。

辅助（非主预注册）L1D refill/loads的spaced−packed差约[.0576,.1196]，cycles也不同；same demandPFN/order不等于全部cache活动相同，不能把latency gap归为TLB/唯一归因预取或cachehash。scan以walk率裁定reach、完整披露cachetap。

source7f1c824（C f9c9e1b/consumer b45da5f），build3a4ad87，actual launchc9e52315cdf6ebbe02cff28d5fa6566cc49385b6，branchcodex/sm8650-tlb-hierarchy-r2，binary SHA63df10356c1818cd6190b5dbf4e24e080c6a77ae5735dfc072b0540eb90ea547。组件 `probes/diagnostic/tlb_observed_reach.c`，`tools/diagnostic/tlb_observed_reach_analysis.py` / `tlb_observed_reach_raw.py` / `run_sm8650_tlb_observed_reach.py`。两NDK27.2/API34/O2/static等字节、12 actual plans/ELF loop独立Capstone、15生产链测试（完整scan正例是软件模拟）通过。

raw `data/private/20261013T072733Z-tlb-observed-reach-qualification`；公开 `docs/reviews/evidence/2026-10-13-tlb-observed-reach/qualification-analysis.json` 与 `qualification-independent-check.json`。端点CPU温度[39.3, 41.1]°C，无环境事务/全局设置写，不认证窗内恒频。下一同source/binary锁定本资格raw manifest/20SHA，18fresh216窗口的[32,1024,1536,1792,2048,2304]冻结scan；首坏停止、不拼接。物理TLB/组织/ROB仍0/3，`docs/open-items.md`。
