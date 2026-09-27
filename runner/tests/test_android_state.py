# SPDX-License-Identifier: Apache-2.0
"""Android 受控安静态快照：解析真实格式，采集只读且关键字段缺失即失败。"""

from copy import deepcopy
import unittest

from runner.environment.android_state import (collect_android_state,
                                              parse_camera,
                                              parse_cpufreq,
                                              parse_device_state,
                                              parse_loadavg,
                                              parse_thermal)
from runner.errors import RunnerError
from runner.environment.policy import evaluate_preconditions, evaluate_stability
from runner.executor.adb import AdbExecutor
from runner.executor.local import ExecutionResult


CPUFREQ = """\
policy0|walt|556800|2265600|2265600
policy2|walt|614400|2707200|2707200
policy5|walt|499200|2707200|2707200
policy7|walt|672000|2745600|2745600
"""

POWER = """\
  mWakefulness=Dozing
  mWakefulnessChanging=false
  mIsPowered=true
"""

DEVICEIDLE = """\
  mForceIdle=false
  mScreenOn=false
  mCharging=true
  mState=ACTIVE mLightState=ACTIVE
"""

CAMERA_IDLE = """\
== Service global info: ==
Active Camera Clients:
[]
Allowed user IDs: 10
== Camera service events log (most recent at top): ==
  CONNECT device 5 client for package com.android.camera
"""

CAMERA_ACTIVE = """\
Active Camera Clients:
[
  Camera ID: 5, package=com.android.camera, state=12
]
Allowed user IDs: 10
"""

THERMAL = """\
Thermal Status: 0
    Temperature{mValue=32.2, mType=2, mName=battery, mStatus=0}
    Temperature{mValue=77.6, mType=0, mName=CPU0, mStatus=0}
    Temperature{mValue=89.9, mType=0, mName=CPU7, mStatus=0}
    Temperature{mValue=57.7, mType=1, mName=GPU0, mStatus=0}
"""

POLICY = {
    "collector": "android-controlled-quiet-v2",
    "required": True,
    "preconditions": {
        "wakefulness": ["Dozing"],
        "screen_on": False,
        "force_idle": False,
        "active_camera": False,
        "services": {"mi_thermald": "running"},
        "cpufreq_governor": "performance",
        "cpufreq_max_khz": {
            "policy0": 2265600,
            "policy2": 2707200,
            "policy5": 2707200,
            "policy7": 2745600,
        },
        "max_cpu_temp_c": 90.0,
    },
    "stable_fields": [
        "airplane_mode", "power.screen_on", "device_idle.force_idle",
        "services.mi_thermald", "cpufreq.*.governor",
        "cpufreq.*.min_khz", "cpufreq.*.max_khz",
    ],
}


class TestAndroidStateParsers(unittest.TestCase):
    def test_cpufreq_four_policy_snapshot(self):
        state = parse_cpufreq(CPUFREQ)
        self.assertEqual(sorted(state), ["policy0", "policy2", "policy5", "policy7"])
        self.assertEqual(state["policy7"], {
            "governor": "walt", "min_khz": 672000,
            "max_khz": 2745600, "cur_khz": 2745600})

    def test_power_deviceidle_and_airplane(self):
        state = parse_device_state(POWER, DEVICEIDLE, "0\n")
        self.assertEqual(state["power"], {
            "wakefulness": "Dozing", "powered": True, "screen_on": False})
        self.assertEqual(state["device_idle"], {
            "force_idle": False, "state": "ACTIVE",
            "light_state": "ACTIVE", "charging": True})
        self.assertFalse(state["airplane_mode"])

    def test_camera_uses_active_block_not_event_history(self):
        idle = parse_camera(CAMERA_IDLE)
        self.assertEqual(idle, {"active": False, "active_clients_raw": "[]"})
        active = parse_camera(CAMERA_ACTIVE)
        self.assertTrue(active["active"])
        self.assertIn("Camera ID: 5", active["active_clients_raw"])

    def test_thermal_only_uses_cpu_sensor_type(self):
        state = parse_thermal(THERMAL)
        self.assertEqual(state["status"], 0)
        self.assertEqual(state["max_cpu_c"], 89.9)
        self.assertEqual(state["cpu_sensors_c"], {"CPU0": 77.6, "CPU7": 89.9})

    def test_loadavg(self):
        self.assertEqual(parse_loadavg("2.27 2.46 2.53 2/11720 27326\n"),
                         {"one": 2.27, "five": 2.46, "fifteen": 2.53})

    def test_required_fields_fail_closed(self):
        cases = (
            lambda: parse_cpufreq("policy0|walt|bad|2265600|2265600\n"),
            lambda: parse_device_state("mWakefulness=Dozing\n", DEVICEIDLE, "0\n"),
            lambda: parse_camera("Camera ID: 5\n"),
            lambda: parse_thermal("Thermal Status: 0\n"),
            lambda: parse_loadavg("not-loadavg\n"),
        )
        for parse in cases:
            with self.subTest(parse=parse):
                with self.assertRaises(RunnerError) as cm:
                    parse()
                self.assertEqual(cm.exception.code, "env-snapshot-parse-failed")


