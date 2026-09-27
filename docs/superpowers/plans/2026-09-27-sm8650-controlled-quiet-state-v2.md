# SM8650 Controlled Quiet State v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed, auditable Android measurement profile that records the state relevant to cache-latency experiments, applies only the minimum safe mutation, and restores the exact pre-run state after success, failure, or interruption.

**Architecture:** Keep the existing generic environment transaction coordinator, but harden its journal so partial apply failures are recoverable. Add an Android state collector made of pure parsers plus executor-backed collection, then evaluate snapshots through a declarative platform profile. The Runner remains transport-neutral: it selects the collector named by the active profile, records before/after snapshots in each run record, and invalidates a case when required evidence is missing or a guard is violated.

**Tech Stack:** Python 3 standard library, `unittest`, existing Runner executor/environment abstractions, Android `adb shell`/KernelSU `su -c`, JSON platform configuration.

---

## Scope and safety decisions

This plan implements the second batch of
`docs/superpowers/specs/2026-09-27-sm8650-cache-evidence-revalidation-design.md`.
It does not implement CPU PMU, LLCC PMU, LKM/MMIO, camera interference, cache
capacity attribution, or a production calibration sweep.

The `controlled-baseline` profile performs only one mutation:

- set every cpufreq policy governor to `performance`, then restore the exact
  per-policy state captured before the run.

The profile does **not** stop `mi_thermald` or perf services, force DeviceIdle,
toggle airplane mode, kill applications, drop caches, change screen state, or
write cpufreq min/max limits. Those values are observed and gated instead.

The live acceptance run is an ABI/control-path smoke test, not cache evidence.
Its output goes to a temporary directory and is deleted after verification.

## File map

- `runner/environment/journal.py`: durable mutation intent and transaction state.
- `runner/environment/controllers.py`: controller registry and exact Android
  cpufreq state restore.
- `runner/environment/coordinator.py`: per-mutation journal persistence and
  rollback after partial apply failure.
- `runner/environment/android_state.py`: pure Android parsers and state collector.
- `runner/environment/policy.py`: declarative snapshot guard evaluation.
- `runner/engine.py`: before/after snapshot capture and fail-closed records.
- `runner/cli.py`: select and preview a named environment profile.
- `runner/tests/test_environment.py`: transaction and controller contracts.
- `runner/tests/test_android_state.py`: parser/collector/guard contracts.
- `runner/tests/test_engine_fields.py`: record and invalidation contracts.
- `runner/tests/test_cli.py`: profile selection and declared-mutation contracts.
- `configs/platforms/redmi-k70pro-01.json`: reusable controlled baseline profile.
- `docs/runbooks/redmi-controlled-quiet-state-v2.md`: operator and recovery flow.
- `runner/schema/README.md`: register environment snapshot extensions.

---

### Task 1: Make partial environment mutations durably recoverable

**Files:**

- Modify: `runner/environment/journal.py`
- Modify: `runner/environment/controllers.py`
- Modify: `runner/environment/coordinator.py`
- Modify: `runner/tests/test_environment.py`

- [ ] **Step 1: Write failing partial-apply rollback tests**

Add tests proving that a successful governor mutation is restored when a later
thermal controller fails, and that the journal records mutation intent before
the failing apply:

```python
def test_second_controller_failure_restores_first_mutation(self):
    ex = FakeCombinedAndroidExecutor(thermal_apply_ok=False)
    with self.assertRaises(EnvironmentError_) as cm:
        execute_environment_tx(
            PLATFORM, ["governor=performance", "thermal=stopped"], lambda: None,
            allow_mutation=True, store=self.store, executor=ex, lock=FakeLock())
    self.assertEqual(cm.exception.code, "env-apply-failed")
    self.assertEqual(ex.governor, "walt")
    journal = self.store.load(next(self.store.root.glob("*.json")).stem)
    self.assertEqual(journal.state, "restored")
    self.assertTrue(journal.mutations[1].apply_started)
    self.assertNotEqual(journal.mutations[1].apply_error, "")

def test_restore_resolves_canonical_controller_key(self):
    journal = self.store.new("fake-01")
    journal.mutations.append(Mutation(
        controller="cpufreq.governor", requested="performance", before="walt",
        after="performance", apply_started=True))
    journal.transition("applying")
    journal.transition("applied")
    self.store.save(journal)
    restore_transaction(journal.tx_id, PLATFORM, store=self.store,
                        executor=FakeAdbExecutor(governor="performance"),
                        lock=FakeLock())
```

