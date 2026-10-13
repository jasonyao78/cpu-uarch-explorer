# ROB自有cache-footprint marker v1.0（N0资格冻结）

## 本次任务的目的（给人类看）

让未决分支后的自有load留下cache状态，而通过架构marker输出证实其未退休。避开 `docs/reviews/2026-10-13-rob-speculative-marker-results.md` 无效0x06及单count的ioctl包络。只先做N0，不测秘密/其它进程，不把cache hit直接叫物理ROB entries。

方案比较：内部TLB/ROB RAM接口需要EL3，Android root不提供；依赖缺失LD_RETIRED不成立；采用own page DC CIVAC+CNTVCT冷热正负对照。旧单marker原门/终态不改，新观测原理独立冻结。

## Actual代码和架构证据

同一RX page/PFN，两个program只有一word LDR X9,[X1] vsNOP差异。MOV X9,XZR；FMOV D0,X0；k=16/32依赖FSQRT；FMOV X12,D0；CBZ X12,marker；B finish；marker；SB；FMOV X0,D0；MRS X12,FPSR；STR X12,[X2]；STR X9,[X2,#8]；RET。marker word为固定自有非秘密常量0x12345678。output是第三独立page，防读取FPSR/架构marker重新加载marker line。FPCR0/FPSR0/input0或1及original result要求不变。HWCAP_SB、own DC CIVAC/CNTVCT/CTR read先能力检查，缺失CAPABILITY_UNAVAILABLE首停。

A:train0/test0，load应留下cache hit且架构marker=常量；NOP架构marker0。B:train1/test1，两mode均marker0/cold。M:train0/test1，load应留下hit但架构marker0；NOP仍cold。每格64次training、line清除在训练后，DSB SY+ISB，然后一次reported JIT调用。代码RW/RX/clear-cache在training之前、计时之外。返回后一次same timing kernel `ISB; MRS CNTVCT; LDR; DSB SY; ISB; MRS CNTVCT`；计时只post-marker load，不包含JIT/syscall/PMU wrapper；结果仍为自有常量。

另外cal-hot（先自有touch）、cal-cold（own DC后）两格同timing kernel，不执行JIT。八格=cal-hot/cal-cold/A-nop/A-load/B-nop/B-load/M-nop/M-load；32trial，每8trial奇block反序，每member每position4次。每process256格；3epochs×k16/32=6fresh/1536格，奇epoch反k次序，15秒进程间冷却。没有PMU，不声称branch miss的独立事件认证；A/B/M只能认证本程序/历史的observable footprint。

## 冻结判据

每process从独立hot/cold校准格得到Type7线性q90hot/q10cold；需q10cold−q90hot≥2 CNTVCT ticks；阈值固定midpoint，hit定义ticks≤threshold。不从M标签挑阈值，不删除tail。cal-hot hit率≥.9、cal-cold≤.1；A-load/M-load≥.9，其余A-nop/B-nop/B-load/M-nop≤.1。全部original结果/架构marker/CPU/codePFN/数据PFN/timer/PFN typed gates必过；任一架构marker异常技术首停，不当科学hit替代。6process全过 CACHE_SPECULATIVE_MARKER_QUALIFIED；否则CACHE_MARKER_NOT_QUALIFIED，不N扫/重试追门。

DC成功只证明可执行与本cache状态干预，不认证native/HPA或cachelevel；CNTVCT ticks非CPU cycles，量化校准失败命名TIMER_OR_CACHE_UNRESOLVED。hit可能代表prefetch/其它微状态：NOP同指针/flush/时间/访问kernel与A/B/M、架构marker正反对照限定本因果；不能笼统排除全部speculation。后续filler必须另冻supply、不同资源class/单位、足够delay与窗口删失、activeconstraint辨识，不自动报384。

## 交付和生命周期

`probes/diagnostic/rob_cache_marker.c`，`tools/diagnostic/rob_cache_marker_analysis.py`、`run_sm8650_rob_cache_marker.py`，producer/analysis/raw tests；实际native plans/两NDK/独立CBZ/B/SB/STR解码与production raw攻击通过后才6process。branch codex/sm8650-tlb-hierarchy-r2，primary独占，不写全局安全/频率/THP设置；raw/address/PFN private，公开仅匿名ticks/谓词/hash。未完成归 `docs/open-items.md`。
