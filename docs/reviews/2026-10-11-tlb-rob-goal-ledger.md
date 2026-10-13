# SM8650 TLB/ROB 目标对账（2026-10-11，有限结果与继续研究）

## 本次任务的目的（给人类看）

区分已完成的有限测量与整个目标，避免有更多测试或漂亮曲线就声称“TLB/ROB全部完成”。用户授权第一性原理、小型可推翻探针、root独占端到端推进；原r2合同是问题来源，不强行复活旧正式大矩阵/旧frozen。

| 目标 | 当前证据/终态 | 尚需完成的工作 |
|---|---|---|
| TLB 反证与局部转折（用户近期优先） | **有限任务完成**：`docs/reviews/2026-10-11-tlb-address-geometry-results.md` / `docs/reviews/2026-10-11-tlb-local-turn-results.md`；7族(7,8]、100族(8,9]，匹配C2、双order/跨度、五mapping复制 | 停止同曲线无限加密；物理ways/descriptor唯一归因保持未识别 |
| TLB Q-A：L1 refill 分布敏感性 | **有限必做完成**：`docs/reviews/2026-10-11-tlb-page-distribution-results.md`，2175窗/2160背景门，三集合/offset/order/五mapping；60区间(96,112]，主分布INCONCLUSIVE | 数值方向/幅度完整保留；HPA/PTE_CONT=UNKNOWN，物理entry/归因不升级；新正交干预触发另案 |
| TLB Q-B：冲突行为 | 条件化操作曲线与victim响应已有真实负控/实测激励；原正式B1/B2合同与新独立协议应分列 | 最终报告说明新协议回答范围；不把lookup当admission、walk数当初始缺失项数，禁止硬换算混合条目物理ways |
| TLB Q-C：候选索引族（探索） | C1/C2低位签名有区分力；新增四域控制在有限H1/H3候选组支持low-only，旧单域等价不再冒充新证据边界 | 明示域内等价与有限候选状态；不因C1正/C2负命名唯一H1 |
| TLB Q-D：有效在飞占用（原必做） | **有限必做完成**：`docs/reviews/2026-10-11-tlb-walk-parallel-results.md`，495窗/240长门、两scope/K=1/2/4/8及低walk匹配line对照；固定总占用.553→3.039，短门235/240真实保留 | 仅认证长窗有效响应；不认证物理walker/MSHR/LQ，短窗/更大K另案触发 |
| ROB：可信流量/码/窗口响应 | 修复probe与GROUP/ID，NOP细扫有效区间，资源/操作事件、零值控制完成；见 `docs/reviews/2026-10-11-rob-zero-value-results.md` | 仅报告实际每gap N/操作性隐藏响应，不以NOP数或OP/IR比计算allocation |
| ROB：区分资源限制 | **有限控制完成**：原跨进程144窗与新同VA480窗均技术接受、主门not-qualified；新15/15 N0稳定、80/80 D正，但NONE范围38.219cycles仍失败。`docs/reviews/2026-10-11-rob-same-address-pair-results.md` | 同VA控制不能等于供给稳定；新资源/packing/生命周期干预须先建立可识别判据，不重复追门 |
| ROB：供给状态/代码维护 | **新增有限对照完成**：`docs/reviews/2026-10-11-rob-resident-control-results.md`，单程序/VA 240窗技术接受；NONE resident仍44–72cycles波动，原字节额外维护效应未一致复制 | 不认定Icache维护或频率为唯一根因；下一资源流/生命周期干预先冻结，不能以N0稳定跳过N128供给资格 |
| TLB：高位折叠辨识 | **新有限主判据通过**：`docs/reviews/2026-10-11-tlb-cross-region-results.md`，34560窗、1440门、两个target的十曲线W12均I/G1正、G3负，low-only候选获支持；W8一多walk残差保留 | 只分辨本候选组，未唯一认证hardware hash/ways；root不是EL3，TRM内部RAM接口不能普通上板读取 |
| ROB：真独立锚点与NOP间隔 | **新有限对照完成**：`docs/reviews/2026-10-11-rob-dual-anchor-v2-results.md`，D0/D1约208/D0串行约416；fresh144资格+720扫描技术过，90进程稳定；渐进退化至N704近串行，单区间INCONCLUSIVE。v1空循环门失败144窗另存不晋升 | 官方NOP+Any fusion提示单位问题；下一匹配ADD工作/值/目的集合的单位与生命周期控制，不能NOP/2报物理entry |
| TLB：均衡全局reach与几何反证 | **新有限主通过**：`docs/reviews/2026-10-12-tlb-balanced-reach-results.md`，825窗/810門全过，同页数/低8位hist/offset仍复制walk差；GEOMETRY_SENSITIVE、三族曲线heterogeneous | 不能报精确物理entries；MMUTC I/D/descriptor代理、PFN/CONT/HPA未唯一辨识，先补可观测物理几何能力 |
| ROB：匹配ADD工作/语法组 | **新有限资格结束**：`docs/reviews/2026-10-12-rob-fusion-groups-results.md`，144窗技术接受，ADD无锚点流波动、另1取指窗越门，not-qualified；扫描未启动 | 下一架构目的/生命周期控制，不以更稳NOP+ADD等同实际fusion或条目标尺；不复跑追门 |
| TLB：同物理数据页几何反证 | **主通过**：`docs/reviews/2026-10-12-tlb-shared-alias-results.md`，279窗/270门，330240原始位及PFN身份通过；七个N/族配对差复制 | 只排除本新协议data PFN不同是必要解释；descriptor/虚拟高位/指针值预取及CONT仍待辨，不回填旧归因 |
| ROB：架构目的与相对单位 | **新目的控制完成**：`docs/reviews/2026-10-12-rob-destination-control-results.md`，192真机窗参考资格过，裸ADD live/XZR均波动，主INCONCLUSIVE；`docs/design/2026-10-12-rob-retirement-units.md` 已冻结、源码df2171d/build47ff455 | 新192真机资格亦已完成：`docs/reviews/2026-10-12-rob-retirement-units-results.md`，两链参考稳，ADD+SUB供给45–50%波动、9取指门失败；2352扫描未启动。实际allocation和活跃ROB约束仍未认证，下一正交干预须另冻 |
| TLB：高位/全位stored pointer反证 | **新有限协议结束**：`docs/reviews/2026-10-12-tlb-pointer-representation-results.md` / `docs/reviews/2026-10-12-tlb-full-pointer-representation-results.md`，333/495窗、324/486主门，实际全位低地址干预和全部signed DID复核；.10尺度GEOMETRY_CONTRAST_NOT_CHANGED_AT_DETECTION_SCALE | 不是全部DMP/预取排除证书；全位简单raw projection非必要，descriptor/HPA/PTE_CONT仍需独立约束 |
| TLB：同VA/同物理轨迹的PFN邻接 | **有限批完成**：`docs/reviews/2026-10-12-tlb-pfn-association-results.md` /d4a6e9a，297窗/288背景门、实际0邻接；六no-adjacent曲线reach=(1792,2048]复制 | 关联主INCONCLUSIVE，自然激励NOT_EXCITED；虚拟顺序残余、descriptor/HPA未知，不改名2048physical entries |
| ROB：零延迟资源类与生命周期 | **有限批完成**：`docs/reviews/2026-10-12-rob-zero-latency-scan-results.md` /a1f0082，192资格+2352扫描；`docs/reviews/2026-10-12-rob-lifetime-heldout-results.md` /6f98b27，E2四预测复制，g+k=(352,368] | 原取指门1792窗失败、18曲线INCOMPUTABLE、main INCONCLUSIVE；实际分配单位和唯一活跃ROB限制仍未认证，下一生命周期干预 |
| TLB：直接descriptor可观测性 | **自有root/leaf能力通过**：`docs/reviews/2026-10-12-translation-self-read-results.md` /64dcbe4，三进程正控3/负控0、两root表项，20raw SHA及实际78指令核验 | 新增 `docs/reviews/2026-10-12-translation-self-leaf-results.md` /77a3293，3进程leaf/PFN身份通过；COW观察不能回填稳态CONT/HPA，shared-alias触发资格 `docs/reviews/2026-10-12-translation-shared-leaf-results.md` /f330dff为NOT_EXCITED、无重试；需新shared入口，descriptor因果/容量仍未认证 |
| ROB：退休状态边界与输入重置 | **384窗有限资格完成**：`docs/reviews/2026-10-12-rob-retirement-drain-results.md` /b930bac，FPSR qualified、FPCR两个NONE0稳定门失败保留not-qualified；I/S k16≈225/432、k32≈462/848 | 只认证本FPSR参考，后续推测allocation和实际单位未认证；下一anchor排程可检验额外延迟，不自动N扫、不把k32改写433 |
| ROB：物理容量 | **本组方法正式终态MODEL_UNIDENTIFIABLE**。长load资格反例与NOP/零值/依赖/同VA完整有限控制已归档；384是第三方参考 | 审查已交付 `docs/reviews/2026-10-11-tlb-rob-identifiability.md`；新单位标尺与活跃约束认证触发另案，物理entries未测得 |
| 软件交付与分支收口 | m0b使命已完成、代码在r2；source/build/launch/protocol/raw逐批分开 | 原独立JSONL不是正式schema v2；正式runner/CMake接入按稳定协议需要决定，未做项归 `docs/open-items.md`；main集成/测试/远端后才删除分支 |

