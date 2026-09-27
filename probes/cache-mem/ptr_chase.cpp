// SPDX-License-Identifier: Apache-2.0
// ptr_chase: 指针追逐内存延迟探针（clean-room 实现，替代历史 lmbench 衍生
// demo；谱系与原因见 docs/adr/ADR-0002-license-apache2.md）。
// 纯 POSIX，跨平台可移植，属"测什么"类探针而非平台特定探针。
//
// 技术原理
// --------
// 1. 为什么用指针追逐测延迟
//    缓冲区内按固定 stride 切槽位，每个槽位存放下一个槽位的地址，形成
//    一条循环链。沿链追逐时，每次 load 的地址都来自上一次 load 的结果，
//    依赖链强制访存级并行度（MLP）= 1——测得的是"单次依赖 load 的
//    真实延迟"，而不是带宽或并发能力。
//
// 2. 为什么链要随机化（Fisher–Yates 洗牌 + 固定种子）
//    顺序或固定步长的访问模式会被硬件 stride prefetcher 预测并预取，
//    预取掩盖真实延迟，测量结果系统性偏低。随机排列让预取器无从预测，
//    迫使每次访问都真实走完存储层次。固定种子（42）保证链结构可复现。
//    使用 std::uniform_int_distribution 保证置换无偏（裸取模会引入
//    模偏差，量级虽小但注释与实现必须一致）。
//
// 3. 为什么必须是单链，且同链展开 8 次（曾经的坑，已修正）
//    - 多链反例：早期版本用 4 条独立环链分摊循环开销，但独立链 = 4 个
//      并行 load，实测延迟被 MLP 摊薄近 4 倍（L1 测出 0.42 ns，荒谬）。
//      教训：任何引入额外并行性的"优化"都会改变被测量本身。
//    - 同链展开：循环控制（计数、比较、跳转）每迭代约 1~2 周期，在 L1
//      尺度（~5 周期）上不可忽略。把同一条链展开 8 次，8 个 load 仍严格
//      串行，开销被摊薄 8 倍，且不引入任何并行性。
//
// 4. 计时口径（与平台能力探针的结论联动）
//    macOS 计时器有效分辨率 41.67 ns（见 probes/platform/macos-arm64/
//    timer_resolution），单次计时区间必须装下足够多的 load：L1 按 ~1 ns/
//    load 计，-n 默认值 2^28 使区间长达百毫秒级，量化噪声被平均到
//    1e-4 以下。统计量取"总时间/load 总数"，不逐 load 计时。
//
// 5. 防优化三重保障
//    mmap 真实内存（编译器不可见内容）＋ 链上 load 有真实数据依赖 ＋
//    结束后把指针写入 volatile sink（结果必须物化，追逐不可被消除）。
//
// 6. 输入校验与退出码（Probe ABI 约定，ADR-0006）
//    非法输入一律 stderr 说明 + 退出码 1，**绝不静默产出无效记录**
//    （nan/inf 会污染实验数据库）。退出码语义：0=成功，1=输入/环境错误，
//    2=能力不支持（保留）。校验项：stride 为指针宽度的整数倍、
//    loads ≥ 展开因子、槽位数 ≥ 2。
//
// 附加：hugepage 支持（-h / -H；measurement-discipline §2 落地）
//    Linux 正式测量须用 2MB hugepage：① 4K 页在工作集超出 TLB 覆盖后
//    每档叠加页遍历开销，把 LLC 平台期拉成斜坡；② buddy 分配器给出的
//    4K 物理页布局可能不均，随机链在 L3 set 上冲突（2026-09-25 Xeon
//    实测：96MiB 档 5 次重复内双峰 60ns vs 108-141ns，铁证）。2MB 大页
//    同时缓解两者。`-h` 缺页池时回退 4K 并在输出标注 fallback（显式
//    标注纪律）；`-H` 严格模式缺页池直接退出码 2（能力不支持）。
//    macOS 无 MAP_HUGETLB：请求 -h/-H 一律退出码 2，不假装支持。
//
// 输出：key=value 行（buffer_kb / stride / loads / elapsed_ns / latency_ns /
// warmup_loads / warmup_passes_effective / warmup_state / page_policy /
// page_kb），由 runner 层包装为 record.schema.json 记录。

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <random>
#include <unistd.h>
#include <sys/mman.h>

