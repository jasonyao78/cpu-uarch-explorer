# SPDX-License-Identifier: Apache-2.0
"""统计量：median / p25 / p75 / min / max + repetitions（run-record v2）。

重复执行与取中位是 runner 层职责（measurement-discipline §3）；
探针保持单次测量纯粹性。分位数用 inclusive 线性插值。
"""

from __future__ import annotations

import statistics


def percentile(sorted_values: list[float], q: float) -> float:
    """inclusive 线性插值分位数；sorted_values 非空且已排序。"""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    pos = q * (n - 1)
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def summarize(values: list[float]) -> dict:
    if not values:
        raise ValueError("summarize() requires at least one sample")
    s = sorted(values)
    return {
        "min": s[0],
        "median": statistics.median(s),
        "p25": percentile(s, 0.25),
        "p75": percentile(s, 0.75),
        "max": s[-1],
    }
