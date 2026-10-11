# SM8650 TLB/ROB 目标对账（2026-10-11，继续执行）

## 本次任务的目的（给人类看）

区分已完成的有限测量与整个目标，避免有更多测试或漂亮曲线就声称“TLB/ROB全部完成”。用户授权第一性原理、小型可推翻探针、root独占端到端推进；原r2合同是问题来源，不强行复活旧正式大矩阵/旧frozen。

| 目标 | 当前证据/终态 | 尚需完成的工作 |
|---|---|---|
| TLB 反证与局部转折（用户近期优先） | **有限任务完成**：`docs/reviews/2026-10-11-tlb-address-geometry-results.md` / `docs/reviews/2026-10-11-tlb-local-turn-results.md`；7族(7,8]、100族(8,9]，匹配C2、双order/跨度、五mapping复制 | 停止同曲线无限加密；物理ways/descriptor唯一归因保持未识别 |
| TLB Q-A：L1 refill 分布敏感性 | 原第一次战役是宽区间；现局部set/victim并不等价分布问题 | 同访问数/节点偏移/代码、连续/稀疏/随机**页集合**、同集合order控制；HPA/PTE_CONT不可观察时记UNKNOWN，给有限终态 |
| TLB Q-B：冲突行为 | 条件化操作曲线与victim响应已有真实负控/实测激励；原正式B1/B2合同与新独立协议应分列 | 最终报告说明新协议回答范围；不把lookup当admission、walk数当初始缺失项数，禁止硬换算混合条目物理ways |
| TLB Q-C：候选索引族（探索） | C1/C2低位签名有区分力；256MiB采样域的高位折叠族仍可等价 | 明示域内等价与有限候选状态；不因C1正/C2负命名唯一H1 |
| TLB Q-D：有效在飞占用（原必做） | **有限必做完成**：`docs/reviews/2026-10-11-tlb-walk-parallel-results.md`，495窗/240长门、两scope/K=1/2/4/8及低walk匹配line对照；固定总占用.553→3.039，短门235/240真实保留 | 仅认证长窗有效响应；不认证物理walker/MSHR/LQ，短窗/更大K另案触发 |
| ROB：可信流量/码/窗口响应 | 修复probe与GROUP/ID，NOP细扫有效区间，资源/操作事件、零值控制完成；见 `docs/reviews/2026-10-11-rob-zero-value-results.md` | 仅报告实际每gap N/操作性隐藏响应，不以NOP数或OP/IR比计算allocation |
| ROB：区分资源限制 | 同值依赖 `docs/reviews/2026-10-11-rob-dependency-results.md` 技术接受、主门not-qualified；NONE波动是实际失败，rename接近零仍有周期响应 | 针对NONE供给波动及同进程配对做有限控制；不简单重跑或删失败负控 |
| ROB：物理容量 | **未识别**。长load模型多条路线不合格，NOP/零值/依赖流非唯一结构解释；384是第三方参考 | 完成可识别性审查；有合格allocation标尺和正交控制才认证，否则给有事实依据的有限不可识别终态，不能把预算停下冒称容量已测 |
| 软件交付与分支收口 | m0b使命已完成、代码在r2；source/build/launch/protocol/raw逐批分开 | 原独立JSONL不是正式schema v2；正式runner/CMake接入按稳定协议需要决定，未做项归 `docs/open-items.md`；main集成/测试/远端后才删除分支 |

当前仍在继续执行。下一补TLB Q-A的页集合/offset/order控制（Q-D有限必做已完成）；ROB供给/配对设计与软件可交错，手机必须串行。未知问题可在有限协议完成后正式判定不可识别，但表中明确尚未实施的必做控制不能由一句“科学问题OPEN”替代。ALU/FPU完整latency/throughput另列后置，不因本轮用fsqrt锚点就声称已完成FPU探测。

执行与归属：当前端到端负责人；工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`，分支 `codex/sm8650-tlb-hierarchy-r2`。所有未完成项、触发条件和owner在 `docs/open-items.md`。远端按用户暂不处理，本文不声称push/main合并或worktree回收。