// MAP_HUGETLB 为 Linux 专有（2MB 默认大页）；macOS 等平台无此能力，
// 请求 hugepage 时以退出码 2（能力不支持）回应（Probe ABI，原理"附加"节）。
#ifndef MAP_HUGETLB
#define CPU_UARCH_NO_HUGEPAGE 1
#else
#define CPU_UARCH_NO_HUGEPAGE 0
#endif

namespace {

constexpr int kUnroll = 8; // 同链展开：摊薄循环控制开销，不引入 MLP（原理 §3）

double now_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return static_cast<double>(ts.tv_sec) * 1e9 + static_cast<double>(ts.tv_nsec);
}

void usage(const char* prog) {
    std::fprintf(stderr,
        "usage: %s -b KB -s stride_bytes [-n loads] [-w warmup_loads] [-h|-H]\n"
        "  -b  buffer size in KB            (default 8192)\n"
        "  -s  stride between chain slots, must be a multiple of %zu (default 64)\n"
        "  -n  total dependent loads, >= %d (default 268435456)\n"
        "  -w  exact warmup loads          (default: 2 complete ring passes)\n"
        "  -h  2MB hugepage (fallback to 4K with explicit tag if pool unavailable)\n"
        "  -H  2MB hugepage strict (exit 2 if pool unavailable)\n",
        prog, sizeof(char*), kUnroll);
}

[[noreturn]] void die(const char* prog, const char* msg) {
    std::fprintf(stderr, "error: %s\n", msg);
    usage(prog);
    std::exit(1);
}

// hugepage 分配：尺寸向上取整到 2MB 对齐 + MAP_HUGETLB；缺页池时 strict 退出 2、
// 非 strict 回退 4K（page_policy 显式标注，requested/actual 纪律）。
char* map_buffer(size_t bytes, bool want_hp, bool strict_hp,
                 const char* prog, const char** policy, unsigned* page_kb) {
#if CPU_UARCH_NO_HUGEPAGE
    (void)bytes; (void)strict_hp;
    if (want_hp) {
        std::fprintf(stderr, "unsupported: MAP_HUGETLB not available on this platform\n");
        std::exit(2);
    }
    *policy = "default-4k"; *page_kb = 4;
    return nullptr;  // 未触发，下行统一走默认 mmap
#else
    if (!want_hp) {
        *policy = "default-4k"; *page_kb = 4;
        return nullptr;
    }
    constexpr size_t kHp = 2 * 1024 * 1024;
    const size_t hp_bytes = (bytes + kHp - 1) / kHp * kHp;
    char* buf = static_cast<char*>(mmap(nullptr, hp_bytes, PROT_READ | PROT_WRITE,
                                        MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB, -1, 0));
    if (buf != MAP_FAILED) {
        *policy = "hugepage-2m"; *page_kb = 2048;
        return buf;
    }
    if (strict_hp) {
        std::fprintf(stderr, "unsupported: hugepage pool unavailable (strict mode)\n");
        std::exit(2);
    }
    std::fprintf(stderr, "warning: hugepage pool unavailable, falling back to 4K pages "
                         "(results keep [fallback-4k] tag; see measurement-discipline §2)\n");
    *policy = "fallback-4k"; *page_kb = 4;
    return nullptr;
#endif
}

} // namespace

