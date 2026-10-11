# SM8650 TLB/ROB 目标对账（2026-10-11，有限结果与继续研究）

## 本次任务的目的（给人类看）

区分已完成的有限测量与整个目标，避免有更多测试或漂亮曲线就声称“TLB/ROB全部完成”。用户授权第一性原理、小型可推翻探针、root独占端到端推进；原r2合同是问题来源，不强行复活旧正式大矩阵/旧frozen。

| 目标 | 当前证据/终态 | 尚需完成的工作 |
|---|---|---|
| TLB 反证与局部转折（用户近期优先） | **有限任务完成**：`docs/reviews/2026-10-11-tlb-address-geometry-results.md` / `docs/reviews/2026-10-11-tlb-local-turn-results.md`；7族(7,8]、100族(8,9]，匹配C2、双order/跨度、五mapping复制 | 停止同曲线无限加密；物理ways/descriptor唯一归因保持未识别 |
| TLB Q-A：L1 refill 分布敏感性 | **有限必做完成**：`docs/reviews/2026-10-11-tlb-page-distribution-results.md`，2175窗/2160背景门，三集合/offset/order/五mapping；60区间(96,112]，主分布INCONCLUSIVE | 数值方向/幅度完整保留；HPA/PTE_CONT=UNKNOWN，物理entry/归因不升级；新正交干预触发另案 |
| TLB Q-B：冲突行为 | 条件化操作曲线与victim响应已有真实负控/实测激励；原正式B1/B2合同与新独立协议应分列 | 最终报告说明新协议回答范围；不把lookup当admission、walk数当初始缺失项数，禁止硬换算混合条目物理ways |
| TLB Q-C：候选索引族（探索） | C1/C2低位签名有区分力；256MiB采样域的高位折叠族仍可等价 | 明示域内等价与有限候选状态；不因C1正/C2负命名唯一H1 |
| TLB Q-D：有效在飞占用（原必做） | **有限必做完成**：`docs/reviews/2026-10-11-tlb-walk-parallel-results.md`，495窗/240长门、两scope/K=1/2/4/8及低walk匹配line对照；固定总占用.553→3.039，短门235/240真实保留 | 仅认证长窗有效响应；不认证物理walker/MSHR/LQ，短窗/更大K另案触发 |
| ROB：可信流量/码/窗口响应 | 修复probe与GROUP/ID，NOP细扫有效区间，资源/操作事件、零值控制完成；见 `docs/reviews/2026-10-11-rob-zero-value-results.md` | 仅报告实际每gap N/操作性隐藏响应，不以NOP数或OP/IR比计算allocation |
| ROB：区分资源限制 | **有限控制完成**：原跨进程144窗与新同VA480窗均技术接受、主门not-qualified；新15/15 N0稳定、80/80 D正，但NONE范围38.219cycles仍失败。`docs/reviews/2026-10-11-rob-same-address-pair-results.md` | 同VA控制不能等于供给稳定；新资源/packing/生命周期干预须先建立可识别判据，不重复追门 |
| ROB：供给状态/代码维护 | **新增有限对照完成**：`docs/reviews/2026-10-11-rob-resident-control-results.md`，单程序/VA 240窗技术接受；NONE resident仍44–72cycles波动，原字节额外维护效应未一致复制 | 不认定Icache维护或频率为唯一根因；下一资源流/生命周期干预先冻结，不能以N0稳定跳过N128供给资格 |
| TLB：高位折叠辨识 | **新设计已冻结**：`docs/design/2026-10-11-tlb-cross-region.md`，共同victim/四域G1与G3相反候选 | 实现/真实producer全链/有限设备数据尚未完成，不能宣称H1/H3已辨识 |
| ROB：物理容量 | **本组方法正式终态MODEL_UNIDENTIFIABLE**。长load资格反例与NOP/零值/依赖/同VA完整有限控制已归档；384是第三方参考 | 审查已交付 `docs/reviews/2026-10-11-tlb-rob-identifiability.md`；新单位标尺与活跃约束认证触发另案，物理entries未测得 |
| 软件交付与分支收口 | m0b使命已完成、代码在r2；source/build/launch/protocol/raw逐批分开 | 原独立JSONL不是正式schema v2；正式runner/CMake接入按稳定协议需要决定，未做项归 `docs/open-items.md`；main集成/测试/远端后才删除分支 |

此前阶段有限必做/反证/控制已闭环；用户本次要求继续，新增正交研究仍执行中。**技术交付通过；物理TLB/ROB容量命名不通过**。Q-A=INCONCLUSIVE、Q-D长窗有效响应通过、Q-B/Q-C仅限定行为/候选状态；ROB同VA科学负控不合格与物理MODEL_UNIDENTIFIABLE分别保存。原正式B1/B2、A1/A2/A3矩阵没有自动完成，按用户第一性原理路线的独立有限协议报告，不伪装合同等价。若“TLB和ROB完整完成”指精确全部物理参数，该目标仍未达成；当前结束的是具有事实终态的有限测量任务。未知问题需新增正交干预/单位标尺才有新可识别路线，不能无限加密或用预算结束冒称测得。ALU/FPU完整latency/throughput另列后置，fsqrt锚点不等于FPU完成。

执行与归属：当前端到端负责人；工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`，分支 `codex/sm8650-tlb-hierarchy-r2`。所有未完成项、触发条件和owner在 `docs/open-items.md`。远端按用户暂不处理，本文不声称push/main合并或worktree回收。
