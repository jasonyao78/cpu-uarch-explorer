# SM8650 LLCC PMU userspace smoke implementation plan

> **Execution mode:** implement on `codex/sm8650-l2-pmu-calibration`; keep
> `codex/sm8650-cache-validation` and `main` unchanged. This gate must finish
> before the X4 L2 calibration matrix is admitted.

**Goal:** prove or falsify, with a minimal read-only userspace tool, that the
Redmi K70 Pro kernel's `llcc-pmu` accepts `config=0x1000` and returns a
repeatable response to memory-read traffic.

**Architecture:** add one Linux-only platform capability probe. It resolves a
PMU type from sysfs, opens one counting event through `perf_event_open`, binds
the process and event to a declared CPU/scope, records an immediate baseline,
runs a controlled idle or streaming-read workload, then records the final
count and reports the delta plus `time_enabled`/`time_running`. This phase does
not modify LLCC MMIO, does not integrate the counter into run-records, and does
not infer cache capacity.

**Tech stack:** C++17/Linux UAPI (`linux/perf_event.h`), CMake/CTest, existing
Xeon AArch64 static cross compiler, adb, Android 15/KernelSU.

---

## Evidence and design constraints

Live read-only inspection on 2026-09-27 established:

- `/sys/bus/event_source/devices/armv8_pmuv3/type = 8` and the kernel exports
  `l2d_cache_refill=0x17`, `l3d_cache_refill=0x2a`, `dtlb_walk=0x34`, and
  `cpu_cycles=0x11`;
- `/sys/bus/event_source/devices/llcc-pmu/type = 9`;
- this downstream LLCC PMU exports no `format/`, `events/`, or `cpumask` files;
- `/proc/sys/kernel/perf_event_paranoid = -1`, all CPUs 0-7 are online, and
  the driver is bound at `24095000.llcc-pmu`;
- Android has no `perf` executable, so shelling out to `perf stat` is not an
  available implementation path.

The Qualcomm downstream driver defines `LLCC_RD_EV=0x1000`, accepts only that
config, indexes the monitor by `event->cpu`, and may expose a cumulative
driver-side total. Therefore the smoke must use per-CPU mode
(`pid=-1,cpu=7`) and report `final - baseline`; it must not assume
`PERF_EVENT_IOC_RESET` zeroes the driver's private accumulator.

Primary references:

- Qualcomm downstream `qcom_llcc_pmu.c`:
  <https://android.googlesource.com/kernel/msm.git/+/90651f2c1e5de4d9359d216a41f94e6a24847404/drivers/perf/qcom_llcc_pmu.c>
- Linux `perf_event_open(2)` ABI:
  <https://man7.org/linux/man-pages/man2/perf_event_open.2.html>

---

## Task 1: Add the Linux-only probe and RED tests

**Files:**

- Create: `probes/platform/linux/CMakeLists.txt`
- Create: `probes/platform/linux/pmu_counter_smoke.cpp`
- Modify: `probes/platform/CMakeLists.txt`
- Modify: `tests/CMakeLists.txt`

1. Register `probes/platform/linux` only when
   `CMAKE_SYSTEM_NAME STREQUAL "Linux"`.
2. Add CTest cases that first fail because the target does not exist:
   malformed config, zero duration, invalid workload, and mutually invalid
   scope/CPU combinations must all exit nonzero without printing `status=ok`.
3. Implement strict CLI parsing:
   `--pmu <sysfs-name> --config <base-0 integer> --scope cpu|thread
   [--cpu N] --workload idle|stream-read --duration-ms N --buffer-mib N`.
4. Resolve the PMU type only from
   `/sys/bus/event_source/devices/<pmu>/type`; reject unsafe PMU names rather
   than accepting arbitrary paths.
5. Pin the process when `--cpu` is present. Open counting mode with
   `disabled=1` and
   `PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING`; do not set
   exclude filters because uncore PMUs may advertise `PERF_PMU_CAP_NO_EXCLUDE`.
