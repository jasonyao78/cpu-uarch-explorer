# SM8650 Cortex-X4 private-L2 calibration implementation plan

> **Execution mode:** continue on `codex/sm8650-l2-pmu-calibration`. Keep
> `main` and `codex/sm8650-cache-validation` unchanged. Implement and verify
> each task with TDD, commit each coherent checkpoint, then run the device
> matrix only from a clean commit.

**Goal:** determine whether the Redmi K70 Pro / SM8650 Cortex-X4 exhibits a
repeatable private-L2 capacity boundary in the 512 KiB–3 MiB region, while
separating cache-refill behavior from DTLB, clock, page-backing, and run-level
aggregation artifacts.

**Architecture:** keep the portable pointer-chase loop as the experiment
harness and place Linux perf-event mechanics behind a Linux platform library.
The unprivileged probe opens per-thread core PMU events and brackets the exact
timed dependent-load loop. Runner aggregates every metric by name and retains
one observation per process/repetition; invariant metadata remains at metric
top level, while sample-varying values stay in observations. Base pages are an
explicit requested policy (`MADV_NOHUGEPAGE`), not an inference from default
allocation. LLCC is not needed to identify a private-L2 boundary and remains a
separate root-sidecar gate for the later outer-cache phase.

**Why this sequence:** core PMU type 8 is directly usable by adb shell, while
LLCC type 9/config 0x1000 requires root. Running the whole probe as root would
change the subject and privilege boundary. L2D refill + DTLB walk + measured
cycles are the relevant discriminators for the private-L2 question; LLCC
counts become relevant only after this gate passes and outer-cache work starts.

---

## Acceptance rules

The experiment may support a measured X4 private-L2 boundary only if all of
the following hold:

1. every admitted case has at least 10 fresh-process repetitions and a complete
   per-sample observation list;
2. requested/actual page policy is preserved per sample, with the base-page
   cohort actually `base`; THP samples are grouped by actual backing and never
   silently merged across `base` / `mixed` / `thp`;
3. core PMU counters bracket the same dependent-load timing loop, report raw
   count plus enabled/running time, and have `time_running > 0`; multiplexed
   samples are reported and excluded from the primary adjudication unless a
   separately documented scaling rule is adopted;
4. the latency/cycles transition is accompanied by a repeatable L2D-refill
   change; a latency shift explained only by DTLB walks is not an L2-capacity
   result;
5. environment pre/post gates pass, the governor transaction restores, and no
   accepted case crosses the thermal cutoff;
6. the conclusion is expressed as an observed transition interval/effective
   boundary, not an exact physical byte count, unless independent evidence
   closes associativity, coloring, and replacement-policy uncertainty.

If any rule fails, retain the run for audit but mark the result
`OPEN/INCONCLUSIVE`; do not promote it to the cache baseline.

---

## Task 1: Preserve every repetition and aggregate metrics generically

**Files:**

- Modify: `runner/engine.py`
- Modify: `runner/schema/run-record.v2.schema.json`
- Modify: `runner/schema/README.md`
- Modify: `runner/tests/test_engine_fields.py`

1. Add RED tests in which two successful repetitions return multiple named
   metrics with different values and sample metadata.
2. Replace the hard-coded `latencies + first_ok_extra` path with aggregation by
   metric name. Require every successful repetition to return the same metric
   name/unit set; mismatch is a structured parse/aggregation failure.
3. For each metric, emit median/p25/p75/min/max and an `observations` array with
   `sample_index`, `value`, `raw_sample_ref`, and the sample's additional
   fields. Copy an additional field to metric top level only when it is
   identical across all repetitions.
4. Preserve existing latency-only records and reports. Do not synthesize a
   value when a repetition fails.
5. Register `metrics[].observations[]` in the schema and schema README.

Verification:

```bash
.venv/bin/python -m unittest runner.tests.test_engine_fields
.venv/bin/python -m unittest discover -s runner/tests -t .
```

Commit:

```bash
git commit -m "feat(runner): preserve per-sample metric observations"
```

---

## Task 2: Add an explicit Linux base-page policy

**Files:**

