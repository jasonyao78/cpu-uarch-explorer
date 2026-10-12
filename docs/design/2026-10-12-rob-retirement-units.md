# ROB退休窗口：相对单位与锚点长度控制（冻结v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-12-rob-destination-control-results.md` 表明XZR并未消除裸ADD波动，而NOP+ADD-discard稳定。下一步先资格检验三种无架构GPR结果的两指令组：双NOP、NOP+ADD XZR、ADD XZR+SUB XZR。后二者同bytes但只有前者属于官方NOP+Any fusion资格；再比较16/32长独立锚点，检验共同窗口解释与“供给×锚点时长”替代解释。不是从NOP/2直接报384。

新增 `probes/diagnostic/rob_retirement_units.c`，两个固定input X16=0x1111/X17=0x2222，ADD/SUB不置标志、目的XZR。五类实际变量分别写出：pattern、g、chain16/32、anchor none/serial/independent、顺逆时序；全部程序字与结果导出。每语法组2ISA指令，不预设等于一个MOP。FP链同D0串行或D0/D1独立，operand/result精确1.0；GPR返回0。单固定64KiB RX/进程，131072 warmup/每窗×8，CPU7/FPCR0及GROUP+ID六事件沿目的控制。

## 阶段一：192窗资格，未过禁止扩展

三epochs，每epoch共享none0（chain16）、四FP0（serial/independent×chain16/32）、三pattern NONE64（chain16），共8条件×3=24进程/192窗。NONE32与NONE16必须实际code字节一致，不能只用config猜共享。每FP参考和各NONE64进程range/median≤.10；每chain maxI0/minS0≤.70；none0绝对range≤.01*min I0(chain16)；全部NONE64 max≤.80*minI0(chain16)，全部Icache/iteration≤.001；回传完整raw与独立重算。只有本新协议complete/qualified/same binary input能授权扫描；旧目的控制不晋升、不拼窗。

## 阶段二：有限共同边界与模型（资格通过后）

从既有真独立NOP窗口约每gap512–768 ISA取得网格，不以第三方384作拟合中心。双NOP与NOP+ADD-discard g={256,288,320,336,352,384}；ADD+SUB-discard g={128,144,160,168,176,192}。每point共享NONE16（code等价），两chain各serial/independent。每epoch为90 point条件+8 refs=98（294进程2352窗）。三个pattern均要完整，不挑通过的pattern替代共同模型。

每point供给/控制可用：各进程range/median≤.10，NONE max≤.90*min I0(chain16)，Icache≤.001。FP/S位值、IR/IDs/noMUX精确；serial高于自身reference不删除，完整资源响应保留。对每epoch/pattern/chain，在同point I_min≥.95*S_max 且I_max≤1.05*S_min判near-serial；I_max<.90*S_min判overlap-retained，其余ambiguous。先资格/ambiguous/非单调，再左右删失；至少两个high点才给操作性saturation interval。three epochs一致才复制；任何缺失或不合资格记INCOMPUTABLE，不能无声覆盖。

**仅作被检验的模型**：假设fused-eligible组α=1、无列出fusion的ADD+SUB组α=2，候选代理 `U=α*g+2*chain`。它不是实际分配单位读数；loop/在飞跨迭代/其它生命周期项可能有未建模偏移。若六条复制曲线（3pattern×2chain）的U区间有共同交集，命名COMMON_RETIREMENT_PROXY_COMPATIBLE；不交或不完整为INCONCLUSIVE，均不设置physical_entries_certified。两chain变化与两α形态提供正交检查，不能仅一条NOP曲线就接受模型。实际fusion、one-MOP/entry定义、活跃替代约束仍须独立证据；第三方384仅报告外部参考。

consumer `tools/diagnostic/rob_units_analysis.py`、driver `tools/diagnostic/run_sm8650_rob_units.py`、tests `tools/diagnostic/tests/test_rob_units*.py`、evidence `docs/reviews/evidence/2026-10-12-rob-retirement-units/`。actual plan/独立opcode/Rd/SUB不置标志/chain字差、双NDK/完整producer→writer→raw→资格授权负例后串行运行；SOURCE/build-consumer/launch/report分列。所有失败保留；qualification未过本批结束，不改变条件重跑追门。owner=当前端到端Agent，branch `codex/sm8650-tlb-hierarchy-r2`。