class ScriptedAdbExecutor(AdbExecutor):
    def __init__(self, fail_command=""):
        self.fail_command = fail_command
        self.commands = []

    def execute(self, argv, command_prefix=()):
        cmd = " ".join(str(a) for a in argv)
        self.commands.append(cmd)
        if self.fail_command and self.fail_command in cmd:
            return ExecutionResult(1, "", "simulated command failure", "fake")
        if "cpu_uarch_state_cpufreq_v1" in cmd:
            out = CPUFREQ
        elif cmd == "dumpsys power":
            out = POWER
        elif cmd == "dumpsys deviceidle":
            out = DEVICEIDLE
        elif cmd == "settings get global airplane_mode_on":
            out = "0\n"
        elif cmd == "dumpsys media.camera":
            out = CAMERA_IDLE
        elif cmd == "dumpsys thermalservice":
            out = THERMAL
        elif cmd == "getprop init.svc.mi_thermald":
            out = "running\n"
        elif cmd == "cat /proc/loadavg":
            out = "2.27 2.46 2.53 2/11720 27326\n"
        else:
            return ExecutionResult(1, "", "unscripted: " + cmd, "fake")
        return ExecutionResult(0, out, "", "fake")


class TestAndroidStateCollector(unittest.TestCase):
    def test_collects_complete_snapshot_without_mutations(self):
        ex = ScriptedAdbExecutor()
        state = collect_android_state(ex)
        self.assertEqual(state["schema_version"], "1.0")
        self.assertEqual(state["services"], {"mi_thermald": "running"})
        self.assertEqual(state["thermal"]["max_cpu_c"], 89.9)
        forbidden = (" stop ", " start ", "settings put", "input keyevent",
                     "force-idle", " > /sys/")
        joined = "\n".join(ex.commands)
        for token in forbidden:
            self.assertNotIn(token, joined)

    def test_command_failure_is_structured(self):
        ex = ScriptedAdbExecutor(fail_command="dumpsys thermalservice")
        with self.assertRaises(RunnerError) as cm:
            collect_android_state(ex)
        self.assertEqual(cm.exception.code, "env-snapshot-failed")
        self.assertIn("thermalservice", str(cm.exception))


class TestAndroidQuietStatePolicy(unittest.TestCase):
    def setUp(self):
        self.snapshot = collect_android_state(ScriptedAdbExecutor())
        for fields in self.snapshot["cpufreq"].values():
            fields["governor"] = "performance"

    def test_valid_snapshot_and_stability(self):
        self.assertEqual(evaluate_preconditions(self.snapshot, POLICY), [])
        self.assertEqual(evaluate_stability(
            self.snapshot, deepcopy(self.snapshot), POLICY), [])

    def test_precondition_violation_codes_are_machine_readable(self):
        bad = deepcopy(self.snapshot)
        bad["camera"]["active"] = True
        bad["thermal"]["max_cpu_c"] = 90.1
        bad["cpufreq"]["policy7"]["max_khz"] = 3110400
        self.assertEqual(evaluate_preconditions(bad, POLICY), [
            "camera-active",
            "cpufreq-max-mismatch:policy7",
            "thermal-over-limit",
        ])

    def test_stability_expands_cpufreq_wildcards(self):
        after = deepcopy(self.snapshot)
        after["airplane_mode"] = True
        after["cpufreq"]["policy5"]["min_khz"] += 1
        self.assertEqual(evaluate_stability(self.snapshot, after, POLICY), [
            "state-drift:airplane_mode",
            "state-drift:cpufreq.policy5.min_khz",
        ])

    def test_malformed_policy_is_rejected(self):
        with self.assertRaises(RunnerError) as cm:
            evaluate_preconditions(self.snapshot, {"preconditions": {"wakefulness": "Dozing"}})
        self.assertEqual(cm.exception.code, "env-policy-invalid")


if __name__ == "__main__":
    unittest.main()
