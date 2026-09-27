# SM8650 cache reverse-engineering handoff (2026-09-28)

This is an execution handoff for another coding agent. Read repository-root
`AGENTS.md` first. Treat every statement below as a checkpoint to verify, not
as an instruction to manufacture a preferred cache-size conclusion.

## User intent and non-negotiable boundaries

- Continue the SM8650/Redmi K70 Pro cache investigation until all currently
  feasible experiments are complete; return to `main` only after that.
- Work only in branch `codex/sm8650-l2-pmu-calibration` and worktree
  `/Users/michaelyao/workspace/cpu-uarch-explorer/.worktrees/sm8650-l2-pmu-calibration`.
- Do not merge, rebase, or modify `main`. Its user-owned state at handoff was:

  ```text
   M docs/design/ptr-chase-pipeline-analysis.md
  ?? data/public/runs/20260927T094438Z-ptr-chase-cache-sweep/
  ?? data/public/runs/20260927T094617Z-ptr-chase-slc-dense/
  ```

- Never promote a cache size from a latency curve alone. The private-L2 gate
  requires sample-aligned latency/cycles and independently meaningful L2 PMU
  evidence. Ambiguous results remain `OPEN/INCONCLUSIVE`.
- Keep raw samples ignored and local. Public records/manifests may be
  committed. Never commit real host addresses, device serials, secrets, or
  private/restricted data.
- Use `/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python`; this
  worktree intentionally has no separate `.venv`.

## Current branch checkpoint

Last data checkpoint before this handoff document: `9f7441b`
(`data(sm8650): record X4 L2 calibration runs`).
The coherent checkpoints added after the LLCC smoke adjudication are:

```text
184ccc3 docs(plan): stage SM8650 X4 L2 calibration
3d50314 feat(runner): preserve per-sample metric observations
5b2d592 feat(ptr-chase): add explicit base-page policy
04f99b4 feat(ptr-chase): sample core PMU in timed window
99c8c72 config(sm8650): define X4 L2 calibration matrix
2e5c757 feat(analysis): split SM8650 L2 samples by page backing
9f7441b data(sm8650): record X4 L2 calibration runs
```

The detailed accepted execution plan is
`docs/superpowers/plans/2026-09-28-sm8650-x4-l2-calibration.md`.

At the checkpoint, tracked files are clean. The following are intentionally
ignored local artifacts:

- both run directories' `raw/` trees (SHA-256 anchored by `artifacts.jsonl`);
- configured builds under `build/`;
- Python `__pycache__/` directories;
- private inventory under `data/private/`.

Do not delete raw data until the review is complete. A deployed probe may
still exist at `/data/local/tmp/cpu-uarch/ptr_chase`; remove it only after all
accepted experiments using the current artifact are finished.

## What is implemented and verified

- Runner retains every metric observation with `sample_index`, value, raw
  reference, and sample-varying metadata. It rejects metric-set drift.
- `ptr_chase -B` requests base pages through `MADV_NOHUGEPAGE` and audits
  actual backing through `/proc/self/smaps`.
- Linux core PMU events are opened per thread and bracket the exact timed
  dependent-load loop. Raw count plus enabled/running time is preserved;
  zero-running and malformed results fail.
- The calibration uses CPU7 (`x4-prime`), fixed governor transaction,
  16,777,216 timed loads, two full ring warmup passes, 10 fresh processes per
  case, and 14 sizes from 512 to 3072 KiB.
- Exact source commit used for the device artifact:
  `99c8c7241170de470414383bd98b7ad96cbc6a69`.
- Device/static artifact SHA-256:
  `c887bc7d094020fe3c57ad19f6aa3e573b7548f72be2967098d9257535c9de03`.
- Exact clean native Linux CTest passed 22/22 before execution. macOS release,
  UBSan, runner, and analysis suites passed at their implementation
  checkpoints.
- Both formal runs restored all policies to `walt`, left no unfinished
  environment journal, stayed below the thermal cutoff, and contain no failed
  case or multiplexed PMU sample.