此前阶段有限必做/反证/控制已闭环；用户本次要求继续，最新有限批已完成，下一可观测descriptor/生命周期正交研究继续推进。**技术交付通过；物理TLB/ROB容量命名不通过**。Q-A=INCONCLUSIVE、Q-D长窗有效响应通过、Q-B/Q-C仅限定行为/候选状态；ROB同VA科学负控不合格与物理MODEL_UNIDENTIFIABLE分别保存。原正式B1/B2、A1/A2/A3矩阵没有自动完成，按用户第一性原理路线的独立有限协议报告，不伪装合同等价。若“TLB和ROB完整完成”指精确全部物理参数，该目标仍未达成；当前结束的是具有事实终态的有限测量任务。未知问题需新增正交干预/单位标尺才有新可识别路线，不能无限加密或用预算结束冒称测得。ALU/FPU完整latency/throughput另列后置，fsqrt锚点不等于FPU完成。

执行与归属：当前端到端负责人；工作树 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2`，分支 `codex/sm8650-tlb-hierarchy-r2`。所有未完成项、触发条件和owner在 `docs/open-items.md`。远端按用户暂不处理，本文不声称push/main合并或worktree回收。

## 2026-10-13 shared descriptor能力增补

`docs/reviews/2026-10-13-translation-installation-read-results.md`：branch codex/sm8650-tlb-hierarchy-r2，source0fcccb2/buildfc2fdcc/launch81fc4d1。entry99/return32的新do_set_pte观察器3/3进程通过，负控0/entry1/return1，canonical-alias PFN及installed leaf匹配；实际父项类型/VA索引与两个层级地址关系一致，20 raw SHA第二算术复核。Linux table child PA可观察，machine DRAM/HPA与稳态CONT、TLB物理capacity/ways/hash仍未认证；三例安装CONT0只属该时点。31新旧关联tests通过，全量新回归另列最终证据。原shared-write NOT_EXCITED、旧ROB/TLB终态均不覆盖。下一先绑同进程性能graph的descriptor身份，再正交布局对照；ROB blocked/interleaved anchor顺序独立推进。

## 2026-10-13 anchor-order参考残差复核

`docs/reviews/2026-10-13-rob-anchor-order-results.md`，branch codex/sm8650-tlb-hierarchy-r2，source d1c99ea/build ead5e51/launch9be15af。完整12新进程768窗、54raw SHA，全部technical与negative/reference/background门通过，实际同进程同code PFN/slot交换；k32 blocked/interleaved≈462/433、六process DID≈29，k16两layout≈225。主BLOCKED_ANCHOR_ORDER_DELAY，辅助k16 median尺度阴性；原参考残差有register schedule贡献，不认证RS/PRF/ROB/physical allocation，不命名32-entry scheduler或用offset拟合384。433现在仅属新interleaved实测，旧blocked462/所有旧终态不回填。558/558完整诊断回归通过（471.147s）。下一采用更可解释排程的生命周期/单位正交资格另案，先注册不自动N扫；整体physical目标仍OPEN。

## 2026-10-13 实际地址链descriptor身份连接

`docs/reviews/2026-10-13-tlb-descriptor-graph-results.md`：source73dbc19/buildf7e0d93/actual launch84b8568，branch codex/sm8650-tlb-hierarchy-r2；3/3 fresh进程、192/192capture、20raw SHA独立复核。相同32-data-PFN/stored ordinal/order、同4ISA graph kernel，卸载observer后两shape各512load闭环；实际Linux leaf-table-pages packed/spaced1/32、leaf descriptor64B lines8/32、PMD lines1/4，root virtual line1，全部安装CONT0只属时点。可观测layout激励已从VA代理升级直接descriptor身份；不认证HPA/steady状态或小N容量。下一large-N容量转折与固定VA/data-PFN改变PTE物理关联另冻；三个最终参数仍0/3定案。15新测试/46关联通过，本全量回归结果另记。
