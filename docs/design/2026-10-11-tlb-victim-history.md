# TLB victim身份与准备次序（冻结 v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-11-tlb-competition-results.md`在8遍竞争下K8..11均双方向5/5响应，但victim固定page0、history固定顺序。反证目标：现有(8,9]操作性转折是否只来自特定victim或准备历史，而非通用同页集响应。直接增K改变集合却不能排此解释；全局TLB reset缺少可审计接口；本轮保留最大12页/同一W页集，只轮换被观察页和history次序。新准备协议不能与旧批拼成物理ways证据。

## 实现合同（实施前冻结）

计划新源 `probes/diagnostic/tlb_victim_history.cpp`、`probes/diagnostic/tlb_victim_history_layout.h`，复用 `probes/diagnostic/tlb_history_layout.h`的实际12页选择、旧9前缀、node64*i、512filler中闭合128前缀。旧probe/header原样。新driver mode `tlb-victim-history`、consumer `tools/diagnostic/tlb_victim_history_analysis.py`，build/plan/evidence `docs/reviews/evidence/2026-10-11-tlb-victim-history/`；源实现与测试通过后另登记实际source/launch/binary，不把这些计划路径冒称已交付代码。

每mapping同2H最大页集；W{8,9}各观察victim索引{0,floor(W/2),W−1}；竞争集合精确为[0,W)除victim，K=W−1，不能因换victim而变页集。history顺/逆、竞争顺/逆各二选。W1/v0/K0为各H/history/竞争方向的匹配空竞争控制，共8cells；主48cells，合56cells。按history→W{1,8,9}→victim→竞争方向→H交错，奇数epoch整体逆序；5mapping。每cell16trial、固定8竞争pass加1victim窗，8064窗/mapping、40320窗。

每cell只建链一次：slot0各页自环，slot3十二页顺/逆闭环，slot4竞争集合顺/逆闭环，所有槽在同一cacheline，不在trial内写页。history顺序起点为0或11，一圈12页全触达；每trial [F128→history12]×8，然后F128→选定victim1次训练。随后每pass F128→snapshot→K次slot4竞争→snapshot，再F128→snapshot→victim1次slot0→snapshot。全部元数据在noinline窗最后F前取得，窗含snapshot/read用户开销。改变victim也改变所读node值/offset，但相同page集合与固定槽控制这些可观测差；准备非reset，lookup非admission。

config完整version/probe/W/rank/history/方向网格、56cells/8064windows；plan与round含h/w/victim/history_direction/direction/passes8/rounds16、position/role/pass_index。geometry私有VA完整，消费者按实际collector及filler数学核后只输出匿名记录。六PMU事件[11,05,2d,2f,34,35]、CPU7/base4K/MIDR/AnonHugePages0、typed uint64/no-mux/全部role/顺序强制。每cell前后backing；每epoch前固定15秒冷却，初末/每进程pre/post环境沿walt既有策略、不更改温控/频率/THP。binary/header递归source、NDK两次重建、实际最后F/单load反汇编、Git launch/driver/protocol/plan/build/raw SHA完整。技术失败停整批，不补格或重试到过门。

## 统计与命名

逐epoch/H/W/victim/history/竞争方向/pass，16窗原值与均值保留；W1匹配同H/history/竞争方向及pass位置。每非零K/pass的0x05及0x2f均值减W1均值须在[.75K,1.25K]，称相关层lookup激励相容，不称真实same-set或allocation。1920激励点全部披露，不能先丢失败cell。

victim逐cell保存walk>0率、均值、count>1、前后8率差；H1−H2率≥.5且各W1对应H≤.125才称该有限条件有响应观察；任一H count>1或前后8漂移>.25命名窗口污染/准备漂移。每W/victim/history要求同mapping两竞争方向皆有效响应，≥4/5mapping才称重复响应，共12复制项。不存在首高点/物理capacity估计量；完整呈现W8与W9、3victim×2history响应表。即使全W8低/W9高也只约束本协议操作性边界，未测试其它victim/target、高位hash、描述符或真实替换算法，不声明物理8ways/LRU。

## 执行与验收

以brainstorming/writing-plans完成冻结自审；按已授权持续自主/TDD执行，不派上板Agent。真实host --plan/config/schedule与实际header逐页链接轨迹先RED→GREEN，独立Python期待56cell/8064role/完整victim与竞争集合，不能只核计数；非法W/victim/history/方向与零竞争不读pointer均拒绝。消费者用真实producer config/plan/geometry，只模拟外部PMU窗口，完整矩阵正例和typed/null/缺失/重复/乱序/错误链接/覆盖/准备漂移负例；真实driver落盘+来源/raw完整闭合测试后才上板。NDK完整编译、独立反汇编、旧40320以外四批重放、全量软件回归、提交启动树，再有限5mapping采样，第二直接JSONL算术核、匿名完整原值/图/报告、README/OI同步与范围提交。

归属当前端到端TLB负责人。后置：实际ways/未建模hash/PFN-cache/描述符竞争与替换算法，仅在本身份/历史对照后选择下一可识别控制；正式A1/旧frozen/14条记录不拼接。ROB资源事件批与依赖/生命周期、固定频率、正式runner/schema/CMake按 `docs/open-items.md`原归属/触发。本轮远程不操作。
