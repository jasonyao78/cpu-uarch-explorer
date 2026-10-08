#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the R7-A takeover fix with real software and synthetic external I/O.

No adb, target binary or PMU is executed. No records are hand-built or enriched.
Exit 0 only verifies the stated software checks, not global RV2-02 closure or
approval of Phase A's frozen calibration/measurement contract.
"""
import argparse
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    tree = args.tree.resolve()
    sys.path.insert(0, str(tree))
    from analysis.load import load_run
    from analysis.sm8650_tlb import TlbError
    from analysis.sm8650_tlb_a1 import run_a1_adjudication
    from analysis.tests.a1_production_fixture import freeze_fixture
    from runner.tests.tlb_set_fixtures import A1_LAYERS, a1_plan, run_synthetic_plan

    def produce(plan, platform, directory, output_filter=None):
        summary, calls = run_synthetic_plan(plan, platform, directory, output_filter)
        loaded = load_run(directory)
        return summary, calls, loaded

    layers, records = {}, []
    with tempfile.TemporaryDirectory(prefix="a1-takeover-synthetic-") as tmp:
        root = Path(tmp)
        for layer in A1_LAYERS:
            plan, platform = a1_plan(layer)
            summary, calls, loaded = produce(plan, platform, root / layer)
            if summary["ok"] != len(plan.cases) or loaded.failed_records:
                raise AssertionError(f"nonempty successful producer required: {summary}")
            if len(loaded.ok_records) != len(plan.cases):
                raise AssertionError("loaded success count differs from plan")
            if not all(r.get("experiment_id") == plan.experiment_id
                       for r in loaded.ok_records):
                raise AssertionError("record experiment_id missing or inconsistent")
            if not all(m["repetitions"] == 10 and len(m["observations"]) == 10
                       for r in loaded.ok_records for m in r["metrics"]):
                raise AssertionError("ten observations per case required")
            if not all(sum(r["probe"]["realized"]["set_target_region_nodes"])
                       == r["params"]["set_window"] for r in loaded.ok_records):
                raise AssertionError("node totals must match requested W")
            if calls != len(plan.cases) * 10:
                raise AssertionError("wrong number of synthetic probe calls")
            layers[layer] = {"summary": summary, "fake_probe_calls": calls,
                "record_ids_present": len(loaded.ok_records),
                "manifest_experiment_id": loaded.manifest["experiment_id"]}
            records.extend(loaded.ok_records)

        frozen = freeze_fixture(root / "calibration")
        baseline = run_a1_adjudication(records, frozen)
        if baseline["h_star"] != 1 or baseline["n_records"] != 128:
            raise AssertionError(f"unexpected synthetic adjudication: {baseline}")
        shuffled = copy.deepcopy(records)
        random.Random(7).shuffle(shuffled)
        shuffled_result = run_a1_adjudication(shuffled, frozen)
        serialize = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
        if baseline != shuffled_result or serialize(baseline) != serialize(shuffled_result):
            raise AssertionError("full result must be permutation invariant")

        failures = {}
        base = [r for r in records if "a1-l3" not in r["experiment_id"]]
        for label, key, mapping, expected_message in (
            ("target_201", "set_target", {200: 201}, "exact coverage"),
            ("windows_100_200", "set_window", {8: 100, 12: 200}, "window grid"),
        ):
            plan, platform = a1_plan("l3-target")
            cases = tuple(dataclasses.replace(c, params=tuple(
                (k, dataclasses.replace(rv, value=mapping.get(rv.value, rv.value)))
                if k == key else (k, rv) for k, rv in c.params)) for c in plan.cases)
            plan = dataclasses.replace(plan, cases=cases)
            summary, calls, loaded = produce(plan, platform, root / label)
            if summary["ok"] != 32 or loaded.failed_records:
                raise AssertionError(f"negative plan must produce valid records: {summary}")
            try:
                run_a1_adjudication(base + loaded.ok_records, frozen)
            except TlbError as error:
                if expected_message not in str(error):
                    raise
                failures[label] = {"producer_summary": summary,
                    "fake_probe_calls": calls, "exception": type(error).__name__,
                    "message": str(error)}
            else:
                raise AssertionError("neighboring plan incorrectly accepted")

        plan, platform = a1_plan("l3-target")
        summary, calls, loaded = produce(plan, platform, root / "failed",
            lambda case, sample, stdout: "malformed\n")
        if summary["failed"] != 32 or loaded.ok_records or len(loaded.failed_records) != 32:
            raise AssertionError("malformed fixture must fail every case")
        if not all(r.get("experiment_id") == plan.experiment_id for r in loaded.failed_records):
            raise AssertionError("failed records must persist plan identity too")

    sources = ["runner/engine.py", "runner/schema/README.md",
        "runner/tests/test_engine_experiment_identity.py", "runner/tests/tlb_set_fixtures.py",
        "analysis/sm8650_tlb_a1.py", "analysis/tests/test_sm8650_tlb_a1.py"]
    sources += [f"configs/experiments/ptr-chase-sm8650-x4-tlb-a1-{layer}.json"
                for layer in A1_LAYERS]
    result = {"scope": __doc__, "source_head": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tree, text=True).strip(),
        "source_sha256": {f: hashlib.sha256((tree / f).read_bytes()).hexdigest()
                          for f in sources},
        "layers": layers, "total_ok_records": len(records),
        "fake_probe_observations": sum(v["fake_probe_calls"] for v in layers.values()),
        "synthetic_frozen": frozen, "synthetic_adjudication": baseline,
        "full_result_permutation_equal": baseline == shuffled_result,
        "canonical_json_permutation_equal": serialize(baseline) == serialize(shuffled_result),
        "neighboring_plan_rejections": failures,
        "malformed_output": {"summary": summary, "fake_probe_calls": calls,
                             "failed_record_ids_present": len(loaded.failed_records)},
        "outcome": "PASS for R7-A/R9 software closure; no global Phase A approval"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: result[k] for k in (
        "outcome", "total_ok_records", "fake_probe_observations",
        "full_result_permutation_equal", "canonical_json_permutation_equal")},
        ensure_ascii=False))


if __name__ == "__main__":
    main()