- Modify: `probes/cache-mem/ptr_chase.cpp`
- Modify: `runner/adapters/ptr_chase.py`
- Modify: `runner/plan.py`
- Modify: `runner/tests/test_plan.py`
- Modify: `runner/tests/test_ptr_chase_contract.py`
- Modify: `tests/CMakeLists.txt`
- Modify: `runner/schema/README.md`

1. Add RED contract tests for `base_pages=1`, mutual exclusion with hugetlb/THP,
   and Linux output `page_policy_requested=base-madvise`.
2. Add `-B` / `MADV_NOHUGEPAGE` before the mapping is touched. On platforms
   without that Linux capability, return exit 2 rather than pretending the
   request succeeded.
3. Make `-B`, `-T`, and `-h/-H` mutually exclusive. Continue to obtain actual
   backing from the guarded VMA in smaps.
4. Thread `base_pages` through plan and adapter without changing old specs.
5. Extend the registered requested-policy enum with `base-madvise`.

Verification:

```bash
ctest --preset macos-arm64-release --output-on-failure
# plus full Linux CTest on xeon-8481c-01
```

Commit:

```bash
git commit -m "feat(ptr-chase): add explicit base-page policy"
```

---

## Task 3: Count core PMU events in the exact chase window

**Files:**

- Create: `probes/platform/linux/perf_counter.h`
- Create: `probes/platform/linux/perf_counter.cpp`
- Modify: `probes/platform/linux/CMakeLists.txt`
- Modify: `probes/cache-mem/CMakeLists.txt`
- Modify: `CMakeLists.txt`
- Modify: `probes/cache-mem/ptr_chase.cpp`
- Modify: `runner/adapters/ptr_chase.py`
- Modify: `runner/plan.py`
- Modify: `runner/tests/test_plan.py`
- Modify: `runner/tests/test_ptr_chase_contract.py`
- Modify: `tests/CMakeLists.txt`
- Modify: `runner/schema/README.md`

1. Add RED parser/argv tests for repeated PMU event descriptors and complete
   PMU output field groups.
2. Implement a Linux-only counting-session abstraction. Each event is opened
   disabled for the current thread, reset/enabled immediately before `t0`, read
   while still enabled immediately after `t1`, then disabled. Preserve an
   immediate post-enable baseline so the interface remains compatible with
   cumulative downstream PMUs later.
3. Add repeatable long option
   `--pmu-event <label>:<type>:<base-0-config>`. Labels are restricted to safe
   lowercase identifier characters and must be unique. A requested event that
   cannot open/read is a non-successful probe, never a missing metric.
4. Emit, for every label, raw count delta, `time_enabled_ns`,
   `time_running_ns`, type, and config. Zero count is valid; regressing values,
   short reads, zero running time, or malformed groups are hard failures.
5. Parse each event into a named metric `pmu.<label>.count` with unit `events`.
   Do not scale multiplexed counts in the probe. The raw timing evidence stays
   attached to each observation.
6. Accept a structured `pmu_events` list in ExperimentSpec fixed parameters and
   translate it deterministically to argv. Existing experiments remain
   unchanged.
7. Bump only the new calibration specs to protocol 1.2; old 1.1 records remain
   readable.

SM8650 event set for the first live gate:

- `cycles`: type 8 / config `0x11`;
- `l2d_cache_refill`: type 8 / config `0x17`;
- `l3d_cache_refill`: type 8 / config `0x2a`;
- `dtlb_walk`: type 8 / config `0x34`.

Verification:

```bash
ctest --preset macos-arm64-release --output-on-failure
ctest --preset macos-arm64-ubsan --output-on-failure
# full Linux CTest on xeon-8481c-01
.venv/bin/python -m unittest discover -s runner/tests -t .
.venv/bin/python -m unittest discover -s analysis/tests -t .
```

Commit:

```bash
git commit -m "feat(ptr-chase): sample core PMU in timed window"
```

---

## Task 4: Define an X4-only, two-page-policy calibration matrix

**Files:**

- Modify: `runner/plan.py`
- Modify: `runner/tests/test_plan.py`
- Modify: `configs/platforms/redmi-k70pro-01.json`
- Create: `configs/experiments/ptr-chase-sm8650-x4-l2-base.json`
- Create: `configs/experiments/ptr-chase-sm8650-x4-l2-thp.json`
- Modify: `docs/open-items.md`

