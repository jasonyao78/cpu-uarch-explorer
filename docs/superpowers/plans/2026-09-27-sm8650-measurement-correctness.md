# SM8650 Measurement Correctness Implementation Plan

> **For Codex:** Execute this plan task-by-task in an isolated worktree. Use test-driven development for every behavior change: add the failing test, run it and observe the expected failure, implement the minimum change, then rerun the focused test. Do not collect new SM8650 capacity data in this plan.

**Goal:** Remove unsupported SM8650 cache conclusions from current documentation and make `ptr_chase` warmup and Linux THP backing auditable before any new capacity experiment.

**Architecture:** Keep the probe ABI backward-compatible: `-w` remains an exact load count, while the Runner derives it from a new `warmup_passes` experiment parameter. Add an orthogonal Linux-only `-T` THP request and report requested versus observed backing; retain `-h/-H` for explicit hugetlb mappings. Historical run records remain immutable and are downgraded by a separate evidence reassessment document.

**Tech Stack:** C++17/POSIX probe, CMake/CTest, Python 3 stdlib Runner and `unittest`, JSON ExperimentSpec/platform configuration, Markdown evidence ledger.

**Design authority:** `docs/superpowers/specs/2026-09-27-sm8650-cache-evidence-revalidation-design.md`

**Non-goals:** Android quiet-state controllers, PMU collection, X4 L2 calibration runs, L3/LLCC runs, camera interference, multi-chain/MLP probes, rewriting historical JSONL artifacts.

---

## Task 1: Correct the repository's current SM8650 evidence claims

**Files:**

- Create: `docs/reviews/2026-09-27-sm8650-cache-evidence-reassessment.md`
- Modify: `configs/platforms/redmi-k70pro-01.json`
- Modify: `docs/open-items.md`
- Modify: `probes/cache-mem/README.md`
- Modify: `docs/methodology/measurement-discipline.md`
- Modify: `docs/requirements/CHANGELOG.md`
- Do not modify: `docs/design/ptr-chase-pipeline-analysis.md`
- Do not modify: `data/public/runs/**`

### Step 1: Capture the contradiction set before editing

Run:

```bash
rg -n "L2=1M|L2.*1 MiB|无 per-cluster L3|末级=LLCC|静态保护份额|PMU.*零事件|12MB.*定案|12MB.*有效容量|相机.*LLCC|scaling_cur_freq" \
  configs/platforms/redmi-k70pro-01.json docs/open-items.md \
  probes/cache-mem/README.md docs/methodology/measurement-discipline.md \
  docs/requirements/CHANGELOG.md
```

Expected: matches include the current X4 L2=1 MiB, no-CPU-L3/merged-SLC, protected-share, and LLCC-PMU-unavailable claims.

### Step 2: Write the reassessment ledger

Create a table with these columns:

```text
claim | previous status | direct evidence | confounder/contradiction | new status | next discriminator
```

Cover at minimum:

- platform baseline: X4 L2 2 MiB, A720 L2 512 KiB/core, A520 L2 512 KiB/pair, shared CPU L3 12 MiB, separate LLCC;
- fixed `warmup=200000` traverses only about 12.2 MiB at 64-byte stride;
- tracked SM8650 runs `20260927T060512Z`, `075007Z`, `082635Z`, and `083827Z` are preserved as observations but excluded from capacity calibration;
- untracked runs `20260927T094438Z` and `094617Z` are explicitly outside this change and are not adjudicated as repository evidence;
- X4 transition between 512 KiB and 1 MiB is an observation, not a 1 MiB capacity result;
- A520 32 MiB latency instability is an observation, not an outstanding-miss or QoS mechanism result;
- `config=0x00..0x27` returning `ENOENT` did not test Qualcomm's downstream `config=0x1000` event;
- `scaling_cur_freq` and integer-looking converted cycles do not prove actual clock frequency;
- random logical permutation does not remove PFN/color or PIPT set/bank effects;
- the one-off camera differential is rejected, not evidence of LLCC stealing.

