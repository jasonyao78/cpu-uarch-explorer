# SPDX-License-Identifier: Apache-2.0
"""Markdown 报告生成：cache/内存层次延迟 sweep。

结构与口径（measurement-discipline §7 报告模板）：
- 元信息块：目标 / 探针谱系 / 测量日期 / 证据等级 / 温度口径 / 页策略；
- 数据表：每 buffer 档 × 每控制组的 median（含 repetitions 与分位距）；
- 台阶分析：相邻档位延迟跳变 >1.5× 标记为层级边界——**推断**而非断言，
  依据与不确定度写明；
- 置信度评级（§4）：说明噪声来源与提升计划；
- 失败记录单列，不混入图表。
"""

from __future__ import annotations

from .load import RunData


def _series_by_control(run: RunData) -> dict[str, list[tuple[float, float, dict]]]:
    """ok 记录按 control 分组为 (buffer_kb, median, record) 序列。"""
    series: dict[str, list[tuple[float, float, dict]]] = {}
    for r in run.ok_records:
        control = r["environment"].get("control", {})
        label = f"{control.get('mechanism', '?')}={control.get('value', '?')}"
        buffer_kb = r["params"].get("buffer_kb")
        metric = r["metrics"][0]
        if buffer_kb is None or metric["name"] != "latency_ns":
            continue
        series.setdefault(label, []).append(
            (float(buffer_kb), float(metric["statistics"]["median"]), r))
    for label in series:
        series[label].sort()
    return series


def _detect_steps(points: list[tuple[float, float, dict]]) -> list[str]:
    """相邻档位 median 比值 > 1.5× 视为层级台阶（推断阈值，报告注明）。"""
    steps = []
    for (kb0, v0, _), (kb1, v1, _) in zip(points, points[1:]):
        if v0 > 0 and v1 / v0 > 1.5:
            steps.append(f"{int(kb0)}KB→{int(kb1)}KB：{v0:.2f}→{v1:.2f} ns（×{v1/v0:.1f}）")
    return steps


# 控制口径说明按 mechanism 分派——报告层不允许平台特判扩散，但"控制手段
# 意味着什么"是测量语义的一部分（2026-09-25 Xeon 接入：硬编码 macOS QoS
# 文案污染了 xeon 报告，此处改为 mechanism 查表 + 未知机制如实直述）。
_CONTROL_EXPLAIN = {
    "qos": "macOS QoS 分流（OI-5 实测双峰；default≈P-core 档，background=E-core）",
    "taskset": "Linux taskset 绑核到指定物理核（SMT sibling 空闲纪律见平台配置 notes）",
    "none": "无调度控制",
}

_CONFIDENCE_NOTES = {
    "qos": [
        "- **噪声来源**：无锁频（DVFS 漂移，QoS 比值 2.6~3.9× 区间漂移即其表现）；QoS 分流是调度 hint 而非严格绑核，同 QoS 内可能迁移；页策略为 4K 默认页。",
        "- **提升计划（MEDIUM→HIGH）**：测量期 powermetrics 并发采样核频入档；hugepage 对照组；重复次数提升至 7+ 并监控热漂移。",
    ],
    "taskset": [
        "- **噪声来源**：无锁频——实测 powersave governor、800MHz~3.8GHz 浮动（2026-09-25 接入时采集），ns 绝对值受 DVFS 污染，跨档比较需谨慎；4K 默认页（TLB 遍历与 LLC 行为耦合）；单控制组，sibling 隔离未主动执行（口径见平台配置 notes）。",
        "- **提升计划（MEDIUM→HIGH）**：锁频复测（governor=performance 或固定 scaling_setspeed，需 root）；hugepage 对照组；cycles 口径（perf 需 sudo，paranoid=4）；evict 工具对照 warm/cold。",
    ],
}


def _mechanism_of(run: RunData) -> str:
    first = run.ok_records[0] if run.ok_records else {}
    return first.get("environment", {}).get("control", {}).get("mechanism", "?")


