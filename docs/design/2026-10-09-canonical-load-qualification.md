# ROB 有效地址位编码与同码形长load资格（冻结v1）

## 本次任务的目的（给人类看）

前一高位编码批次 `docs/reviews/2026-10-09-encoded-load-results.md` 已完成12进程72窗，技术通过而两mask均无长load资格，128MiB LL代理仍约1.64–1.71/iter。高位XOR不提供“预取已关闭”的证据：不能排除相关硬件忽略高位。现在预注册bit20的低位XOR；该位改变1MiB地址位置，不改变THP页编号，提供比高位更强的指针值对照。仍只问地址值域是否影响远层信号及原资格，**不假定有DMP、不假定bit20能关闭全部预取**。根Agent独占手机，有限新批次，不追门重试，不增加足迹。

## 机制、控制与解释边界

生产实现 `docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c` 显式加入 `--pointer-xor uint64`，仅miss允许。节点存next XOR mask，head仍为真实VA；每个LDR后立即EOR解码再解引用，mask在caller-saved x12，filler不覆盖。独立P为LDR/EOR x0和LDR/EOR x1；串行S的两组都为x0。**显式mask0仍执行相同两条EOR**；未提供flag的旧JIT/config/graph保持不变。

long映射由实际生产helper 2MiB对齐且bytes为2MiB整倍数；节点raw VA XOR bit20仍在同一2MiB块内，满足一一映射且不是原地址。这个结论来自地址算术，不是实测物理cache粒度。config/源码与JIT核验mask；不导出私有VA。hot1MiB 4K映射中，bit20翻转使每个raw值与真实节点相差±1MiB，因此raw值均在自身这段半开1MiB映射外（可能落在其他VMA，不能称unmapped）；**软件总先解码才解引用**，而硬件是否对raw值预取及其可能增加的walk/LL须由hot负控披露，原科学门不能豁免。

本对照不是“已关闭预取”。正值差异可能包含预取、值域依赖优化与解码执行残差；mask0与非零mask存在数据值差异，不能排除zero elision。每进程内P/S同一VA映射、same seed全环拓扑；不同编码进程只保证相同节点索引顺序，**不保证VA/PFN相同**。跨encoding平均差异不单独证明编码因果，两个逆序epoch用于暴露布局/历史残差。旧无EOR批次只作历史背景，不拼入本资格。

## 唯一矩阵与数据流

`tools/diagnostic/run_sm8650_minimal.py` 的新mode=`rob-xor-canonical-qualify`。epoch0顺序为 footprint {1,64,128}MiB 内各 mask {0x0000000000000000,0x0000000000100000}；epoch1完整逆序。条件名 `e{epoch}-xor{16位小写hex无0x}-miss-m{MiB}-n0`。共12进程、每进程paired三轮P/S，即72窗，不追加样本。1MiB实际4K、64/128实际THP2MiB；i=max(131072,MiB×8192)、N0/NOP/seed42/align0、CPU7/type8、事件0x11/08/03/17/34/37。每进程15秒固定冷却后原环境检查，原backing pre/post、无mux、退休量、SHA与精确覆盖硬门不变，技术失败停整块。

config只有显式flag时新增 `pointer_xor_requested=true`、canonical `pointer_xor` 和 `decode_instructions_per_iteration=2`；N0 loop6条、loop offset64、code92B。原 config version2 仍兼容旧读者。requested→actual config→ `tools/diagnostic/summarize_sm8650_minimal.py` rows→ `tools/diagnostic/analyze_encoded_load.py` 必须保留这三字段及loop_instructions，禁止由条件名猜身份或跨mask池化。mask0和非零mask各恰好6进程/12member/36窗；先验完整12进程矩阵再分别评分。

## 科学门与推翻路径

完全沿用 `docs/design/2026-10-09-long-load-qualification.md`（c93e788）原门：每长点P/S/round 0x03/17/37 ∈[1.8,2.2]/iter；0x34≤.02；每member cycle极差/中位≤.10；每配对S/P∈[1.6,2.4]；P/S的L2与LL均值差/平均≤.10；P中位≥max(同epoch同mask热P中位×4,171)；热点LL各≤.1。**同mask同footprint两epoch独立通过**才允许该条件有限N扫描；任一编码不通过不得借另一编码补齐。整体无资格不扫描。资格即使通过也只命名远层miss主导、低翻译干扰的操作性双长load候选，不认证DRAM或物理ROB。

分析器先核源/启动/build/protocol/raw SHA、actual backing、全环与生产92B生成码；动态IR分母6i+17，保留实测wrapper残差。原资格数学可复用，但必须在新身份与raw审核之后、各mask独立规范化；不允许旧数据重贴标签。输出每mask资格、各footprint/epoch的全部原值、负对照与mask差值；技术停块标不可计算，不造零metrics。若对照无效或不合格，物理ROB继续OPEN，后续转锚点/分配资源的其他可证伪设计，不能放宽已观测门来救扫描。

## 执行与交付

先真实producer红/绿测试（码形、图拓扑、身份及负例）、独立审查、全量回归，再源码提交→独立NDK两次构建→build/protocol/plan SHA提交→根Agent串行采样→审核/报告。分支 `codex/sm8650-tlb-hierarchy-r2`；证据 `docs/reviews/evidence/2026-10-09-canonical-load/`，raw仅 `data/private/`，不入库VA/PFN/序列号。二进制沿用source `1ef4baa` / SHA `cb4645f65d8352e839144541bcaefab32cad5a7ce2006d9fb219479c8384d5ba`，只新增固定driver/consumer profile；build/plan须新登记，源码commit、launch commit、binary/source/driver/protocol/raw SHA分别登记。后置问题登记 `docs/open-items.md`，失败证据不删不拼。