Link the primary sources already listed in the design authority. Give every claim one of `PLATFORM_BASELINE`, `MEASUREMENT_FACT`, `HYPOTHESIS`, `REJECTED`, or `OPEN`.

### Step 3: Replace current-facing claims without rewriting history

In `redmi-k70pro-01.json`, replace the monolithic `capabilities_note` with a concise note that:

- preserves measured topology, cpufreq domains, root and PMU registration facts;
- records the sourced cache hierarchy baseline;
- labels the four tracked SM8650 runs as methodologically confounded by fixed warmup and 4 KiB/TLB or backing uncertainty;
- states that `type=9` is registered but `config=0x1000` remains untested;
- states that `scaling_cur_freq` is a reported cpufreq value, not actual-frequency proof;
- removes final X4/A520 capacity, protected-share, merged-L3/SLC, and camera mechanism claims.

Update OI-11 to make the next gate: measurement fixes → X4 L2 calibration → CPU/LLCC PMU → L3/LLCC and interference. Move direct-MMIO/LKM behind userspace `config=0x1000` and core-PMU failure.

In `probes/cache-mem/README.md`, mark older dated conclusions as superseded by the reassessment rather than deleting their historical text. Correct the backlog to include THP actual-backing verification and the userspace LLCC PMU event.

In `measurement-discipline.md`, add rules that ns is primary; converted cycles carry a frequency source; logical randomization is not physical-color control; requested page policy and actual backing are separate fields.

Append a correction entry to `CHANGELOG.md`; do not edit previous dated entries.

### Step 4: Validate the documentation-only change

Run:

```bash
python3 -m json.tool configs/platforms/redmi-k70pro-01.json >/dev/null
rg -n "L2=1M|无 per-cluster L3|末级=LLCC|静态保护份额.*实证|PMU 已注册.*零事件" \
  configs/platforms/redmi-k70pro-01.json docs/open-items.md probes/cache-mem/README.md
git diff --check
git diff --name-only
```

Expected: JSON parses; remaining historical phrases, if any, are adjacent to an explicit `SUPERSEDED`/“已纠偏” marker; only the six intended documentation/config files plus the new reassessment are changed.

### Step 5: Commit the evidence correction

```bash
git add configs/platforms/redmi-k70pro-01.json \
  docs/reviews/2026-09-27-sm8650-cache-evidence-reassessment.md \
  docs/open-items.md probes/cache-mem/README.md \
  docs/methodology/measurement-discipline.md docs/requirements/CHANGELOG.md
git diff --cached --name-only
git diff --cached --check
git commit -m "docs(sm8650): reopen cache hierarchy conclusions"
```

---

## Task 2: Derive warmup loads from complete ring passes in the Runner

**Files:**

- Modify: `runner/tests/test_plan.py`
- Modify: `runner/plan.py`

### Step 1: Add failing plan tests

Add tests using a spec with `warmup_passes=2` and buffers 4 MiB, 12 MiB, and 32 MiB at stride 64 B. Assert:

```python
self.assertEqual(by_buffer[4096].param_value("warmup"), 2 * 4096 * 1024 // 64)
self.assertEqual(by_buffer[12288].param_value("warmup"), 2 * 12288 * 1024 // 64)
self.assertEqual(by_buffer[32768].param_value("warmup"), 2 * 32768 * 1024 // 64)
self.assertEqual(by_buffer[4096].param_value("warmup_passes"), 2)
self.assertEqual(dict(by_buffer[4096].params)["warmup"].source, "derived")
```

Also add independent tests that reject:

- `warmup_passes=-1`;
- both `warmup` and `warmup_passes` in resolved fixed parameters;
- a derived load count greater than signed 64-bit max;

and a compatibility test proving a legacy spec with only `warmup=1000` still emits exactly 1000 loads with its original provenance.

### Step 2: Run the focused tests and observe failure

Run:

```bash
python3 -m unittest runner.tests.test_plan -v
```

Expected: new pass-derived tests fail because `runner/plan.py` still defaults to 200,000 exact loads and has no conflict/overflow checks.

