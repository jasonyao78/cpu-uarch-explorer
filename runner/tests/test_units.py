# SPDX-License-Identifier: Apache-2.0
"""单位解析契约：GB10 静默降级教训的直接对冲——未知单位必须报错。"""

import unittest

from runner.errors import RunnerError
from runner.resolve import parse_size_bytes, parse_size_kb


class TestUnitParsing(unittest.TestCase):
    def test_binary_units(self):
        self.assertEqual(parse_size_bytes("64MiB"), 64 * 1024 * 1024)
        self.assertEqual(parse_size_bytes("32KiB"), 32 * 1024)
        self.assertEqual(parse_size_bytes("64B"), 64)
        self.assertEqual(parse_size_kb("64MiB"), 65536)
        self.assertEqual(parse_size_kb("512KiB"), 512)

    def test_decimal_spelling_is_binary_semantics(self):
        # 本仓文档化口径：KB/MB/GB 一律按 1024 进制解释
        self.assertEqual(parse_size_kb("64MB"), 65536)

    def test_unknown_unit_rejected_no_silent_default(self):
        for bad in ("64M", "64Mi", "1024", "abc", "64MiBB", ""):
            with self.assertRaises(RunnerError, msg=f"{bad!r} must be rejected"):
                parse_size_bytes(bad)

    def test_sub_kb_or_misaligned_rejected(self):
        with self.assertRaises(RunnerError):
            parse_size_kb("512B")


if __name__ == "__main__":
    unittest.main()
