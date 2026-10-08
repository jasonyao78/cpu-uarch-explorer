# analysis —— 报告生成与校准对比

当前实现（2026-09-25）：消费 run 目录的 `records.jsonl`，生成 Markdown 报告 + SVG 延迟曲线（纯 stdlib，零依赖）。

```bash
.venv/bin/python -m analysis.cli report --run data/public/runs/<run目录>
# 产出写回 run 目录：report.md（元信息/数据表/台阶推断/置信度）+ latency.svg
```

- 报告口径遵守 `docs/methodology/measurement-discipline.md` §7（温度/页策略/统计量/置信度/核型/证据等级/日期逐项入档）；
- 台阶检测阈值：相邻档位 median 比值 >1.5×，标注为推断而非断言；
- failed 记录隔离展示，不进图表；
- 测试：`analysis/tests/`（合成 fixture 为主；`test_sm8650_tlb` 的参照池互钉与 `test_tlb_figures` 的数据集形状钉读仓内 `data/public/runs`，数据修正走 revision history 时随数据集更新）。

## 战役图表生成器（tlb_figures）

```bash
.venv/bin/python -m analysis.tlb_figures --runs-root data/public/runs --out <目录>
# 产出：refill-density.svg / walk-onset.svg / latency-cycles.svg / thp-cohort.svg + report.md
```

SM8650 X4 TLB 战役（终审 `docs/reviews/2026-09-28-sm8650-tlb-hierarchy.md`）的同事版四图 + 读法报告；run 名单与 (buffer × seed) 网格钉死在 `analysis/tlb_figures.py` 模块常量，chart.py 的 shaded/vlines 泛化参数由此引入。

待做：跨 run 汇总对比、校准差异单（MEASURED vs SIMULATED）。

### SM8650 r2 A1 两阶段入口

`analysis/sm8650_tlb_a1_cli.py` 提供 freeze/adjudicate；正式三层配置与
专用 floor/scatter 标定在 `configs/experiments/ptr-chase-sm8650-x4-tlb-a1-*.json`。
完整条件/统计/几何合同在 `analysis/sm8650_tlb_a1_contract.py`，冻结工件与
谱系核验在 `analysis/sm8650_tlb_a1_freeze.py`；规则见
`docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md` §5.5，交接见
`docs/runbooks/2026-10-08-sm8650-a1-integrated-handoff.md`。