### Step 3: Implement the minimum derivation

In `runner/plan.py`:

- define `MAX_PROBE_LOADS = (1 << 63) - 1`;
- resolve all names in `fixed_params` as today;
- after `slots` is known, inspect whether `warmup` and/or `warmup_passes` are present in resolved params;
- reject both being present;
- for `warmup_passes`, require integer `>= 1`, compute `warmup = passes * slots`, reject `> MAX_PROBE_LOADS`, and emit both `warmup_passes` with original provenance and `warmup` with `derived` provenance;
- for legacy `warmup`, require integer `>= 0`, preserve the exact value and source, and do not synthesize `warmup_passes`;
- reject a ptr-chase experiment declaring neither instead of silently reintroducing a fixed default.

Do not change the adapter ABI in this task: it still receives exact `warmup` loads.

### Step 4: Rerun focused and Runner suites

```bash
python3 -m unittest runner.tests.test_plan -v
python3 -m unittest discover -s runner/tests -t .
```

Expected: all tests pass.

---

## Task 3: Make the direct probe default two full passes and expose effective warmup

**Files:**

- Modify: `tests/CMakeLists.txt`
- Modify: `runner/tests/test_ptr_chase_contract.py`
- Modify: `probes/cache-mem/ptr_chase.cpp`
- Modify: `runner/adapters/ptr_chase.py`

### Step 1: Add failing ABI tests

Add CTest assertions for a 64 KiB/64 B ring:

- no `-w`: `warmup_loads=2048`, `warmup_passes_effective=2.000000`, `warmup_state=warm`;
- `-w 1000`: `warmup_loads=1000`, `warmup_passes_effective=0.976562`;
- `-w 0`: `warmup_state=cold-warm0`.

Extend the real-binary contract test to assert that the parser preserves:

```python
metric["warmup_loads"] == 1000
metric["warmup_passes_effective"] == 1000 / 1024
metric["warmup_state"] == "warm"
```

Add a parser-only test that rejects non-finite `warmup_passes_effective` and non-integer/negative `warmup_loads`.

### Step 2: Run tests and observe failure

```bash
cmake --preset macos-arm64-release
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release --output-on-failure
python3 -m unittest runner.tests.test_ptr_chase_contract -v
```

Expected: the new output-field assertions fail because the probe emits none of them.

### Step 3: Implement probe warmup semantics

In `ptr_chase.cpp`:

- use a sentinel (for example `std::optional<long long>`) to distinguish omitted `-w` from explicit `-w 0`;
- compute slots first, then set omitted warmup to `2 * slots`, with signed-64-bit overflow validation;
- preserve explicit `-w N` exactly;
- output `warmup_loads`, `warmup_passes_effective` with six decimals, and `warmup_state=warm|cold-warm0`;
- update usage and top-of-file ABI comments;
- keep `-w` as an exact-load option, so old commands remain replayable.

In `PtrChaseAdapter.parse_output`, parse and validate the three optional fields and attach them to the latency metric. Keep accepting old captured output that lacks the new fields. Update `protocol_version` to `1.1` only after the experiment configs are migrated in Task 4.

### Step 4: Rerun focused tests

```bash
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release --output-on-failure
python3 -m unittest runner.tests.test_ptr_chase_contract -v
```

Expected: all focused tests pass.

---

## Task 4: Migrate current ptr-chase ExperimentSpecs and close the contract

**Files:**

- Modify: `configs/experiments/ptr-chase-cache-sweep.json`
- Modify: `configs/experiments/ptr-chase-cache-sweep-hp2m.json`
- Modify: `configs/experiments/ptr-chase-l3-boundary-hp2m.json`
- Modify: `configs/experiments/ptr-chase-slc-dense.json`
- Modify: `runner/adapters/ptr_chase.py`
- Modify: `runner/tests/test_ptr_chase_contract.py`
- Modify: `runner/tests/test_cli.py` if plan snapshots assert exact parameters

### Step 1: Add a configuration contract test

Add a test that loads every `configs/experiments/ptr-chase*.json`, builds a plan against a minimal ptr-chase platform, and asserts:

