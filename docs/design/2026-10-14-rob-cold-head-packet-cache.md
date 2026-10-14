# 当前packet-PC配方缓存剂量资格 v1.0

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-14-rob-cold-head-branch-sites-results.md` 的packet32/32机会资格已通过，但它搬整个routine，也搬head LDR PC，head2延迟与fixed不同。下一只四配置验证当前packet PC配方的cache剂量，避免外推旧固定PC证据；通过后才冻gap/packing/PRF/supply/独立deadline，不报告物理ROB数。

producer `probes/diagnostic/rob_cold_head_packet_cache.c` 是 `probes/diagnostic/rob_cold_head_branch_sites.c` 的显式compile-time palette wrapper，不复制ROI。consumer `tools/diagnostic/rob_cold_head_packet_cache_analysis.py`；controller `tools/diagnostic/run_sm8650_rob_cold_head_packet_cache.py`。共享实际位置/FD审计 `tools/diagnostic/rob_cold_head_branch_sites_analysis.py`，默认issue合同不改变。

## 冻结矩阵与判据

2fresh epoch × heads1/2=4process，head offset1024、branch_layout packet；每process32trial×2state×8role=512attempt，共2048formal/8192own warm。same数据mapping/PFN/counter context；hot/cold实际code/branch PC不同是已注册packet干预，位移4*(trial*16+role+8*cold)，最大2044，全部程序同4KiB JIT页；不宣称PC历史绝对空白、machine cache selector或HPA。

实际palette[17,8,112,113,3,23]，last two为L1D/L2D_REFILL。没有0x22或I-cache，因此不从本profile声称错方向或供给事件；issue资格16199b1分列，ISA body/暖链完全相同但每FD current index必须fresh。默认producer只issue；wrapper只能cache+packet，actual argv与native words都核验。

原A8/Mpre0/IR/separation门，cold near eligible≥24/32、far|near≥.9；warm0训练64+实际RX四own热call，结构阴性与架构原值不变。每architect pre/post taps/nop四role同trial冷热交集≥31/32，cycle差中位heads1≥64/heads2≥96；mean ΔL1D与ΔL2D均在[.75*heads,1.25*heads]。全部两epoch/head通过才PACKET_CACHE_PRIMARY_QUALIFIED。不看结果换offset/PC/threshold，不回救原v1/v2失败。仅1个真实ROI-metadata-changed/process，512全部account，无retry/补样，其它技术错误首停。

actual head/load/code/branch地址、内容链、LinuxPFN端点、metadata/GROUP+ID绝对包络、ABI/ISA/source-build-launch-rawSHA逐层审计；新wrapper编译宏是实际build参数，禁止只重写plan事件名。primary独占，双journal检查0→1→durable finally/readback0。资格成功后另冻冷头gap协议；原单位反例和384候选仍原样。
