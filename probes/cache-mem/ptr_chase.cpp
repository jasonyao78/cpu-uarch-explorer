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
// 2. 为什么链要随机化（Fisher–Yates 洗牌 + 可记录种子）
//    顺序或固定步长的访问模式会被硬件 stride prefetcher 预测并预取，
//    预取掩盖真实延迟，测量结果系统性偏低。随机排列**削弱简单
//    stride/next-line 预取器**的有效性，但**不保证消除所有预取**——
//    固定随机环会被反复遍历，地址相关/学习类预取器仍可能跟踪它
//    （SM8650 X4 实测 L1 预取事件高达 ~0.93/load，见 P0″ 评审
//    2026-09-28）。因此预取活动必须被列为测量对象（PMU demand/
//    prefetch 分离事件），而不是假设为零。
//    种子默认 42（与历史记录一致），可用 -S 覆盖；无论取值如何都经
//    `seed=` 输出入档——访问序列本身是实验变量（地址相关预取/索引
//    共振判别），必须可溯源。
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
//    loads ≥ 展开因子、槽位数 ≥ 2、seed 为可解析的非负整数。
//
// 附加：页策略（-B / -h / -H / -T；measurement-discipline §2 落地）
//    `-h/-H` 请求显式 hugetlb（fallback/strict）；`-T` 请求 Linux THP
//    (`MADV_HUGEPAGE`)；`-B` 用 `MADV_NOHUGEPAGE` 显式请求 base pages。
//    请求成功不等于实际 backing：普通匿名映射在 warmup 后、测量窗前
//    与 timed/PMU 窗结束后各解析一次 /proc/self/smaps；两端实际类别或
//    AnonHugePages 不同则退出 1，不产出有效 metrics。端点相同只证明两次
//    观测一致，不声称排除窗内瞬态 promotion/demotion。非 Linux 平台请求
//    这些 Linux 能力时退出码 2。
//
// 可选 core PMU：Linux `--pmu-event label:type:config` 可重复；每个 event
// 在同一 timed loop 前 reset/enable/baseline，t1 后先 read 再 disable，输出
// raw count delta 与 enabled/running time。未请求时不改变既有测量路径。
//
// 输出：key=value 行（buffer_kb / stride / loads / elapsed_ns / latency_ns /
// warmup_loads / warmup_passes_effective / warmup_state / page_policy /
// page_policy_requested / page_policy_actual / anon_huge_kb / page_kb /
// page_policy_actual_before/after / anon_huge_kb_before/after /
// page_backing_endpoints_equal / vma_base（建链缓冲区起始 VA，ASLR 布局
// 观测）/ seed），由 runner 层包装为
// record.schema.json 记录。

#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <getopt.h>
#include <limits>
#include <random>
#include <set>
#include <string>
#include <utility>
#include <vector>
#include <unistd.h>
#include <sys/mman.h>

#include "page_policy.h"   // M0-1：共享页策略支撑（probe_common）

// 平台能力宏（页策略抬升后保留在调用方；语义同 v1 战役版）
#if defined(__linux__) && defined(MADV_HUGEPAGE)
#define CPU_UARCH_NO_THP 0
#else
#define CPU_UARCH_NO_THP 1
#endif

#if defined(__linux__) && defined(MADV_NOHUGEPAGE)
#define CPU_UARCH_NO_BASE_PAGE_ADVICE 0
#else
#define CPU_UARCH_NO_BASE_PAGE_ADVICE 1
#endif

#if defined(CPU_UARCH_HAVE_LINUX_PERF)
#include "perf_counter.h"
#endif

