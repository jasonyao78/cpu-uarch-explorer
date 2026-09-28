# SM8650 X4 demand/prefetch positive-control re-test (P0″) plan

> **Execution mode:** continue on `codex/sm8650-l2-pmu-calibration`, worktree
> `.worktrees/sm8650-l2-pmu-calibration`. LLCC stays locked; no outer-cache
> work. This plan exists because the external review (2026-09-28) rejected
> the previous adjudication chain: a post-hoc gate rewrite, an exclusive
> mechanism claim, an unsupported onset interval, and an erroneous geometry
> argument. **Acceptance rules below are pre-registered; if they fail, the
> result is `OPEN/INCONCLUSIVE` and the rules are NOT rewritten afterwards.**

**Goal:** establish (a) the mechanism of the 512→640 KiB transition
(hardware-prefetch coverage collapse vs replacement/resonance), and (b)
whether a stable, reproducible private-L2 capacity signal exists at all —
using demand/prefetch-separated PMU events, multiple ring seeds, two
training levels, and page-policy contrasts.

**Architecture:** same harness/environment as the accepted runs (CPU7
taskset, controlled-baseline governor transaction, 2 full-ring warmup
passes, 10 fresh processes per case, per-sample smaps audit, 6 events in
one window, no multiplexing). New degrees of freedom, all recorded per
sample: ring **seed** (new probe `-S` flag; 4 seeds), **training level**
(timed loads = fixed ring passes: 8 vs 512; no fixed total-loads floor),
and **page policy** (base everywhere; THP-request variant at >2 MiB,
grouped by actual backing). The analyzer is committed to the repo with
tests — no more ad-hoc scripts.

**Event set (6 = X4 programmable-counter budget, encodings verified against
ARM-software/data `pmu/cortex-x4.json`, TRM-derived):**

- `cycles` `0x11` — cycle.
- `mem_access_rd` `0x66` (impdef) — data memory read accesses (loads);
  excludes instruction fetches, CMOs, TTW, prefetches.
- `l1d_cache_miss` `0x8144` — L1 data cache **demand** access miss.
- `l1d_cache_hwprf` `0x8154` — L1 data cache hardware prefetch.
- `l2d_cache_miss` `0x814c` — L2 data cache **demand** access miss.
- `l2d_cache_hwprf` `0x8155` — L2 data cache hardware prefetch.

The generic `l2d_cache_refill (0x17)` is deliberately absent: its magnitude
was shown to be uninterpretable as a demand-miss meter on this part, and
this re-test relies only on demand/prefetch-separated events.

---

## Acceptance rules (pre-registered)

1. **Integrity:** 10 fresh processes per case; per-sample `seed`,
   `page_policy_actual`, and all six event counts recorded;
   `time_running == time_enabled` for every event/sample; environment
   pre/post gates valid; governor restores; thermal cutoff respected.
2. **Event sanity:** every event must show coherent counts somewhere in
   the matrix (no always-zero event across all regimes); any always-zero
   event → that event is `SEMANTICS-UNVERIFIED`, capacity inference stops.
3. **Mechanism discrimination (512→640 KiB), decided by `l1d_cache_hwprf`,
   not by narrative:**
   - prefetch-collapse: high `l1d_cache_hwprf` per load at ≤512 KiB
     collapsing toward ~0 by 640 KiB, with `l1d_cache_miss` rising
     complementarily, at **both** training levels and **all 4 seeds**;
   - replacement/resonance: `l1d_cache_hwprf` ≈ 0 throughout while
     `l1d_cache_miss` still jumps;
   - seed-dependent flip-flop between the two → address-pattern artifact;
     **neither mechanism is promoted**, result OPEN.
4. **Capacity signal admissibility:** a private-L2 capacity reading is
   admissible only if the `l2d_cache_miss` per-1k-loads curve is
   (a) regime-consistent across all 4 seeds (same regime, overlapping
   spreads), (b) regime-consistent between 8-pass and 512-pass training,
   and (c) at >2 MiB sizes, variance is explained by the actual-backing
   split (base vs mixed/thp). If any leg fails → OPEN/INCONCLUSIVE,
   no geometry argument substitutes for the data.
