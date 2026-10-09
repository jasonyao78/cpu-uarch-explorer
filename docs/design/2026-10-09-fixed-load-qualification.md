# ROB 固定256MiB长load资格重建（冻结v1）

## 本次任务的目的（给人类看）

`data/private/20261009T035527Z-rob-miss-wide-thp/`在512MiB初始backing核验失败后按协议停块。已完成256MiB只有单epoch，不能晋升为合格锚点。现固定已技术可用的256MiB，独立重建完整两epoch资格；不是拼接旧前缀，也不修改原科学门。用户授权持续推进，当前Agent独占手机，与TLB串行。

## 固定4进程 /24窗

分支`codex/sm8650-tlb-hierarchy-r2`；驱动`tools/diagnostic/run_sm8650_minimal.py`显式mode=`rob-miss-fixed-thp`。epoch0={1,256}MiB，epoch1={256,1}MiB；N0/NOP/seed42/对齐0，3轮同VA P/S交错，CPU7/type8，i=max(131072,MiB×8192)，完整环每call覆盖全部line。热点1MiB显式4k、256MiB显式thp2m；同binary/source/事件/每进程前15秒冷却与上一轮一致。旧256前缀仅作选择本轮可用激励的探索背景，既不代替本轮重复，也不进入资格计算。

build注册`docs/reviews/evidence/2026-10-09-long-load-fixed/build.json`，沿用binary SHA `afeafad4b9538768efacddf07ee50b5ba6b8795c70fdf5e070b246c5d1f7b161`、source `2a37795107163a9c3effd8fc3e25410c0dd75695`。实际THP exact VMA/AnonHugePages=Rss/Swap0及逐窗pre/post必须全过；任何技术失败停块，不retry512、不改全局defrag。

## 原科学门与后续

`tools/diagnostic/analyze_long_load.py`新mode须恰好4进程/8member/24窗，旧6进程或64/128/512shape不得重标；每member仍3轮，沿`c93e788`全部科学门：每轮L1/L2/LL1.8–2.2，walk≤.02，member cycles range/median≤.10，每对S/P1.6–2.4，P/S L2和LL均值差/两均值≤.10，P中位cycles≥max(同epoch热P×4,171)，热点各轮LL≤.1。256必须在两epoch独立通过才可称低翻译干扰、远层miss主导的候选；不命名DRAM或物理ROB。

通过后按`docs/design/2026-10-09-long-load-qualification.md`有限N0/128/256/384/512做同VA P/S响应；不通过保留具体门并转访问次序/地址编码/已认证事件分母对照，不增足迹追门。原始stdout/环境/生成码私有，全部脱敏轮计数公开；source/launch/driver/protocol/build SHA分开。512初始失败缺实际smaps诊断，根因仍OPEN，登记`docs/open-items.md`，不得猜成唯一THP覆盖原因。
