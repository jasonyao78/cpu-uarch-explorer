/* SPDX-License-Identifier: Apache-2.0
 * Explicit v2 finite attempts with raw invalid-window retention.
 * docs/design/2026-10-13-pmu-bounded-counter.md. No same-window retry.
 */
#define CPU_UARCH_PMU_BOUNDED 1
#include "pmu_own_counter.c"