If `restore_transaction` does not yet accept an injectable lock, add that
parameter as part of the minimal implementation; production callers keep the
existing default.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest runner.tests.test_environment -v
```

Expected: failure because `Mutation` has no `apply_started`, partial apply is
left in `apply-failed`, or canonical controller resolution is unavailable.

- [ ] **Step 3: Add durable intent and legal rollback transitions**

Extend `Mutation` with a backward-compatible default:

```python
@dataclass
class Mutation:
    controller: str
    requested: str
    before: str
    after: str = ""
    apply_error: str = ""
    apply_started: bool = False
```

Allow `applying -> restoring` so an ambiguous or partially successful apply can
be rolled back. Old journals load because the new field has a default.

Register controllers by both CLI alias and canonical key:

```python
_CONTROLLERS = {
    "governor": CpufreqGovernorController,
    "cpufreq.governor": CpufreqGovernorController,
    "thermal": SvcThermalDaemonController,
    "svc.thermal": SvcThermalDaemonController,
}

def controller_from_key(key: str) -> Controller:
    try:
        return _CONTROLLERS[key]()
    except KeyError as exc:
        raise RunnerError("env-unknown-controller", ...) from exc
```

Do not reconstruct controllers with `split('.')[-1]` during restore.

For `AdbExecutor`, upgrade `CpufreqGovernorController.inspect()` to capture a
canonical JSON object for every `policy*`, including `governor`, `min_khz`, and
`max_khz`. A simple request such as `performance` changes only each governor;
it must not write min/max. A JSON value is accepted only on the internal
restore path and restores each policy's captured min/max/governor after strict
policy-name, integer, and governor validation. Order min/max writes so a target
minimum above the current maximum writes max first, while a target maximum
below the current minimum writes min first. Non-ADB behavior retains the
existing Linux wrapper contract.

Add an Android test with four policies that proves `performance` was applied to
all four during `work()` and the exact original per-policy governors and limits
were restored afterwards. This is required because reading only `cpu0` cannot
detect a half-old/half-new policy state.

- [ ] **Step 4: Persist every mutation boundary and rollback on apply errors**

Change `_apply_all` to receive `JournalStore`. For each mutation:

1. validate and inspect;
2. append the mutation and save the journal;
3. set `apply_started=True` and save before calling `apply`;
4. apply, inspect, verify, and save the observed `after` value.

On any exception, save `apply_error`, transition to `restoring` when any
mutation has `apply_started`, restore in reverse order, save the final journal,
and re-raise the original apply error. A restore failure must be attached to
the raised error without hiding the original cause.

Restoration treats `apply_started=True` as the conservative criterion. Writing
the captured `before` value is safe even if the failed apply changed nothing.

- [ ] **Step 5: Run focused and full Runner tests**

```bash
python3 -m unittest runner.tests.test_environment -v
python3 -m unittest discover -s runner/tests -t .
```

Expected: all pass; no unfinished journal remains after a handled partial
failure.

- [ ] **Step 6: Commit the coordinator hardening**

```bash
git add runner/environment/journal.py runner/environment/controllers.py \
  runner/environment/coordinator.py runner/tests/test_environment.py
