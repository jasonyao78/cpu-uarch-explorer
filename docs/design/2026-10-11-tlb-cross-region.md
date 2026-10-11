# TLB 四域高位折叠反证（冻结 v1）

## 本次任务的目的（给人类看）

旧局部转折 `docs/reviews/2026-10-11-tlb-local-turn-results.md` 只在一个256MiB域中观察C1。H1=VPN[7:0]与H3=VPN[7:0] XOR VPN[23:16]在单域可等价。本批跨四个256MiB域，保持共同victim、竞争数量/页内offset/访问顺序、尽量匹配页表几何，检验两个有限候选的相反预测。结果只认证候选间条件化区分，不认证完整hardware hash、物理ways或descriptor/PFN唯一归因。

## 地址算术与可推翻预测

独立 `probes/diagnostic/tlb_cross_region_layout.h` / `probes/diagnostic/tlb_cross_region.cpp`，复用 `probes/diagnostic/tlb_history_layout.h` 的walk与闭合F128，旧组件合同不改。reserve2GiB虚拟池、ceil至1GiB对齐起点A，实触碰仅小页集，不是2GiB数据冲刷；noTHP4K端点核验。A0=VPN(A)，h0=(A0>>16)&255，target t={7,100}。

I（单域控制）：i=0..11，region0，q=(A0>>8)+16*i，low=t。
G1（四域低位恒定）：region r=i%4，j=i//4，q=(A0>>8)+256*r+16*j，low=t。
G3（四域折叠恒定）：q与G1逐页相同，hi=(q>>8)&255，low=t XOR hi XOR h0。
VPN=(q<<8)|low；三族page0完全相同，victim固定0；node=page+64*i，12页最大history固定，只有竞争prefix W变化。G1/G3每域恰3页，0..11全激励；I max12都在region0。1GiB对齐使四个hi只低两位不同，所以G1/G3对应VPN仅低两位不同。

下表是数学候选，非已测硬件set：

| family | H1 | H2=low XOR mid | H3 | H4=low XOR mid XOR hi |
|---|---:|---:|---:|---:|
| I | 1 | 12 | 1 | 12 |
| G1 | 1 | 3 | 4 | 12 |
| G3 | 4 | 12 | 1 | 3 |

两模型set数量由全部实际VPN重算；不把collection假设当hardware模型。原字节生成和符号差保持各自含义。

在常规4K、64bit descriptor格式下，G1/G3对应页位于同2MiB父覆盖、同8项L3 descriptor组，这是由VA算术推导的匹配代理。[Arm Memory Management §6/7](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/LearnTheArchitecture-MemoryManagement-101811_0100_00_en.pdf) 给出64bit项及4K索引VA[20:12]；未实读PTE/CONT/PFN，不把组匹配升级为实测物理PTE cacheline或排除aggregation。

F512候选位于独立8MiB池，排除六族全部页在四个候选模型中的occupied sets；seed137洗牌，闭合前128节点，不推测无冲突模型外的未知hash。所有最大族在测量前prefault、建链，raw完整保留VA/实际所有候选sets/四域计数；公开只匿名完整计数和相对几何。

## 有限矩阵与冻结门

2target×3family×2order×W{1,8,9,12}=48 cells；每trial八遍F128→history12，再F128→victim训练，八遍F128→snapshot→竞争K=W-1→snapshot，最后F128→snapshot→单victim→snapshot。16trials×9窗=144/cell，五fresh mappings（奇mapping全矩阵反序）、进程间15s，共34560窗。CPU7、PMUtype8、事件[11,05,2d,2f,34,35]及已有真实PerfWindow/noRESET/noMux；元数据在最终F前取得。quiet-state只读baseline，无环境事务。

消费 `tools/diagnostic/tlb_region_analysis.py`、driver `tools/diagnostic/run_sm8650_region.py`：完整producer计划/六实际几何族/共同victim/所有链接与窗形状、源/build/launch/protocol/plan/driver/rawSHA/4K backing先核验。缺失/重复/冲突/乱序/额外/首坏step停整批，不拼旧A1/frozen或旧局部批。

每K/pass对同family/order W1差分0x05和0x2f须∈[.75K,1.25K]；任何失败比较=INCOMPUTABLE。W1 datawalk须0、victim单load walk≤1，否则INCOMPUTABLE。每曲线每W的16trial victim非零率≥.5=response，否则no-response；所有原计数都保留。

主比较仅W12：每target的I须五mapping×双order全部可算且response，才允许候选辨识。G1/G3同样全部可算：全十条G1=response且G3=no-response→low-only-candidate-favored；反向→high-fold-candidate-favored；两者同高/同低→non-discriminating；复制不齐→heterogeneous；控制不合格→INCOMPUTABLE。两个target各自判定，不多数合并；只有二者相同favored才给replicated候选偏好。W8/9报告限定曲线，不据四点模板强算新容量。模型外hash/descriptor/replacement/PFN仍未唯一排除。

## 实施计划与归属

r2 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`、branch `codex/sm8650-tlb-hierarchy-r2`。root一个手机操作者；完成前批ROB设备进程后才允许新TLB部署。

- [ ] `tools/diagnostic/tests/test_tlb_region.py` 实际C++ plan/selector/链接harness先RED→GREEN；base未对齐/跨hi低字节回绕/目标域计数/数学预测/共同victim/PTE代理、所有W/order真实环均验证。
- [ ] source scoped提交→双NDK静态O2/Werror→实际窗反汇编和独立数学consumer；身份/激励/完整覆盖/判据反例，不以手写计划替代producer。
- [ ] 实际producer→driver/writer→raw回读、首坏停机后提交launch，串行有限五mapping；原始数据不删，不追门重复。
- [ ] 全部窗独立第二算术/SHA/几何复核、完整匿名证据/图/报告，刷新目标账与 `docs/open-items.md`。无区分力也给真实有限终态；ALU/FPU专项与物理allocation标尺沿原owner/trigger后置。
