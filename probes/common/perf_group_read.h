// SPDX-License-Identifier: Apache-2.0
// Linux GROUP+TIME_ENABLED+TIME_RUNNING+ID wire contract, C/C++ pure decoder.
// All requested IDs must occur exactly once. Never infer cycles from position.
#ifndef CPU_UARCH_PERF_GROUP_READ_H
#define CPU_UARCH_PERF_GROUP_READ_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define PG_MAX_EVENTS 8
struct pg_sample { uint64_t enabled, running, values[PG_MAX_EVENTS]; };
static inline const char *pg_decode(const uint64_t *wire, size_t words,
                                    const uint64_t *ids, size_t n,
                                    struct pg_sample *out) {
    if (!wire || !ids || !out || !n || n > PG_MAX_EVENTS || words < 3)
        return "group-invalid-input";
    if (wire[0] != n || words != 3 + 2*n) return "group-length-or-nr";
    struct pg_sample s; memset(&s, 0, sizeof(s));
    s.enabled = wire[1]; s.running = wire[2];
    if (s.running > s.enabled) return "group-time-inconsistent";
    unsigned seen = 0;
    for (size_t j = 0; j < n; ++j) {
        size_t k = 0;
        for (; k < n && ids[k] != wire[4 + 2*j]; ++k) {}
        if (k == n) return "group-unknown-id";
        if (seen & (1u << k)) return "group-duplicate-id";
        seen |= 1u << k; s.values[k] = wire[3 + 2*j];
    }
    if (seen != ((1u << n)-1)) return "group-missing-id";
    *out = s; return NULL;
}
// Times are cumulative across RESET; callers do not RESET between snapshots.
static inline const char *pg_delta(const struct pg_sample *a, const struct pg_sample *b,
                                   size_t n, struct pg_sample *out) {
    if (!a || !b || !out || !n || n > PG_MAX_EVENTS) return "delta-invalid-input";
    if (b->enabled < a->enabled || b->running < a->running) return "time-regressed";
    struct pg_sample d; memset(&d, 0, sizeof(d));
    d.enabled = b->enabled-a->enabled; d.running = b->running-a->running;
    if (!d.enabled) return "enabled-zero";
    if (d.running != d.enabled) return "mux-detected";
    for (size_t k=0; k<n; ++k) {
        if (b->values[k] < a->values[k]) return "value-regressed";
        d.values[k]=b->values[k]-a->values[k];
    }
    *out=d; return NULL;
}
#endif