1. Add optional `execution.controls` filtering in the generic planner. Unknown
   control ids fail at plan time. This avoids creating a one-off platform file
   merely to select CPU7.
2. Select only `x4-prime`. Sweep these buffer sizes:
   `512, 640, 768, 896, 1024, 1152, 1280, 1536, 1792, 2048, 2304, 2560,
   2816, 3072 KiB`.
3. Use stride 64 B, two complete-ring warmup passes, at least 16,777,216 timed
   loads, and 10 fresh-process repetitions per case.
4. The base spec requests `base_pages=1`; the THP spec requests `thp=1`.
   Both request the same four core PMU events. THP admission remains based on
   actual smaps backing, not the request flag.
5. Correct the Android deploy mapping to the repository's canonical
   `build/linux-aarch64-cross/release/...` preset path and update the measured
   LLCC capability note without promoting cache capacity.

Verification:

```bash
.venv/bin/python -m runner.cli plan \
  --experiment configs/experiments/ptr-chase-sm8650-x4-l2-base.json \
  --platform configs/platforms/redmi-k70pro-01.json \
  --environment-profile controlled-baseline
```

Each plan must contain exactly 14 X4 cases × 10 repetitions and no A520 case.

Commit:

```bash
git commit -m "config(sm8650): define X4 L2 calibration matrix"
```

---

## Task 5: Cross-build and run bounded device preflight

1. Build the exact clean commit with the Xeon AArch64 static cross preset;
   copy the artifact to the configured local deploy path and record SHA-256.
2. Run all local/remote tests again, then deploy through Runner so the actual
   device binary digest is manifest-anchored.
3. Inspect `controlled-baseline` before mutation. Do not run if screen/camera,
   thermal, service, or unfinished-transaction gates fail.
4. Run three manual one-process preflights on CPU7 from adb shell:
   512 KiB base, 2 MiB base, and 3 MiB THP request. Require all four events to
   open/read, nonzero running time, coherent cycles/load, and exact page audit.
5. If four simultaneous core events multiplex on this PMU, stop and reduce the
   event set in a documented second preflight; do not silently scale or accept.

No preflight number is a capacity result.

---

## Task 6: Execute, analyze, and adjudicate the X4 L2 matrix

**Files:**

- Create: `analysis/sm8650_l2.py`
- Create: `analysis/tests/test_sm8650_l2.py`
- Create: accepted run directories under `data/public/runs/`
- Create: `docs/reviews/2026-09-28-sm8650-x4-l2-calibration.md`
- Modify: `docs/open-items.md`
- Modify: `README.md`

1. Run base first, allow a thermal recovery interval if needed, then run THP.
   Each run uses `--environment-profile controlled-baseline --allow-mutation`.
2. Verify the durable governor transaction restored all policies after each
   run. A restore failure blocks the second run.
3. Add a deterministic analyzer that validates target/protocol/status, consumes
   per-sample observations, checks PMU running/enabled ratios, and groups by
   actual page backing.
4. Report per buffer: latency ns, measured cycles/load, L2D refill per 1000
   loads, L3D refill per 1000 loads, DTLB walks per 1000 loads, IQR/range, and
   admitted sample count. Keep raw counts available in run records.
5. Identify a transition interval only when latency/cycles and L2D refills move
   together across adjacent sizes and remain reproducible across repetitions.
   Compare base vs actual-THP cohorts to bound TLB influence.
6. Assign a confidence grade and explicitly list PFN coloring, replacement,
   undocumented event semantics, and uncore DVFS as residuals.
7. Update OI-11. If the private-L2 gate passes, the next plan is the minimal
   LLCC fd-broker plus outer L3/LLCC sweep; if it fails, refine only the private
   L2 experiment and continue to block outer-cache capacity claims.

Final verification before any completion claim:

```bash
ctest --preset macos-arm64-release --output-on-failure
ctest --preset macos-arm64-ubsan --output-on-failure
.venv/bin/python -m unittest discover -s runner/tests -t .
.venv/bin/python -m unittest discover -s analysis/tests -t .
git diff --check
git status --short
```

The ignored `raw/` directories remain local and SHA-256 anchored; only public
records/manifests/reports may be committed. Temporary Xeon/device binaries are
removed after accepted artifacts have been recorded.
