# SM8650 Gate 5 Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four Gate 5 review findings and convert unresolved L2 capacity into a bounded, non-global blocker.

**Architecture:** Preserve the existing ptr_chase ABI fields and add a measurement-window backing audit around the timed region. Evidence documents are regenerated from committed runs; wording and provenance are reduced to claims supported by the repository evidence.

**Tech Stack:** C++17/POSIX, Linux `/proc/self/smaps`, Python unittest, CMake/CTest, JSON schema v2, Git.

---

### Task 1: Freeze the accepted repair design

**Files:**
- Create: `docs/superpowers/specs/2026-09-28-sm8650-gate5-remediation-design.md`
- Create: `docs/superpowers/plans/2026-09-28-sm8650-gate5-remediation.md`

- [ ] **Step 1:** Check the design for placeholders, contradictions, scope expansion, and missing review findings.
- [ ] **Step 2:** Run `git diff --check` on the two new files; expect no output.
- [ ] **Step 3:** Commit only the design and plan with `docs(sm8650): plan Gate 5 remediation`.

### Task 2: Repair the committed evidence ledger

**Files:**
- Modify: `docs/reviews/2026-09-28-sm8650-x4-p0prime.md`
- Regenerate: `docs/reviews/2026-09-28-sm8650-x4-p0prime-analysis.md`
- Modify: `docs/runbooks/redmi-manet-freq-control-chain.md`
- Modify: `configs/experiments/ptr-chase-sm8650-x4-p0prime-long-base-r2a.json`
- Modify: `configs/experiments/ptr-chase-sm8650-x4-p0prime-long-base-r2b.json`
- Modify: `docs/open-items.md`

- [ ] **Step 1:** Run the analyzer on all six committed P0″ run directories and verify that the generated body contains 41 rejected records, including all eight records from `20260928T122738Z`.
- [ ] **Step 2:** Replace the generated report body and update its reproducibility header with all six run paths.
- [ ] **Step 3:** Correct the review ledger to 6/156/115/41/1166 and three drift incidents; change “all cases valid” to “accepted cases valid.”
- [ ] **Step 4:** Replace residual “thermal clamp” causal labels with “dynamic cpufreq ceiling drift”; keep the root cause OPEN.
- [ ] **Step 5:** Change causal shorthand for the 512→640 KiB transition to an accompanied-by statement and record the mainline dependency-slicing rule in OI-11.
- [ ] **Step 6:** Run analysis tests and a script that independently recounts the six runs; expect exact agreement.
- [ ] **Step 7:** Commit this evidence-only scope as `docs(sm8650): correct P0-prime evidence ledger`.

### Task 3: Add measurement-window page-backing endpoint audit

**Files:**
- Modify: `runner/tests/test_ptr_chase_contract.py`
- Modify: `runner/adapters/ptr_chase.py`
- Modify: `probes/cache-mem/ptr_chase.cpp`
- Modify: `probes/cache-mem/README.md`
- Modify: `docs/methodology/measurement-discipline.md`
- Modify: `runner/schema/README.md`

- [ ] **Step 1 (RED):** Add parser tests requiring the five new fields to be all-or-none, validating `page_backing_endpoints_equal == 1`, and rejecting inconsistent before/after values. Run the targeted unittest and confirm failure because the parser ignores the new audit group.
- [ ] **Step 2 (GREEN):** Parse and preserve the new fields while continuing to accept legacy captured output without them. Run the targeted unittest and confirm pass.
- [ ] **Step 3 (RED):** Extend the real-binary contract test to require the paired fields on successful output. Rebuild nothing and confirm the test fails against the old binary.
- [ ] **Step 4 (GREEN):** Move the Linux first observation to after warmup, add the after-window observation, fail with exit 1 before stdout metrics if either observation fails or differs, and emit the equal-endpoint audit group on success. Keep the snapshots outside the timed/PMU interval.
- [ ] **Step 5:** Rebuild Release and run the contract test; expect the new real-binary assertion to pass.
- [ ] **Step 6:** Update source/module comments, probe README, measurement discipline, and schema registry with the exact observation semantics.
- [ ] **Step 7:** Run Release CTest, UBSan CTest, and all runner tests.
- [ ] **Step 8:** Commit as `fix(ptr-chase): audit backing across measurement window`.

### Task 4: Resolve provenance and byte-exact whitespace handling

**Files:**
- Modify: `docs/reference-materials/README.md`
- Modify: `docs/reference-materials.md`
- Modify: `.gitattributes`

- [ ] **Step 1:** Normalize provenance to “repository-owner-directed work with possible agent assistance” and cite the recorded owner decision as the Apache-2.0 authorization basis; do not claim sole natural-person authorship.
- [ ] **Step 2:** Add exact path-level `whitespace=-blank-at-eol` attributes for the two archives whose original bytes contain Markdown hard-break spaces.
- [ ] **Step 3:** Recompute SHA-256 against `../cpu-uarch-ref`, then run `git diff --check main...HEAD`; expect exact hashes and no whitespace diagnostics.
- [ ] **Step 4:** Commit as `docs(reference): clarify archive provenance`.

### Task 5: Linux/Xeon and repository-wide verification

**Files:** none expected beyond test artifacts ignored by Git.

- [ ] **Step 1:** Sync the branch checkout to an isolated Xeon directory with `rsync -a --delete --exclude build/ --exclude .DS_Store`.
- [ ] **Step 2:** Configure/build Linux x86-64 Release, run CTest and runner/analysis unit tests, and execute a real `ptr_chase -B` sample; require equal paired backing fields.
- [ ] **Step 3:** On macOS rerun Release CTest, UBSan CTest, runner tests, analysis tests, all-branch schema/hash/reference integrity, `git diff --check main...HEAD`, and clean-tree checks.
- [ ] **Step 4:** Push the current feature branch. Do not merge or modify `main`; submit the fresh evidence for formal review.
