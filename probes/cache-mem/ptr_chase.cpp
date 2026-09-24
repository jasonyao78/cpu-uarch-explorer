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
//    迫使每次访问都真实走完存储层次。固定种子（42）保证链结构可复现，
//    同一二进制两次运行访问同一序列。
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
// 输出：key=value 行（buffer_kb / stride / loads / elapsed_ns / latency_ns），
// 由 runner 层包装为 record.schema.json 记录。

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
    long long loads = 268435456; // 2^28；按计时器分辨率反推的最小安全量级（见文件头 §4）
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

    constexpr int kUnroll = 8; // 同链展开：摊薄循环控制开销，不引入 MLP（文件头 §3）
    const size_t bytes = buffer_kb * 1024;
    const size_t slots = bytes / stride;
    loads -= loads % kUnroll;

    char* buf = static_cast<char*>(mmap(nullptr, bytes, PROT_READ | PROT_WRITE,
                                        MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
    if (buf == MAP_FAILED) {
        std::perror("mmap");
        return 1;
    }

    // Fisher–Yates 洗牌：无偏置换，固定种子保证可复现（文件头 §2）
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

    // volatile sink：追逐结果必须物化，整条链不可被优化掉（文件头 §5）
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
