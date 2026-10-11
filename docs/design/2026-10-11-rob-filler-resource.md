# ROB filler资源与有效隐藏窗口（冻结v1.0.1，事件标签勘误）

## 本次任务的目的（给人类看）

旧NOP+fsqrt的有效窗口已取得，而冷load理想串行模型不合格。下一步优先比较指令流如何改变有效隐藏窗口，不追冷模型或384。三方向中，继续加密NOP不新增资源辨识；为救长load改门违反原资格；本轮选现有真实生成器的NOP/ADD/MOVI/MOVR/FADD，避免新框架和码形重写。采用brainstorming/writing-plans自审、executing-plans与TDD；用户已授权持续自主推进，不新增例行确认或代理。

## 精确合同与命名

生产源 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c` 原样，binary source1ef4baa，SHA cb4645f65d8352e839144541bcaefab32cad5a7ce2006d9fb219479c8384d5ba；两次独立重建已一致，本轮复核source/deps及导出。新mode `rob-resource`，driver `tools/diagnostic/run_sm8650_minimal.py`，消费者 `tools/diagnostic/rob_resource_analysis.py`，build/plan `docs/reviews/evidence/2026-10-11-rob-resource/`。不改变旧mode或旧门。

每epoch按class{nop,add,movi,movr,fadd}×anchor{none,fsqrt}×每gap N{0,128,256,384,512,704,768}枚举，epoch1整个70条件反序；共140进程/420窗。i131072、rounds3（全保留）、chain16/align0/seed42/CPU7/type8，events[11,08,03,17,34,02]，两侧均N filler。0x02为L1I_TLB_REFILL计数（0x01才为L1I_CACHE_REFILL），不作前端供给充分证明。FADD只写d4..7，anchor d0、operand sqrt(1)、FPCR0；ADD/MOVI/MOVR写x4..11，源x16/17，不改loop x3。不使用miss/THP/任何内存锚点，code <7KiB但不据大小排除前端限制。MOVR/MOVI的elimination、融合及实际分配粒度未经本轮认证。

每进程固定1秒间隔，root串行独占；部署与初末/每进程pre/post环境策略沿现有walt基线，不改温控/频率/PMU权限。强制host-exporter，真实producer每条件--write-asm；实际config与注册plan/export精确typed匹配。独立A64 words核全部140代码的prologue、FP初始化、两gap filler、branch回跳/RET和字节数；raw含kernel event ID完整唯一、六uint64/no-mux、typed runtime/round。stderr、缺失/重复/乱序/来源/环境失败停整批，保留前缀不补测。前后端点频率不等同窗内频率。

每class/epoch/anchor/N三窗原值与中位保留。D_e(N)=median fsqrt(N)−median fsqrt(0)，效果量δ固定1 cycle/iter（沿旧局部报告，仅可比选择，不是显著性）。首个N_i使两epoch在该点和全部后点D>1、至少两个高点、此前全部|D|≤1，且所有该class fsqrt格三窗range/median≤.10，才给操作性隐藏消失区间(N_prev,N_i]。128首点高记left-censored；仅末点高right-censored；两epoch分歧/负向越界/回落至效果阈值带或以下/波动超门ambiguous；全点低no-onset-through768。none按同网格原值展示，同时报告max[fsqrt(0),none(N)]参考及signed残差，不统一扣开销、不作ROB/PRF数量。classes分别裁定不池化；不输出物理capacity，物理ROB/PRF/RS/融合继续OPEN。

## 执行与验收步骤

1. `tools/diagnostic/tests/test_rob_resource.py`真实编译immutable1ef4baa三源，独立140请求/实际config/codeword；先缺消费者/新mode RED，再实现固定plan/config/code/audit/数学GREEN。反例含类型、branch、寄存器、事件ID、缺格/重复/乱序、mux、坏数据/左右删失/epoch冲突；事件/环境外部值可合成，但不手写producer config/code。raw绑定测试在build注册后补，Gitblob/source/env/plan完整复现。
2. 源码/driver/consumer提交；注册实际host导出140plan与build。确保binary/source/driver/protocol/plan相互绑定；旧10400 TLB和冷state完整raw重放不漂移；全diagnostic/runner/analysis/CTest后提交launch。
3. root有限140进程；消费者先完整raw技术接受再420窗统计；另一条直接JSONL算术复算；公开匿名完整原值、图与 `docs/reviews/2026-10-11-rob-resource-results.md`，README/OI更新。原始数据仅data/private，无VA/序列号入库。技术失败不臆造科学结果，科学失败不增N/放宽δ追门。

## v1.0.1勘误（执行完成后登记，统计规则不变）

启动1551c99的v1误将0x02标签写为I-cache refill；[Arm官方事件表](https://raw.githubusercontent.com/ARM-software/data/master/pmu/cortex-x4.json)明确0x02是L1I_TLB_REFILL，0x01才是L1I_CACHE_REFILL。编码、矩阵、原始数据、效果量/波动门均未变，不重标采样；本次实际protocol SHA仍为 `cd4ecca1d3e0db2e7c1ac8d6a9082ca7a18c2c48019ff0fd1703f9a24fde21f1`（Gitblob1551c99）。同时将“回落”精确写成已有数学条件的反面：后点回落至δ带或以下，不是禁止阈值之上的数值下降；1551c99已交付的判据函数不改，完整重放字节一致。
