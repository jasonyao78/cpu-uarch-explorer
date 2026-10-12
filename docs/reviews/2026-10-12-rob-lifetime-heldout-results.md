# ROB生命周期盲留E2：LIFETIME_PROXY_PREDICTION_REPLICATED（2026-10-12）

**四条E2预测复制，候选g+chain代理区间(352,368]；物理entries/实际allocation/唯一活跃ROB限制仍未认证。原2352窗容量判据INCONCLUSIVE未更改。**

## 本次任务的目的（给人类看）

`docs/design/2026-10-12-rob-lifetime-heldout.md` 在E0完整、E1部分且E2零记录时冻结（365f0f2），新scorer `tools/diagnostic/rob_lifetime_analysis.py`（6109767）固定chain16=(336,352]、chain32=(320,336]。E0是发现、E1不入新确认，E2是盲留验证；不是冒称scan开始前预注册。

| pattern | chain | E2 groups/gap操作区间 | 固定预测匹配 | g+chain候选代理 |
|---|---:|---|---|---|
| nop-pair | 16 | (336, 352] | True | (352, 368] |
| nop-pair | 32 | (320, 336] | True | (352, 368] |
| nop-movzero | 16 | (336, 352] | True | (352, 368] |
| nop-movzero | 32 | (320, 336] | True | (352, 368] |

原cache/iteration门在所选E2窗口434处仍失败，完整值在 `docs/reviews/evidence/2026-10-12-rob-lifetime-heldout/validation.json`；没有删除窗口或晋升原容量终态。另冻的frontend stall/cycles≤1%观察条件通过，最大0.00005244，不能等同前端所有影响都被观测。稳定/供给/完整硬审计、near/below范围规则和两个高侧点均保留。

链长改变的转折约移动16组，而非原静态g+2k方程的32组；逐条退休及跨迭代生命周期必须进入解释。MOV/MOV在原网格末点才近串行，没有两个平台点，不能硬凑共同模型。这个新结果支持一个有效窗口预测，不能将(352,368]改名物理ROB entries或为了384补任意固定offset。α融合、credit/packet以及其它活跃资源仍未知。

完整raw `20261012T102234Z-rob-zero-latency-units-scan`，1182文件SHA；source5aecbbb/build7c7647e/actual launch3124a73，新分析HEAD `04d99859708d9cc2263da80b0159e741f09c6601`，branch `codex/sm8650-tlb-hierarchy-r2`。第二算术直接raw核验2352窗、四条E2分类/区间/前端条件与全部原cache失败列表，以及E0的98输入SHA，与新consumer完全相同。`docs/reviews/2026-10-12-rob-zero-latency-scan-results.md` 保存原冻结判据、完整18曲线/事件/删失；两种裁定分列，不混证据级别。

本有限预测验证结束，未认证项继续 `docs/open-items.md`，禁止从synthetic金样或third-party384指定物理答案。下一优先可直接约束生命周期/实际分配单位的证据，不再重复本网格追同一门。
