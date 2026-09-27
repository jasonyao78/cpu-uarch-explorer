# SPDX-License-Identifier: Apache-2.0
"""CLI 环境 profile：显式选择、声明式 mutation 与冲突门禁。"""

import io
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest import mock

from runner.cli import (_cmd_env, _cmd_plan, _cmd_run, _resolve_environment_profile,
                        _resolve_environment_specs)
from runner.errors import RunnerError


PROFILE_POLICY = {
    "collector": "android-controlled-quiet-v2",
    "required": True,
    "preconditions": {
        "wakefulness": ["Dozing"], "screen_on": False, "force_idle": False,
        "active_camera": False, "services": {"mi_thermald": "running"},
        "cpufreq_governor": "performance",
        "cpufreq_max_khz": {"policy7": 2745600},
        "max_cpu_temp_c": 90.0,
    },
    "stable_fields": ["airplane_mode"],
}

PLATFORM = {
    "target": {"target_id": "fake-android", "transport": "adb"},
    "probes": {"ptr_chase": "/probe"},
    "environment_profiles": {
        "controlled-baseline": {
            "host_requirements": {"cpufreq.governor": "performance"},
            "measurement_environment": PROFILE_POLICY,
        }
    },
}


class TestEnvironmentProfileResolution(unittest.TestCase):
    def test_named_profile_is_copied_into_active_platform(self):
        active, requirements = _resolve_environment_profile(
            PLATFORM, "controlled-baseline")
        self.assertIsNot(active, PLATFORM)
        self.assertEqual(active["measurement_environment"], PROFILE_POLICY)
        self.assertEqual(active["active_environment_profile"], "controlled-baseline")
        self.assertEqual(requirements, {"cpufreq.governor": "performance"})
        self.assertNotIn("measurement_environment", PLATFORM)

    def test_unknown_profile_fails_before_execution(self):
        with self.assertRaises(RunnerError) as cm:
            _resolve_environment_profile(PLATFORM, "missing")
        self.assertEqual(cm.exception.code, "config-invalid")

    def test_cli_specs_append_and_conflicts_are_rejected(self):
        specs = _resolve_environment_specs(
            {"cpufreq.governor": "performance"}, ["thermal=stopped"])
        self.assertEqual(specs, ["governor=performance", "thermal=stopped"])
        with self.assertRaises(RunnerError) as cm:
            _resolve_environment_specs(
                {"cpufreq.governor": "performance"}, ["governor=powersave"])
        self.assertEqual(cm.exception.code, "env-conflicting-request")


class TestEnvironmentProfileCLI(unittest.TestCase):
    def setUp(self):
        self.plan = SimpleNamespace(
            experiment_id="smoke", protocol_version="1.1", cases=(),
            target={"target_id": "fake-android"})

    def _run_args(self, **updates):
        values = dict(experiment="e.json", platform="p.json", out="/tmp/runs",
                      env=None, allow_mutation=True,
                      environment_profile="controlled-baseline")
        values.update(updates)
        return Namespace(**values)

    def test_plan_previews_profile_and_mutations(self):
        args = Namespace(experiment="e.json", platform="p.json",
                         environment_profile="controlled-baseline")
        with (mock.patch("runner.cli.load_experiment", return_value={}),
              mock.patch("runner.cli.load_platform", return_value=PLATFORM),
              mock.patch("runner.cli.build_plan", return_value=self.plan)):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(_cmd_plan(args), 0)
        self.assertIn("environment_profile=controlled-baseline", out.getvalue())
        self.assertIn("governor=performance", out.getvalue())

    def test_profile_requirements_trigger_tx_without_cli_env(self):
        summary = {"total": 1, "ok": 1, "failed": 0,
                   "skipped": 0, "unsupported": 0}
        with (mock.patch("runner.cli.load_experiment", return_value={}),
              mock.patch("runner.cli.load_platform", return_value=PLATFORM),
              mock.patch("runner.cli.build_plan", return_value=self.plan),
              mock.patch("runner.environment.reconcile_unfinished", return_value=[]),
              mock.patch("runner.environment.execute_environment_tx",
                         return_value=summary) as execute):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(_cmd_run(self._run_args()), 0)
        self.assertEqual(execute.call_args.args[1], ["governor=performance"])
        self.assertTrue(execute.call_args.kwargs["allow_mutation"])

    def test_profile_mutation_requires_explicit_authorization(self):
        with (mock.patch("runner.cli.load_experiment", return_value={}),
              mock.patch("runner.cli.load_platform", return_value=PLATFORM),
              mock.patch("runner.cli.build_plan", return_value=self.plan)):
            with self.assertRaises(RunnerError) as cm:
                _cmd_run(self._run_args(allow_mutation=False))
        self.assertEqual(cm.exception.code, "env-mutation-not-allowed")

    def test_env_inspect_is_read_only_and_reports_violations(self):
        args = Namespace(platform="p.json", action="inspect", tx=None,
                         environment_profile="controlled-baseline")
        snapshot = {"schema_version": "1.0"}
        executor = object()
        with (mock.patch("runner.cli.load_platform", return_value=PLATFORM),
              mock.patch("runner.cli.make_executor", return_value=executor),
              mock.patch("runner.environment.collect_environment_state",
                         return_value=snapshot) as collect,
              mock.patch("runner.environment.evaluate_preconditions",
                         return_value=["thermal-over-limit"])):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(_cmd_env(args), 1)
        collect.assert_called_once_with(executor, PROFILE_POLICY)
        self.assertIn('"valid": false', out.getvalue())
        self.assertIn('"thermal-over-limit"', out.getvalue())

    def test_env_inspect_treats_declared_governor_change_as_covered(self):
        args = Namespace(platform="p.json", action="inspect", tx=None,
                         environment_profile="controlled-baseline")
        with (mock.patch("runner.cli.load_platform", return_value=PLATFORM),
              mock.patch("runner.cli.make_executor", return_value=object()),
              mock.patch("runner.environment.collect_environment_state",
                         return_value={"schema_version": "1.0"}),
              mock.patch("runner.environment.evaluate_preconditions",
                         return_value=["cpufreq-governor-mismatch:policy7"])):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(_cmd_env(args), 0)
        self.assertIn('"ready_for_transaction": true', out.getvalue())
        self.assertIn('"covered_by_mutation"', out.getvalue())


if __name__ == "__main__":
    unittest.main()
