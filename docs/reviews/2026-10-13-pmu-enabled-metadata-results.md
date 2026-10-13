# 临时perf profile的元数据前置条件通过，基线已恢复

## 本次任务的目的（给人类看）

用单项已注册sysctl0→1→0事务验证自己的long64 perf metadata接口，避免在index0下猜寄存器；协议 `docs/design/2026-10-13-pmu-enabled-metadata.md`，无MRS。

**三fresh全部METADATA_PREREQUISITES_OBSERVED**：policy1下自己的4事件（cycles/IR/LD_SPEC/ST_SPEC）index实际[32,3,4,5]、width全部64、cap全部true、序列相同偶数、Own IDs正确，CPU7／baseline环境完整。原policy0时index全0的反例不改写。本snapshot不能复用于后续FD／进程，不是counter读取或ROB单位／容量资格，实际PMU寄存器读取0次。

host确实临时修改了一个全局sysctl；producer本身只读。private write-ahead事务已闭环：baseline0、apply1真实exit0／readback1、finally restore0真实exit0／readback0、state=restored，无journal手改。原频率／governor等未改。独立source/head与saved helper/driver/consumer SHA，逐process producer plan／raw SHA／classification／合法indices与width、restore transcript、全部环境重新核验。公共 `docs/reviews/evidence/2026-10-13-pmu-enabled-metadata/profile-analysis.json`；private `data/private/20261013T123432Z-pmu-enabled-metadata`，恢复事务 `data/private/perf-user-access-transactions/20261013T123432Z-90a9597c8920.json`。Root/globalpolicy/cap单独都不代表可读，后续需当前own index/seqlock/offset/wrap+actual MRS正控。

branch `codex/sm8650-tlb-hierarchy-r2`；controller/helper/source与actual launch `8bf1f8e92dce4064c05a7000187e9ab25e48461a`（8bf1f8e）；C source3d13bc5/buildccece66，binarySHA `5a367fcf16974954b488227902ebe05fd34cba6c6493b999c988013458458006`。7项异常/全controller生产链测试通过（mock device不当target）；已有674诊断回归不含随后metadata/事务模块，这些新模块分别9/7 targeted检查。整体TLB/ROB目标未完成：L2规格2048/256×8已官方匹配，set映射与有效分配未唯一解释；ROB只有结构性发射观察，下一先qualify直接自身counter读法，再做容量窗口／单位／activeconstraint控制。
