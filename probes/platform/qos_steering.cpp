// SPDX-License-Identifier: Apache-2.0
// qos_steering: verify QoS-to-cluster steering on Apple Silicon by measuring
// bimodal per-core throughput at different QoS classes. A serial LCG chain is
// latency-bound, so per-iteration time directly reflects the core type the
// thread is steered to (P core ~2x faster than E core on M4 class chips).
// Capability discovery for the macos-arm64 backend.

#include <cstdio>
#include <cstdint>
#include <pthread.h>
#include <sys/qos.h>
#include <mach/mach_time.h>

static double now_ns() {
    static double ns_per_tick = 0;
    if (ns_per_tick == 0) {
        mach_timebase_info_data_t tb;
        mach_timebase_info(&tb);
        ns_per_tick = static_cast<double>(tb.numer) / tb.denom;
    }
    const uint64_t t = mach_absolute_time();
    return t * ns_per_tick;
}

static double run_once(long long iters) {
    volatile uint64_t x = 0x1234567887654321ULL;
    const double t0 = now_ns();
    for (long long i = 0; i < iters; ++i)
        x = x * 6364136223846793005ULL + 1442695040888963407ULL;
    const double t1 = now_ns();
    if (x == 1) std::printf("unreachable\n"); // sink
    return (t1 - t0) / iters;
}

static void probe(const char* name, qos_class_t q) {
    const int rc = pthread_set_qos_class_self_np(q, 0);
    double best = 1e30;
    for (int r = 0; r < 3; ++r) {
        const double v = run_once(200000000);
        if (v < best) best = v;
    }
    std::printf("qos=%-22s set_rc=%d ns_per_iter_best=%.4f\n", name, rc, best);
}

int main() {
    std::printf("# qos steering probe (bimodal => steering works; ratio ~2 => P:E)\n");
    probe("USER_INTERACTIVE", QOS_CLASS_USER_INTERACTIVE);
    probe("DEFAULT", QOS_CLASS_DEFAULT);
    probe("BACKGROUND", QOS_CLASS_BACKGROUND);
    probe("USER_INTERACTIVE(2nd)", QOS_CLASS_USER_INTERACTIVE);
    return 0;
}
