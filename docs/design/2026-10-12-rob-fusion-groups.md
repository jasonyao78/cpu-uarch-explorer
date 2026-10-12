# ROB 匹配工作量的语法组对照（冻结v1）

## 本次任务的目的（给人类看）

在 `docs/reviews/2026-10-11-rob-dual-anchor-v2-results.md` 已验证D0/D1重叠且观察渐进退化后，问不同ISA长度/官方fusion资格、相同ADD工作/值/目的集合是否给出匹配的有效响应。旧NOP网格重跑不能校准单位；改锚点长度会引入FP队列；选择匹配ADD与NOP+ADD并加双NOP无GPR目的控制。先做有限资格，合格才扫语法组。不直接给物理ROB entries。

依据 `/Users/michaelyao/workspace/cpu-uarch-ref/docs/Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf` Issue3.0/r0p1 §4.11列NOP+相邻Any fusion；§2.1/4.1区分MOP/µOP。`docs/reviews/2026-10-11-rob-fusion-unit-audit.md` 指出资格不等于实测fusion/ROB分配。第三方384不作拟合中心。

## 精确激励

新增 `probes/diagnostic/rob_fusion_groups.c`，只复用 `probes/common/rob_codegen.h` 的opcode/prologue规则，不修改它或任何历史producer。两侧各g个语法组：add=ADD X(4+j%8),X16,X17；nop-add=NOP,同ADD；nop-pair=NOP,NOP。X16=0x1111、X17=0x2222，ADD输出固定0x3333，目的集合/出现顺序/每侧ADD次数完全匹配。nop-add有两倍ISA长度，这是被操纵变量，不冒称相同取指工作。64B loop对齐，配对起点8B对齐，实际每指令/代码跨度均导出。

anchor none/serial/independent分别无FP链、两侧16次D0、两侧16次D0/D1。D0/D1均由同prologue初始化1.0；不带FP→GPR桥。固定每进程一个程序/64KiB VA，安装一次RX不重写。生成循环后增加一条return-value指令：有ADD且g>0返回X4=0x3333，否则返回0；C调用立刻捕获返回值和D0/D1，不能经过会clobber FP的libc。FP结果必须精确1.0。该return指令不在迭代循环内，IR名义为iterations×loop_instructions+prologue+2；包装容差max(1000,1%)。

8窗，warmup/正式各131072 iterations。CPU7/FPCR0/4KiB，GROUP+ID/pinned/user-only/noRESET/noMUX，六事件[0x11 cycles,0x08 IR,0x3a OP_RETIRED,0x816d rename,0x23 frontend stall,0x01 Icache refill]；不把µOP当MOP。每窗顺序奇epoch反转；奇epoch整条件序反转。进程间5s；每进程pre/post及整体initial/final只读baseline门，不修改cpufreq/温控/THP，异常停块、原样保留。

## 两阶段与命名（设备数据产生前冻结）

支持g={0,64,128,192,256,384}全部108顺逆真实计划。资格6条件：nop-pair g0的none/serial/independent +三pattern的none g64，3epochs=18进程/144窗。扫描只在本协议完整资格raw通过且same binary/SHA绑定后启动：共享nop-pair g0三anchor，所有非零g×3pattern×3anchor，3epochs=144进程/1152窗；扫描自带参考/供给，资格窗不拼接。g0所有pattern的实际代码等价，故共享参考有字节证明，不依赖元数据推断。

C=cycles/131072。每非零程序/FP参考各进程8窗range/median≤.10。资格：max independent0/min serial0≤.70；none0全窗绝对range≤.01×min independent0；三个NONE g64稳定且max C≤.80×min independent0；全部Icache refill/iteration≤.001。通过=group-controls-qualified，否则not-qualified、禁止扫描。

扫描重新满足资格（六个参考/NONE64条件及其Icache窗），高g背景逐比较阻断。每pattern/g比较可用需none/serial/independent各进程稳定、NONE max≤.90×min independent0及各窗Icache/iteration≤.001。serial大于1.1参考单独标记serial-resource-response，并完整保留；本实验要比较资源流，不能用这个响应把真实现象删掉。independent所有窗≥1.25×max independent0为response；≤1.10×min independent0为below-response-band，其他ambiguous，不强求单knee。

**主对照**：同g ADD与NOP+ADD两者可用且都是response，每个epoch的independent median差绝对值≤.03×min independent0、serial median差≤.03×min serial0。至少两个相邻非零g满足才命名fusion-compatible-work-response。相同ADD实际工作、两倍ISA指令但响应匹配支持有限兼容解释，不证明实际MOP数或物理allocation；仅一个点不能关闭。主不成立且任一比较不可用=inconclusive，全部可用且不成立=matching-response-not-replicated（不是无fusion）。

双NOP背景另报每g模式间带符号差；至少两个相邻g三epoch均ADD/NOP+ADD较双NOP更慢≥.05×min independent0（全部三模式可用）=replicated-GPR-flow-associated-response，反向另名，否则not-replicated。两个主结论独立；不据它们唯一命名PRF/RS/ROB。

## 实现计划、组件和出口

工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`、branch `codex/sm8650-tlb-hierarchy-r2`；单primary拥有设备，远端暂不操作。

- [ ] `tools/diagnostic/tests/test_rob_fusion.py` 先RED缺真实producer/consumer/driver，再native真实108plan逐字独立oracle、同g0等价、ADD顺序/值/返回和FP差分字节GREEN。
- [ ] `tools/diagnostic/rob_fusion_analysis.py` 精确矩阵/类型/代码/IDs/IR/结果/时序消费、冻结所有科学门；`tools/diagnostic/run_sm8650_rob_fusion.py` 实际producer→writer→raw、资格授权/首坏停机。
- [ ] `tools/diagnostic/tests/test_rob_fusion_raw.py` 真实配置至落盘，仅mock外部adb/PMU；成功、重算SHA的缺/重/乱/冲突/结果/背景/资格拒绝以及audit绕过反例必须过。
- [ ] 两次NDK27.2/API34/O2/Werror/static字节一致；全部实际words独立Capstone；source/build-consumer/actual-launch分开提交。构建/plan/code-audit见 `docs/reviews/evidence/2026-10-12-rob-fusion-groups/`。
- [ ] 全量诊断回归后串行资格/扫描，第二算术全部窗/SHA核对，完整匿名CSV/summary/图与结果 `docs/reviews/2026-10-12-rob-fusion-groups-results.md`。手机缺失时完成软件并登记阻塞，不能mock数据冒称已测。

原始和console留private，独立JSONL不冒充schema-v2。physical α/active constraint、formal接入及其它部件归 `docs/open-items.md`；新门不改历史结果。
