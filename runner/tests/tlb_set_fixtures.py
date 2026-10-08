# SPDX-License-Identifier: Apache-2.0
"""Synthetic probe transport for real A1 plans; never a hardware measurement.

Keep planner, engine, adapter, artifact writer and record serialization real.
Only external execution/system collection and binary registration are replaced.
No record is built or enriched here; consumers must read the producer's files.
"""
import contextlib
import io
import json
from pathlib import Path
from unittest import mock

from runner import engine
from runner.adapters.ptr_chase import PtrChaseAdapter
from runner.executor.local import ExecutionResult
from runner.plan import build_plan

REPO_ROOT = Path(__file__).resolve().parents[2]
A1_LAYERS = ("l1-main", "l2-repro", "l3-target")


def a1_plan(layer):
    """Expand the checked-in experiment and platform without rewriting cases."""
    platform = json.loads((REPO_ROOT / "configs/platforms/redmi-k70pro-01.json").read_text())
    spec = json.loads((REPO_ROOT / "configs/experiments" /
        f"ptr-chase-sm8650-x4-tlb-a1-{layer}.json").read_text())
    return build_plan(spec, platform), platform


def synthetic_stdout(case):
    """Complete requested descriptor/events, with an explicitly synthetic H1 curve.

    Distribute exactly W nodes over the requested regions. Values are per-round
    synthetic observations, not counts acquired from a PMU or evidence for H1.
    """
    params = {k: v.value for k, v in case.params}
    scope, window, regions = (params[k] for k in
        ("set_region_scope", "set_window", "set_regions"))
    nodes = [0] * regions
    if scope < 0:
        for i in range(window):
            nodes[i % regions] += 1
    else:
        nodes[scope] = window
    fields = {out: str(params[param])
              for out, param in PtrChaseAdapter._TLB_SET_DESCRIPTOR_MAP
              if param in params}
    valid_rounds = str(params["set_rounds"] - 1)  # production excludes cold round 0
    fields.update(mode="tlbset", page_kb="4", scatter="0",
        set_domain="multi-region", set_active_regions=str(sum(n > 0 for n in nodes)),
        set_target_region_nodes=",".join(map(str, nodes)),
        set_region_vpn_hi="5,6,7,8", set_region_vpn_hi_pure="1",
        window_valid_rounds=valid_rounds, window_invalid_rounds="0", window_mux_rounds="0",
        valid_rounds=valid_rounds, probe_ns="1000")
    h1_value = 0.2 if window < 8 else 4.0 if window == 8 else 6.5
    for event in params["pmu_events"]:
        label = event["name"]
        value = ((h1_value if params["set_hypothesis"] == 1 else 0.2)
                 if label == "l2d_tlb_refill" else 1000 if label == "cycles" else window)
        fields[f"pmu_{label}_count"] = str(value)
        fields[f"pmu_{label}_valid_rounds"] = valid_rounds
    return " ".join(f"{k}={v}" for k, v in fields.items()) + "\n"


class SyntheticExecutor:
    """Accept the actual planned argv/prefix and return synthetic probe stdout."""

    def __init__(self, plan, platform, output_filter):
        self.samples = iter((case, sample) for case in plan.cases
                            for sample in range(case.repetitions))
        self.probe_calls = 0
        self.aux_commands = [a["command"] for a in platform.get("aux_snapshots", [])]
        self.output_filter = output_filter

    def execute(self, argv, command_prefix=()):
        if argv in self.aux_commands:
            return ExecutionResult(0, "SYNTHETIC auxiliary snapshot\n", "", "SYNTHETIC")
        case, sample = next(self.samples)
        params = {k: v.value for k, v in case.params}
        expected = ["/SYNTHETIC-UNEXECUTED"] + PtrChaseAdapter().build_argv(params)
        if argv != expected or command_prefix != case.control.command_prefix:
            raise AssertionError("executor received argv/prefix different from the plan")
        self.probe_calls += 1
        stdout = synthetic_stdout(case)
        if self.output_filter is not None:
            stdout = self.output_filter(case, sample, stdout)
        return ExecutionResult(0, stdout, "", "SYNTHETIC-UNEXECUTED")

    def system_info(self):
        return {"os_version": "SYNTHETIC", "kernel": "SYNTHETIC", "compiler": "SYNTHETIC"}

    def freq_snapshot(self, cpu_hint):
        return None


def run_synthetic_plan(plan, platform, run_dir, output_filter=None):
    """Run the actual producer; no phone, adb, binary or perf execution.

    Return summary and probe-call count, including failed cases. Callers MUST
    assert successful/failed record counts before asserting record fields.
    Does not patch _run_case, parsing, writing, loading or experiment identity.
    """
    executor = SyntheticExecutor(plan, platform, output_filter)
    with mock.patch.object(engine, "make_executor", return_value=executor), \
         mock.patch.object(engine, "_register_probe", return_value=(
             "/SYNTHETIC-UNEXECUTED", {"sha256": "f" * 64})), \
         mock.patch.object(engine, "git_provenance", return_value={
             "commit": "0" * 40, "dirty": False}), \
         contextlib.redirect_stdout(io.StringIO()):
        summary = engine.run_plan(plan, platform, Path(run_dir), REPO_ROOT)
    return summary, executor.probe_calls
