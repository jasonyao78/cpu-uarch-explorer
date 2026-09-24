# SPDX-License-Identifier: Apache-2.0
"""Artifact 落盘契约：每个 sample 的原始输出必须独立保存。

回归锚点：曾用 Path.with_suffix(".stdout.txt") 把 ".s0" 当后缀替换，
同 case 的 5 个重复样本互相覆盖，只剩最后一趟。
"""

import tempfile
import unittest
from pathlib import Path

from runner.artifacts import ArtifactStore


class TestRawSamples(unittest.TestCase):
    def test_repeated_samples_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            store = ArtifactStore(Path(d))
            for i in range(5):
                store.write_raw_sample("exp:c:b64K", i, f"stdout-{i}", f"stderr-{i}")
            files = sorted((Path(d) / "raw").iterdir())
            self.assertEqual(len(files), 10)  # 5 样本 × (stdout+stderr)
            first = (Path(d) / "raw" / "exp_c_b64K.s0.stdout.txt").read_text()
            self.assertEqual(first, "stdout-0")
            self.assertEqual(len(store.entries), 5)
            self.assertEqual(len({e["sha256"] for e in store.entries}), 5)  # 内容不同则摘要不同


if __name__ == "__main__":
    unittest.main()