namespace {

constexpr int kUnroll = 8; // 同链展开：摊薄循环控制开销，不引入 MLP（原理 §3）
constexpr size_t kMaxPmuEvents = 16;

struct PmuEventRequest {
    std::string label;
    uint32_t type;
    uint64_t config;
};

bool safe_pmu_label(const std::string& label) {
    if (label.empty())
        return false;
    for (unsigned char ch : label) {
        const bool valid = (ch >= 'a' && ch <= 'z')
                        || (ch >= '0' && ch <= '9') || ch == '_';
        if (!valid)
            return false;
    }
    return true;
}

bool parse_u64_base0(const std::string& text, uint64_t* value) {
    if (text.empty() || text[0] == '-')
        return false;
    errno = 0;
    char* end = nullptr;
    const unsigned long long parsed = std::strtoull(text.c_str(), &end, 0);
    if (errno != 0 || end == text.c_str() || *end != '\0')
        return false;
    *value = static_cast<uint64_t>(parsed);
    return true;
}

bool parse_pmu_event(const char* text, PmuEventRequest* request) {
    if (text == nullptr)
        return false;
    const std::string descriptor(text);
    const size_t first = descriptor.find(':');
    const size_t second = first == std::string::npos
        ? std::string::npos : descriptor.find(':', first + 1);
    if (first == std::string::npos || second == std::string::npos
            || descriptor.find(':', second + 1) != std::string::npos)
        return false;
    const std::string label = descriptor.substr(0, first);
    uint64_t type = 0;
    uint64_t config = 0;
    if (!safe_pmu_label(label)
            || !parse_u64_base0(descriptor.substr(first + 1, second - first - 1), &type)
            || type > std::numeric_limits<uint32_t>::max()
            || !parse_u64_base0(descriptor.substr(second + 1), &config))
        return false;
    *request = PmuEventRequest{label, static_cast<uint32_t>(type), config};
    return true;
}

double now_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return static_cast<double>(ts.tv_sec) * 1e9 + static_cast<double>(ts.tv_nsec);
}

void usage(const char* prog) {
    std::fprintf(stderr,
        "usage: %s -b KB -s stride_bytes [-n loads] [-w warmup_loads] "
        "[-S seed] [-B|-h|-H|-T] [--pmu-event label:type:config]...\n"
        "  -b  buffer size in KB            (default 8192)\n"
        "  -s  stride between chain slots, must be a multiple of %zu (default 64)\n"
        "  -n  total dependent loads, >= %d (default 268435456)\n"
        "  -w  exact warmup loads          (default: 2 complete ring passes)\n"
        "  -S  ring shuffle seed           (default 42; recorded as seed=N)\n"
        "  -h  2MB hugepage (fallback to 4K with explicit tag if pool unavailable)\n"
        "  -H  2MB hugepage strict (exit 2 if pool unavailable)\n"
        "  -T  Linux THP via MADV_HUGEPAGE; actual backing read from smaps\n"
        "  -B  Linux base pages via MADV_NOHUGEPAGE; actual backing read from smaps\n"
        "  --pmu-event label:type:config  Linux per-thread counting event (repeatable)\n",
        prog, sizeof(char*), kUnroll);
}

[[noreturn]] void die(const char* prog, const char* msg) {
    std::fprintf(stderr, "error: %s\n", msg);
    usage(prog);
    std::exit(1);
}

} // namespace