int main(int argc, char** argv) {
    size_t buffer_kb = 8192;
    size_t stride = 64;
    long long loads = 268435456; // 2^28；按计时器分辨率反推的最小安全量级（原理 §4）
    long long warmup = 0;
    bool warmup_set = false;
    bool want_hp = false, strict_hp = false;

    int opt;
    while ((opt = getopt(argc, argv, "b:s:n:w:hH")) != -1) {
        switch (opt) {
        case 'b': buffer_kb = std::strtoull(optarg, nullptr, 10); break;
        case 's': stride = std::strtoull(optarg, nullptr, 10); break;
        case 'n': loads = std::strtoll(optarg, nullptr, 10); break;
        case 'w': warmup = std::strtoll(optarg, nullptr, 10); warmup_set = true; break;
        case 'h': want_hp = true; break;
        case 'H': want_hp = true; strict_hp = true; break;
        default: usage(argv[0]); return 1;
        }
    }

    // 输入校验（原理 §6）：任何一项不过即非零退出，不产出记录
    if (buffer_kb == 0)
        die(argv[0], "buffer size must be positive");
    if (stride < sizeof(char*) || stride % sizeof(char*) != 0)
        die(argv[0], "stride must be a multiple of the pointer size");
    if (loads < kUnroll)
        die(argv[0], "loads must be >= the unroll factor (8)");
    if (warmup < 0)
        die(argv[0], "warmup must be >= 0");

    const size_t bytes = buffer_kb * 1024;
    const size_t slots = bytes / stride;
    if (slots < 2)
        die(argv[0], "buffer too small for this stride (need at least 2 slots)");
    if (!warmup_set) {
        if (slots > static_cast<size_t>(INT64_MAX / 2))
            die(argv[0], "default warmup exceeds signed 64-bit load limit");
        warmup = static_cast<long long>(slots) * 2;
    }
    loads -= loads % kUnroll;

    // hugepage 分配（-h/-H）；nullptr 表示走默认 4K 路径
    const char* page_policy = "default-4k";
    unsigned page_kb = 4;
    char* hp_buf = map_buffer(bytes, want_hp, strict_hp, argv[0], &page_policy, &page_kb);
    size_t map_bytes = bytes;
#if !CPU_UARCH_NO_HUGEPAGE
    if (hp_buf != nullptr) {
        constexpr size_t kHp = 2 * 1024 * 1024;
        map_bytes = (bytes + kHp - 1) / kHp * kHp;
    }
#endif
    char* buf = hp_buf != nullptr ? hp_buf
              : static_cast<char*>(mmap(nullptr, bytes, PROT_READ | PROT_WRITE,
                                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
    if (buf == MAP_FAILED) {
        std::perror("mmap");
        return 1;
    }

    // Fisher–Yates 洗牌：uniform_int_distribution 保证无偏，固定种子保证可复现（原理 §2）
    size_t* perm = static_cast<size_t*>(malloc(slots * sizeof(size_t)));
    if (!perm) {
        std::perror("malloc");
        return 1;
    }
    for (size_t i = 0; i < slots; ++i) perm[i] = i;
    std::mt19937_64 rng(42);
    for (size_t i = slots - 1; i > 0; --i) {
        std::uniform_int_distribution<size_t> dist(0, i);
        const size_t j = dist(rng);
        const size_t t = perm[i]; perm[i] = perm[j]; perm[j] = t;
    }

    // 按置换序把整个缓冲区链接成一条随机环
    for (size_t i = 0; i + 1 < slots; ++i)
        *reinterpret_cast<char**>(buf + perm[i] * stride) = buf + perm[i + 1] * stride;
    *reinterpret_cast<char**>(buf + perm[slots - 1] * stride) = buf + perm[0] * stride;

    // 预热：让页错误、TLB、缓存都进入稳态，不计入测量
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

    // volatile sink：追逐结果必须物化，整条链不可被优化掉（原理 §5）
    volatile uintptr_t sink = reinterpret_cast<uintptr_t>(p);
    (void)sink;

    const double elapsed = t1 - t0;
    const double latency = elapsed / static_cast<double>(loads);
    const double warmup_passes =
        static_cast<double>(warmup) / static_cast<double>(slots);
    const char* warmup_state = warmup == 0 ? "cold-warm0" : "warm";

    std::printf("buffer_kb=%zu stride=%zu loads=%lld elapsed_ns=%.0f latency_ns=%.4f "
                "warmup_loads=%lld warmup_passes_effective=%.6f warmup_state=%s "
                "page_policy=%s page_kb=%u\n",
                buffer_kb, stride, loads, elapsed, latency, warmup, warmup_passes,
                warmup_state, page_policy, page_kb);

    free(perm);
    munmap(buf, map_bytes);
    return 0;
}
