# ROB近端／远端发射观察 v1.0（仅N0资格冻结）

## 本次任务的目的（给人类看）

证明支持的PMU事件能看到分支后未退休的自有指令，避免把“不曾预测／发射”当ROB小、把cache fill当issue。本任务只有N0，不自动授权容量scan。原648-window退休事件不支持、1536-cell cache marker失败保持终态，详见 `docs/reviews/2026-10-13-rob-speculative-marker-results.md`、`docs/reviews/2026-10-13-rob-cache-marker-results.md`。本稿落实 `docs/design/2026-10-13-rob-near-far-marker-draft.md` 的资格部分。

## 激励与不退休证据

自有独立code/near/far/output四个4KiB页。一个code VA/PFN，两种同长程序，仅16个tap位置NOP或8个不同64B line的LDR X9,[X1,#j*64]加8个不同line的STR X6,[X2,#j*64]。X9先清零，X6是非秘密常数0x12345678。FMOV D0,X0、k次FSQRT D0,D0、FMOV X12,D0、CBNZ X12,finish。finish SB封闭错误路径，返回原bits、存FPSR和X9到独立output。原bits只能0/1.0；FPCR/FPSR0。A训练0/测0，应near寄存器=常数且far8字全部改变；B训练1/测1，M训练0/测1，两者near0、far8字未改。M未退休是自身架构状态检查，不用不支持的LD_RETIRED0x06。

每窗先hot所有near/far line；64训练+4完整wrapper训练均固定，清far在窗外并DSB后调用一次。24trial×A/B/M×NOP/taps=144窗／process，六trial轮转、奇block反序，各member每position4次。3fresh epochs×k16/32=6process/864窗，15秒固定进程间隔。只改自身FPSR/映射，原环境不修改。FD完整关闭，技术／环境first failure即停、partial保留。

## 支持事件与独立校准

6events[0x11,0x08,0x70,0x71,0x22,0x01] = cycles/IR/LD_SPEC/ST_SPEC/BR_MIS_PRED_RETIRED/L1Irefill，USER-only GROUP+ID/pinned/noMUX。官方匹配r0p1 TRM 102484_0001_04_en§18事件表（印刷页136）列0x70/71（https://documentation-service.arm.com/static/6473ef18bae17b773b05d1e8）；必须实际A正控成功，open不作语义支持证明。动态字节需实际producer plan+独立Capstone decode，binary两次NDK一致。

逐trial对taps−NOP求LD/ST/IR/Icache delta，不clip。各process A LD/ST mean[7,9]、q90(abs(delta−8))≤3；B absmean≤1、q90(abs(delta))≤3。A q10−B q90≥4各事件才可用，阈值=(A q10+B q90)/2；M不参与选值。所有control IR delta absmean≤2；Icache delta q90(abs)≤1；披露每窗绝对Icache，门只限定tap增量，不能认证完整前端无瓶颈、不能放宽旧失败门。A/B branchmiss各mode median≤.25。

M eligibility = LD delta≥A/B冻结near阈值且本trial taps窗口branchmiss≥1。全24条保留，至少8eligible；eligible中ST delta≥独立far阈值比例≥.9，才N0通过。报告eligible率、阈值、所有tails、M-on/off branch counts；条件化不能当普遍物理容量证明、miss不作branch-PC唯一归因。6process全部通过才ISSUE_MARKER_QUALIFIED，否则ISSUE_MARKER_NOT_QUALIFIED；无自动加chain／调训练／改门。

## 交付及后续边界

`probes/diagnostic/rob_issue_marker.c`、`tools/diagnostic/rob_issue_marker_analysis.py`、`tools/diagnostic/run_sm8650_rob_issue_marker.py`；tests同名producer/analysis/raw，build/plan/decode在 `docs/reviews/evidence/2026-10-13-rob-issue-marker/`。branch codex/sm8650-tlb-hierarchy-r2，primary独占设备；raw在data/private，公共只匿名摘要。资格不能证明allocation单位／MCQ唯一active constraint；未来容量需固定branch/text/skip/PFN、deadline与filler/resource正交控制，另冻结，不拟合384。跟踪 `docs/open-items.md`。
