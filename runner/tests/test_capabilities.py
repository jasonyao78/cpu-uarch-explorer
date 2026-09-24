# SPDX-License-Identifier: Apache-2.0
"""能力采集器契约：sysfs 拓扑/cpufreq 解析、探测失败的如实降级。

守两条契约：
1. 解析正确性：CSV 行字段对齐、数字字段类型转换；
2. 失败语义：通道失败/输出缺失 → supported=false + 原因，
   collect_all 产物满足 capability-manifest schema 1.0 的必需键。
全部用 FakeExecutor（脚本化响应），不依赖真机。
"""

import unittest

from runner.executor.local import ExecutionResult
from runner.targets.capabilities import collect_all, collect_cache_topology, collect_cpufreq


class FakeExecutor:
    """脚本化假执行器：按 argv 子串匹配响应，守 execute() 契约（不抛）。"""

    def __init__(self, responses: list[tuple[str, ExecutionResult]]):
        self._responses = responses

    def execute(self, argv, command_prefix=()):
        cmd = " ".join(str(a) for a in argv)
        for key, res in self._responses:
            if key in cmd:
                return res
        return ExecutionResult(returncode=1, stdout="", stderr="no scripted response",
                               raw_command="fake")


_XEON_TOPOLOGY = """1,Data,48K,12,0,56
1,Instruction,32K,8,0,56
2,Unified,2048K,16,0,56
3,Unified,107520K,15,0-111"""

_XEON_CPUFREQ = """intel_pstate
powersave
performance powersave
800000
3800000"""


class TestCacheTopology(unittest.TestCase):
    def test_parse_xeon_topology(self):
        ex = FakeExecutor([("cache/index", ExecutionResult(0, _XEON_TOPOLOGY, "", "fake"))])
        cap = collect_cache_topology(ex)
        self.assertTrue(cap["supported"])
        levels = cap["values"]["levels"]
        self.assertEqual(len(levels), 4)
        self.assertEqual(levels[0]["size"], "48K")
        self.assertEqual(levels[3]["size"], "107520K")
        self.assertEqual(levels[3]["shared_cpu_list"], "0-111")

    def test_unreadable_sysfs_degrades_honestly(self):
        ex = FakeExecutor([("cache/index", ExecutionResult(2, "", "Permission denied", "fake"))])
        cap = collect_cache_topology(ex)
        self.assertFalse(cap["supported"])
        self.assertIn("Permission denied", cap["detail"])


class TestCpufreq(unittest.TestCase):
    def test_parse_xeon_cpufreq(self):
        ex = FakeExecutor([("scaling_driver", ExecutionResult(0, _XEON_CPUFREQ, "", "fake"))])
        cap = collect_cpufreq(ex)
        self.assertTrue(cap["supported"])
        v = cap["values"]
        self.assertEqual(v["driver"], "intel_pstate")
        self.assertEqual(v["governor"], "powersave")
        self.assertEqual(v["max_khz"], 3800000)
        self.assertIn("performance", v["available_governors"])


class TestManifestShape(unittest.TestCase):
    def test_collect_all_matches_schema_required_keys(self):
        ex = FakeExecutor([
            ("cache/index", ExecutionResult(0, _XEON_TOPOLOGY, "", "fake")),
            ("scaling_driver", ExecutionResult(0, _XEON_CPUFREQ, "", "fake")),
        ])
        manifest = collect_all(ex, {"target_id": "xeon-8481c-01"})
        for key in ("schema_version", "target", "capabilities"):
            self.assertIn(key, manifest)
        self.assertIn("cache-topology", manifest["capabilities"])
        self.assertEqual(manifest["capabilities"]["cache-topology"]["evidence"], "MEASURED")


if __name__ == "__main__":
    unittest.main()
