# ROB锚点顺序对照 v1.0（有限协议冻结）

## 本次任务的目的（给人类看）

上一FPSR边界资格的实际k32 independent≈462 cycles，不能套13*k+17写433。先检验两条链按D0全链后D1全链（blocked）与D0/D1交替（interleaved）的排程是否贡献延迟；消除一个reference模型残差，再考虑physical allocation。不是容量扫描，不以384拟合。

候选方案：直接加N扫描不能区分anchor迟启动；改变FP operand会同时改变执行延迟；推荐保持FSQRT1.0/code histogram/retirement reset不变，只改register schedule，配同码阴性和同code PFN/slot交换。任何结果只命名本顺序干预的贡献，不唯一命名RS/PRF/ROB。

## 生成程序与配对

固定FPSR读取+输入reset，D0/D1原结果在reset前捕获并在window末核对1.0/raw FPSR0/GPR checksum0，沿用 `probes/diagnostic/rob_fp_drain.c` 的16ISA prefix与9ISA尾部/5ISA epilogue。四anchor/group条件NONE0/SERIAL0/INDEPENDENT0/NONE64，每个两个layout。NONE/SERIAL两layout逐字相同；INDEPENDENT只改变2k条FSQRT的D0/D1寄存器次序，opcode histogram/branch/prefix/tail相同。

同进程四页RX code，两个layout分别page内0/2048，loop64B对齐，初次安装后不改码。每pair共享一个实际code PFN，四code PFN present/unique/before-after稳定，两个slot assignment跨新进程交换，防地址与layout混淆。pagemap绝对PFN/VA只入private，公开关系与SHA。

chain16/32×slots normal/swapped×3epoch=12新进程。每进程8trial×8condition=64窗口，总768；warm/measure均262144 iterations，只降低本新协议热负载，不替换旧资格。每trial条件按trial轮转，E1反序，8trial让每condition各position恰一次。trial间固定3秒（最后不sleep），进程间15秒，不挑quiet窗口；无sysfs/environment mutation。GROUP+ID USER-only/noMUX，events[17,8,58,33133,35,1]。窗口IR=ITER*(4g+2k*(anchor!=NONE)+9)+21，wrapper容差max(1000,1% expected)；original FP/result/code/CPU/time严格门。观察器必须已卸载。

## 预注册判据

每个condition八窗range/median≤.05、L1I refill/ITER≤.001。每process逐trial的ΔI=Iblocked−Iinterleaved，ΔS=Sblocked−Sinterleaved，DID=ΔI−ΔS。三个阴性条件NONE0/SERIAL0/NONE64各要求paired delta绝对中位≤1 cycle、每trial绝对值≤2；四condition的两layout参考均需I/S max/min≤.70且NONE64 max/min(I)≤.80。全部12process满足才解释main，否则CONTROL_NOT_QUALIFIED，失败窗/条件完整保留。

primary为k32的六process：若六个median(DID)均≥10且48trial DID均>0，BLOCKED_ANCHOR_ORDER_DELAY；反向全部≤−10且48trial<0，INTERLEAVED_ANCHOR_ORDER_DELAY；六个abs median(DID)均≤2则ORDER_CONTRAST_NOT_CHANGED_AT_REGISTERED_MEDIAN_SCALE；其它INCONCLUSIVE。k16同样列原值与分类为辅助，不能用它替代primary，也不用结果调整阈值或定位scheduler容量。slot/epoch每项独立呈现，未冻结任何linear latency模型。median scale不是置信区间或完整absence证书。

首个技术/环境失败即停，不重跑追门；完整但控制不合格保留命名状态。source/build/plan/实际launch分别锚定；真实C producer→独立words/decode→registered driver→writer→immutable-source raw reader，typed/缺失/冲突/乱序/code/PFN/结果/门失败攻击，全部通过才部署。不能由FPSR等待更早指令退休推“禁止未来fetch/rename/allocation”。旧2352原INCONCLUSIVE与g+chain代理=(352,368]不变；physical entries/units/唯一活跃瓶颈OPEN。

## 文件与责任

实现 `probes/diagnostic/rob_anchor_order.c`；消费者 `tools/diagnostic/rob_order_analysis.py`；编排 `tools/diagnostic/run_sm8650_rob_order.py`；测试 `tools/diagnostic/tests/test_rob_order.py` / `test_rob_order_raw.py`；证据 `docs/reviews/evidence/2026-10-13-rob-anchor-order/`。当前branch codex/sm8650-tlb-hierarchy-r2，primary独占设备；owner/后置触发 `docs/open-items.md`。
