# ROB 探针批判性吸收与并行推进裁定

## 本次任务的目的（给人类看）

判断 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c` 哪些设计值得保留、哪些会制造错误结论，并将用户指定材料转成下一版最小探针的可执行约束。TLB 不必先完成完整hash才能推进ROB软件工作；手机由当前Agent独占，任何两个部件的采样仍串行。

## 裁定

**并行推进 ROB 研究/软件设计合理；当前骨架不通过目标板容量采数资格。** 这不是因 ROB 没有官方真值，而是程序和协议仍有可复现错误。先取得可信的“特定填充流有效在飞窗口 W_class”，再用对照判断能否归因ROB。384仅是第三方候选，不作为拟合中心、取整目标或接受条件。

当前轮未改骨架行为、未执行ROB目标板测量。已实际编译并调用 `--write-asm` 导出生成码，确认软件缺陷；没有执行导出的JIT循环，也没有把host编译成功冒充硬件正确性。

## 必读材料核对与吸收范围

| 材料及具体位置 | 值得吸收 | 必须重审 |
|---|---|---|
| https://github.com/travisdowns/robsize ，`robsize.cc` L342–390、451–467、623–650，源码blob `53a97119be18cffe05a9470c3f985ae08ee02e98` | 两独立链；**两侧均有filler**；类别/混合流；精确生成码和计数留存 | x86计时/编码/屏障不直接移植。17次展开搬到A64，在N≈512时热代码约68KiB，可能跨X4 L1I64KiB；256MiB分配不等于256MiB cache足迹（该构造每4KiB一line，约4MiB line足迹，并有TLB压力） |
| `../cpu-uarch-ref/cpu微架构材料/src/pattern.c` L30–41、59–81；`src/main.c` L185–187、249、284–291 | 极小fsqrt链+NOP原型；builder接口；改变锚点长度检查转折稳定 | 主控把d0置0，实际为sqrt(0)；sum未逐N清零且先整数除法，旧CSV统计不能直接用。`BTBSize_Probe_H2`只是注册builder，`b +16`跳过3个NOP：它是分支/前端实验，三个NOP不执行，不能用于ROB filler计数 |
| `../cpu-uarch-ref/cpu微架构材料/src/utils/utils.h` L253–258、669–680、730–743 | count/pitch/offset/mod参数表达依赖图和多独立链，对ALU/FPU/ROB均有用 | ns×假设频率不是PMU cycles；只取minimum不作为新统计默认 |
| `docs/cpu-uarch-deep-analysis/rob-deep-analysis/ROB微架构深度分析报告.md` v0.1 | 估计量先行、混淆清单、跨类别/跨锚点、机器码留存、允许不可识别 | 下述协议和命名判据不可直接冻结；采数前重写相关段落 |
| `../cpu-uarch-ref/docs/如何测量ROB容量？梦想开始的地方 - 知乎.md` 方法论/测试过程/实现细节 | 阻塞退休才能积累窗口；锚点长度敏感性；平台与供给斜率同时看 | Golden Cove/x87结果不是X4；fsqrt恒延迟须按实际operand验证；不能向2的幂或4的倍数取整救结论；剩余未退休锚点数不恒等于整条链长度 |
| `../cpu-uarch-ref/docs/Arm_Cortex_X4_Core_Software_Optimization_Guide.pdf` r0p1/Issue3.0，§2.1 p11–13、§4.1 p55、§4.10–12 p60–64 | MOP/µOP分层、dispatch类型上限、重命名/零延迟操作约束 | §4.11明确 NOP可与后续指令融合；纯NOP条数不能预设1:1 ROB条目。10MOP/20µOP是dispatch上限，不是ROB或实际填窗速度 |
| `../cpu-uarch-ref/docs/Arm_Cortex_X4_Core_TRM_102484_0003_06_en.pdf` r0p3/Issue06，p35–37、70–72、123–128、136–137、1239/1242 | cache/预取与PMU定义；0x816D只说明rename full | 目标MIDR0x410fd821为r0p1；指定TRM是r0p3，不能默认修订无差异。`arm-docs/x4trm.txt`对应另一份r0p2/Issue05，1365页，不可混用页码 |

Arm官方事件数据 https://raw.githubusercontent.com/ARM-software/data/master/pmu/cortex-x4.json 对0x1b写“duplicates INST_RETIRED”，指定TRM p126则写推测执行operation；这是**来源差异**，不是已经解决的目标机事实。0x3a/0x3b在TRM p128分别是OP_RETIRED/OP_SPEC，可作后续口径核验，但执行/退休数量均不等于ROB分配数量。不得仅凭任一比值宣称条目拆分因子。

## 当前骨架逐项判定

### 保留的结构

1. **被测序列由生成器决定，C只负责控制。** 保留 `emitter_t`、类别函数、导出字节，增加标签/有符号位移和显式循环描述；每次导出都能核实际指令数、锚点数、寄存器集合、分支目标、代码字节数。
2. **filler替换独立于锚点/数据构造。** 先少数类别验证，再加ADD/FADD和混合流；不要第一轮铺七类×1024点×30进程。
3. **两独立指针链是好起点。** 需要实际验证环完整性、独立性、访问line足迹与缺失延迟；大mmap、random名义、MADV请求都不能代替这些证据。
4. **PMU在整个内循环外批量读、同时保留ns和逐轮数据。** 方向正确，避免每个小窗口syscall。但必须以共同验证过的decoder/差分规则保存事件ID、enabled/running和失效原因；无效不能化成0。
5. **W→X和icache同步保留。** 记录实际生成码hash和循环地址，接口参数/失败行为需收紧；不要只留“冒烟通过”。

### 不可原样使用的部分

| ID / 优先级 | 代码或报告位置 | 事实与反例 | 下一版要求 |
|---|---|---|---|
| R1 / P1，旧项未修 | probe L153–154 | `off=loop_start-e.pos`已是指令下标，又`>>2`。本轮实际导出N64/NOP/miss：branch在byte372，跳byte304（NOP），应回byte112锚点；稳态绕过锚点 | 标签位移统一以字节或指令为单位；实际反汇编验证所有N和两锚点模式 |
| R2 / P1，旧项未修 | probe L182–213、390 | GROUP实际顺序nr/enabled/running/values；struct却nr/val[8]/ena/run。`nr`有效也不能令val[0]成为cycles；cycles打开失败后首个其它事件又会被冒用 | decoder按实际返回长度/组成员解析；事件按ID/请求身份映射；显式选择目标PMU类型（本设备type8，不能直接沿用PERF_TYPE_RAW=4）及内核/虚拟化过滤；缺失、读失败、回退、mux单独失效 |
| R3 / P1，旧项未修 | probe L99、137、148 | fsqrt d0未初始化；FADD写s0，覆盖同一v0寄存器。实际N64导出含8条fsqrt d0和8条fadd s0 | 锚点专用寄存器，与所有filler及ABI保存集无交集；记录FPCR和实际稳定operand。连续sqrt会趋向1，初始化正常数不等于全程正常延迟 |
| ROB-PROT-1 / P1，协议反例 | probe L143–146 | 实际循环A_i→N→B_i→A_(i+1)，缺B之后的N。即使A_i/B_i不重叠，B_i仍可与A_(i+1)重配并行；不能预设稳态D→2D | 采用对称 A→N→B→N，显式保留非对称版本与串行依赖负控。理想平台形态是待验证预测 |
| ROB-PROT-2 / P1，输入/失效 | probe L275–283、390–409 | `-l`不在getopt字符串；任意未知anchor被当miss；atoi无范围检查、追加事件可越界；its/outer=0可出坏数据；PMU失败/无有效周期仍输出0.0 | 封闭输入域、实际参数/发射数量全部输出；无有效估计量命名失败，不能把未知当默认 |
| ROB-ALIGN / P2 | probe L140–141、378–380 | 四入口只改变着陆NOP数量，真实loop_start相同；并未抖动热循环对齐 | 真正改变循环地址/对齐，并固定代码字节预算，避免前端假拐点 |
| ROB-MISS / P1，归因前置 | probe L229–240、329–331 | 初始化/随机化/大buffer不保证每次DRAM miss；两链逐元素相邻追逐及页跨越会混入预取/TLB状态 | 报实际独占line/page足迹、遍历完整性与长缺失证据；hot/long条件有同构控制 |
| ROB-EST / P1，判据错误 | report §4/§5.3–5.8 | 固定ROB−8、NOP不发射推出不占ROB、taken分支必flush、W_ADD与W_NOP差值当PRF下界均不成立。J2预期D→2D却要求差≥1.5D，理想差仅D | 留原始曲线；NOP分配/融合待验；正确预测分支不等于flush；类别差异先报告资源限制。若用平台比值必须显式写比值，不把差/比混淆 |

这些阻塞只约束ROB本项目，不阻塞已验证的TLB测量链。旧R1–R4来源仍见 `docs/reviews/2026-09-30-sm8650-tlb-r2-first-principles.md`，不得把本轮重新确认包装成新问题。

## 最小推进顺序：软件可并行，板上排队

1. **先产可验证生成码。** 下一版组件拟位于 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/`，沿用独立原型边界；只共享已验证的PMU/计时/原始记录能力，不先建ROB专属runner框架。修R1–R3/输入失效，同时交付对称双链、串行负控、精确N=0语义与实际循环对齐；生成码测试覆盖分支、计数、寄存器交集和边界N。
2. **先标定锚点，再扫窗口。** FP相关链的operand/FPCR/特殊值及整数/FP latency-throughput可一起给ALU/FPU研究打底。fsqrt链长度只选两档已实测足以填窗的值；长缺失双链是正交确认，不要求先确定精确cache容量。
3. **有限探索预算。** N从0到1024粗扫（不围着384调参数），只在可解释夹界补细点；先少数filler/低展开/两个真实对齐，确认真实周期和对照方向，再设正式重复与判据。无锚点对照不是可统一扣除的固定开销；N=0仍包含锚点本身的时延。
4. **主张逐层升级。** 第一层输出W_class；类别/锚点/代码布局/延迟供给变化后稳定才讨论ROB约束。PRF/LSQ/前端先触发或NOP融合口径未识别，就保持有效窗口命名，不用候选384兜底。

本轮到此完成“批判性吸收和并行软件路线裁定”。新生成器实现、真实周期标定和ROB采数均在 `docs/open-items.md` 的ROB条目跟踪；本轮不宣布已修骨架或已测ROB。

## 可复现的软件证据

```bash
clang -O2 -Wall -Wextra -Werror \
 docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c \
 -o /private/tmp/rob-window-reviewed-20261009
/private/tmp/rob-window-reviewed-20261009 -t nop -n 64 -i 8 -r 1 -m 1 \
 --write-asm /private/tmp/rob-window-nop-miss-20261009.bin
/private/tmp/rob-window-reviewed-20261009 -t fadd -n 64 -a fsqrt -i 8 -r 1 \
 --write-asm /private/tmp/rob-window-fadd-fsqrt-20261009.bin
```

macOS主机编译及NDK27.2/API34 Android arm64静态交叉编译均无warning；目标产物仅在本机临时目录保留，未部署或运行。导出分别380/396 bytes；按A64条件分支signed imm19解码，回跳372→304而不是112；FP导出8条fsqrt d0、8条fadd s0，寄存器冲突确定。命令只走导出分支，不执行JIT，不采数。后续修复须让这些反例变成验证真实生成码的金样，而非源码字符串断言。
