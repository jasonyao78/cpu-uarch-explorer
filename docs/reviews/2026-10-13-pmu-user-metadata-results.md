# Own perf metadata：cap标志不能单独当计数器读取资格

## 本次任务的目的（给人类看）

减少ROB短窗enable/disable syscall包络前，先确认目标的自己事件metadata接口，不试MRS、不改策略。协议 `docs/design/2026-10-13-pmu-user-metadata.md`。

**ACCESS_DISABLED，第一process命名停。** 请求config1=2（USER access），4own pinned USER-only事件[0x11,0x08,0x70,0x71]全部open/ID/mmap/group读成功；实际sysctl=0。四页cap_user_rdpmc全true、pmc_width全32、sequence前后均6，**index全部0**。cap位true不等于有合法physical counter index，更不能由它直接MRS。源程序实际counter register reads=0，FD/maps全部关闭，环境基线未改。不能当counter-read／ROB容量资格或声称该接口永远不可用。

10rawSHA，immutable Git source/实际C plans/二进制及saved classification复核。branch codex/sm8650-tlb-hierarchy-r2，Csource3d13bc5/consumer a298e36/buildccece66/actual launch `a731636b708764e717ba6efdfcb230426c7b13b0`；binarySHA `5a367fcf16974954b488227902ebe05fd34cba6c6493b999c988013458458006`。NDK27.2/API34双构建同字节、2actual flag plans、8production-chain软件测试通过，mockkernel不当target。源 `probes/diagnostic/pmu_user_reader.c`（第一阶段metadata-only）；`tools/diagnostic/pmu_user_metadata_analysis.py` / `pmu_user_metadata_raw.py` / `run_sm8650_pmu_user_metadata.py`；public `docs/reviews/evidence/2026-10-13-pmu-user-metadata/metadata-analysis.json`，private `data/private/20261013T115207Z-pmu-user-metadata-metadata`。不冒称既有674回归覆盖这后加模块。

下一读法必须先有一个单独冻结的临时profile恢复事务（baseline0→1→验证→own metadata合格／index>0／width真实→finally恢复0），并验证自身event seqlock/offset/wrap及实际读数正控。不复用本snapshot的index，不猜寄存器号，不在policy0下强试MRS，不以root身份代替硬件访问资格。暂未实施该写入；另注册才执行。SB旧1536窗整资格失败保持，命名未知值不写0；数据cacheline／固定VA/PFN的PT关联对照作为TLB下一有限项，`docs/open-items.md`。
