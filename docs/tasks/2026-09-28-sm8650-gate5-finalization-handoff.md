# SM8650 Gate 5 finalization handoff (2026-09-28)

This document hands the final review and push of the SM8650 private-L2/PMU
calibration branch to another coding agent. Read repository-root `AGENTS.md`
first. Verify this checkpoint against Git before acting; do not manufacture a
cache-capacity conclusion merely to close the branch.

## Mission and boundaries

- Work only in branch `codex/sm8650-l2-pmu-calibration` and worktree
  `/Users/michaelyao/workspace/cpu-uarch-explorer/.worktrees/sm8650-l2-pmu-calibration`.
- Do not modify, merge into, rebase, reset, or clean `main`.
- Review and, if necessary, fix only the Gate 5 delta described below. Keep
  any fix in a focused commit and rerun the tests affected by it.
- Do not rerun completed SM8650/device experiments. No scientific result in
  this branch currently requires another device run for branch closure.
- Do not merge this branch or archive/remove its worktree. After a clean
  review, push the feature branch to `origin` and report the verdict to the
  primary agent/user; integration is a separate decision.
- Preserve ignored raw samples and private inventory. Never commit device
  serials, real host addresses, secrets, or private/restricted data.

## Git checkpoint

At handoff creation, the worktree is clean and `HEAD` is:

```text
ef6dda4 chore(git): sync main into SM8650 calibration
```

The branch is six commits ahead of its then-current remote branch
`origin/codex/sm8650-l2-pmu-calibration` at `2ed7ab4`. The relevant commits
after that remote checkpoint are:

```text
002fd04 docs(sm8650): plan Gate 5 remediation
1d7003f docs(sm8650): correct P0-prime evidence ledger
c0f19b4 fix(ptr-chase): audit backing across measurement window
407535a docs(reference): clarify archive provenance
4c08c91 data(quarantine): archive 2026-09-27 manual-differential runs (from main)
ef6dda4 chore(git): sync main into SM8650 calibration
```

This handoff document will add one further documentation commit. Confirm the
actual `HEAD`, divergence, and clean status rather than assuming these hashes
remain current.

## Gate 5 findings already remediated

1. The P0-prime evidence ledger and report now include all six formal runs:
   156 records, 115 successful records, 41 structured failures, 1,166
   artifacts, and three recorded ceiling-drift episodes. The run at
   `20260928T122738Z` is no longer omitted.
2. Residual text no longer calls the unproven condition a thermal clamp. It is
   recorded as dynamic cpufreq ceiling drift with root cause `OPEN`.
3. `ptr_chase` audits Linux anonymous-memory backing at both ends of the
   measurement window: after warmup/before timed and PMU collection, and
   after timed and PMU collection. A changed endpoint class or
   `AnonHugePages` value fails before emitting measurements. The output and
   runner contract preserve both observations and the legacy summary fields.
4. The documentation explicitly says endpoint equality is only a discrete
   observation. It does not prove that no transient promotion or demotion
   happened inside the timed interval.
5. Reference-material provenance now describes repository-owner-directed
   work that may include human and agent collaboration; it makes no unsupported
   sole-natural-person authorship claim. The recorded owner authorization is
   the Apache-2.0 inclusion basis.
6. Exact path-level `.gitattributes` exceptions preserve two byte-exact
   Markdown archives without disabling whitespace checks repository-wide.
7. The private X4 L2 capacity remains `OPEN/INCONCLUSIVE`. THP rule 4c is
   indefinitely deferred with an explicit reopen trigger. Only L3/LLCC
   capacity adjudication is blocked; orthogonal microarchitecture work may
   proceed.

The design and implementation plans are:

- `docs/superpowers/specs/2026-09-28-sm8650-gate5-remediation-design.md`
- `docs/superpowers/plans/2026-09-28-sm8650-gate5-remediation.md`

## Verification evidence already obtained

Do not repeat expensive work merely for ceremony. Review the changed code and
rerun only a cheap gate or a test affected by a new fix.

### macOS arm64, fresh after the backing-audit change

