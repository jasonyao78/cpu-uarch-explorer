# SM8650 Cache 证据重审与测量协议修复设计

**状态**：已批准方向的详细设计；实现前评审稿

**日期**：2026-09-27

**范围**：先修复证据结论与测量协议，再校准私有 L2，最后建立 CPU/LLCC PMU 联合验证路径

## 1. 问题与裁定

当前仓库把以下判断写成了定论：SM8650 没有独立 CPU L3、X4 L2 为
1 MiB、12 MiB 延迟边界是 L3/SLC 合并级或 LLCC 有效容量、`llcc-pmu`
没有可用事件。现有证据不支持这些定论：

- SM8650 设备树同时描述共享 CPU L3 和独立 LLCC system-cache controller；
- 上游 CPU cache 属性补丁给出 X4 L2 2 MiB、A720 L2 512 KiB、A520
  双核共享 L2 512 KiB、共享 L3 12 MiB；
- Qualcomm 下游 LLCC PMU 驱动仅接受事件 `config=0x1000`，此前扫描
  `0x00..0x27` 得到 `ENOENT` 不能证明 PMU 不可用；
- dense sweep 固定执行 200,000 次、stride 为 64 B 的预热，覆盖量恰为
  12,800,000 B（约 12.2 MiB）。小工作集在测量前完整遍历，大工作集则
  未完整遍历，因此 12 MiB 附近的拐点不是独立容量证据。

本轮把“名义层级/容量”和“运行时有效容量”拆开：前者可由设备树和内核
属性建立高置信度平台基线，后者必须经修复后的 latency、CPU PMU 和 LLCC
PMU 联合实验重新裁定。

### 1.1 结论等级与禁区

后续报告统一区分三类陈述：

- **平台基线**：有 TRM、设备树或内核属性直接支持的层级、名义容量和共享域；
- **测量事实**：当前数据直接显示的延迟分布、变化区间或计数器变化；
- **机理假设**：对共享份额、路由、DVFS、冲突、带宽竞争等原因的解释。

机理假设必须列出竞争解释和可证伪实验，不能由单一延迟曲线升级为硬件事实。
在重测完成前，以下结论不得定稿：X4 L2 为 1 MiB、X4 约 12 MiB/A520
约 8 MiB 是受保护份额、相机抢占 LLCC、LLCC PMU 不可用，以及 12 MiB
拐点独立证明某级 cache 容量。

`scaling_cur_freq` 只能记录为 cpufreq 报告值或请求 P-state，不能当作实际
硬件时钟。L1 延迟换算后接近整数周期只能提供一致性支持，不能反向证明
频率已锁定。正式结果以 ns 为原始量；cycles 是使用明确频率来源计算的派生
量，并标注来源。只有 PMU/AMU cycle 观测闭环后，才能提高周期数结论的
置信度。

## 2. 备选方案

### 方案 A：先修协议，再接 PMU（采用）

第一批纠正文档、降级旧数据并修复 warmup/页策略；第二批建立可逆的受控
安静态；第三批用 CPU PMU 校准 X4 私有 L2，再验证 `type=9/config=0x1000`
并重测 L3/LLCC；最后才做多链和干扰实验。

优点是每一阶段都产生可验证、可回滚的结论，PMU 数据不会建立在已知有
混杂的 workload 上。缺点是不能一次提交完成所有 SM8650 逆向工作。

### 方案 B：warmup、PMU、干扰编排一次完成

优点是最终实验接口一次成形；缺点是同时修改 Probe ABI、Runner、平台工具
和实验语义，失败时难以分辨是计数器、调度还是 workload 本身的问题。

### 方案 C：不改协议，只手工调整每个工作集的 `-w`

改动最小，但预热次数仍由操作者计算，ExperimentSpec 不能表达“完整遍历
N 次”，重复实验容易再次引入同类错误，因此不采用。

## 3. 第一批：证据纠偏与 warmup 协议

### 3.1 历史证据处理

- 不修改、删除或重写既有 run record 和 raw artifact。
- 建立一份 SM8650 cache 证据重审报告，列出受影响 run、原始观察、混杂因素
  和允许继续使用的范围。
- 受固定 200,000-load warmup 影响的 run 降级为“原始观察/方法学反例”，
  禁止作为容量 baseline 或 calibration 输入。
