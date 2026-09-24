# SPDX-License-Identifier: Apache-2.0
"""真实二进制契约测试（OI-9 修订纪律：fixture 必须真实捕获）。

adapter 生成的 argv 直接被**真实编译的 ptr_chase** 执行，stdout/stderr
再回给 parser——任何 argv/输出漂移都会在这里炸出来，而不是在实验数据里。
二进制未编译时 skip（不伪造通过）。
"""

import subprocess
import unittest
from pathlib import Path

from runner.adapters.ptr_chase import PtrChaseAdapter
from runner.errors import ParseError

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / "build" / "probes" / "cache-mem" / "ptr_chase"


@unittest.skipUnless(BINARY.is_file(), f"ptr_chase not compiled: {BINARY}")
class TestPtrChaseContract(unittest.TestCase):
    def setUp(self):
        self.adapter = PtrChaseAdapter()

    def _run(self, argv):
        return subprocess.run([str(BINARY), *argv], capture_output=True, text=True, timeout=60)

    def test_argv_accepted_and_output_parses(self):
        argv = self.adapter.build_argv(
            {"buffer_kb": 64, "stride": 64, "loads": 8000, "warmup": 1000})
        proc = self._run(argv)
        self.assertEqual(proc.returncode, 0, f"probe rejected adapter argv: {proc.stderr}")
        metrics = self.adapter.parse_output(proc.stdout, proc.stderr)
        self.assertEqual(metrics[0]["name"], "latency_ns")
        self.assertGreater(metrics[0]["value"], 0.0)

    def test_probe_abi_invalid_input_nonzero_exit(self):
        # Probe ABI（ADR-0006 §3）：非法输入非零退出，绝不静默产出记录
        proc = self._run(["-n", "1"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("latency_ns", proc.stdout)

    def test_parser_refuses_nan_inf_and_garbage(self):
        for bad in ("latency_ns=nan", "latency_ns=inf", "", "no fields here"):
            with self.assertRaises(ParseError, msg=f"{bad!r} must be refused"):
                self.adapter.parse_output(bad, "")


if __name__ == "__main__":
    unittest.main()
