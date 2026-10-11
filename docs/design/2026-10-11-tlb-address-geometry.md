# TLB 同映射地址几何对照（采样前冻结 v1）

## 本次任务的目的（给人类看）

`docs/reviews/2026-10-11-tlb-victim-history-results.md` 的 W8→W9 转折跨 victim/history/order 复制，但低 VPN 位与页表描述符地址形状仍耦合。本次保持每条件的十二页池、W8/9 同一 victim rank4、F128、准备次数和窗口程序，配对三个 target 和三种高位跨度，尝试推翻转折仅由一种局部地址几何造成的解释。不是物理 ways 的认证；也不将新结果拼入旧 A1。

方案比较：只扩 W 不能解耦；改页大小同时改覆盖与系统行为；同一 256MiB VA 池内改变高 VPN 步长最小，且多个 target 可约束偶然 bucket。选择第三种。若不同几何有差异，报告其方向，后续针对差异设计控制；没有差异只支持本有限几何的稳健性。

## 地址、激励与有限预算

待实现路径：`probes/diagnostic/tlb_address_geometry.cpp`、`probes/diagnostic/tlb_address_geometry_layout.h`、`tools/diagnostic/tlb_geometry_analysis.py`、`tools/diagnostic/run_sm8650_geometry.py`；证据 `docs/reviews/evidence/2026-10-11-tlb-address-geometry/`。

同一 pool 65536×4K，q0=ceil(pool_base_VPN/256)。每 family i=0..11、q=q0+i*step；C1 的 VPN=(q<<8)|target，C2 的 VPN=(q<<8)|(target XOR (q&255))。target={7,100,200}，step={1,2,16}；分别对应约1/2/16MiB相邻目标跨度，所有 VA 必须落在池内、页对齐、唯一、C 索引恰为 target、另一 C 有十二不同索引。C 是收集模型，不冒称硬件哈希。同一 family 各 W 的最大页集不变。

地址审计保存全部目标 VA、VPN>>9 区域键及 VPN&511 局部键的完整分布；后两者只是可核算的 VA 几何代理，不是物理 PTE/descriptor cache 的测量。跨步还改变高位/缓存残差，不能将结果唯一归因描述符。共享 filler 在两个候选模型下排除全部18个 family占用集合，512候选、只访问闭合前128页，不越界推测。

每mapping target×step×direction{0,1}×C{1,2}×W{1,8,9}=108cells；W1/v0空竞争，W8/v4、W9/v4同victim；history固定正序12页。复用 `probes/diagnostic/tlb_victim_history_layout.h` 的链接和 shot schedule，每trial八遍 F→history，再F→victim训练；八遍 F→snapshot→K竞争load→snapshot，最后 F→snapshot→单victim→snapshot。三槽同cacheline，node偏移64*i。16trial×9窗，15552windows/mapping；五fresh-process mapping，总77760窗。奇数mapping整体逆序，进程间固定15秒；不重采到过门。

## 接受与判据

技术接受：真实 --plan 与实际程序共用 cells；完整config/geometry/108cell/15552shot/order/backing端点、全部六事件[11,05,2d,2f,34,35]、typed uint64/正enabled且no-mux、pool/filler 4K无THP，CPU7/启动MIDR/页长、来源/NDK双构建/driver/build/plan/raw SHA核验。窗口包装背景保留；没有保存kernel event ID的接口不声称已存。缺失/重复/乱序/身份/额外raw/首坏点须拒绝，不补格。环境只观察walt/既有policy，不改频率、温控、THP或全局PMU；端点不能证明窗内恒频。

每非零K/pass，对应同mapping/target/step/C/order/pass的W1空竞争均值相减。0x05与0x2f分别须位于[.75K,1.25K]，任一失败该点 INCOMPUTABLE，不默认为负证据。lookup激励不证明admission。

主要观测固定为最终victim的0x34非零率。单load datawalk>1记single-load-residual、不作容量命名，原值保留；W1如出现datawalk则该matched比较记control-background，不扣计数硬造成功。每mapping/W/target/step/C/order，16trial非零率≥.5才称response；五mapping必须同mapping双order均成立，5/5才称replicated。W8/9只给操作性配对响应，不拟合不存在的物理容量估计量。

结果按全部3target×3step分别报告C1/C2、W8/W9、两个order及五mapping，禁止用总均值掩盖几何差异。不通过科学门保持ambiguous或INCOMPUTABLE。不同target/跨度全部保持旧模式，只能排除“仅target100/约1MiB跨度”的解释，仍不能排除高位hash、descriptor cache竞争、PFN/cache或翻译结构共享。

## 实施与收口

真实host selector先RED→GREEN，算术核全部18族和两方向108cell/15552 schedule及实链轨迹；新C source范围提交。consumer独立期待实际plan/VA/shot，各类负例和真实driver写盘/回读/首坏点停止；提交新source/build/launch才采样。直接JSONL第二算术路径逐77760窗/全部身份/SHA核对；完整原值、图、结论登记，未识别项进入 `docs/open-items.md`。本批与ROB板测串行，当前文档是设计，不算目标数据。

几何代理的架构出处：[Arm Memory management](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/LearnTheArchitecture-MemoryManagement-101811_0100_00_en.pdf)，4K granule 的 level3 索引 VA[20:12]；VPN>>9 对应2MiB范围。这里据此选择对照轴，不从 VA 推物理 descriptor 地址。
