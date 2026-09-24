# SPDX-License-Identifier: Apache-2.0
"""纯 stdlib SVG 延迟曲线图（log2 X = buffer 大小，log2 Y = 延迟 ns）。

不引入 matplotlib 的理由：报告层与 runner 一样保持零运行时依赖
（ADR-0003 精神），SVG 手写生成完全可控且 git diff 可读。
"""

from __future__ import annotations

import math
import xml.sax.saxutils

W, H = 860, 500
MARGIN = dict(left=80, right=30, top=40, bottom=70)
_COLORS = ["#2563eb", "#dc2626", "#059669", "#7c3aed", "#ea580c"]


def _nice_ticks(lo: float, hi: float) -> list[float]:
    """log2 域内的 2 的幂刻度，覆盖 [lo, hi]。"""
    return [2.0 ** e for e in range(math.floor(math.log2(lo)), math.ceil(math.log2(hi)) + 1)]


def _fmt_size(kb: float) -> str:
    if kb >= 1024:
        return f"{int(kb / 1024)}M"
    return f"{int(kb)}K"


def _fmt_ns(v: float) -> str:
    return f"{v:g}"


def latency_svg(series: dict[str, list[tuple[float, float]]], title: str) -> str:
    """series: {系列名: [(buffer_kb, latency_ns), ...]} → SVG 字符串。

    系列名转义防 XML 注入；空系列抛 ValueError（没数据不出图）。
    """
    points = [(x, y) for pts in series.values() for (x, y) in pts]
    if not points:
        raise ValueError("no data points to plot")
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_lo, x_hi = min(xs), max(xs)
    y_lo, y_hi = min(ys), max(ys)
    # log2 域映射；y 轴上下各留半档余量
    lx0, lx1 = math.log2(x_lo), math.log2(x_hi)
    ly0, ly1 = math.log2(y_lo) - 0.5, math.log2(y_hi) + 0.5

    def X(kb: float) -> float:
        return MARGIN["left"] + (math.log2(kb) - lx0) / (lx1 - lx0 or 1) * (W - MARGIN["left"] - MARGIN["right"])

    def Y(ns: float) -> float:
        return MARGIN["top"] + (ly1 - math.log2(ns)) / (ly1 - ly0) * (H - MARGIN["top"] - MARGIN["bottom"])

    e = xml.sax.saxutils.escape
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'font-family="Menlo, monospace" font-size="12">',
             f'<rect width="{W}" height="{H}" fill="#fafafa"/>',
             f'<text x="{W/2}" y="22" text-anchor="middle" font-size="14" font-weight="bold">{e(title)}</text>']

    # 网格与坐标轴刻度
    for kb in sorted(set(xs)):
        x = X(kb)
        parts.append(f'<line x1="{x:.1f}" y1="{MARGIN["top"]}" x2="{x:.1f}" y2="{H-MARGIN["bottom"]}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{x:.1f}" y="{H-MARGIN["bottom"]+16}" text-anchor="middle">{_fmt_size(kb)}</text>')
    for ns in _nice_ticks(y_lo, y_hi):
        y = Y(ns)
        parts.append(f'<line x1="{MARGIN["left"]}" y1="{y:.1f}" x2="{W-MARGIN["right"]}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{MARGIN["left"]-8}" y="{y+4:.1f}" text-anchor="end">{_fmt_ns(ns)}</text>')
    parts.append(f'<text x="{W/2}" y="{H-8}" text-anchor="middle">buffer size（log2，每格一倍）</text>')
    parts.append(f'<text x="16" y="{H/2}" text-anchor="middle" transform="rotate(-90 16 {H/2})">latency_ns（log2）</text>')

    # 数据线 + 数据点 + 图例
    for i, (name, pts) in enumerate(sorted(series.items())):
        color = _COLORS[i % len(_COLORS)]
        coords = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in sorted(pts))
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"/>')
        for x, y in sorted(pts):
            parts.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="3" fill="{color}"/>')
        parts.append(f'<rect x="{W-MARGIN["right"]-150}" y="{46+i*20}" width="12" height="12" fill="{color}"/>')
        parts.append(f'<text x="{W-MARGIN["right"]-132}" y="{57+i*20}">{e(name)}</text>')

    parts.append("</svg>")
    return "\n".join(parts)
