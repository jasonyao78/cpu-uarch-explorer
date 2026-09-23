# workloads — 综合 Benchmark 适配层

政策（需求 v0.3 §6/§7）：**本目录只提供 Runner、配置模板与结果解析器，绝不提交 SPEC CPU 源码/输入/二进制与 Geekbench 商业二进制**。授权 workload 通过本地路径或环境变量接入：

```bash
export GB5_BIN=/path/to/geekbench5
export GB6_BIN=/path/to/geekbench6
export SPEC_ROOT=/path/to/spec2017
```

| 优先级 | Workload | 用途 |
|---:|---|---|
| P1 | Geekbench 5/6 | 综合验证（校准铁律中的"验证集"角色，ADR-0005） |
| P1 | SPEC CPU Integer | 模型泛化验证 |
| P2 | CoreMark | 工具链检查 |
| P3 | Dhrystone | 历史参考 |

运行结果统一走 `record.schema.json` 记录（evidence_level=MEASURED）。