- 在 CHANGELOG 追加纠偏记录，不改写历史条目；当前平台配置中的事实性描述
  则更新为最新裁定，避免 Runner 继续传播错误能力声明。
- 工作树中现有未提交文档和两组未跟踪 run 属于既有工作，本轮不代为修改、
  移动或提交。

### 3.2 平台基线

平台描述采用以下分层，并对来源和置信度分别标注：

1. L1I/L1D：各核 64 KiB，line size 64 B；
2. A520 双核共享 L2 512 KiB；A720 每核 L2 512 KiB；X4 L2 2 MiB；
3. 八核共享 CPU L3 12 MiB；
4. 独立 Qualcomm LLCC/system cache；物理约 6 MiB 是驱动配置推导，不能
   标成仓库实测；
5. CPUSS slice 的 `max_cap=5120 KiB`、reserved/bonus ways 是配置事实，
   不能直接等同于 CPU 可独占或有效容量。

X4 L2 的当前运行数据只支持“512 KiB 到 1 MiB 之间出现延迟变化”，不支持
“容量为 1 MiB”。在继续解释 L3/LLCC 之前必须先做 X4 L2 校准：覆盖
512 KiB 到 3 MiB，步长 128 KiB 或 256 KiB，比较 4 KiB 基页与实际 THP
backing，每点至少 10 个独立进程/新分配，并联合 L2 refill 与 DTLB walk
计数。若已知 2 MiB 私有 L2 仍不能被 latency + PMU 识别，则停止外层 cache
容量解释，先修复探针或实验模型。

随机置换只保证逻辑访问顺序随机，不保证物理地址在 cache set/bank 上均匀。
Cortex-X4 L2 为 PIPT，4 KiB 页下 PFN/color、组冲突与 bank 映射仍可能影响
曲线。校准数据应跨多次新分配，并在权限允许时记录 `/proc/pagemap` 导出的
PFN/color 摘要；无法读取时明确记为未控制混杂，而不是宣称已消除。

### 3.3 warmup 语义

ExperimentSpec 新增 `warmup_passes`，含义是随机单环链的完整遍历次数。
正式 warm 实验默认值为 2，且必须大于等于 1。

Runner 在 plan 阶段计算：

```text
slots = floor(buffer_bytes / stride_bytes)
warmup_loads = warmup_passes * slots
```

`warmup_loads` 作为派生参数记录，并继续通过现有 `-w` Probe ABI 传给
`ptr_chase`。这样不破坏旧二进制接口，同时保证每个 buffer 的预热覆盖率
一致。plan 必须拒绝负数、乘法溢出以及同时声明新旧两种 warmup 语义的配置。

兼容策略：

- 新实验只声明 `warmup_passes`；
- 旧 ExperimentSpec 的 `warmup` 仍按“精确 load 次数”读取，以便重放历史
  实验，但 plan 输出明确标为 legacy；
- `ptr_chase -w N` 保持精确 load 次数的含义；
- 直接运行探针且未传 `-w` 时，默认改为完整遍历 2 次，而不是固定
  200,000 次；
- `-w 0` 保留为显式 `cold-warm0`，不得标成真正 cold。

探针 stdout 增加 `warmup_loads` 和 `warmup_passes_effective`。后者按
`warmup_loads / slots` 输出，便于审计非整数遍历的 legacy run；现有 parser
继续接受附加字段。

### 3.4 页策略与实际 backing

当前设备内核没有 `CONFIG_HUGETLBFS`，因此 `MAP_HUGETLB` 不可能成功；但
`CONFIG_TRANSPARENT_HUGEPAGE=y`、`CONFIG_TRANSPARENT_HUGEPAGE_MADVISE=y`
且系统存在 `AnonHugePages`，所以不能把“无 hugetlb pool”写成“无 hugepage”。

探针新增显式 THP/madvise 页策略。请求 THP 后必须解析本进程
`/proc/self/smaps`，记录目标 VMA 的 `AnonHugePages` 和实际 backing 状态
（base/THP/mixed）；请求策略与实际 backing 分字段保存。仅调用
`madvise(MADV_HUGEPAGE)` 而未获得 THP 的 run 不得标成 2 MiB hugepage run。
原有 `MAP_HUGETLB` fallback/strict 语义保留，用于兼容和错误路径验证。

### 3.5 配置迁移

下列实验从固定 `warmup=200000` 迁移为 `warmup_passes=2`：