def build_report(run: RunData, svg_name: str) -> str:
    """生成完整 Markdown 报告文本。"""
    series = _series_by_control(run)
    manifest = run.manifest
    first = run.ok_records[0] if run.ok_records else {}
    target = first.get("target", {})
    probe = first.get("probe", {})
    evidence = first.get("evidence", {})
    n_rep = first.get("metrics", [{}])[0].get("repetitions", "?")

    lines = [
        f"# Cache/内存层次延迟报告 — {manifest.get('experiment_id', '?')}",
        "",
        "## 元信息（measurement-discipline §7 强制项）",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 目标 | {target.get('target_id', '?')}（{target.get('cpu_profile', '?')}，{target.get('os', '?')}/{target.get('isa', '?')}） |",
        f"| 探针 | {probe.get('name', '?')} protocol={probe.get('protocol_version', '?')} impl={probe.get('implementation_id', '?')} |",
        f"| 探针谱系 | git `{probe.get('git', {}).get('commit', '?')[:10]}` dirty={probe.get('git', {}).get('dirty', '?')} sha256={probe.get('artifact', {}).get('sha256', '?')[:16]}… |",
        f"| 测量日期 | {first.get('timestamp', '?')} |",
        f"| 温度口径 | warm（显式预热 + 多趟 median，§1 主口径） |",
        f"| 页策略 | 默认 4K 页（未启用 hugepage；TLB 效应与 cache 效应在小步长区间耦合，见 probes/cache-mem/README 已知局限） |",
        f"| 重复次数 | 每 case {n_rep} 次，统计量 median（min/p25/p75/max 见 records.jsonl） |",
        f"| 证据等级 | {evidence.get('provenance', '?')} |",
        f"| 控制口径 | 按 environment.control 分组（{_CONTROL_EXPLAIN.get(_mechanism_of(run), '机制见 records.jsonl 各记录')}） |",
        "",
        "## 延迟曲线",
        "",
        f"![latency curve]({svg_name})",
        "",
        "## 数据表（median，ns）",
        "",
    ]

    labels = sorted(series)
    all_kb = sorted({kb for pts in series.values() for kb, _, _ in pts})
    header = "| buffer |" + "".join(f" {label} |" for label in labels)
    lines.append(header)
    lines.append("|---|" + "---|" * len(labels))
    lookup = {label: {kb: v for kb, v, _ in pts} for label, pts in series.items()}
    for kb in all_kb:
        kb_str = f"{int(kb/1024)}MiB" if kb >= 1024 else f"{int(kb)}KiB"
        row = f"| {kb_str} |"
        for label in labels:
            v = lookup[label].get(kb)
            row += f" {v:.3f} |" if v is not None else " — |"
        lines.append(row)

    # P/E 比值列（恰好两组时）
    if len(labels) == 2:
        lines += ["", f"### 双峰比值（{labels[1]} / {labels[0]}，随频率漂移，不作常量引用）", ""]
        a, b = labels[0], labels[1]
        for kb in all_kb:
            va, vb = lookup[a].get(kb), lookup[b].get(kb)
            if va and vb:
                lines.append(f"- {int(kb)}KB：×{vb/va:.2f}")

    lines += ["", "## 层级台阶（推断，阈值：相邻档位比值 >1.5×）", ""]
    for label in labels:
        steps = _detect_steps(series[label])
        lines.append(f"**{label}**")
        lines += [f"- {s}" for s in steps] or ["- 未检测到明显台阶"]
        lines.append("")

    lines += ["## 置信度：MEDIUM", ""]
    lines += _CONFIDENCE_NOTES.get(_mechanism_of(run), [
        "- **噪声来源**：见 records.jsonl 各记录的 environment 与 failure 段；未识别的控制机制不做臆断。",
        "- **提升计划（MEDIUM→HIGH）**：补 capability 快照后再定。",
    ])
    lines.append("")

    if run.failed_records:
        lines += ["## 失败记录（不进入图表与结论）", ""]
        for r in run.failed_records:
            f = r.get("failure", {})
            lines.append(f"- `{r.get('probe', {}).get('name')}` status={r['status']} "
                         f"reason={f.get('reason', '?')} params={r.get('params')}")
        lines.append("")

    lines += ["---",
              f"数据来源：{run.run_dir}/records.jsonl（raw 样本引用见各记录 raw_samples_ref）",
              ""]
    return "\n".join(lines)