- Schema validation after capture passed for all 28 run records and all 282
  artifact-manifest entries. If repeating it, use an ephemeral environment
  (`uv run --no-project --with jsonschema ...`) rather than creating a
  worktree-local `.venv`.

Accepted public runs:

```text
data/public/runs/20260927T175218Z-ptr-chase-sm8650-x4-l2-base/
data/public/runs/20260927T175405Z-ptr-chase-sm8650-x4-l2-thp/
```

Run the strict sample-aligned analysis with:

```bash
/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python \
  -m analysis.sm8650_l2 \
  --base data/public/runs/20260927T175218Z-ptr-chase-sm8650-x4-l2-base \
  --thp data/public/runs/20260927T175405Z-ptr-chase-sm8650-x4-l2-thp
```

## Evidence already extracted

All values below are medians. Counts are normalized per 1,000 timed loads.
The base-page cohort is internally very stable except where the IQR noted in
the analyzer is broad.

| Buffer KiB | Latency ns | Cycles/load | L2 refill/1k | L3 refill/1k | DTLB walk/1k |
|---:|---:|---:|---:|---:|---:|
| 512 | 2.389 | 6.556 | 0.218 | 0.014 | 0.011 |
| 640 | 4.435 | 12.169 | 0.314 | 0.017 | 0.016 |
| 768 | 4.884 | 13.400 | 4.890 | 0.020 | 0.017 |
| 1024 | 5.107 | 14.013 | 0.992 | 0.020 | 0.018 |
| 1152 | 5.436 | 14.915 | 15.000 | 0.016 | 0.020 |
| 1280 | 5.596 | 15.354 | 22.489 | 0.019 | 0.020 |
| 1536 | 5.696 | 15.627 | 22.324 | 0.018 | 0.016 |
| 2048 | 6.097 | 16.725 | 43.472 | 0.027 | 0.020 |
| 3072 | 6.601 | 18.105 | 68.280 | 0.025 | 0.019 |

The THP request did not produce full-THP mappings. Sizes through 2048 KiB
were all base-backed; larger sizes produced a mix of base and a 2048 KiB
`AnonHugePages` region. Never use the case-level aggregate at those sizes.

| Buffer KiB | Actual backing | n | Latency ns | Cycles/load | L2 refill/1k |
|---:|---|---:|---:|---:|---:|
| 2304 | base | 9 | 6.191 | 16.987 | 46.616 |
| 2304 | mixed | 1 | 4.199 | 11.515 | 24.050 |
| 2560 | base | 6 | 6.372 | 17.475 | 56.194 |
| 2560 | mixed | 4 | 4.505 | 12.355 | 39.281 |
| 2816 | base | 6 | 6.487 | 17.796 | 61.672 |
| 2816 | mixed | 4 | 4.769 | 13.080 | 49.863 |
| 3072 | base | 5 | 6.589 | 18.073 | 68.476 |
| 3072 | mixed | 5 | 4.938 | 13.543 | 55.769 |

## Current adjudication — do not overstate it

1. **Measurement integrity: high.** Process repetition, backing audit,
   environment restore, artifact lineage, same-window cycles, and absence of
   multiplexing are all directly recorded.
2. **The 512→640 KiB latency/cycle transition is real and repeatable**, but it
   is **not yet an L2-capacity transition**: latency and cycles rise about
   1.86x while L2 refills remain near zero (0.218→0.314 per 1,000). It fails
   the plan's own coupled-evidence acceptance rule.
3. **L2 refill starts rising materially around 1–1.25 MiB and then grows
   gradually**, not as a clean cliff. This may reflect event semantics,
   replacement/coloring, or a distributed capacity effect; it is not enough
   to declare 1 MiB or 2 MiB.
4. **Mixed THP backing materially changes the path** above 2 MiB, reducing
   both latency and L2 refill rate. This confirms that requested-page cohorts
   must be split by actual backing, but does not by itself identify whether
   the cause is TLB, coloring, allocation, or cache residency.
5. The measured DTLB-walk and L3-refill rates are extremely small throughout.
   Their raw event semantics on this implementation need a positive-control
   calibration before they can exclude those mechanisms with high confidence.