- `ptr-chase-cache-sweep.json`
- `ptr-chase-cache-sweep-hp2m.json`
- `ptr-chase-slc-dense.json`
- 其他经仓库搜索发现仍使用固定 warmup 的 ptr-chase ExperimentSpec

`ptr-chase-slc-dense` 的标题和说明改为“共享 CPU L3/外层系统缓存边界”，
不再预设观测到的是 SLC 单级；文件名和 id 暂时保留，避免无关路径 churn。

## 4. 第二批：受控安静态 v2

该协议命名为“受控安静态”，不称“纯净态”：飞行模式、Doze、停服务和
锁频都会改变被测系统，不能暗示等同于正常运行态。Runner 现有环境事务
机制继续作为实现基础，所有变更遵守 inspect → apply → verify → reverse
restore → reconcile，并写入 journal。

默认吸收以下控制：

- 每个 cpufreq policy 记录并恢复 governor、min、max；块前后分别记录
  `scaling_cur_freq`，但只把它视为 cpufreq 报告值；
- 屏幕状态采用幂等的显式目标和验证，禁止盲发 `KEYCODE_POWER`；
- 相机实验在测量前后解析 `Active Camera Clients` 块，不能用全量 dump 中
  `Camera ID` 的出现次数代替 active client；
- 条件切换后丢弃首跑；跨条件比较采用相邻配对或随机交错，并保存每块的
  频率、温度、负载、相机和服务快照；
- 飞行模式可作为显式实验条件，但保存并恢复原始状态，不默认强制启用。

以下动作只能作为独立实验条件，不能混入默认 baseline：

- `dumpsys deviceidle force-idle`，因为实机 `Dozing` 与 `mForceIdle=false`
  可以同时存在，二者语义不同；
- 停止 `mi_thermald`，仅限短时实验，并设置温度中止线；服务自行重启或恢复
  失败时整块无效；
- 停止 `perf2-hal-1-0`，必须先做独立 A/B，证明收益和副作用后再决定是否
  纳入某个 profile。

默认拒绝 `drop_caches`、`am kill-all`、硬编码停止 GMS/微信/输入法、硬编码
恢复为 `walt`/飞行模式关闭/服务运行，以及不保存原值的 min/max 修改。
匿名 `ptr_chase` 不从文件页缓存获益，`drop_caches` 还会制造全局扰动。

当前设备只确认 `mi_thermald` 和 `perf2-hal-1-0` 为有效且运行中的服务；
`vendor.miperf`、`vendor.perfs`、`vendorfservice`、`thermal-hal` 不能未经检测
写入通用脚本。已有“纯净态协议”命令还含缺失重定向、错误 `su` 参数、错误
property 名、无循环变量及停止/恢复服务名不对称等问题，只能作为需求素材，
不得原样执行。

## 5. 第三批：PMU 与重测顺序

前两批验证通过后，在 Android/Linux arm64 平台目录增加最小只读工具：

- 从 sysfs 读取或由参数接收 PMU type，SM8650 当前实测值为 9；
- 通过 `perf_event_open` 请求 `config=0x1000`；
- 明确区分 open 失败、权限不足、事件不支持和计数成功；
- 只进行 counter reset/enable/disable/read，不映射或写入 LLCC MMIO；
- 第一阶段只证明事件可打开且内存读负载期间计数有响应，不立即接入正式
  run-record。

smoke test 通过后再把计数器包装为 Runner 的测量伴随通道，使同一次
`ptr_chase` case 同时记录 latency 与 LLCC read miss。CPU PMU 中的 L2/L3
refill、LL-cache read/miss 和 DTLB walk 也在该阶段接入，以免把 page walk
或 DRAM 慢路径误判为 LLCC 容量变化。

LKM/MMIO 仍是有条件的第三选择：只有用户态 PMU 和 core PMU 无法回答
geometry 问题时，才单独评审只读模块；量产机禁止写 LLCC 控制寄存器。

新一轮实机实验严格按以下门禁推进：

1. X4 L2 校准；
2. X4 共享 L3 8–16 MiB dense sweep；
3. LLCC PMU 与 core PMU 联合观测；
4. A520/A720/X4 跨核型复核；
5. 相机或其他 master 的配对干扰实验；
6. 多链/MLP 实验。

