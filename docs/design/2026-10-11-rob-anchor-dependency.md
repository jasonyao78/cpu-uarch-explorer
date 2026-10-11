# ROB 锚点依赖控制（采样前冻结 v1）

## 本次任务的目的（给人类看）

零值对照 `docs/reviews/2026-10-11-rob-zero-value-results.md` 支持值域影响rename响应，但没有分离“指令退休跟踪”与“结果可就绪/调度及寄存器资源”。本批让同一ADD流能早执行或必须等fsqrt完成：只改ADD的Rn域，实际运算输入和结果保持相同；跨两档锚点长度观察。目标是反证把单一NOP/ADD转折当通用ROB数的解释，不输出物理entry。

候选：加密旧N曲线不能分离机制；改寄存器轮转数同时改变依赖距离与寄存器布局；同码形anchor→GPR桥与Rn位域对照直接操纵结果就绪。选择第三项，暂不新增寄存器池或DRAM路线。

## 精确程序和有限矩阵

扩展 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c` 的可选 `--anchor-link independent|dependent`，仅class add、anchor fsqrt/none、对称、非paired、无xor允许。无旗标时所有旧配置和字节不变。桥 `FMOV X12,D0` 在每段锚点之后、N个ADD之前，两组均执行；X12为caller-saved，与X4..11 filler、X3 loop、X16/17独立源不冲突。

fsqrt仍double sqrt(1.0)、FPCR0。两个分组初始化X16为1.0的bits `0x3ff0000000000000`，X17仍0x2222、D0为1.0。independent: ADD Xd,X16,X17；dependent: ADD Xd,X12,X17。两组结果均同一64位值，无异常或溢出差异。每gap N相同、八dest轮转相同；唯一生成码差为2N个ADD Rn(16→12)，N0全部字节相同。none保留同FMOV桥和同operand，为无长依赖负控，不删掉额外桥。自描述 `anchor_link`/`bridges_per_iteration=2` 仅新旗标输出，legacy读者/档案不改变。桥不是free指令，0点与none匹配控制保留其成本。

两epoch（第二完整反序）；anchor/chain=(none,16),(fsqrt,8),(fsqrt,16)，N={0,64,128,256}，link={independent,dependent}交错，48进程/144窗。i131072、rounds3、align0、CPU7/type8；events=[11,08,3a,3b,816d,23]，新独立consumer `tools/diagnostic/rob_dependency_analysis.py`，注册证据 `docs/reviews/evidence/2026-10-11-rob-dependency/`。复用driver `tools/diagnostic/run_sm8650_minimal.py` 的已验部署、环境和实际code导出，mandatory新consumer先审计再推进。每进程1秒，板测与TLB串行，既有walt环境只读。

## 技术接受、可推翻判据与边界

48条件/144窗/245raw精确inventory；源码、构建、实际launch、plan/protocol/driver/SHA分别绑定。实际C导出与独立A64字公式、所有Rn域/桥/branch/RET/寄存器及两次NDK一致；全部PMU组六唯一ID、uint64、no-mux、cycles>0、IR按实际instructions*iterations+prologue检查，误差≤max(1000,1%)。首坏点停批，禁止补点、拼批、挑窗。环境端点不证窗内恒频。

全部24有限cell的三窗 cycles/IR/OP/rename/frontend及每链、每N、每epoch的有符号差和range/median完整报告。cycle类比例>1命名semantics-incompatible；rename计数不由名字认证PRF full。N128是固定主点，其他N不用于事后改选主点。对每k∈{8,16}/epoch，令C(link,anchor,k,N)为3窗周期中位，B(link,anchor,k)=C(...,0)。主差D(k,e)=[C(dep,fsqrt,k,128)-B(dep,fsqrt,k)]-[C(ind,fsqrt,k,128)-B(ind,fsqrt,k)]-([C(dep,none,16,128)-B(dep,none,16)]-[C(ind,none,16,128)-B(ind,none,16)])。

四个D均>5cycles/iter且各自涉及八组周期range/median≤.1，才命名 `dependency-associated-hiding-response`。不满足报告 `not-qualified`，任何不稳cell保留ambiguous。这个门只表示依赖相关周期响应，不能唯一归因RS/PRF/ROB，不能宣称ADD分配因子。即使无差异，也只给本有限流的检出能力（5cycle门），不是硬件不存在该约束。

## 实施计划与自审

使用brainstorming/writing-plans，依既有连续自主授权执行，不插入例行人工审查。

1. `tools/diagnostic/tests/test_rob_dependency.py`：真实exporter先RED缺旗标；核48配置、N0同码、非零唯一Rn域和结果值、拒绝不支持组合、旧八类完整字节与配置不漂移。源码范围提交。
2. 新consumer先RED，再独立生成字/config/有限统计；阈值与缺失/重复/冲突/乱序/坏ID/mux/IR/来源/实际码及whole-matrix负例，真实producer→driver→写盘→raw回读；旁路审计会使首坏点测试RED。
3. 双NDK、实际全码独立Capstone解码及source/build/plan注册；提交启动树，跑适当全量回归后deploy有限采样。已有TLB/ROB历史raw不覆盖。
4. 直接raw第二算术路径复核144窗、全部身份与245SHA，匿名全部计数/图/报告及README/OI，及时本地范围提交。

下一科学边界：物理ROB/PRF/RS/融合、rename full语义正控、窗内clock仍OPEN。ALU/FPU专项、正式runner/schema/CMake仍沿 `docs/open-items.md` 原负责人/触发，不以本新独立JSONL冒充正式record。远端本轮不操作。