git diff --cached --name-only
git diff --cached --check
git commit -m "fix(runner): restore partial environment mutations"
```

---

### Task 2: Capture Android measurement state with fixture-tested parsers

**Files:**

- Create: `runner/environment/android_state.py`
- Create: `runner/tests/test_android_state.py`
- Modify: `runner/environment/__init__.py`

- [ ] **Step 1: Write parser tests from observed Android 15 output**

Use sanitized inline fixtures matching the Redmi output. Tests must cover:

- four cpufreq policies with governor/min/max/current frequency;
- `mWakefulness`, `mIsPowered`, `mScreenOn`, `mForceIdle`, and DeviceIdle states;
- `Active Camera Clients:\n[]\nAllowed user IDs:` as no active camera;
- a non-empty active-client block as active, without counting historical
  `CONNECT` events or HAL device dumps;
- CPU thermal sensors and maximum CPU temperature;
- malformed or missing required fields raising
  `RunnerError("env-snapshot-parse-failed", ...)`.

The public shape is:

```python
{
    "schema_version": "1.0",
    "cpufreq": {
        "policy0": {"governor": "walt", "min_khz": 556800,
                    "max_khz": 2265600, "cur_khz": 2265600},
        # policy2, policy5, policy7
    },
    "power": {"wakefulness": "Dozing", "powered": True,
              "screen_on": False},
    "device_idle": {"force_idle": False, "state": "ACTIVE",
                    "light_state": "ACTIVE"},
    "airplane_mode": False,
    "camera": {"active": False, "active_clients_raw": "[]"},
    "thermal": {"status": 0, "max_cpu_c": 89.9,
                "cpu_sensors_c": {"CPU0": 77.6}},
    "services": {"mi_thermald": "running"},
    "loadavg": {"one": 2.27, "five": 2.46, "fifteen": 2.53},
}
```

- [ ] **Step 2: Run parser tests and verify RED**

```bash
python3 -m unittest runner.tests.test_android_state -v
```

Expected: import failure because `runner.environment.android_state` does not
exist.

- [ ] **Step 3: Implement pure parsers and required-command collection**

Implement focused pure functions plus:

```python
def collect_android_state(executor) -> dict:
    """Collect one fail-closed Android state snapshot through AdbExecutor."""
```

Run commands through the executor, never by direct `subprocess`. Required
commands returning nonzero raise `env-snapshot-failed`; output parsing failures
raise `env-snapshot-parse-failed`. Use an explicit rooted cpufreq script that
emits one delimited row per `policy*`. Keep raw camera data limited to the active
client block; do not store the historical event log.

Do not mutate the device in this module.

- [ ] **Step 4: Add collector tests with a scripted fake AdbExecutor**

Test command failures, malformed outputs, and one complete success path. Assert
that the collector does not issue `stop`, `start`, `settings put`, `input`,
`force-idle`, or writes to `/sys`.

- [ ] **Step 5: Run tests and commit**

```bash
python3 -m unittest runner.tests.test_android_state -v
python3 -m unittest discover -s runner/tests -t .
git add runner/environment/android_state.py runner/environment/__init__.py \
  runner/tests/test_android_state.py
