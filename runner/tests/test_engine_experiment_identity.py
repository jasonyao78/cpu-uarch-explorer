# SPDX-License-Identifier: Apache-2.0
"""R7-A/R9: plan identity must survive real producer serialization for every status.

The transport is synthetic. No target binary is required and no adb is executed.
Assertions first require nonempty successful/failed sets, preventing vacuous ID
checks when a malformed probe response makes every case fail.
"""
import json
from pathlib import Path
import tempfile
import unittest

from runner.tests.tlb_set_fixtures import a1_plan, run_synthetic_plan


class TestEngineExperimentIdentity(unittest.TestCase):
    def _run(self, output_filter=None):
        plan, platform = a1_plan("l3-target")
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            summary, calls = run_synthetic_plan(plan, platform, run_dir, output_filter)
            records = [json.loads(line) for line in
                       (run_dir / "records.jsonl").read_text().splitlines()]
            manifest = json.loads((run_dir / "run-manifest.json").read_text())
        self.assertEqual(len(plan.cases), 32)
        self.assertEqual(calls, 320)
        self.assertEqual(summary["total"], 32)
        self.assertEqual(len(records), 32)
        self.assertEqual(manifest["experiment_id"], plan.experiment_id)
        return plan, summary, records

    def test_success_records_persist_plan_identity(self):
        plan, summary, records = self._run()
        self.assertEqual(summary, {"total": 32, "ok": 32, "failed": 0,
                                   "skipped": 0, "unsupported": 0})
        self.assertTrue(all(r["status"] == "ok" for r in records))
        for record, case in zip(records, plan.cases):
            self.assertEqual(record.get("experiment_id"), plan.experiment_id)
            self.assertEqual(record["params"], {k: v.value for k, v in case.params})
            self.assertEqual(sum(record["probe"]["realized"]["set_target_region_nodes"]),
                             record["params"]["set_window"])
            for metric in record["metrics"]:
                self.assertEqual(metric["repetitions"], 10)
                self.assertEqual(len(metric["observations"]), 10)

    def test_failed_records_also_persist_plan_identity(self):
        plan, summary, records = self._run(lambda case, sample, stdout: "malformed\n")
        self.assertEqual(summary["ok"], 0)
        self.assertEqual(summary["failed"], 32)
        for record in records:
            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["metrics"], [])
            self.assertEqual(record["failure"]["reason"], "parse-error")
            self.assertEqual(record.get("experiment_id"), plan.experiment_id)

    def test_valid_va_reallocation_is_not_a_mixed_domain(self):
        def varying_va(case, sample, stdout):
            return stdout.replace("set_region_vpn_hi=5,6,7,8",
                "set_region_vpn_hi=" + ",".join(str(x + sample) for x in (5, 6, 7, 8)))
        _, summary, records = self._run(varying_va)
        self.assertEqual(summary["ok"], 32)
        for record in records:
            realized = record["probe"]["realized"]
            self.assertTrue(realized["domain_consistent"])
            self.assertEqual(len(realized["samples"]), 10)
            self.assertNotEqual(realized["samples"][0]["realized"]["set_region_vpn_hi"],
                                realized["samples"][-1]["realized"]["set_region_vpn_hi"])

    def test_missing_requested_event_cannot_be_a_success_fixture(self):
        def without_cycles(case, sample, stdout):
            return " ".join(t for t in stdout.split() if not t.startswith("pmu_cycles_"))
        _, summary, records = self._run(without_cycles)
        self.assertEqual(summary["ok"], 0)
        self.assertEqual(summary["failed"], 32)
        self.assertTrue(all(r["status"] == "failed" for r in records))
        self.assertTrue(all("cycles" in r["failure"]["detail"] for r in records))


if __name__ == "__main__":
    unittest.main()
