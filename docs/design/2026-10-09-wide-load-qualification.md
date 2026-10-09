# ROB 长load足迹上推反证（冻结v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-09-long-load-thp-results.md`已证明实际大页使翻译干扰很低，64/128MiB仍非每次load都由远层miss代理覆盖。本轮仅上推足迹，检验剩余命中/访问预测残差是否随足迹改变，不预设随机指针已排除预取；不通过便保留边界，不调低原资格门。用户授权持续端到端推进，当前Agent独占手机，与TLB串行。

## 固定6进程 /36窗

分支`codex/sm8650-tlb-hierarchy-r2`。`tools/diagnostic/run_sm8650_minimal.py` mode=`rob-miss-wide-thp`：epoch0 footprint={1,256,512}MiB、epoch1反序。1MiB显式4k热点，256/512显式thp2m长点；i=max(131072,MiB×8192)，完整环每call访问全部line。N0/NOP/seed42/对齐0/同VA paired P-S，3轮交错顺序，CPU7/type8、6事件及每进程前15秒固定冷却不变。

使用已构建并在目标板实际THP通过的同binary `afeafad4b9538768efacddf07ee50b5ba6b8795c70fdf5e070b246c5d1f7b161`、source `2a37795107163a9c3effd8fc3e25410c0dd75695`；不改JIT。新的build注册`docs/reviews/evidence/2026-10-09-long-load-wide/build.json`，沿原THP精确单VMA/AnonHugePages=Rss/Swap0及每窗pre/post核验；hint失败/部分覆盖/环境漂移停块，不fallback。512MiB/进程为本轮最大足迹，留有充足设备空闲内存；不无限增加footprint追门。

## 同一科学门、独立判定

`tools/diagnostic/analyze_long_load.py`显式mode接受新shape，旧64/128shape不能混入。仍复算`c93e788`原门：P/S每轮L1/L2/LL均1.8–2.2，walk≤.02，member cycles range/median≤.10，各对S/P1.6–2.4，P/S L2与LL均值差/两均值≤.10，P中位cycles≥max(热P×4,171)，热P/S各轮LL≤.1。长点各自在两epoch通过才有资格，不跨footprint或轮次平均救门。

- 通过：按`docs/design/2026-10-09-long-load-qualification.md`有限N0/128/256/384/512扫描，检查双锚点与serial对照再决定细扫，不预定384。
- 不通过：明确究竟miss/稳定/比率/翻译哪门失败；下一路线优先做不改足迹的访问次序/编码地址或已认证事件分母对照，命名仍受限，不能把本批失败推广为所有长load方法都不可行。

raw私有，脱敏逐轮全部保存；source/binary/launch/driver/protocol绑定。源码`docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c`与`probes/common/rob_backing.h`，actual-backing审计`tools/diagnostic/summarize_sm8650_minimal.py`。未竟物理ROB/PRF/RS/融合识别由当前端到端负责人登记`docs/open-items.md`。