6. Therefore the X4 private-L2 size remains **OPEN/INCONCLUSIVE**. Do not write
   “512 KiB”, “1 MiB”, or “2 MiB” as a fact.

## Recommended next execution order

### P0 — positive-control the PMU event semantics

Before a finer capacity sweep, add a small diagnostic matrix that proves the
architected raw events behave as assumed on CPU7. Verify the event encodings
against the applicable Arm PMUv3 architectural documentation first. A useful
four-event set is the L1D refill/access and L2D access/refill pair (commonly
architected as `0x03`, `0x04`, `0x16`, `0x17`), with deliberately tiny L1-fit
and clearly L1-overflow working sets. Do not treat those encodings as verified
merely because they are listed here.

Acceptance for the positive control:

- an L1-fit case has a low steady-state L1 refill rate;
- an L1-overflow dependent chain produces coherent L1 refill and L2 access
  counts on the scale implied by the timed load count;
- L2 refill remains low for an unambiguously L2-resident case;
- all events have `running == enabled` and stable ratios across 10 processes.

If the positive control fails, stop capacity inference and investigate the
PMU mapping/semantics. A counter that opens and increments is not necessarily
evidence for the event name assigned to it.

### P1 — refine only the unresolved private-L2 region

If P0 passes, run a base-page sweep with denser points around both observed
features, e.g. 448–800 KiB in 32/64 KiB steps and 896–1408 KiB in 64 KiB
steps. Keep the same CPU, frequency transaction, process count, timed loads,
warmup-pass semantics, and page audit. Include the positive-control access and
refill events if the hardware counter budget permits without multiplexing;
otherwise split event groups into paired adjacent runs.

The purpose is to distinguish:

- a 512 KiB structural latency effect with no L2 misses;
- the onset and slope of verified L2 refills near/above 1 MiB;
- page/color sensitivity across fresh processes.

Do not widen to outer-cache sizes until this gate is adjudicated.

### P2 — outer cache only after the private-L2 gate

The earlier LLCC smoke evidence is in
`docs/reviews/2026-09-27-sm8650-llcc-pmu-smoke.md`. Core PMU type 8 works as
ordinary shell; LLCC type 9/config `0x1000` requires root and cleanly separates
idle/load in the smoke. Preserve the architecture decision: keep `ptr_chase`
unprivileged and add only a minimal root LLCC fd-broker/sidecar for the later
L3/LLCC phase. Do not run the whole experiment as root.

### P3 — close and clean only after accepted evidence is committed

- write `docs/reviews/2026-09-28-sm8650-x4-l2-calibration.md` with explicit
  claim grades and residuals;
- update `docs/open-items.md` and README only to the level supported by data;
- run release CTest, UBSan CTest, runner tests, analysis tests, schema
  validation, `git diff --check`, and inspect `git status`;
- remove temporary/device binaries only after manifests and reports are
  durable; raw data may remain local and ignored;
- keep this branch separate until the user explicitly approves returning to
  the main line.

## Device/run safety reminder

Use the repository environment controller and `controlled-baseline`; do not
copy an ad-hoc “pure state” shell recipe without checking every command. The
formal runs already proved transactional governor restoration. Inspect
preflight state before mutation, reject camera/screen/thermal/journal gate
failures, and verify post-run restore. Do not stop thermal protection merely
to reduce variance.

Useful planning command:

```bash
/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python \
  -m runner.cli plan \
  --experiment configs/experiments/ptr-chase-sm8650-x4-l2-base.json \
  --platform configs/platforms/redmi-k70pro-01.json \
  --environment-profile controlled-baseline
```

## First command for the receiving agent

```bash
cd /Users/michaelyao/workspace/cpu-uarch-explorer/.worktrees/sm8650-l2-pmu-calibration
git status --short
git log -8 --oneline
/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python \
  -m unittest discover -s analysis/tests -t .
```

If the last data checkpoint, worktree state, or recorded source/artifact
lineage differs, investigate the drift before editing or running another
device experiment.