A520 32 MiB 在既有 dense run 中出现约 255/302/147 ns 的大幅波动，只能
记录为不稳定现象。当前 `ptr_chase` 为 MLP=1，把该差异主要归因于
outstanding-miss 能力也缺乏证据。相机“+51%”在仓库中没有可追溯、获接纳
的 run，且 OI-11 已否决一次性亮屏/相机差分；重做时必须使用 A/B/A/B 或
随机交错，切换后弃首跑，在双峰区每条件至少 20 次，并在前后确认 active
camera client。结果先写“稀释区延迟变化”，SLC 份额或 DRAM 带宽竞争均保留
为候选机理。

## 6. 测试与验收

第一批必须按测试驱动实现：

1. Runner 单元测试先证明 4 MiB、12 MiB、32 MiB 在相同
   `warmup_passes=2` 下分别派生出各自的两次完整遍历 load 数。
2. 测试拒绝负数、冲突的新旧参数和整数溢出。
3. CTest 验证探针无 `-w` 时输出两次完整遍历；显式 `-w` 保持原语义；
   `-w 0` 输出 `cold-warm0` 标签。
4. 真实二进制契约测试验证 adapter argv、stdout 和 parser 仍闭环。
5. Linux/Android 测试验证 THP 请求、实际 backing 识别和 smaps 解析；
   非 Linux 平台明确返回 unsupported 或 base backing，不伪装成功。
6. 全量运行 CTest、Runner unittest、Analysis unittest 和 UBSan 目标。
7. `runner.cli plan` 检查所有迁移后的 ptr-chase 配置，确认 warmup 随
   buffer 成比例增长且来源可审计。

第三批 PMU 验收分两级：

- 开发机/非 SM8650：构建和错误路径测试通过，unsupported 不伪装成功；
- Redmi K70 Pro：`type=9/config=0x1000` 能打开，空闲与受控内存读取阶段的
  计数差异可重复；未满足时保留原始 errno 和环境信息，不得写“零事件”。

## 7. 提交边界

实现按可独立验证的提交组织：

1. `docs(sm8650): reopen cache hierarchy conclusions`
2. `fix(ptr-chase): derive warmup from full ring passes`
3. `feat(ptr-chase): report requested and actual THP backing`
4. `feat(runner): add transactional Android quiet-state controls`
5. `feat(android-arm64): validate Qualcomm LLCC PMU read-miss event`

提交 1–3 构成首份实现计划；受控安静态和 PMU/实机校准分别写后续计划，
避免在一个变更中同时修改 Probe ABI、Android 状态控制和结论模型。第一份
计划完成前不采集新的 SM8650 容量数据。

每个提交只包含本轮文件；现有
`docs/design/ptr-chase-pipeline-analysis.md` 修改和未跟踪 run 不纳入提交。

## 8. 主要依据

- [Arm Cortex-X4 Technical Reference Manual](https://documentation-service.arm.com/static/6473ef18bae17b773b05d1e8)；
- [Linux SM8650 CPU cache properties patch](https://patchew.org/linux/20260615-topic-sm8650-upstream-cpu-props-v3-0-eeb6e9fa7581@linaro.org/20260615-topic-sm8650-upstream-cpu-props-v3-2-eeb6e9fa7581@linaro.org/)
  与 [SM8650 device tree](https://android.googlesource.com/kernel/common/+/cf1ca1f66d301a55ab8e79188ddf347a8d011e35/arch/arm64/boot/dts/qcom/sm8650.dtsi)；
- [Linux CPUFreq](https://cdn.kernel.org/doc/html/latest/admin-guide/pm/cpufreq.html)、
  [`drop_caches`](https://www.kernel.org/doc/html/v6.12/admin-guide/sysctl/vm.html) 文档；
- [AOSP DeviceIdleController](https://android.googlesource.com/platform/frameworks/base/+/add9526/services/core/java/com/android/server/DeviceIdleController.java)
  与 [`svc power` 实现](https://android.googlesource.com/platform/frameworks/base/+/406a41b/cmds/svc/src/com/android/commands/svc/PowerCommand.java)；
- [Qualcomm downstream LLCC PMU driver](https://android.googlesource.com/kernel/msm.git/+/90651f2c1e5de4d9359d216a41f94e6a24847404/drivers/perf/qcom_llcc_pmu.c)
  与 [SM8650 LLCC configuration](https://android.googlesource.com/kernel/common/+/14d0e1a09fe97a7524ff36baa695900cb0c10c23/drivers/soc/qcom/llcc-qcom.c)。
