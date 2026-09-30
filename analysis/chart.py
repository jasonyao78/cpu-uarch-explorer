# SPDX-License-Identifier: Apache-2.0
"""纯 stdlib SVG 延迟曲线图（log2 X = buffer 大小，log2 Y = 延迟 ns）。

不引入 matplotlib 的理由：报告层与 runner 一样保持零运行时依赖
（ADR-0003 精神），SVG 手写生成完全可控且 git diff 可读。
"""

from __future__ import annotations

import math
import unicodedata
import xml.sax.saxutils

W, H = 860, 500
MARGIN = dict(left=80, right=30, top=40, bottom=70)
_COLORS = ["#2563eb", "#dc2626", "#059669", "#7c3aed", "#ea580c"]
_ANNOTATION_FONT_SIZE = 10


def _nice_ticks(lo: float, hi: float) -> list[float]:
    """log2 域内的 2 的幂刻度，覆盖 [lo, hi]。"""
    return [2.0 ** e for e in range(math.floor(math.log2(lo)), math.ceil(math.log2(hi)) + 1)]


def _fmt_size(kb: float) -> str:
    if kb >= 1024:
        return f"{int(kb / 1024)}M"
    return f"{int(kb)}K"


def _fmt_ns(v: float) -> str:
    return f"{v:g}"


def _annotation_cx(note: str, left: float, right: float) -> float:
    """shaded 标注的水平中心：默认取区间中心，估算文本半宽（全角字符计
    2 em）超出绘图区时夹回——只用于标注摆放，不参与几何映射。"""
    em = sum(2.0 if unicodedata.east_asian_width(ch) in "WF" else 1.0 for ch in note)
    half = em * _ANNOTATION_FONT_SIZE * 0.3
    plot_left, plot_right = MARGIN["left"], W - MARGIN["right"]
    if 2 * half >= plot_right - plot_left:
        return (plot_left + plot_right) / 2
    return min(max((left + right) / 2, plot_left + half), plot_right - half)


def latency_svg(series: dict[str, list[tuple[float, float]]], title: str, *,
                x_label: str = "buffer size（log2，每格一倍）",
                y_label: str = "latency_ns（log2）",
                shaded: list[tuple[float, float, str]] = [],
                vlines: list[tuple[float, str]] = []) -> str:
    """series: {系列名: [(buffer_kb, latency_ns), ...]} → SVG 字符串。

    系列名转义防 XML 注入；空系列抛 ValueError（没数据不出图）。
    shaded: (x0, x1, 标注) 的 x 轴区间半透明底色块 + 绘图区顶缘小字标注
    （顶缘上方 = 避开右上角图例区）；vlines: (x, 标注) 竖直虚线 + 标注
    （按线在中线左/右自动选标注侧，同理避开图例）。两者都画在数据线之
    下；x 越出数据范围时底色块按绘图区截断、整体在外则 ValueError（
    fail-closed，同空系列纪律）。默认参数下输出与泛化前逐字节一致
    （test_report.TestChartAnnotations 的 sha256 钉）。
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

    # 区间底色块 + 顶缘标注（先于网格绘制 = 画在网格与数据线之下）
    for x0, x1, note in shaded:
        if x0 <= 0 or x1 <= 0:
            raise ValueError(f"shaded bounds must be positive (log2 domain): {(x0, x1)}")
        left = max(X(min(x0, x1)), float(MARGIN["left"]))
        right = min(X(max(x0, x1)), float(W - MARGIN["right"]))
        if right <= left:
            raise ValueError(f"shaded band {(x0, x1)} outside data x-range")
        parts.append(f'<rect x="{left:.1f}" y="{MARGIN["top"]}" width="{right - left:.1f}" '
                     f'height="{H - MARGIN["top"] - MARGIN["bottom"]}" '
                     f'fill="#2563eb" fill-opacity="0.08"/>')
        parts.append(f'<text x="{_annotation_cx(note, left, right):.1f}" '
                     f'y="{MARGIN["top"] - 8}" text-anchor="middle" '
                     f'font-size="{_ANNOTATION_FONT_SIZE}" fill="#6b7280">{e(note)}</text>')

    # 网格与坐标轴刻度
    for kb in sorted(set(xs)):
        x = X(kb)
        parts.append(f'<line x1="{x:.1f}" y1="{MARGIN["top"]}" x2="{x:.1f}" y2="{H-MARGIN["bottom"]}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{x:.1f}" y="{H-MARGIN["bottom"]+16}" text-anchor="middle">{_fmt_size(kb)}</text>')
    for ns in _nice_ticks(y_lo, y_hi):
        y = Y(ns)
        parts.append(f'<line x1="{MARGIN["left"]}" y1="{y:.1f}" x2="{W-MARGIN["right"]}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{MARGIN["left"]-8}" y="{y+4:.1f}" text-anchor="end">{_fmt_ns(ns)}</text>')
    parts.append(f'<text x="{W/2}" y="{H-8}" text-anchor="middle">{e(x_label)}</text>')
    parts.append(f'<text x="16" y="{H/2}" text-anchor="middle" transform="rotate(-90 16 {H/2})">{e(y_label)}</text>')

    # 竖直参考虚线 + 标注（画在数据线之下；标注按线位置选侧避开图例）
    mid_x = (MARGIN["left"] + W - MARGIN["right"]) / 2
    for xv, note in vlines:
        if xv <= 0:
            raise ValueError(f"vline x must be positive (log2 domain): {xv}")
        x = X(xv)
        if not MARGIN["left"] <= x <= W - MARGIN["right"]:
            raise ValueError(f"vline {xv} outside data x-range")
        parts.append(f'<line x1="{x:.1f}" y1="{MARGIN["top"]}" x2="{x:.1f}" '
                     f'y2="{H - MARGIN["bottom"]}" stroke="#dc2626" stroke-width="1" '
                     f'stroke-dasharray="4 3"/>')
        anchor, tx = ("end", x - 5) if x > mid_x else ("start", x + 5)
        parts.append(f'<text x="{tx:.1f}" y="{MARGIN["top"] + 14}" text-anchor="{anchor}" '
                     f'font-size="{_ANNOTATION_FONT_SIZE}" fill="#dc2626">{e(note)}</text>')

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