5. **Interpretation bounds:** demand-miss rates may be read as miss rates;
   prefetch counts describe prefetch activity, never "capacity"; absolute
   cross-run comparisons use anchors (512/1280/3072 KiB vs calibration and
   fine-sweep runs). DTS (`sm8650.dtsi`: CPU7 L2 = 2 MiB, Qualcomm-reviewed)
   and the running device's `/proc/device-tree` dump are logged as
   **platform evidence**, independent of this behavioral test.
6. **Reporting:** per-sample rows are published (committed analyzer
   output); medians never hide bimodality — any case whose per-sample
   spread crosses regimes is reported as bimodal, not averaged.

---

## Task 1: Probe gains a recorded seed

**Files:**

- Modify: `probes/cache-mem/ptr_chase.cpp`
- Modify: `runner/adapters/ptr_chase.py`
- Modify: `runner/plan.py` (only if sweep pass-through needs it)
- Modify: `runner/tests/test_plan.py`
- Modify: `runner/tests/test_ptr_chase_contract.py`
- Modify: `tests/CMakeLists.txt` (if C++-side CLI tests exist for ptr_chase)

1. RED tests: contract tests for `seed` param → `-S` argv; output `seed=N`
   lifted into metric metadata; distinct seeds produce distinct chains
   (latency-identical not required, chain differs — verified via
   deterministic construction: two seeds, same buffer, compare nothing but
   presence/parsing; chain difference is asserted C++-side if a harness
   exists there, else by construction review).
