# SPDX-License-Identifier: Apache-2.0
"""PMU 事件注册表守卫：configs/pmu-event-registry.json 结构完整性与 candidate/qualified 资格语义。

对应任务书 §3.1/S4（docs/tasks/2026-09-28-sm8650-tlb-hierarchy.md）：事件资格是数据记录而
非分析器常量——每条注册必须携带完整溯源字段，资格只取 candidate/qualified 两级；SM8650
Cortex-X4（midr 0x410fd821）的 0x05/0x34/0x8144 三条锚点事件必须已升 qualified。
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs" / "pmu-event-registry.json"

REQUIRED_KEYS = {
    "type",
    "config",
    "name",
    "midr",
    "source_doc",
    "source_revision",
    "positive_control_run",
    "outcome",
    "review_ref",
    "validity_scope",
    "qualification",
}
QUALIFICATIONS = {"candidate", "qualified"}
SM8650_X4_MIDR = "0x410fd821"
SM8650_X4_QUALIFIED_CONFIGS = {"0x05", "0x34", "0x8144"}


class TestPmuEventRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_registry_exists_and_holds_event_array(self):
        self.assertTrue(REGISTRY.is_file())
        self.assertIsInstance(self.registry, dict)
        self.assertEqual(self.registry["schema_version"], "1.0")
        self.assertIsInstance(self.registry["events"], list)
        self.assertTrue(self.registry["events"])

    def test_every_record_has_required_keys_and_valid_qualification(self):
        for record in self.registry["events"]:
            with self.subTest(config=record.get("config")):
                self.assertIsInstance(record, dict)
                self.assertLessEqual(REQUIRED_KEYS, set(record))
                self.assertIn(record["qualification"], QUALIFICATIONS)

    def test_sm8650_x4_anchor_events_are_qualified(self):
        by_config = {record["config"]: record for record in self.registry["events"]}
        for config in sorted(SM8650_X4_QUALIFIED_CONFIGS):
            with self.subTest(config=config):
                self.assertIn(config, by_config)
                self.assertEqual(by_config[config]["qualification"], "qualified")
                self.assertEqual(by_config[config]["midr"], SM8650_X4_MIDR)


if __name__ == "__main__":
    unittest.main()
