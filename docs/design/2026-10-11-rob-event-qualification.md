# ROB 操作与 rename 事件有限资格（冻结 v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-11-rob-resource-results.md`发现NOP与三类GPR写入流的隐藏响应不同。下一步先检验计数器是否能区分这些流，避免把架构指令数当ROB分配数。三候选：直接加密N不能识别资源；立刻改依赖/生命周期会同时改变码形；本轮选复用不变binary的有限事件控制，先约束观测工具。FADD超波动门仍OPEN，不靠剔除轮次关闭。TLB竞争结果不拼本批，下一victim身份/历史对照沿 `docs/open-items.md`。

## 来源与命名边界

代码 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`，binary source1ef4baa、SHA cb4645f65d8352e839144541bcaefab32cad5a7ce2006d9fb219479c8384d5ba，不变。Arm官方[PMU事件表](https://raw.githubusercontent.com/ARM-software/data/master/pmu/cortex-x4.json)与知识库 `cpu-uarch-ref/arm-docs/x4trm.txt`（r0p2/Issue05，非目标r0p1实测真值）列0x3a=OP_RETIRED、0x3b=OP_SPEC、0x816d=STALL_BACKEND_RENAME（rename full），0x23为前端发射停顿。这些事件不是物理ROB/PRF occupancy；OP退休/执行口径不是allocation口径，rename full也不专指ROB。SOG r0p1 §4.11/4.12允许NOP融合、部分MOV零延迟但留条件，本轮不得先假定成功或乘/除二救384。

## 完整生产合同

新mode `rob-event-qualify`；driver `tools/diagnostic/run_sm8650_minimal.py`、consumer `tools/diagnostic/rob_event_analysis.py`、真实C测试 `tools/diagnostic/tests/test_rob_event.py`，raw测试 `tools/diagnostic/tests/test_rob_event_raw.py`；build/plan/code证据在 `docs/reviews/evidence/2026-10-11-rob-event/`。所有64请求/导出代码与config必须相符。

每epoch按anchor{none,fsqrt}×N{0,128,256,704}×class{nop,add,movi,movr}交错；epoch1整体反序，64进程/192窗。i131072/rounds3/chain16/align0/CPU7/type8，事件顺序[0x11,0x08,0x3a,0x3b,0x816d,0x23]，现有程序自动置cycles与IR。每gap N、每iter2N；MOVI=1，MOVR源x16，写x4..11，fsqrt稳定1/d0/FPCR0。真实host导出与独立A64 words逐字节核对，immutable source/deps/host-exporter、binary/build/plan/launch/driver/protocol/raw SHA贯穿。不修改C或旧profile/门。

固定每进程1秒间隔、初末与每次pre/post环境、walt基线、无频率/温控/THP/全局PMU权限变更；单设备/root独占/unfinished0，否则停。所有config/ID/typed uint64/IR ±max(1000,1%)/positivecycle/no-mux/3round/64case顺序与精确325 raw inventory强制；任一技术失败停整批不补测。环境端点不证明窗内恒频/恒温；完整保留温度、ns、周期、全部事件与轮次。

## 判据与可推翻路径

首先完整技术接受，再为每event/class/anchor/N/epoch报告三窗、中位、range/median与对自身N0的有符号差。正控仅ADD及MOVI、NONE、N128：各epoch ΔOP_RETIRED与ΔOP_SPEC必须>128 operations/iter（少于已知256 filler，宽控制带）；这四条件各三窗两OP的range/median≤10%，同class/event两epoch的差额相对均值差≤10%。全部成立才称“两操作事件对本控制流响应资格通过”，不是通用事件语义认证。任一不成立，报告not-qualified，不重试换门。其余NOP/MOVR/Fsqrt事件仅完整原值与对照，不把零视为不占资源。

每非零N报告 ΔIR/(2N)、ΔOP_RETIRED/(2N)、ΔOP_SPEC/(2N)；这些是计数响应密度而非ROB分配系数。rename/frontend同窗计数除cycles作观察比例；任何比例>1记cycle-semantics-incompatible，不根据事件名做P1硬件归因。全部rename为零时，该事件positive-response未取得；非零也只证明在这些流有响应，没有专门已知rename-full正控，不称rename语义全面qualified。类间差、锚点增量与负残差保留，不定义物理容量或新onset，不拼旧批提高精度。

下一步只由结果决定：操作事件有可复制类差则设计独立融合/结果生命周期控制；无类差则它们不足以区分原解释。rename响应可约束关联，不能唯一定位PRF/ROB，若需要因果必须新增专门控制。FADD原因、窗内clock、精确allocation、正式runner/schema/CMake仍按 `docs/open-items.md`归属/触发跟踪。

## 执行与收口

采用brainstorming/writing-plans自审、TDD与verification-before-completion；用户已授权自主连续推进，无新例行人工关卡，不派代理。先真实producer RED→consumer/driver GREEN；注册两独立NDK构建/64实际计划/解码；再全raw来源/缺失/冲突/乱序/额外文件/重哈希反例与全量回归，旧140/420、36480、10400、6144重放不漂移。提交启动树后串行有限采样，直接JSONL第二路径复算、全部匿名证据/图/报告、README/OI同步、本地范围提交。技术或科学失败都保留原始数据，不追门；本轮不push。
