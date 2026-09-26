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
        if not parts[0].strip() and not parts[2].strip():
            continue  # 未展开的通配符字面行（非 Linux sysfs）——跳过，不算有效层级
        levels.append({
            "level": int(parts[0]) if parts[0].strip().isdigit() else parts[0],
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


def collect_core_topology(executor) -> dict[str, Any]:
    """核型/拓扑事实（任务书 §2.3）：ARM64 平台的定义性维度。

    Linux 侧逐个检测存在性（cpu_capacity / cluster_cpus_list /
    cpuinfo_max_freq / midr_el1——部分路径需 root 或仅 ARM 提供，采不到
    的维度记 None，**不许猜**）；无 Linux sysfs 时退 macOS sysctl
    （hw.nperflevels / perflevel*）。两边皆空 → supported:false。
    """
    linux_script = (
        "for c in /sys/devices/system/cpu/cpu[0-9]*; do "
        "n=${c##*cpu}; "
        "echo \"$n|$(cat $c/cpu_capacity 2>/dev/null)"
        "|$(cat $c/topology/cluster_cpus_list 2>/dev/null)"
        "|$(cat $c/cpufreq/cpuinfo_max_freq 2>/dev/null)"
        "|$(cat $c/regs/identification/midr_el1 2>/dev/null)\"; done"
    )
    res = executor.execute(["sh", "-c", linux_script])
    if res.returncode == 0 and res.stdout.strip():
        cpus: dict[str, Any] = {}
        clusters: dict[str, set] = {}
        for line in res.stdout.splitlines():
            parts = (line.strip().split("|") + [""] * 5)[:5]
            cpu, cap, cl, mf, midr = parts
            if not cpu.strip().isdigit():
                continue  # 未展开的通配符字面行（非 Linux sysfs）——跳过
            entry: dict[str, Any] = {
                "capacity": int(cap) if cap.isdigit() else None,
                "max_freq_khz": int(mf) if mf.isdigit() else None,
                "midr_el1": midr or None,
                "cluster_cpus_list": cl or None,
            }
            cpus[cpu] = entry
            if cl:
                clusters.setdefault(cl, set()).add(cpu)
        # 所有维度全空 = sysfs 实际不存在（字面行残留）；交给 macOS 路径
        if cpus and any(any(v is not None for v in e.values()) for e in cpus.values()):
            return {"supported": True, "detail": "linux sysfs per-cpu (absent dims = None, not guessed)",
                    "values": {"source": "linux-sysfs", "cpus": cpus,
                               "clusters": {k: sorted(v, key=int) for k, v in clusters.items()}}}

    mac_script = ("sysctl hw.nperflevels "
                  "hw.perflevel0.name hw.perflevel0.logicalcpu hw.perflevel0.physicalcpu "
                  "hw.perflevel1.name hw.perflevel1.logicalcpu hw.perflevel1.physicalcpu 2>/dev/null")
    res = executor.execute(["sh", "-c", mac_script])
    if res.returncode == 0 and "hw.nperflevels" in res.stdout:
        fields: dict[str, str] = {}
        for line in res.stdout.splitlines():
            if ": " in line:
                k, _, v = line.partition(": ")
                fields[k.strip()] = v.strip()
        levels = []
        for i in range(int(fields.get("hw.nperflevels", "0"))):
            p = f"hw.perflevel{i}"
            levels.append({"name": fields.get(f"{p}.name"), "logicalcpu": fields.get(f"{p}.logicalcpu"),
                           "physicalcpu": fields.get(f"{p}.physicalcpu")})
        return {"supported": True, "detail": "macOS sysctl hw.perflevel*",
                "values": {"source": "macos-sysctl", "nperflevels": int(fields.get("hw.nperflevels", "0")),
                           "perflevels": levels}}
    return {"supported": False, "detail": "no linux sysfs topology and no macOS sysctl perflevels"}


def collect_all(executor, target: dict) -> dict:
    """采集全部已定义能力，组装 capability-manifest 记录（schema 1.0）。"""
    caps = {
        "cache-topology": collect_cache_topology(executor),
        "cpufreq": collect_cpufreq(executor),
        "core-topology": collect_core_topology(executor),
    }
    for entry in caps.values():
        entry["evidence"] = "MEASURED"
    return {
        "schema_version": "1.0",
        "target": target,
        "capabilities": caps,
    }