- `protocol_version == "1.1"`;
- current specs declare `warmup_passes` and do not declare legacy `warmup`;
- every case contains derived `warmup` and explicit `warmup_passes`;
- `warmup / slots == warmup_passes` exactly.

### Step 2: Run and observe failure

```bash
python3 -m unittest discover -s runner/tests -t .
```

Expected: the configuration contract fails because current specs still declare `warmup=200000` and protocol 1.0.

### Step 3: Migrate specs

For all four ptr-chase specs:

- replace the `warmup` parameter with integer `warmup_passes`, default 2;
- replace `warmup` with `warmup_passes` in `fixed_params`;
- bump protocol version to `1.1`;
- correct notes that treat 2 MiB hugetlb as a universal Linux requirement;
- retitle `ptr-chase-slc-dense` as a shared CPU L3/outer-cache boundary sweep without asserting a single SLC level;
- mark `ptr-chase-l3-boundary-hp2m` as a historical/non-SM8650 profile rather than a current SM8650 64–128 MiB L3 assumption.

Set `PtrChaseAdapter.protocol_version = "1.1"` and update its docstring.

### Step 4: Validate plan output and test suite

Run each migrated configuration through the CLI using an existing local platform config. Inspect at least the smallest and largest cases:

```bash
python3 -m runner.cli plan --experiment configs/experiments/ptr-chase-cache-sweep.json \
  --platform configs/platforms/macbook-m4pro-01.json
python3 -m unittest discover -s runner/tests -t .
git diff --check
```

Expected: warmup is exactly two ring traversals for every buffer and all Runner tests pass.

### Step 5: Commit warmup changes

Stage only the probe, Runner, tests, and four migrated specs. Verify staged filenames before committing:

```bash
git add probes/cache-mem/ptr_chase.cpp tests/CMakeLists.txt \
  runner/plan.py runner/adapters/ptr_chase.py \
  runner/tests/test_plan.py runner/tests/test_ptr_chase_contract.py \
  runner/tests/test_cli.py configs/experiments/ptr-chase-cache-sweep.json \
  configs/experiments/ptr-chase-cache-sweep-hp2m.json \
  configs/experiments/ptr-chase-l3-boundary-hp2m.json \
  configs/experiments/ptr-chase-slc-dense.json
git diff --cached --name-only
git diff --cached --check
git commit -m "fix(ptr-chase): derive warmup from full ring passes"
```

If `runner/tests/test_cli.py` did not require changes, do not stage it.

---

## Task 5: Add Linux THP request and actual-backing reporting

**Files:**

- Modify: `tests/CMakeLists.txt`
- Modify: `runner/tests/test_ptr_chase_contract.py`
- Modify: `probes/cache-mem/ptr_chase.cpp`
- Modify: `runner/adapters/ptr_chase.py`
- Modify: `runner/plan.py`
- Modify: `runner/tests/test_plan.py`
- Modify: `configs/experiments/ptr-chase-cache-sweep-hp2m.json`
- Modify: `configs/experiments/ptr-chase-l3-boundary-hp2m.json`
- Modify: `probes/cache-mem/README.md`
- Modify: `docs/methodology/measurement-discipline.md`

### Step 1: Add failing page-policy tests

Define the ABI:

```text
-T                         request Linux MADV_HUGEPAGE
page_policy_requested=default|hugetlb-fallback|hugetlb-strict|thp-madvise
page_policy_actual=platform-default|base|thp|mixed|hugetlb-2m
anon_huge_kb=<non-negative integer>
page_policy=<legacy summary retained for compatibility>
page_kb=<legacy field retained for compatibility>
```

Add tests that:

- reject simultaneous `-T` and `-h/-H` as an input error;
- on macOS, return exit code 2 for `-T` and emit no latency record;
- on Linux, accept `-T` and output requested `thp-madvise`, non-negative `anon_huge_kb`, and actual `base|thp|mixed` without requiring THP allocation to succeed;
- preserve `-h/-H` behavior;
- make the adapter pass `-T` for `thp=1`, reject `thp=1` plus `hugepage=1`, and preserve all requested/actual fields in the metric;
- reject malformed actual-backing values and negative/non-integer `anon_huge_kb`.

