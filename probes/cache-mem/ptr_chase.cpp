// SPDX-License-Identifier: Apache-2.0
// ptr_chase: pointer-chase memory latency probe (clean-room implementation).
//
// Replaces the legacy lmbench-derived demo; provenance and rationale:
//   docs/adr/ADR-0002-license-apache2.md
//
// Methodology (public knowledge, independent implementation):
//   A buffer is divided into slots spaced `stride` bytes apart and linked
//   into one cycle ordered by a Fisher-Yates shuffled permutation. Chasing
//   the cycle for N dependent loads and dividing elapsed monotonic time by N
//   gives average dependent-load latency. The random order defeats stride
//   prefetchers. The chase is a SINGLE dependent chain: loop-control overhead
//   is amortized by unrolling the same chain 8x per iteration — the 8 loads
//   stay strictly dependent, so no extra memory-level parallelism is
//   introduced (multiple independent chains would divide latency by the
//   achievable MLP and corrupt the measurement; do not add them).
//
// Output: key=value lines (machine-parseable) on stdout.

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <random>
#include <unistd.h>
#include <sys/mman.h>

namespace {

double now_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return static_cast<double>(ts.tv_sec) * 1e9 + static_cast<double>(ts.tv_nsec);
}

void usage(const char* prog) {
    std::fprintf(stderr,
        "usage: %s -b KB -s stride_bytes [-n loads] [-w warmup_loads]\n"
        "  -b  buffer size in KB            (default 8192)\n"
        "  -s  stride between chain slots  (default 64)\n"
        "  -n  total dependent loads       (default 268435456)\n"
        "  -w  warmup loads                (default 200000)\n",
        prog);
}

} // namespace

int main(int argc, char** argv) {
    size_t buffer_kb = 8192;
    size_t stride = 64;
    long long loads = 268435456; // 2^28
    long long warmup = 200000;

    int opt;
    while ((opt = getopt(argc, argv, "b:s:n:w:")) != -1) {
        switch (opt) {
        case 'b': buffer_kb = std::strtoull(optarg, nullptr, 10); break;
        case 's': stride = std::strtoull(optarg, nullptr, 10); break;
        case 'n': loads = std::strtoll(optarg, nullptr, 10); break;
        case 'w': warmup = std::strtoll(optarg, nullptr, 10); break;
        default: usage(argv[0]); return 1;
        }
    }

    if (stride < sizeof(char*) || buffer_kb == 0 || loads <= 0) {
        usage(argv[0]);
        return 1;
    }

    constexpr int kUnroll = 8; // same-chain unroll: keeps loads dependent
    const size_t bytes = buffer_kb * 1024;
    const size_t slots = bytes / stride;
    loads -= loads % kUnroll;

    char* buf = static_cast<char*>(mmap(nullptr, bytes, PROT_READ | PROT_WRITE,
                                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
    if (buf == MAP_FAILED) {
        std::perror("mmap");
        return 1;
    }

    // Fisher-Yates shuffle of slot indices with a fixed seed for reproducibility.
    size_t* perm = static_cast<size_t*>(malloc(slots * sizeof(size_t)));
    if (!perm) {
        std::perror("malloc");
        return 1;
    }
    for (size_t i = 0; i < slots; ++i) perm[i] = i;
    std::mt19937_64 rng(42);
    for (size_t i = slots - 1; i > 0; --i) {
        size_t j = static_cast<size_t>(rng() % (i + 1));
        size_t t = perm[i]; perm[i] = perm[j]; perm[j] = t;
    }

    // Link the whole buffer into a single random cycle.
    for (size_t i = 0; i + 1 < slots; ++i)
        *reinterpret_cast<char**>(buf + perm[i] * stride) = buf + perm[i + 1] * stride;
    *reinterpret_cast<char**>(buf + perm[slots - 1] * stride) = buf + perm[0] * stride;

    // Warm-up: settle TLB and cache state.
    char* p = buf + perm[0] * stride;
    for (long long i = 0; i < warmup; ++i)
        p = *reinterpret_cast<char**>(p);

    const double t0 = now_ns();
    const long long iters = loads / kUnroll;
    for (long long i = 0; i < iters; ++i) {
        p = *reinterpret_cast<char**>(p);
        p = *reinterpret_cast<char**>(p);
        p = *reinterpret_cast<char**>(p);
        p = *reinterpret_cast<char**>(p);
        p = *reinterpret_cast<char**>(p);
        p = *reinterpret_cast<char**>(p);
        p = *reinterpret_cast<char**>(p);
        p = *reinterpret_cast<char**>(p);
    }
    const double t1 = now_ns();

    // Volatile sink: the chase result must be materialized, so the loads
    // above cannot be optimized away.
    volatile uintptr_t sink = reinterpret_cast<uintptr_t>(p);
    (void)sink;

    const double elapsed = t1 - t0;
    const double latency = elapsed / static_cast<double>(loads);

    std::printf("buffer_kb=%zu stride=%zu loads=%lld elapsed_ns=%.0f latency_ns=%.4f\n",
                buffer_kb, stride, loads, elapsed, latency);

    free(perm);
    munmap(buf, bytes);
    return 0;
}