6. Read baseline immediately after reset/enable, execute the workload, read
   final while still enabled, then disable. The read-before-disable order is
   required because the downstream LLCC driver updates `event->count` only
   while its private hw state is not stopped. Output one machine-readable line containing at
   least `status`, `pmu`, `type`, `config`, `scope`, `cpu`, `workload`,
   `count_initial`, `count_final`, `count_delta`, `time_enabled_ns`,
   `time_running_ns`, and `bytes_read`.
7. Preserve zero as a valid observation. Overflow, a decreasing cumulative
   count, short reads, affinity failure, or ioctl failure are hard errors.
8. Classify missing PMU/type and open-time
   `EACCES|EPERM|ENOENT|ENODEV|EOPNOTSUPP|EINVAL` as exit 2 with errno/stage in
   stderr; invalid CLI and runtime corruption use exit 1.

Verification:

```bash
cmake --preset macos-arm64-release
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release --output-on-failure
python3 -m unittest discover -s runner/tests -t .
python3 -m unittest discover -s analysis/tests -t .
```

macOS must remain unchanged because the Linux target is not configured there.

Commit:

```bash
git add probes/platform/CMakeLists.txt probes/platform/linux tests/CMakeLists.txt
git commit -m "feat(linux): add perf counter smoke probe"
```

---

## Task 2: Cross-build and run bounded device discrimination

1. Build the exact clean commit as a static AArch64 Linux executable on the
   Xeon and verify the local artifact hash before deployment.
2. Deploy to a temporary path under `/data/local/tmp/cpu-uarch/`; do not add a
   platform probe mapping or write under `data/` in this phase.
3. Run a core-PMU sanity check on CPU7 using `armv8_pmuv3/config=0x11` in
   thread scope. This separates a broken helper/perf ABI from an LLCC-specific
   failure.
4. Run the LLCC negative control `config=0x27`; preserve exact errno/stage and
   require unsupported rather than a false success.
5. Run paired blocks of idle and streaming-read with
   `llcc-pmu/config=0x1000`, CPU7, equal duration, and at least 10 fresh
   processes per condition. Keep the pair order alternating to reduce temporal
   bias. Each process uses a preallocated/pre-touched buffer and starts counting
   only after setup.
6. Acceptance requires every positive-control open/read to succeed,
   `time_running_ns > 0`, and the stream-read delta distribution to separate
   reproducibly from the paired idle floor. If counts remain zero or overlap,
   report `OPEN/INCONCLUSIVE`; do not write “LLCC has no event”.
7. The result proves only event responsiveness. It does not identify whether
   the count is CPU7-local, bank-local, global, read-miss-only, or suitable for
   occupancy/capacity inference.
8. Delete all temporary local, Xeon, and device artifacts after recording the
   acceptance summary in documentation.

---

## Task 3: Record the decision gate

**Files:**

- Modify: `probes/platform/README.md`
- Modify: `docs/open-items.md`
- Create: `docs/reviews/2026-09-27-sm8650-llcc-pmu-smoke.md`

Record:

- exact source commit and artifact SHA-256;
- tool arguments, CPU, duration, buffer size, sample count, user/security
  context, PMU sysfs types, and kernel version;
- all idle/load deltas or a compact table with immutable raw hashes;
- negative-control errno;
- what the smoke proves and explicitly does not prove;
- the next gate: design a separate Runner/record integration and X4 L2 matrix
  only after this smoke passes.

Commit:

```bash
git add probes/platform/README.md docs/open-items.md \
  docs/reviews/2026-09-27-sm8650-llcc-pmu-smoke.md
git commit -m "docs(sm8650): adjudicate LLCC PMU smoke"
```

Final verification:

```bash
ctest --preset macos-arm64-release --output-on-failure
ctest --preset macos-arm64-ubsan --output-on-failure
python3 -m unittest discover -s runner/tests -t .
python3 -m unittest discover -s analysis/tests -t .
git diff --check
git status --short
```