2. C++: add `-S seed` (uint64, default 42 — preserves every existing
   record's semantics), print `seed=N` in the key=value line, update the
   header comment (原理 §2 fixed-seed rationale + ABI line) and usage.
   Reject trailing garbage; `-S` with non-numeric input exits 1.
3. Adapter: pass `-S` when `seed` param present; parse `seed=` into the
   metric (so it lands in per-sample observations via the existing
   sample-varying metadata path). Update the module docstring's ABI block
   (comment discipline).
4. Sweep: `seed` is a declared int parameter; the existing
   `itertools.product` cross-product expands `buffer × seed` natively —
   no runner surgery expected; add plan tests proving 14×4 = 56 cases.

Verification:

```bash
ctest --preset macos-arm64-release --output-on-failure
ctest --preset macos-arm64-ubsan --output-on-failure
.venv/bin/python -m unittest discover -s runner/tests -t .
```

Commit:

```bash
git commit -m "feat(ptr-chase): add recorded ring seed"
```

## Task 2: Committed analyzer

**Files:**

- Create: `analysis/sm8650_x4_p0prime.py`
- Create: `analysis/tests/test_sm8650_x4_p0prime.py`

1. RED tests on synthetic records: per-sample rows emit
   `case_id, seed, page_policy_actual, loads, latency_ns, cyc_per_load,
   mem_access_rd/1k, l1d_miss/1k, l1d_hwprf/1k, l2d_miss/1k, l2d_hwprf/1k`;
   running≠enabled samples rejected; non-`ok` records skipped; grouping by
   (buffer, seed, backing, training) yields median/p25/p75/min/max plus a
   bimodality flag when sorted samples split across a regime threshold
   documented in the module docstring.
2. Implement against `records.jsonl` (schema v2 observations), CLI:
   `--run <dir>` repeatable, markdown table to stdout.
3. Keep `analysis/sm8650_l2.py` untouched (historical runs depend on it).

Commit:

```bash
git commit -m "feat(analysis): add P0″ per-sample demand/prefetch analyzer"
```

## Task 3: Four experiment configs + protocol guard

**Files:**

- Create: `configs/experiments/ptr-chase-sm8650-x4-p0prime-short-base.json`
- Create: `configs/experiments/ptr-chase-sm8650-x4-p0prime-long-base.json`
- Create: `configs/experiments/ptr-chase-sm8650-x4-p0prime-short-thp.json`
- Create: `configs/experiments/ptr-chase-sm8650-x4-p0prime-long-thp.json`
- Modify: `runner/tests/test_plan.py`

1. All: protocol 1.2, stride 64 B, `warmup_passes=2`, `repetitions=10`,
   controls `["x4-prime"]`, the 6-event set above.
2. short: `loads_per_slot=8`, `min_loads=4096` (floor below 8×slots at every
   swept size, so passes dominate); long: `loads_per_slot=512`,
   `min_loads=4096`.
3. base configs sweep `buffer`: `448, 512, 544, 576, 608, 640, 768, 1024,
   1216, 1408, 1792, 2048, 2304, 3072 KiB` × `seed`: `42, 7, 1337,
   20260928` = 56 cases; `base_pages=1`.
4. thp configs sweep only `2304, 3072 KiB` × same 4 seeds = 8 cases;
   `thp=1`; admission by actual backing (analyzer groups).
5. Extend the protocol/case-count guard in `test_plan.py` for the new
   prefix (`ptr-chase-sm8650-x4-p0prime-`, protocol 1.2, 56/56/8/8 cases).

Verification: plan previews show exact case counts; loads at 512 KiB =
8×8192 = 65,536 (short) and 512×8192 = 4,194,304 (long).

Commit:

```bash
git commit -m "config(sm8650): stage P0″ demand/prefetch matrix"
```

## Task 4: Cross-build, deploy, platform-geometry evidence

1. Build the exact clean commit on `xeon-8481c-01` with the AArch64 static
   cross preset; copy the artifact to the configured local deploy path;
   record SHA-256 (replaces the previous digest in new run manifests; old
   runs keep theirs).
2. Deploy through Runner so the device binary digest is manifest-anchored.
3. Geometry evidence (read-only, logged in the review, not baseline):
   - `adb shell 'ls /sys/devices/system/cpu/cpu7/cache/ 2>/dev/null'`
     (expected absent per OI-2 — record actual);
   - `adb shell 'su -c "find /proc/device-tree -path \"*l2*\" -name cache-size -o -path \"*cache*\" -name cache-size 2>/dev/null\"'`
     then dump each node's `cache-size`/`cache-line-size` for cpu7's L2 —
     the running kernel's own description (root, read-only).
4. One-process smoke of the new binary on CPU7 at 512 KiB with the 6
   events: all open, `running == enabled`, `seed=` echoed.

Commit: none (artifact/geometry go into the review; build trees stay
ignored).

## Task 5: Execute the matrix

Order: short-base → long-base → short-thp → long-thp; governor restore
verified (adb spot-check) between runs.

```bash
.venv/bin/python -m runner.cli run \
  --experiment configs/experiments/ptr-chase-sm8650-x4-p0prime-short-base.json \
  --platform configs/platforms/redmi-k70pro-01.json \
  --environment-profile controlled-baseline --allow-mutation
# … same for the other three configs
```

Schema-validate all records/artifacts with the ephemeral
`uv run --no-project --with jsonschema` flow; commit public
records/manifests:

```bash
git commit -m "data(sm8650): record P0″ demand/prefetch runs"
```

## Task 6: Adjudicate strictly by the pre-registered rules

**Files:**

- Create: `docs/reviews/2026-09-28-sm8650-x4-p0prime.md`
- Modify: `docs/open-items.md`
- Modify: `README.md` (only to the level the data earns; default is to
  keep OPEN/INCONCLUSIVE)

1. Run the committed analyzer on all four run dirs; publish the full
   per-sample tables (or a digest + the analyzer command to reproduce).
2. Rule 2 event sanity; rule 3 mechanism verdict (with the exact
   `l1d_cache_hwprf` numbers, both training levels, all seeds);
   rule 4 capacity admissibility; rule 6 bimodality audit.
3. If admissible: state the capacity reading as an observed interval with
   residuals and set against DTS = 2 MiB; if not admissible:
   OPEN/INCONCLUSIVE with the instability documented. Either way the
   private-L2 gate state is updated in OI-11; LLCC remains locked until
   the user explicitly unblocks it.
4. Final verification: ctest release+UBSan, runner/analysis tests,
   `git diff --check`, `git status --short`.

Commit:

```bash
git commit -m "docs(sm8650): adjudicate P0″ demand/prefetch re-test"
```
