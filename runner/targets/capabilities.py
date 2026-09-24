# SPDX-License-Identifier: Apache-2.0
"""cache 拓扑与 cpufreq 事实采集（经执行器通道，跨 transport 同码）。

采集失败（非 Linux / 无 sysfs / 权限不足）一律返回 {"supported": false,
...}——探测不到是合法结果，绝不编造（measurement-discipline；
capability-manifest schema 的 available/unsupported 语义）。
"""

from __future__ import annotations

from typing import Any

# cpu0 sysfs，单行 CSV 输出（逗号不会出现在任何字段值中）
_TOPOLOGY_SCRIPT = (
    "for i in /sys/devices/system/cpu/cpu0/cache/index*; do "
    "echo \"$(cat $i/level),$(cat $i/type),$(cat $i/size),"
    "$(cat $i/ways_of_associativity 2>/dev/null),"
    "$(cat $i/shared_cpu_list)\"; done"
)

_CPUFREQ_FIELDS = (
    "scaling_driver", "scaling_governor", "scaling_available_governors",
    "cpuinfo_min_freq", "cpuinfo_max_freq",
)


def collect_cache_topology(executor) -> dict[str, Any]:
    """Linux cache 拓扑（cpu0 sysfs index*）→ capability 条目。

    values.levels: [{level, type, size, ways, shared_cpu_list}]，size 保留
    sysfs 原值（48K/2048K/107520K——报告层对照时自行换算）。"""
    res = executor.execute(["sh", "-c", _TOPOLOGY_SCRIPT])
    if res.returncode != 0 or not res.stdout.strip():
        return {"supported": False, "detail": f"sysfs cache nodes unreadable: {res.stderr.strip()[:120]}"}
    levels = []
    for line in res.stdout.splitlines():
        parts = (line.strip().split(",") + [""] * 5)[:5]
        levels.append({
            "level": int(parts[0]) if parts[0].isdigit() else parts[0],
            "type": parts[1], "size": parts[2],
            "ways": parts[3], "shared_cpu_list": parts[4],
        })
    if not levels:
        return {"supported": False, "detail": "no cache index nodes on target"}
    return {"supported": True, "detail": "cpu0 sysfs (/sys/devices/system/cpu/cpu0/cache/index*)",
            "values": {"levels": levels}}


def collect_cpufreq(executor) -> dict[str, Any]:
    """cpufreq 机制事实：driver/governor/可用 governor/频率范围。"""
    base = "/sys/devices/system/cpu/cpu0/cpufreq"
    script = "; ".join(f'echo "$(cat {base}/{f} 2>/dev/null)"' for f in _CPUFREQ_FIELDS)
    res = executor.execute(["sh", "-c", script])
    lines = res.stdout.splitlines()
    if res.returncode != 0 or len(lines) < len(_CPUFREQ_FIELDS) or not lines[1].strip():
        return {"supported": False, "detail": f"cpufreq sysfs unreadable: {res.stderr.strip()[:120]}"}
    return {"supported": True, "detail": base, "values": {
        "driver": lines[0].strip(),
        "governor": lines[1].strip(),
        "available_governors": lines[2].split(),
        "min_khz": int(lines[3]) if lines[3].strip().isdigit() else None,
        "max_khz": int(lines[4]) if lines[4].strip().isdigit() else None,
    }}


def collect_all(executor, target: dict) -> dict:
    """采集全部已定义能力，组装 capability-manifest 记录（schema 1.0）。"""
    caps = {
        "cache-topology": collect_cache_topology(executor),
        "cpufreq": collect_cpufreq(executor),
    }
    for entry in caps.values():
        entry["evidence"] = "MEASURED"
    return {
        "schema_version": "1.0",
        "target": target,
        "capabilities": caps,
    }
