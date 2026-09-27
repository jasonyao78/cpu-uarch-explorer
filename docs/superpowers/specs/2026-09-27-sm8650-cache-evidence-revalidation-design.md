# SM8650 Cache 证据重审与测量协议修复设计

**状态**：已批准方向的详细设计；实现前评审稿

**日期**：2026-09-27

**范围**：先修复证据结论与 `ptr_chase` warmup 语义，再建立 LLCC PMU 用户态验证路径

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

## 2. 备选方案

### 方案 A：先修协议，再接 PMU（采用）

第一批纠正文档、降级旧数据、修复 warmup；第二批验证 `type=9/config=0x1000`
并与 `ptr_chase` 同步采样；第三批再做多链和干扰实验。

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

### 3.4 配置迁移

下列实验从固定 `warmup=200000` 迁移为 `warmup_passes=2`：

- `ptr-chase-cache-sweep.json`
- `ptr-chase-cache-sweep-hp2m.json`
- `ptr-chase-slc-dense.json`
- 其他经仓库搜索发现仍使用固定 warmup 的 ptr-chase ExperimentSpec

`ptr-chase-slc-dense` 的标题和说明改为“共享 CPU L3/外层系统缓存边界”，
不再预设观测到的是 SLC 单级；文件名和 id 暂时保留，避免无关路径 churn。

## 4. 第二批：LLCC PMU 用户态验证

第一批验证通过后，在 Android/Linux arm64 平台目录增加最小只读工具：

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

## 5. 测试与验收

第一批必须按测试驱动实现：

1. Runner 单元测试先证明 4 MiB、12 MiB、32 MiB 在相同
   `warmup_passes=2` 下分别派生出各自的两次完整遍历 load 数。
2. 测试拒绝负数、冲突的新旧参数和整数溢出。
3. CTest 验证探针无 `-w` 时输出两次完整遍历；显式 `-w` 保持原语义；
   `-w 0` 输出 `cold-warm0` 标签。
4. 真实二进制契约测试验证 adapter argv、stdout 和 parser 仍闭环。
5. 全量运行 CTest、Runner unittest、Analysis unittest 和 UBSan 目标。
6. `runner.cli plan` 检查所有迁移后的 ptr-chase 配置，确认 warmup 随
   buffer 成比例增长且来源可审计。

第二批 PMU 验收分两级：

- 开发机/非 SM8650：构建和错误路径测试通过，unsupported 不伪装成功；
- Redmi K70 Pro：`type=9/config=0x1000` 能打开，空闲与受控内存读取阶段的
  计数差异可重复；未满足时保留原始 errno 和环境信息，不得写“零事件”。

## 6. 提交边界

实现按三个独立提交组织：

1. `docs(sm8650): reopen cache hierarchy conclusions`
2. `fix(ptr-chase): derive warmup from full ring passes`
3. `feat(android-arm64): validate Qualcomm LLCC PMU read-miss event`

每个提交只包含本轮文件；现有
`docs/design/ptr-chase-pipeline-analysis.md` 修改和未跟踪 run 不纳入提交。