git diff --cached --check
git commit -m "feat(runner): collect Android measurement state"
```

---

### Task 3: Evaluate a declarative quiet-state policy and fail closed

**Files:**

- Create: `runner/environment/policy.py`
- Modify: `runner/tests/test_android_state.py`
- Modify: `runner/engine.py`
- Modify: `runner/tests/test_engine_fields.py`

- [ ] **Step 1: Write policy evaluator tests**

Define and test this platform-facing policy:

```python
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
            "policy7": 2745600
        },
        "max_cpu_temp_c": 90.0
    },
    "stable_fields": [
        "airplane_mode", "power.screen_on", "device_idle.force_idle",
        "services.mi_thermald", "cpufreq.*.governor",
        "cpufreq.*.min_khz", "cpufreq.*.max_khz"
    ]
}
```

Test exact violation codes such as `camera-active`, `thermal-over-limit`,
`cpufreq-max-mismatch:policy7`, and `state-drift:airplane_mode`.

- [ ] **Step 2: Run evaluator tests and verify RED**

```bash
python3 -m unittest runner.tests.test_android_state -v
```

- [ ] **Step 3: Implement the pure evaluator**

Expose:

```python
def evaluate_preconditions(snapshot: dict, policy: dict) -> list[str]: ...
def evaluate_stability(before: dict, after: dict, policy: dict) -> list[str]: ...
```

Return machine-readable strings; do not raise for a policy violation. Raise
`env-policy-invalid` only for malformed policy configuration.

- [ ] **Step 4: Write engine RED tests**

Test three paths in `_run_case`:

1. valid before/after snapshots are recorded under
   `environment.state_snapshot` and the case stays `ok`;
2. a failed precondition prevents the probe from executing and produces
   `failure.reason=environment-precondition-failed`;
3. postcondition drift invalidates otherwise successful samples with
   `failure.reason=environment-postcondition-failed`.

The failure detail contains sorted violation codes. Raw samples may remain for
audit after a postcondition failure, but metrics must be empty.

- [ ] **Step 5: Implement generic collector selection in the engine**

Add one transport-neutral helper selected by the profile's `collector` name.
No SM8650 target-id special case is allowed. If a required collector is
unsupported or fails, construct a failed run record rather than silently
omitting the snapshot.

- [ ] **Step 6: Run tests and commit**

```bash
python3 -m unittest runner.tests.test_android_state runner.tests.test_engine_fields -v
python3 -m unittest discover -s runner/tests -t .
git add runner/environment/policy.py runner/engine.py \
  runner/tests/test_android_state.py runner/tests/test_engine_fields.py
git diff --cached --check
git commit -m "feat(runner): gate runs on Android quiet-state evidence"
```

---

### Task 4: Add an explicit controlled-baseline profile to CLI and platform config

**Files:**

- Modify: `runner/cli.py`
- Modify: `runner/tests/test_cli.py`
- Modify: `configs/platforms/redmi-k70pro-01.json`
- Modify: `runner/schema/README.md`

- [ ] **Step 1: Write profile-resolution and CLI RED tests**

Test that:

- `--environment-profile controlled-baseline` resolves the named platform
  profile for both `plan` and `run`;
- an unknown profile fails with `config-invalid` before mutation;
- profile host requirements trigger a transaction even without CLI `--env`;
- profile or top-level host requirements without `--allow-mutation` fail closed;
- CLI `--env` appends to, rather than replaces, declared requirements;
- duplicate controller requests with conflicting values are rejected.

- [ ] **Step 2: Run CLI tests and verify RED**

```bash
python3 -m unittest runner.tests.test_cli -v
```

- [ ] **Step 3: Implement named profile resolution**

Add `--environment-profile` to `plan` and `run`. A profile has this shape:

```json
{
  "host_requirements": {"cpufreq.governor": "performance"},
  "measurement_environment": {"collector": "android-controlled-quiet-v2"}
}
```

Resolve it into a shallow copy of the platform passed to `run_plan`; do not
mutate the loaded config object. Print the selected profile and declared
mutations in `plan` output.

Fix `_cmd_run` so top-level or profile `host_requirements` activate an
environment transaction even when `args.env` is empty.

- [ ] **Step 4: Register the Redmi controlled baseline**

Add `environment_profiles.controlled-baseline` using the exact policy in Task
3 and only `cpufreq.governor=performance` as a mutation. Keep
`mi_thermald=running`, `force_idle=false`, camera inactive, screen off/Dozing,
and the four observed max-frequency caps as preconditions.

- [ ] **Step 5: Register schema extensions and validate JSON**

Document:

- `environment_profiles` platform extension;
- `environment.state_snapshot` run-record extension;
- the distinction between a policy violation and a probe failure.

Run:

```bash
python3 -m json.tool configs/platforms/redmi-k70pro-01.json >/dev/null
python3 -m runner.cli plan \
  --experiment configs/experiments/ptr-chase-cache-sweep.json \
  --platform configs/platforms/redmi-k70pro-01.json \
  --environment-profile controlled-baseline
