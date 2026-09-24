// SPDX-License-Identifier: Apache-2.0
// timer_resolution: measure mach_absolute_time timebase, effective
// resolution, and per-call overhead. Capability discovery for the
// macos-arm64 backend (runner/targets will reuse this).

#include <cstdio>
#include <cstdint>
#include <mach/mach_time.h>

int main() {
    mach_timebase_info_data_t tb;
    mach_timebase_info(&tb);
    const double ns_per_tick = static_cast<double>(tb.numer) / tb.denom;
    std::printf("timebase numer=%u denom=%u (1 tick = %.6f ns)\n",
                tb.numer, tb.denom, ns_per_tick);

    const int SAMPLES = 1000000;
    uint64_t prev = mach_absolute_time();
    uint64_t min_delta = ~0ULL, max_delta = 0;
    long long zero_deltas = 0;
    for (int i = 0; i < SAMPLES; ++i) {
        const uint64_t t = mach_absolute_time();
        const uint64_t d = t - prev;
        if (d == 0) {
            ++zero_deltas;
        } else {
            if (d < min_delta) min_delta = d;
            if (d > max_delta) max_delta = d;
        }
        prev = t;
    }
    std::printf("samples=%d zero_delta=%lld (%.1f%%) min_delta=%llu ticks (%.2f ns) max_delta=%llu ticks\n",
                SAMPLES, zero_deltas, 100.0 * zero_deltas / SAMPLES,
                min_delta, min_delta * ns_per_tick, max_delta);

    const int ROUNDS = 5, CALLS = 10000000;
    double best = 1e30;
    for (int r = 0; r < ROUNDS; ++r) {
        const uint64_t t0 = mach_absolute_time();
        uint64_t acc = 0;
        for (int i = 0; i < CALLS; ++i) acc += mach_absolute_time();
        const uint64_t t1 = mach_absolute_time();
        const double per = (t1 - t0) * ns_per_tick / CALLS;
        if (per < best) best = per;
        if (acc == 42) std::printf("unreachable\n"); // sink
    }
    std::printf("call_overhead_best_ns=%.2f (%d calls x %d rounds)\n", best, CALLS, ROUNDS);
    return 0;
}