int main(int argc, char** argv) {
    size_t buffer_kb = 8192;
    size_t stride = 64;
    long long loads = 268435456; // 2^28；按计时器分辨率反推的最小安全量级（原理 §4）
    long long warmup = 0;
    bool warmup_set = false;
    bool want_hp = false, strict_hp = false, want_thp = false, want_base = false;
    uint64_t seed = 42; // 历史默认；访问序列是实验变量，随输出入档（原理 §2）
    std::vector<PmuEventRequest> pmu_requests;

    enum : int { kPmuEvent = 1000 };
    const option long_options[] = {
        {"pmu-event", required_argument, nullptr, kPmuEvent},
        {nullptr, 0, nullptr, 0},
    };
    int opt;
    while ((opt = getopt_long(argc, argv, "b:s:n:w:hHTBS:",
                              long_options, nullptr)) != -1) {
        switch (opt) {
        case 'b': buffer_kb = std::strtoull(optarg, nullptr, 10); break;
        case 's': stride = std::strtoull(optarg, nullptr, 10); break;
        case 'n': loads = std::strtoll(optarg, nullptr, 10); break;
        case 'w': warmup = std::strtoll(optarg, nullptr, 10); warmup_set = true; break;
        case 'h': want_hp = true; break;
        case 'H': want_hp = true; strict_hp = true; break;
        case 'T': want_thp = true; break;
        case 'B': want_base = true; break;
        case 'S':
            if (!parse_u64_base0(optarg, &seed))
                die(argv[0], "seed must be a non-negative integer (base 0)");
            break;
        case kPmuEvent: {
            PmuEventRequest request;
            if (!parse_pmu_event(optarg, &request))
                die(argv[0], "pmu-event must be label:uint32-type:uint64-config");
            pmu_requests.push_back(std::move(request));
            break;
        }
        default: usage(argv[0]); return 1;
        }
    }
    if (optind != argc)
        die(argv[0], "unexpected positional argument");

    // 输入校验（原理 §6）：任何一项不过即非零退出，不产出记录
    if (buffer_kb == 0)
        die(argv[0], "buffer size must be positive");
    if (stride < sizeof(char*) || stride % sizeof(char*) != 0)
        die(argv[0], "stride must be a multiple of the pointer size");
    if (loads < kUnroll)
        die(argv[0], "loads must be >= the unroll factor (8)");
    if (warmup < 0)
        die(argv[0], "warmup must be >= 0");
    if (static_cast<int>(want_hp) + static_cast<int>(want_thp)
            + static_cast<int>(want_base) > 1)
        die(argv[0], "cannot request both; page policies are mutually exclusive");
    if (pmu_requests.size() > kMaxPmuEvents)
        die(argv[0], "too many PMU events (maximum 16)");
    std::set<std::string> pmu_labels;
    for (const auto& request : pmu_requests) {
        if (!pmu_labels.insert(request.label).second)
            die(argv[0], "PMU event labels must be unique");
    }
#if !defined(CPU_UARCH_HAVE_LINUX_PERF)
    if (!pmu_requests.empty()) {
        std::fprintf(stderr, "unsupported: Linux perf_event_open is not available\n");
        return 2;
    }
#endif
#if CPU_UARCH_NO_THP
    if (want_thp) {
        std::fprintf(stderr, "unsupported: MADV_HUGEPAGE not available on this platform\n");
        return 2;
    }
#endif
#if CPU_UARCH_NO_BASE_PAGE_ADVICE
    if (want_base) {
        std::fprintf(stderr, "unsupported: MADV_NOHUGEPAGE not available on this platform\n");
        return 2;
    }
#endif

    const size_t bytes = buffer_kb * 1024;
    size_t normal_map_bytes = bytes;
#if defined(__linux__)
    const long base_page_bytes_raw = sysconf(_SC_PAGESIZE);
    if (base_page_bytes_raw <= 0) {
        std::fprintf(stderr, "error: cannot determine Linux base page size\n");
        return 1;
    }
    const size_t base_page_bytes = static_cast<size_t>(base_page_bytes_raw);
    normal_map_bytes = (bytes + base_page_bytes - 1) / base_page_bytes * base_page_bytes;
#endif
    const size_t slots = bytes / stride;
    if (slots < 2)
        die(argv[0], "buffer too small for this stride (need at least 2 slots)");
    if (!warmup_set) {
        if (slots > static_cast<size_t>(INT64_MAX / 2))
            die(argv[0], "default warmup exceeds signed 64-bit load limit");
        warmup = static_cast<long long>(slots) * 2;
    }
    loads -= loads % kUnroll;

    // hugetlb 成功时返回显式大页映射；nullptr 表示走普通匿名映射。THP 只
    // 能作用于后者，且最终状态必须由 smaps 观测，不能由请求结果推断。
    char* hp_buf = probe_common::map_hugetlb_buffer(bytes, want_hp, strict_hp);
    char* mapping_base = hp_buf;
    size_t mapping_bytes = bytes;
#if !PROBE_COMMON_NO_HUGEPAGE
    if (hp_buf != nullptr) {
        constexpr size_t kHp = 2 * 1024 * 1024;
        mapping_bytes = (bytes + kHp - 1) / kHp * kHp;
    }
#endif
    char* buf = hp_buf;
    if (buf == nullptr) {
#if defined(__linux__)
        // 匿名 mmap 可与邻接、属性相同的 VMA 合并；Android 实测默认映射因此
        // 无法把 VMA 级 AnonHugePages 精确归到目标 buffer。两侧 PROT_NONE
        // guard page 强制目标 RW 段成为边界精确的独立 VMA，不改变中间页的
        // default/THP policy，也不放宽 smaps 的保守归属规则。
        const probe_common::GuardedMap guarded =
            probe_common::map_guarded_anonymous(bytes, base_page_bytes);
        if (guarded.buf == nullptr) {
            std::perror("mmap guarded buffer");
            return 1;
        }
        mapping_base = guarded.mapping_base;
        mapping_bytes = guarded.mapping_bytes;
        buf = guarded.buf;
#else
        mapping_base = static_cast<char*>(mmap(
            nullptr, bytes, PROT_READ | PROT_WRITE,
            MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
        if (mapping_base == MAP_FAILED) {
            std::perror("mmap");
            return 1;
        }
        buf = mapping_base;
        mapping_bytes = bytes;
#endif
    }

#if !CPU_UARCH_NO_THP
    if (want_thp && madvise(buf, bytes, MADV_HUGEPAGE) != 0) {
        std::perror("madvise(MADV_HUGEPAGE)");
        munmap(mapping_base, mapping_bytes);
        return 1;
    }
#endif
#if !CPU_UARCH_NO_BASE_PAGE_ADVICE
    if (want_base && madvise(buf, normal_map_bytes, MADV_NOHUGEPAGE) != 0) {
        std::perror("madvise(MADV_NOHUGEPAGE)");
        munmap(mapping_base, mapping_bytes);
        return 1;
    }
#endif

    // Fisher–Yates 洗牌：uniform_int_distribution 保证无偏，种子入档保证可复现（原理 §2）
    size_t* perm = static_cast<size_t*>(malloc(slots * sizeof(size_t)));
    if (!perm) {
        std::perror("malloc");
        munmap(mapping_base, mapping_bytes);
        return 1;
    }
    for (size_t i = 0; i < slots; ++i) perm[i] = i;
    std::mt19937_64 rng(seed);
    for (size_t i = slots - 1; i > 0; --i) {
        std::uniform_int_distribution<size_t> dist(0, i);
        const size_t j = dist(rng);
        const size_t t = perm[i]; perm[i] = perm[j]; perm[j] = t;
    }

    // 按置换序把整个缓冲区链接成一条随机环
    for (size_t i = 0; i + 1 < slots; ++i)
        *reinterpret_cast<char**>(buf + perm[i] * stride) = buf + perm[i + 1] * stride;
    *reinterpret_cast<char**>(buf + perm[slots - 1] * stride) = buf + perm[0] * stride;

    const char* page_policy_requested = want_base ? "base-madvise"
        : (want_thp ? "thp-madvise"
        : (want_hp ? (strict_hp ? "hugetlb-strict" : "hugetlb-fallback") : "default"));
    std::string page_policy_actual_before = "platform-default";
    std::string page_policy_actual_after = "platform-default";
    std::string page_policy = "platform-default";
    size_t anon_huge_kb_before = 0;
    size_t anon_huge_kb_after = 0;
    unsigned page_kb = probe_common::base_page_kb();
    if (hp_buf != nullptr) {
        page_policy_actual_before = "hugetlb-2m";
        page_policy_actual_after = "hugetlb-2m";
        page_policy = "hugepage-2m";
        page_kb = 2048;
    }

    // 预热：让页错误、TLB、缓存都进入稳态，不计入测量
    char* p = buf + perm[0] * stride;
    for (long long i = 0; i < warmup; ++i)
        p = *reinterpret_cast<char**>(p);

#if defined(__linux__)
    if (hp_buf == nullptr) {
        // 第一次 smaps 观测必须在 warmup 后：初始化写入和 warmup 都可能
        // 触发 khugepaged；只有这里才是 timed/PMU 窗入口的 backing。
        if (!probe_common::read_anon_huge_kb(buf, normal_map_bytes, &anon_huge_kb_before)) {
            std::fprintf(stderr,
                         "error: cannot inspect target mapping before measurement\n");
            free(perm);
            munmap(mapping_base, mapping_bytes);
            return 1;
        }
        const probe_common::PageBackingClass before =
            probe_common::classify_page_backing(anon_huge_kb_before, normal_map_bytes);
        page_policy_actual_before = before.actual;
        page_kb = before.page_kb;
    }
#endif

#if defined(CPU_UARCH_HAVE_LINUX_PERF)
    std::vector<cpu_uarch::PerfEventSpec> perf_specs;
    perf_specs.reserve(pmu_requests.size());
    for (const auto& request : pmu_requests)
        perf_specs.push_back({request.label, request.type, request.config});
    cpu_uarch::PerfCounterSession perf_session(std::move(perf_specs));
    cpu_uarch::PerfCounterError perf_error;
    if (!perf_session.open_for_current_thread(&perf_error)) {
        const int exit_code = cpu_uarch::perf_open_errno_is_unsupported(
            perf_error.error_number) ? 2 : 1;
        std::fprintf(stderr, "%s: stage=%s errno=%d error=%s\n",
                     exit_code == 2 ? "unsupported" : "error",
                     perf_error.stage.c_str(), perf_error.error_number,
                     std::strerror(perf_error.error_number));
        free(perm);
        munmap(mapping_base, mapping_bytes);
        return exit_code;
    }
    if (!perf_session.start(&perf_error)) {
        std::fprintf(stderr, "error: stage=%s errno=%d error=%s\n",
                     perf_error.stage.c_str(), perf_error.error_number,
                     std::strerror(perf_error.error_number));
        free(perm);
        munmap(mapping_base, mapping_bytes);
        return 1;
    }
#endif

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

#if defined(CPU_UARCH_HAVE_LINUX_PERF)
    std::vector<cpu_uarch::PerfEventObservation> perf_observations;
    if (!perf_session.stop(&perf_observations, &perf_error)) {
        std::fprintf(stderr, "error: stage=%s errno=%d error=%s\n",
                     perf_error.stage.c_str(), perf_error.error_number,
                     std::strerror(perf_error.error_number));
        free(perm);
        munmap(mapping_base, mapping_bytes);
        return 1;
    }
#endif

    // volatile sink：追逐结果必须物化，整条链不可被优化掉（原理 §5）
    volatile uintptr_t sink = reinterpret_cast<uintptr_t>(p);
    (void)sink;

#if defined(__linux__)
    if (hp_buf == nullptr) {
        // PMU 已停止、计时已结束；smaps I/O 不进入任何测量窗口。
        if (!probe_common::read_anon_huge_kb(buf, normal_map_bytes, &anon_huge_kb_after)) {
            std::fprintf(stderr,
                         "error: cannot inspect target mapping after measurement\n");
            free(perm);
            munmap(mapping_base, mapping_bytes);
            return 1;
        }
        const probe_common::PageBackingClass after =
            probe_common::classify_page_backing(anon_huge_kb_after, normal_map_bytes);
        page_policy_actual_after = after.actual;
    }
#endif

    if (page_policy_actual_before != page_policy_actual_after
            || anon_huge_kb_before != anon_huge_kb_after) {
        std::fprintf(
            stderr,
            "error: page-backing endpoint drift: before=%s/%zuKiB after=%s/%zuKiB\n",
            page_policy_actual_before.c_str(), anon_huge_kb_before,
            page_policy_actual_after.c_str(), anon_huge_kb_after);
        free(perm);
        munmap(mapping_base, mapping_bytes);
        return 1;
    }

#if defined(__linux__)
    if (hp_buf == nullptr) {
        const char* prefix = want_base ? "base-madvise"
            : (want_thp ? "thp" : (want_hp ? "fallback" : "default"));
        if (page_policy_actual_before == "base")
            page_policy = std::string(prefix) + "-4k";
        else if (page_policy_actual_before == "thp")
            page_policy = std::string(prefix) + "-thp";
        else
            page_policy = std::string(prefix) + "-mixed";
    }
#endif

    const double elapsed = t1 - t0;
    const double latency = elapsed / static_cast<double>(loads);
    const double warmup_passes =
        static_cast<double>(warmup) / static_cast<double>(slots);
    const char* warmup_state = warmup == 0 ? "cold-warm0" : "warm";

    std::printf("buffer_kb=%zu stride=%zu loads=%lld elapsed_ns=%.0f latency_ns=%.4f "
                "warmup_loads=%lld warmup_passes_effective=%.6f warmup_state=%s "
                "page_policy=%s page_kb=%u page_policy_requested=%s "
                "page_policy_actual=%s anon_huge_kb=%zu "
                "page_policy_actual_before=%s page_policy_actual_after=%s "
                "anon_huge_kb_before=%zu anon_huge_kb_after=%zu "
                "page_backing_endpoints_equal=1 vma_base=%p seed=%llu",
                buffer_kb, stride, loads, elapsed, latency, warmup, warmup_passes,
                warmup_state, page_policy.c_str(), page_kb, page_policy_requested,
                page_policy_actual_before.c_str(), anon_huge_kb_before,
                page_policy_actual_before.c_str(), page_policy_actual_after.c_str(),
                anon_huge_kb_before, anon_huge_kb_after,
                static_cast<void*>(buf),
                static_cast<unsigned long long>(seed));
#if defined(CPU_UARCH_HAVE_LINUX_PERF)
    for (const auto& observation : perf_observations) {
        std::printf(
            " pmu_%s_type=%u pmu_%s_config=%llu pmu_%s_count=%llu "
            "pmu_%s_time_enabled_ns=%llu pmu_%s_time_running_ns=%llu",
            observation.spec.label.c_str(), observation.spec.type,
            observation.spec.label.c_str(),
            static_cast<unsigned long long>(observation.spec.config),
            observation.spec.label.c_str(),
            static_cast<unsigned long long>(observation.count),
            observation.spec.label.c_str(),
            static_cast<unsigned long long>(observation.time_enabled_ns),
            observation.spec.label.c_str(),
            static_cast<unsigned long long>(observation.time_running_ns));
    }
#endif
    std::putchar('\n');

    free(perm);
    munmap(mapping_base, mapping_bytes);
    return 0;
}
