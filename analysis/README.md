# analysis —— 报告生成与校准对比

当前实现（2026-09-25）：消费 run 目录的 `records.jsonl`，生成 Markdown 报告 + SVG 延迟曲线（纯 stdlib，零依赖）。

```bash
.venv/bin/python -m analysis.cli report --run data/public/runs/<run目录>
# 产出写回 run 目录：report.md（元信息/数据表/台阶推断/置信度）+ latency.svg
```

- 报告口径遵守 `docs/methodology/measurement-discipline.md` §7（温度/页策略/统计量/置信度/核型/证据等级/日期逐项入档）；
- 台阶检测阈值：相邻档位 median 比值 >1.5×，标注为推断而非断言；
- failed 记录隔离展示，不进图表；
- 测试：`analysis/tests/`（合成 fixture，不依赖真机数据）。

待做：跨 run 汇总对比、校准差异单（MEASURED vs SIMULATED）。
