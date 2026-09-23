# data/public/legacy — 历史探测数据（来自 cpu-cache-demo-code 的副本）

> 来源：`cpu-cache-demo-code/`（历史 demo，lmbench 衍生，见 ADR-0002）。原件保留在本地未入库目录，此处为入库副本，**仅作历史参考，不进任何校准决策**。

| 文件 | 内容 | 已知信息 | 证据等级 | 备注 |
|---|---|---|---|---|
| `sm8650-x4.txt` | SM8650（骁龙 8 Gen 3）X4 核内存延迟曲线，`taskset 80`（CPU7） | 无日期、无 kernel/编译器信息 | MEASURED（待复核） | 与 `probes/cache-mem/ptr_chase` 的可比性需确认（测量方法不同：该数据为 demo 旧探针所测） |
| `sm8650-a510.txt` | SM8650 A510 核数据 | 同上 | MEASURED（待复核） | 同上 |
| `sm8550-cacheline.txt` | SM8550（骁龙 8 Gen 2）cacheline 探测（64B 拐点） | **来源设备已不可考**（OI-4） | UNKNOWN | 禁止用于校准或对比结论 |

统一数据模型（`runner/schema/record.schema.json`）生效后的所有新数据均带完整元数据信封；本目录数据的缺陷正是 ADR-0003 立项的原因。