```text
Release CTest: 17/17 passed
UBSan CTest:   18/18 passed
runner tests:  138/138 passed
analysis tests: 21/21 passed
```

The backing-contract change was developed red-to-green. The rebuilt probe
passed 22 contract tests; legacy captured output remains accepted, while a
partially populated or inconsistent new endpoint contract is rejected.

### Linux Xeon

The normal remote checkout `~/cpu-uarch-explorer` was deliberately left
untouched because it contained user-owned local state. The branch was synced
with `rsync -a --delete`, excluding `build/`, `.DS_Store`, and `.git`, into:

```text
/tmp/cpu-uarch-explorer-sm8650-gate5-c0f19b4
```

The isolated copy produced:

```text
Linux CTest:   25/25 passed
runner tests:  138 passed, 22 skipped by platform contract
analysis tests: 21/21 passed
```

There is no `linux-x86_64-release` CTest preset. The valid command is:

```bash
ctest --test-dir build/linux-x86_64/release --output-on-failure
```

A real Linux base-page invocation emitted a stable endpoint contract:

```text
page_policy_actual=base anon_huge_kb=0 \
page_policy_actual_before=base page_policy_actual_after=base \
anon_huge_kb_before=0 anon_huge_kb_after=0 \
page_backing_endpoints_equal=1
```

### Data and archive integrity

Full validation across public runs completed with:

```text
runs=11 records=212 artifacts=1731 raw_hashes=1720 errors=0
```

The validation required every record's probe SHA-256 to match a
`probe-binary` artifact. A `manifest_ref` was checked when present but was not
incorrectly required for legacy records.

The three reference archives also matched their recorded originals byte for
byte. Recorded SHA-256 prefixes are `012574`, `ed9668`, and `26bd61`.

## Required receiving-agent procedure

1. Inspect `git status --short --branch`, `git log --oneline --decorate -12`,
   and `git diff --check main...HEAD`.
2. Perform an independent review of `main...HEAD`, prioritizing:
   - cleanup and failure paths surrounding the two backing observations in
     `probes/cache-mem/ptr_chase.cpp`;
   - `printf` format/argument correctness and no metric emission after a
     failed backing audit;
   - legacy/new output parsing invariants in `runner/adapters/ptr_chase.py`;
   - schema documentation and test coverage for every new output field;
   - scientific wording: association must not become capacity or root-cause
     proof;
   - provenance/license wording and the narrowness of `.gitattributes`.
3. If a Critical/P1 defect is found, fix it test-first, make a focused commit,
   and rerun the directly affected suite plus `git diff --check`. Do not widen
   scope into new experiments or general refactoring.
4. If the review is clean, or after verified fixes, push
   `codex/sm8650-l2-pmu-calibration` to `origin` and verify that local and
   remote branch tips match.
5. Return a concise verdict containing findings, fixes if any, exact tests
   run, final commit, remote synchronization status, and residual risks.

## Known residuals that do not block branch closure

- Endpoint backing equality cannot observe transient changes entirely inside
  the timed interval. No automated test currently forces such an in-window
  transition; the limitation is documented rather than hidden.
- The private X4 L2 capacity is not identified. A failed scientific
  adjudication is not an implementation failure and must not keep this branch
  alive indefinitely.
- Dynamic cpufreq ceiling drift has no established root cause. Its recurrence,
  trigger, and escalation options are tracked in `docs/open-items.md`.
- L3/LLCC capacity inference remains blocked by the unresolved private-L2
  model. LLCC tooling/PMU validation may proceed, but it must not be presented
  as a capacity result.

## Recommended mainline continuation after integration

After formal review, integration, full testing on `main`, and push, retire the
worktree and branch according to `AGENTS.md` rule 7. Then continue with an
orthogonal microarchitecture topic rather than reopening the same L2 sweep.
The recommended first topic is the TLB hierarchy: `dtlb_walk` semantics already
have a positive control, and useful TLB questions do not require an exact L2
capacity. Branch prediction, frontend, execution-port/throughput, MLP, and
cross-core migration are also unblocked if they preserve the same evidence
discipline.
