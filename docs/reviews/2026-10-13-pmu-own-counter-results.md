# 自有直接 PMU counter 资格结果

## 本次任务的目的（给人类看）

验证自有counter实际MRS能力、读数/FD绝对身份和已知工作；不是ROB容量扫描。协议 `docs/design/2026-10-13-pmu-own-direct-counter.md`，producer `probes/diagnostic/pmu_own_counter.c`，guard `probes/common/perf_user_counter.h`，consumer `tools/diagnostic/pmu_own_counter_analysis.py`，controller `tools/diagnostic/run_sm8650_pmu_own_counter.py`。

**整体 OWN_DIRECT_COUNTER_NOT_QUALIFIED**。E0/E1完整24窗分别通过全部正控；E2仅完整发出1窗后，下一窗被source守卫 `metadata-changed` 拒绝（exit1、空metrics、FD关闭），因此本批只有49完整窗口，不能写72/72。旧失败不抹除，不Nscan、不放宽门。

source `2634f1ef2b1612e78d9b97987a25e633ca3ce0b9`，实际launch `b4401db23f6253b2aa12bb25330b7793ce3558fd`，branch `codex/sm8650-tlb-hierarchy-r2`，binary `c2b1a4ffffb197a8f6967152970aa337b298de11d8465b6a5b107bfed4a5177b`；双NDK/实际3ISA loops和PMCCNTR/PMXEVCNTR/唯一PMSELR select解码在 `docs/reviews/evidence/2026-10-13-pmu-own-counter/decode.json`。无PMCR/PMUSERENR/counter-value写入。

正面证据：前两fresh已经按自己当前index/64位/offset/稳定锁正确直接读数，独立FD绝对包含和delta校验全过，LOAD−NOP LD_SPEC约8198–8205.5、STORE−NOP ST_SPEC约8198–8198.5，均在预注册8192±82；完整值见 `docs/reviews/evidence/2026-10-13-pmu-own-counter/qualification-analysis.json` 和全窗CSV。这个只证明路线实际可用，不自动认证所有窗口，更不能证明ROB allocation单位。

拒绝原因边界：C实际检测到before/after metadata seq/index/offset之一改变；现raw未保存被拒窗口的两组metadata，不能精确区分调度/中断/重新编程。不要把 `metadata-changed` 说成已经证明context switch或读错counter。下一改进必须先记录被拒metadata和明确invalid-window，不修改原raw；若使用固定attempt预算处理非稳定窗口，需要新预注册覆盖/失效率/各role规则，禁止按计数信号挑点重试。

恢复：host仅perf_user_access0→1→0，tx state restored/readback0，journalSHA锚定；CPU频率/governor无写入，pre/post环境无violations。全22raw SHA核对，49完整窗直接以原hardware/offset/FD重新算；第三失败窗口没有计数不补造。raw `data/private/20261013T135131Z-pmu-own-direct-counter` 和私有journal保留。7新增生产/consumer/controller测试通过，另4事务回归；无全量诊断测试最新声明。