python3 -m unittest discover -s runner/tests -t .
```

- [ ] **Step 6: Commit profile support**

```bash
git add runner/cli.py runner/tests/test_cli.py \
  configs/platforms/redmi-k70pro-01.json runner/schema/README.md
git diff --cached --check
git commit -m "feat(runner): add controlled Android environment profiles"
```

---

### Task 5: Write the runbook and prove the control path on the Redmi

**Files:**

- Create: `docs/runbooks/redmi-controlled-quiet-state-v2.md`
- Modify: `docs/methodology/measurement-discipline.md`
- Modify: `docs/open-items.md`

- [ ] **Step 1: Write the operator runbook**

The runbook must include:

- profile semantics and explicit non-goals;
- read-only preflight and expected fields;
- command preview with `runner.cli plan`;
- mutation authorization with `--allow-mutation`;
- journal inspection/recovery commands;
- cooldown gate when `max_cpu_c >= 90.0`;
- requirement that `mi_thermald` remains running;
- prohibition on `drop_caches`, blind `KEYCODE_POWER`, force-stopping arbitrary
  packages, and hard-coded restoration values;
- explicit statement that passing the profile proves measurement control, not
  cache geometry.

- [ ] **Step 2: Add a read-only profile inspection path**

Add `runner.cli env inspect --environment-profile controlled-baseline`. It must
collect one snapshot, print formatted JSON, evaluate preconditions, and return
exit 1 when the state is not ready. It must never apply mutations and must not
require `--allow-mutation`.

Write its CLI test first, observe RED, then implement it.

- [ ] **Step 3: Run all local verification**

```bash
cmake --preset macos-arm64-release
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release --output-on-failure
python3 -m unittest discover -s runner/tests -t .
python3 -m unittest discover -s analysis/tests -t .
cmake --preset macos-arm64-ubsan
cmake --build --preset macos-arm64-ubsan
ctest --preset macos-arm64-ubsan --output-on-failure
git diff --check
```

- [ ] **Step 4: Perform a read-only device inspection**

Run the new inspect command against `redmi-k70pro-01`. If temperature, camera,
screen, service, or frequency-cap gates fail, stop and report the exact
violation; do not weaken the policy to force a pass.

- [ ] **Step 5: Perform one temporary transaction smoke test**

After the device is ready, cross-compile the exact branch's `ptr_chase` for
AArch64, deploy it temporarily, and run one 4 MiB/64 B case with two complete
warmup passes under `controlled-baseline`. Store output outside `data/`.

Verify:

- all four governors are `performance` inside the transaction;
- `mi_thermald` remains `running`;
- state snapshots and policy result are present;
- journal ends `restored`;
- all four governors return to their captured pre-run value;
- temporary local, remote, and device files are deleted.

Do not interpret the measured latency as cache capacity evidence.

- [ ] **Step 6: Commit documentation and tracking changes**

```bash
git add docs/runbooks/redmi-controlled-quiet-state-v2.md \
  docs/methodology/measurement-discipline.md docs/open-items.md runner/cli.py \
  runner/tests/test_cli.py
git diff --cached --check
git commit -m "docs(sm8650): operationalize controlled quiet-state validation"
```

---

## Completion gate

This plan is complete only when:

1. partial apply failure is proven to restore earlier mutations;
2. every required Android snapshot field is fixture-tested and fail-closed;
3. a policy violation creates an invalid run record rather than a numeric
   metric;
4. the controlled profile mutates only the governor and preserves thermal
   protection;
5. the live transaction smoke restores the exact pre-run governor values;
6. no capacity claim or persistent SM8650 run is produced;
7. the frozen parent branch remains exactly at `1532274`.

After this gate, write a separate plan for the finite cache-validation matrix.
Do not append PMU or cache-attribution work to this implementation branch.