### Step 2: Run focused tests and observe failure

```bash
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release --output-on-failure
python3 -m unittest runner.tests.test_plan runner.tests.test_ptr_chase_contract -v
```

Expected: `-T` and the new fields are not implemented.

### Step 3: Implement THP request and Linux backing inspection

In `ptr_chase.cpp`:

- compile `MADV_HUGEPAGE` code only on Linux; non-Linux `-T` exits 2;
- allocate normal anonymous memory, call `madvise(buf, bytes, MADV_HUGEPAGE)` before first touch, and return an explicit environment error if madvise itself fails;
- after the ring is fully written/touched, parse `/proc/self/smaps` mappings overlapping `[buf, buf + map_bytes)` and sum `AnonHugePages`;
- classify `base` for zero huge KB, `thp` when huge backing covers the target mapping, and `mixed` for partial coverage;
- fail rather than fabricate actual backing when `/proc/self/smaps` cannot be read on a requested-THP run;
- for explicit successful hugetlb mmap, report `hugetlb-2m` independently of `AnonHugePages`;
- for non-Linux default mappings, report `platform-default` rather than claiming 4 KiB actual pages.

Keep requested policy and actual backing separate. Do not label a successful `madvise` call as `thp` unless smaps confirms backing.

In the Runner, accept optional integer `thp` in plan/adapter, require `0|1`, and reject a case that requests both `thp` and `hugepage`.

### Step 4: Migrate the misleading hp2m specs

For the Android-relevant hp2m configurations, replace `hugepage=1` with `thp=1`, update titles/preconditions/notes, and state that acceptance depends on `page_policy_actual`, not the request. Preserve explicit hugetlb coverage in probe tests; do not claim current SM8650 supports hugetlb.

### Step 5: Rerun tests

```bash
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release --output-on-failure
python3 -m unittest discover -s runner/tests -t .
python3 -m unittest discover -s analysis/tests -t .
```

Expected: macOS unsupported path and all portable contracts pass. Linux success-path acceptance remains part of the Linux/Android build gate; no real capacity sweep is run.

### Step 6: Commit THP correctness

```bash
git add probes/cache-mem/ptr_chase.cpp probes/cache-mem/README.md \
  tests/CMakeLists.txt runner/plan.py runner/adapters/ptr_chase.py \
  runner/tests/test_plan.py runner/tests/test_ptr_chase_contract.py \
  configs/experiments/ptr-chase-cache-sweep-hp2m.json \
  configs/experiments/ptr-chase-l3-boundary-hp2m.json \
  docs/methodology/measurement-discipline.md
git diff --cached --name-only
git diff --cached --check
git commit -m "feat(ptr-chase): report requested and actual THP backing"
```

---

## Task 6: Full verification and handoff gate

**Files:**

- Modify only if needed by verified failures in the files already scoped above.

### Step 1: Run the repository-prescribed suites

```bash
cmake --preset macos-arm64-release
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release --output-on-failure
python3 -m unittest discover -s runner/tests -t .
python3 -m unittest discover -s analysis/tests -t .
```

### Step 2: Run UBSan

Configure the repository's UBSan option in a separate build tree/preset-supported invocation, build `ptr_chase`, and run its CTest target. Record the exact command and result in the final handoff.

### Step 3: Recheck scope and history integrity

```bash
git status --short
git diff --check
git log --oneline --decorate -6
git diff main...HEAD --name-only
git diff main...HEAD -- data/public/runs docs/design/ptr-chase-pipeline-analysis.md
```

Expected: no differences under historical run data or the user's pre-existing analysis document; the branch contains exactly the evidence-correction, warmup, and THP commits.

### Step 4: Stop before data collection

Do not run Android sweeps. The next plan begins with transactional controlled-quiet-state v2, followed by PMU observability and the X4 512 KiB–3 MiB calibration gate.
