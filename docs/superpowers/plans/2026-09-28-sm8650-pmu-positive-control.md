# SM8650 core-PMU positive-control (event semantics) plan

> **Execution mode:** continue on `codex/sm8650-l2-pmu-calibration`, worktree
> `.worktrees/sm8650-l2-pmu-calibration`. Keep `main` and the other SM8650
> branches unchanged. No probe or runner code changes are expected: the probe
> already accepts runtime `--pmu-event label:type:config` (≤16 events). Commit
> each coherent checkpoint, and run the device matrix only from a clean commit.

**Goal:** prove — or falsify — that the architected core-PMU raw events used
for the SM8650 X4 cache investigation count what their names claim on CPU7,
before any finer private-L2 capacity sweep (P1) is interpreted.

**Architecture:** reuse the existing unprivileged `ptr_chase` harness, the
`controlled-baseline` environment transaction, and per-thread perf-event
counting in the exact timed window. Add two new experiment configs only: a
cache-semantics group (6 events, at the X4's 6-programmable-counter budget)
and a small TLB-semantics group (3 events). Working sets are chosen so the
expected count scale of each event is known a priori from first principles.

**Why this sequence:** the X4 L2 calibration (runs
`20260927T175218Z-…-base` / `20260927T175405Z-…-thp`) showed a 512→640 KiB
latency/cycles step with near-zero L2D refill, and a gradual refill rise from
~1–1.25 MiB instead of a cliff. Whether that falsifies a 512 KiB capacity
reading or reveals event-semantics artifacts is undecidable until the events
are positively controlled. A counter that opens and increments is not evidence
for the event name assigned to it — blind raw-event testing on other Qualcomm
devices has produced always-zero `0x03` counters
(<https://bbs.kanxue.com/thread-291487.htm>). If this control fails, capacity
inference stops and the PMU mapping/semantics are investigated instead.

**Event-encoding evidence (verified 2026-09-28):** ARM-software/data
`pmu/cortex-x4.json` (TRM-derived, timestamp 2025-01-17,
<https://raw.githubusercontent.com/ARM-software/data/master/pmu/cortex-x4.json>)
states `counters: 6` and defines, for the Cortex-X4 (armv9.2-a, PMUv3):

- `0x03 L1D_CACHE_REFILL`: load/store/TTW causing data read from outside L1,
  including non-allocating accesses; excludes cache maintenance and prefetches.
- `0x04 L1D_CACHE`: any load/store/TTW looking up L1D; every REFILL-able
  access counts.
- `0x05 L1D_TLB_REFILL`: L1 data TLB refill from the MMUTC.
- `0x11 CPU_CYCLES`: cycle.
- `0x16 L2D_CACHE`: per-core L2 configuration — transactions from L1 looking
  up L2, plus L1 writebacks; snoops/CMOs excluded.
- `0x17 L2D_CACHE_REFILL`: Cacheable transaction from L1 causing data read
  from outside the core; L2 stash refills not counted.
- `0x2a L3D_CACHE_REFILL`: cacheable read returning data from the SCU whose
  source was outside the cluster.
- `0x34 DTLB_WALK`: data TLB access causing at least one translation table
  walk; counts on any data access that counts L2D_TLB_REFILL.

The architected encodings match the common-event table used by independent
tooling (Arm PMU blog, <https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/profile-firmware-with-performance-monitor-unit-in-armv8-a-cpu>;
windowsperf alias list, <https://github.com/arm-developer-tools/windowsperf/blob/main/wperf/README.md>).

---

## Acceptance rules

The positive control passes only if all of the following hold:

1. **L1-fit:** for the 16/32 KiB base-page cases (X4 L1D = 64 KiB per the
   platform baseline), steady-state `l1d_cache_refill` is low relative to
   `l1d_cache` (order ≤ a few per 1,000 timed loads after 2 full warmup ring
   passes), while `l1d_cache` ≈ 1,000 per 1,000 loads (every dependent load
   looks up L1).
2. **L1-overflow:** for the 512 KiB base-page case, `l1d_cache_refill` and
   `l2d_cache` land on the scale implied by the timed load count — with a
   64 B stride every load touches an independent random 64 B line, so a
   random-replacement estimate gives ≈ 1 − 64/512 ≈ 875 refills per 1,000
   loads; order-of-magnitude agreement (hundreds per 1,000) is required, not
   an exact figure.
3. **L2-resident:** for the same 512 KiB case, `l2d_cache_refill` stays low
   (≈ the 0.218/1,000 measured in the accepted calibration run), and for the
   8 MiB case `l2d_cache_refill` rises to the hundreds-per-1,000 scale (a
   1–4 MiB private L2 against an 8 MiB random ring implies ≥ 50 % miss).
4. **L3/DTLB scale anchors:** for the 16 MiB case, `l3d_cache_refill` (cache
   group) and `dtlb_walk` (TLB group, 4,096 random 4 KiB pages) leave the
   near-zero regime measured at ≤ 3 MiB; for the 512 KiB TLB case `dtlb_walk`
   stays near zero.
5. **No multiplexing, stable ratios:** every admitted sample has
   `time_running_ns == time_enabled_ns` for every event; per-case event
   ratios are stable across the 10 fresh processes (IQR reported; broad-IQR
   cases are flagged, not silently averaged).
6. **Measurement integrity:** 10 fresh processes per case, actual page
   backing `base` per sample, environment pre/post gates pass, governor
   transaction restores, thermal cutoff respected.

If any rule fails, retain runs for audit, mark the affected event
`SEMANTICS-UNVERIFIED`, stop capacity inference, and investigate the PMU
mapping instead of proceeding to P1. No number from this plan is a cache
capacity result.

---

## Task 1: Cache-semantics positive-control config

**Files:**

- Create: `configs/experiments/ptr-chase-sm8650-x4-pmu-ctrl-cache.json`

1. Clone the structure of `configs/experiments/ptr-chase-sm8650-x4-l2-base.json`
   (protocol `1.2`, stride 64 B, `warmup_passes=2`, `min_loads=16777216`,
   `repetitions=10`, `base_pages=1`, controls `["x4-prime"]`).
2. Sweep exactly: `16KiB, 32KiB, 512KiB, 8MiB, 16MiB`.
3. Event set (type 8, exactly 6 = the X4 programmable-counter budget):
   `cycles` `0x11`, `l1d_cache_refill` `0x03`, `l1d_cache` `0x04`,
   `l2d_cache` `0x16`, `l2d_cache_refill` `0x17`, `l3d_cache_refill` `0x2a`.
4. Preconditions require: controlled-baseline gates; all six events in one
   window with `time_running == time_enabled`; every repetition a fresh
   process with actual backing `base`.
5. Notes must state this is an event-semantics control, not a capacity
   experiment.

Verification:

```bash
/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m runner.cli plan \
  --experiment configs/experiments/ptr-chase-sm8650-x4-pmu-ctrl-cache.json \
  --platform configs/platforms/redmi-k70pro-01.json \
  --environment-profile controlled-baseline
```

Expected: exactly 5 cases × 10 repetitions, all on `x4-prime`.

Commit:

```bash
git commit -m "config(sm8650): stage PMU cache-event positive control"
```

---

## Task 2: Manual one-process preflight from adb shell (smoke only)

The deployed probe is unchanged and digest-anchored
(`c887bc7d094020fe3c57ad19f6aa3e573b7548f72be2967098d9257535c9de03`); no
rebuild or redeploy is needed.

1. From adb shell, on CPU7 via `taskset 80`, run one process each of
   32 KiB and 8 MiB, base pages, small load count, with all six events:

```bash
adb shell 'cd /data/local/tmp/cpu-uarch && taskset 80 ./ptr_chase -b 32 -s 64 -n 1000000 -B \
  --pmu-event cycles:8:0x11 --pmu-event l1d_cache_refill:8:0x03 \
  --pmu-event l1d_cache:8:0x04 --pmu-event l2d_cache:8:0x16 \
  --pmu-event l2d_cache_refill:8:0x17 --pmu-event l3d_cache_refill:8:0x2a'
adb shell 'cd /data/local/tmp/cpu-uarch && taskset 80 ./ptr_chase -b 8192 -s 64 -n 1000000 -B \
  --pmu-event cycles:8:0x11 --pmu-event l1d_cache_refill:8:0x03 \
  --pmu-event l1d_cache:8:0x04 --pmu-event l2d_cache:8:0x16 \
  --pmu-event l2d_cache_refill:8:0x17 --pmu-event l3d_cache_refill:8:0x2a'
```

2. Require: all six events open; `time_running == time_enabled` for each;
   32 KiB shows `l1d_cache` ≈ 1,000,000-scale with small refill; 8 MiB shows
   refill/access counts on the hundreds-per-1,000 scale.
3. If any event multiplexes or reads always-zero at both scales, stop: record
   the observation, do not run the formal matrix, adjudicate
   `SEMANTICS-UNVERIFIED` for that event, and reduce/split the event set only
   in a documented second preflight.

No preflight number is a result; the governor is not transacted for this
smoke, so only count scales and running/enabled ratios are checked.

---

## Task 3: TLB-semantics positive-control config

**Files:**

- Create: `configs/experiments/ptr-chase-sm8650-x4-pmu-ctrl-tlb.json`

1. Same protocol/loop semantics as Task 1.
2. Sweep exactly: `512KiB, 16MiB`.
3. Event set (type 8): `cycles` `0x11`, `l1d_tlb_refill` `0x05`,
   `dtlb_walk` `0x34`.

Verification: plan preview shows exactly 2 cases × 10 repetitions.

Commit:

```bash
git commit -m "config(sm8650): stage PMU TLB-event positive control"
```

---

## Task 4: Execute both formal runs

```bash
/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m runner.cli run \
  --experiment configs/experiments/ptr-chase-sm8650-x4-pmu-ctrl-cache.json \
  --platform configs/platforms/redmi-k70pro-01.json \
  --environment-profile controlled-baseline --allow-mutation
/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m runner.cli run \
  --experiment configs/experiments/ptr-chase-sm8650-x4-pmu-ctrl-tlb.json \
  --platform configs/platforms/redmi-k70pro-01.json \
  --environment-profile controlled-baseline --allow-mutation
```

1. Run the cache group first, confirm governor restore, then the TLB group.
2. Verify: no failed case, `time_running == time_enabled` on every sample,
   environment journal clean, all policies back to `walt`, thermal cutoff
   untouched.
3. Schema-validate the new run records with an ephemeral environment
   (`uv run --no-project --with jsonschema …`), never a worktree-local venv.

Commit public records/manifests (raw/ stays ignored and local):

```bash
git commit -m "data(sm8650): record PMU positive-control runs"
```

---

## Task 5: Adjudicate and archive

**Files:**

- Create: `docs/reviews/2026-09-28-sm8650-pmu-positive-control.md`
- Modify: `docs/open-items.md`

1. Extract per-case medians/IQRs from `records.jsonl` with an ad-hoc
   read-only script (no new committed analyzer; P1 tooling decisions wait for
   the P1 plan). Normalize counts per 1,000 timed loads.
2. Grade each acceptance rule pass/fail with the actual numbers; list
   residuals (event-definition nuances such as prefetch exclusion, MMUTC
   behavior, replacement policy, uncore DVFS).
3. Verdict wording: events are `SEMANTICS-VERIFIED` only for the regimes
   actually exercised; near-zero readings at unexercised scales remain open.
4. Update OI-11 with the verdict and the P1 gate state. README stays
   unchanged at this stage (no capacity claim is being made).
5. If all rules pass, the P1 fine sweep plan (448–800 KiB @ 32/64 KiB steps,
   896–1408 KiB @ 64 KiB steps, per the handoff) is the next plan; if any
   rule fails, capacity inference stops and the failure mode is investigated.

Final verification before any completion claim:

```bash
ctest --preset macos-arm64-release --output-on-failure
.venv/bin/python -m unittest discover -s runner/tests -t .
.venv/bin/python -m unittest discover -s analysis/tests -t .
git diff --check
git status --short
```

Commit:

```bash
git commit -m "docs(sm8650): adjudicate PMU positive control"
```
