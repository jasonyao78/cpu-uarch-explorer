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

#if defined(__linux__)
#include "perf_window.h"  // M0-4b：TLB set 模式 GROUP 原子读（F5）
#endif

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
        "       %s --tlb-set-mode --set-hypothesis H --set-target T "
        "--set-window W [--set-target2 T2] [--set-rounds R]\n"
        "       [--set-pool-pages P] [--set-filler F] [--set-regions K] "
        "[--set-scatter] [-S seed] [--pmu-event label:type:config]...\n"
        "  -b  buffer size in KB            (default 8192)\n"
        "  -s  stride between chain slots, must be a multiple of %zu (default 64)\n"
        "  -n  total dependent loads, >= %d (default 268435456)\n"
        "  -w  exact warmup loads          (default: 2 complete ring passes)\n"
        "  -S  ring shuffle seed           (default 42; recorded as seed=N)\n"
        "  -h  2MB hugepage (fallback to 4K with explicit tag if pool unavailable)\n"
        "  -H  2MB hugepage strict (exit 2 if pool unavailable)\n"
        "  -T  Linux THP via MADV_HUGEPAGE; actual backing read from smaps\n"
        "  -B  Linux base pages via MADV_NOHUGEPAGE; actual backing read from smaps\n"
        "  --pmu-event label:type:config  Linux per-thread counting event (repeatable)\n"
        "  --tlb-set-mode                 M0-4b TLB set prime+probe 模式"
        "（与 -b/-s/-n/-w 互斥；Linux + 4K 页 + PMU 事件必填）\n"
        "  --set-hypothesis 1..4          候选 VPN→set 索引假设 H1..H4\n"
        "  --set-target N                 目标 set（<256）；--set-target2 = T2 对照组\n"
        "  --set-window W                 每轮 probe 访问数（0=空窗底噪 case）\n"
        "  --set-scatter                  无冲突负控：W 页各落不同 set（G0-3）\n"
        "  --set-rounds R                 轮数（默认 20，>=2；round 0 冷启动剔除）\n"
        "  --set-pool-pages P             目标地址池总页数（默认 65536）\n"
        "  --set-filler F                 prime 驱逐链页数（默认 512）\n"
        "  --set-regions K                F4 多稀疏 VA 区域数（默认 4；1=单区域）\n",
        prog, prog, sizeof(char*), kUnroll);
}

[[noreturn]] void die(const char* prog, const char* msg) {
    std::fprintf(stderr, "error: %s\n", msg);
    usage(prog);
    std::exit(1);
}

// ---- M0-4b：TLB set prime+probe 模式（工程路径 A——原型 l2_set_probe v2.3
// 方法移植的证据探针版）----
// 与原型版的三个决定性差异（任务书 v1.3 §5 口径）：
//   F5：PMU 走 PerfWindow GROUP 原子读 + window_delta 有效性（原型逐事件
//       read 不保证同窗）；任一事件打开失败 = 协议无效，exit 1（fail-closed），
//       不做原型式的逐事件 n/a（三事件门控缺一角即不可判读）。
//   F4：多稀疏 VA 区域激励——单一对齐 256MiB 池内 VPN[23:16] 恒定，H3≡H1⊕
//       常数、H4≡H2⊕常数（假设在域上不可区分）；默认 4 个区域跨 256MiB
//       边界（VPN[23:16] 各异）。预约失败回退单区域并输出
//       set_domain=single-region（命名降级，分析器不得据此区分 H 假设）。
//   G0-3：--set-window 0 = 空窗底噪 case；--set-scatter = 无冲突同长度窗
//       负控（W 页各落不同 set，无自冲突）。
// 4K 硬门：set 索引按 4K 粒度计算（原型 P0-5 同款），页大小不符直接拒绝。
// 候选索引假设与收集器：RPA-02 起与金样测试共享同一实现
// （probes/common/tlb_set_collect.h），评审"生产函数提取复现"法的
// 直接对象——修复必须落在共享代码上，金样才与探针同源。
#include "tlb_set_collect.h"

namespace tlc = tlb_set_collect;

constexpr uint32_t kTlbSets = tlc::kSets;  // X4 TRM Table 9-32（探测目标 set 空间）
constexpr uint32_t kTlbWaysTruth = 8;  // X4 TRM Table 5-1（判读参考线，非探针假设）
constexpr size_t kRegionStridePages = 65536;  // 2^28 B = 256MiB：相邻区域 VPN[23:16] 不同

struct SetModeOptions {
    int hypothesis = 0;        // 1..4（必填）
    uint32_t target = 0;       // 目标 set（nsets=0 时必填，< kTlbSets）
    bool have_target2 = false; // T2 对照组（原型 P0-3：真实第二组）
    uint32_t target2 = 0;
    long long window = -1;     // 每轮 probe 访问数 W（必填，>=0；0=空窗）
    long long rounds = 20;     // >=2（round 0 冷启动剔除）
    size_t pool_pages = 65536; // 目标地址池总页数（多区域共享）
    long long filler_pages = 512; // prime 驱逐链页数（原型 P0-1/P0-2 语义）
    int regions = 4;           // F4 多区域数（1 = 显式单区域）
    bool scatter = false;      // 无冲突负控：W 页各落不同 set
    int region_scope = -1;     // 收集范围：-1=全域配额取样；0..K-1=仅该区域
    int nsets = 0;             // N-set 模式：>0 时收集 set 0..nsets-1 各 W 页
};

void build_chain(const std::vector<uintptr_t>& vas) {
    for (size_t i = 0; i < vas.size(); ++i)
        *reinterpret_cast<char**>(vas[i]) =
            reinterpret_cast<char*>(vas[(i + 1) % vas.size()]);
}

// set 模式主体。实现仅 Linux 编译（perf_window 的 GROUP 原子读是协议
// 必需）；非 Linux 走下方桩（main 分发处已先 exit 2，桩只保证可编译）。
#if defined(__linux__)
int run_tlb_set_mode(const char* prog, const SetModeOptions& opt,
                     const std::vector<PmuEventRequest>& pmu_requests,
                     uint64_t seed) {
    if (opt.hypothesis < 1 || opt.hypothesis > 4)
        die(prog, "tlb-set mode requires --set-hypothesis 1..4");
    if (opt.window < 0)
        die(prog, "tlb-set mode requires --set-window >= 0 (0 = empty window)");
    if (opt.rounds < 2)
        die(prog, "--set-rounds >= 2 (round 0 = cold-start warmup, excluded)");
    if (opt.target >= kTlbSets || (opt.have_target2 && opt.target2 >= kTlbSets))
        die(prog, "set target must be < 256");
    if (opt.scatter && (opt.window < 1 || opt.window > (long long)kTlbSets))
        die(prog, "--set-scatter requires 1 <= --set-window <= 256");
    if (opt.nsets > 0) {
        // N-set 模式是独立估计量：不与 target/T2/scatter 组合（防语义叠加）
        if (opt.have_target2 || opt.scatter)
            die(prog, "--set-nsets is exclusive with --set-target2/--set-scatter");
        if (opt.nsets > (int)kTlbSets)
            die(prog, "--set-nsets must be <= 256");
    }
    if (opt.region_scope >= opt.regions)
        die(prog, "--set-region-scope must be < --set-regions");
    if (pmu_requests.empty())
        die(prog, "tlb-set mode requires --pmu-event (0x05/0x2d/0x2f triple gate)");
    const long long base_page_bytes = sysconf(_SC_PAGESIZE);
    if (base_page_bytes != 4096) {
        std::fprintf(stderr,
                     "error: tlb-set mode assumes 4K granule, got %lld\n",
                     base_page_bytes);
        return 1;
    }

    // ---- 目标池：多区域 VA 预约（F4）----
    // 区域 k 起点 = k*256MiB + k*8 页（奇数页偏移打破对齐）。预约 PROT_NONE
    // 不提交内存，mprotect 逐区域 RW 只提交实际池页。
    std::vector<tlc::Region> regions;
    char* reservation = nullptr;
    size_t reservation_pages = 0;
    const char* set_domain = "single-region";
    if (opt.regions > 1) {
        reservation_pages = static_cast<size_t>(opt.regions - 1)
                                * kRegionStridePages
                            + opt.pool_pages + 64;
        reservation = static_cast<char*>(mmap(
            nullptr, reservation_pages * 4096u, PROT_NONE,
            MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0));
        if (reservation != MAP_FAILED) {
            const size_t per = opt.pool_pages / static_cast<size_t>(opt.regions);
            bool ok = per >= 2;
            for (int k = 0; ok && k < opt.regions; ++k) {
                const size_t off = static_cast<size_t>(k) * kRegionStridePages
                                   + static_cast<size_t>(k) * 8;
                const size_t sz = (k == opt.regions - 1)
                    ? opt.pool_pages - per * static_cast<size_t>(opt.regions - 1)
                    : per;
                if (off + sz > reservation_pages) { ok = false; break; }
                char* base = reservation + off * 4096u;
                if (mprotect(base, sz * 4096u, PROT_READ | PROT_WRITE) != 0) {
                    ok = false; break;
                }
#ifdef MADV_NOHUGEPAGE
                madvise(base, sz * 4096u, MADV_NOHUGEPAGE);
#endif
                regions.push_back({base, sz});
            }
            if (!ok) {
                munmap(reservation, reservation_pages * 4096u);
                reservation = nullptr;
                regions.clear();
            } else {
                set_domain = "multi-region";
            }
        }
    }
    if (regions.empty()) {
        if (reservation != nullptr) {
            munmap(reservation, reservation_pages * 4096u);
            reservation = nullptr;
        }
        const size_t total = opt.pool_pages + 256;  // 原型 F3a 头程补偿
        char* base = static_cast<char*>(mmap(
            nullptr, total * 4096u, PROT_READ | PROT_WRITE,
            MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
        if (base == MAP_FAILED) {
            std::perror("mmap tlb-set pool");
            return 1;
        }
#ifdef MADV_NOHUGEPAGE
        madvise(base, total * 4096u, MADV_NOHUGEPAGE);
#endif
        reservation = base;
        reservation_pages = total;
        regions.push_back({base, total});
        set_domain = opt.regions > 1 ? "single-region-fallback" : "single-region";
    }

    // ---- 目标地址收集（W=0 空窗不收集不建链）----
    // region_scope：-1 = 全域配额取样（每区域 need/K）；>=0 = 仅该区域（
    // A1 配对对照的隔离收集）。nsets>0 = N-set 模式（当前仅 A3 后置登记，
    // 保持协议可用）。RPA-02：审计向量固定 K 槽位按区域 ID 累加——
    // 目标链与 T2 各用独立向量，跨多次收集调用聚合（调用次数 ≠ 区域数）。
    std::vector<uintptr_t> vas, vas2;
    const size_t n_regions = regions.size();
    std::vector<int> target_region_nodes(n_regions, 0);  // 目标链审计
    std::vector<int> t2_region_nodes(n_regions, 0);      // T2 审计（独立）
    std::vector<tlc::Region> collect_regions = regions;
    size_t collect_offset = 0;
    if (opt.region_scope >= 0) {
        if (opt.region_scope >= static_cast<int>(regions.size())) {
            std::fprintf(stderr, "error: region_scope %d >= regions %zu\n",
                         opt.region_scope, regions.size());
            munmap(reservation, reservation_pages * 4096u);
            return 1;
        }
        collect_offset = static_cast<size_t>(opt.region_scope);
        collect_regions = {regions[collect_offset]};
    }
    int got = 0, got2 = 0;
    if (opt.window > 0) {
        const int need = static_cast<int>(opt.window);
        if (opt.nsets > 0) {
            // N-set 模式：nsets 个候选 set 各 need 页，链顺序按 set 序；
            // 审计跨 set 迭代累加进同一 K 槽位向量
            for (int s = 0; s < opt.nsets; ++s) {
                const int g = tlc::collect_set_addrs(
                    opt.hypothesis, static_cast<uint32_t>(s), need,
                    collect_regions, collect_offset, &vas,
                    &target_region_nodes);
                if (g < need) {
                    std::fprintf(stderr,
                                 "error: nsets mode: only %d addrs for set %d "
                                 "under H%d (increase --set-pool-pages)\n",
                                 g, s, opt.hypothesis);
                    munmap(reservation, reservation_pages * 4096u);
                    return 1;
                }
            }
            got = static_cast<int>(vas.size());
        } else if (opt.scatter) {
            got = tlc::collect_scatter_addrs(opt.hypothesis, need,
                                             collect_regions, collect_offset,
                                             &vas, &target_region_nodes);
        } else {
            got = tlc::collect_set_addrs(opt.hypothesis, opt.target, need,
                                         collect_regions, collect_offset, &vas,
                                         &target_region_nodes);
        }
        if (opt.nsets <= 0 && got < need) {
            std::fprintf(stderr,
                         "error: only %d addrs for window %lld under H%d "
                         "(increase --set-pool-pages)\n",
                         got, opt.window, opt.hypothesis);
            munmap(reservation, reservation_pages * 4096u);
            return 1;
        }
        build_chain(vas);
        if (opt.have_target2) {
            got2 = tlc::collect_set_addrs(opt.hypothesis, opt.target2, need,
                                          collect_regions, collect_offset,
                                          &vas2, &t2_region_nodes);
            if (got2 < need) {
                std::fprintf(stderr, "error: cannot collect T2 set %u under H%d\n",
                             opt.target2, opt.hypothesis);
                munmap(reservation, reservation_pages * 4096u);
                return 1;
            }
            for (int i = 0; i < need; ++i)   // 原型 P0-1：T/T2 无交集断言
                for (int j = 0; j < need; ++j)
                    if (vas[i] == vas2[j]) {
                        std::fprintf(stderr, "error: T/T2 overlap\n");
                        munmap(reservation, reservation_pages * 4096u);
                        return 1;
                    }
            build_chain(vas2);
        }
    }
    // RPA-02 审计汇总 + 不变量校验（fail-closed，不满足即结构化失败）：
    //   目标链节点总和 == window×max(nsets,1)（空窗 = 0）
    //   scope>=0 时仅 slot[scope] 非零
    //   T2 节点总和 == window（有 T2 且 window>0 时）
    int active_regions = 0;
    long long target_node_sum = 0;
    for (size_t i = 0; i < n_regions; ++i) {
        if (target_region_nodes[i] > 0) ++active_regions;
        target_node_sum += target_region_nodes[i];
    }
    const long long expected_nodes =
        opt.window > 0 ? opt.window * (opt.nsets > 0 ? opt.nsets : 1) : 0;
    auto audit_fail = [&](const char* msg) {
        std::fprintf(stderr, "error: tlb-set audit invariant: %s\n", msg);
        munmap(reservation, reservation_pages * 4096u);
    };
    if (target_node_sum != expected_nodes) {
        audit_fail("target node sum != window*nsets");
        return 1;
    }
    if (opt.region_scope >= 0
            && target_region_nodes[static_cast<size_t>(opt.region_scope)]
                   != target_node_sum) {
        audit_fail("region_scope isolation violated");
        return 1;
    }
    if (opt.have_target2 && opt.window > 0) {
        long long t2_sum = 0;
        for (int n : t2_region_nodes) t2_sum += n;
        if (t2_sum != opt.window) {
            audit_fail("T2 node sum != window");
            return 1;
        }
    }

    // ---- filler：独立映射（与池天然不相交，P0-1），按候选 H 过滤目标 set ----
    // N-set 模式过滤全部 nsets 个目标 set
    std::vector<uintptr_t> fvas;
    char* filler_map = nullptr;
    size_t filler_map_pages = 0;
    if (opt.filler_pages > 0) {
        filler_map_pages = static_cast<size_t>(opt.filler_pages) + 256;
        filler_map = static_cast<char*>(mmap(
            nullptr, filler_map_pages * 4096u, PROT_READ | PROT_WRITE,
            MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
        if (filler_map == MAP_FAILED) {
            std::perror("mmap filler");
            munmap(reservation, reservation_pages * 4096u);
            return 1;
        }
#ifdef MADV_NOHUGEPAGE
        madvise(filler_map, filler_map_pages * 4096u, MADV_NOHUGEPAGE);
#endif
        const uintptr_t fmap_end = reinterpret_cast<uintptr_t>(filler_map)
                                   + filler_map_pages * 4096u;
        for (uint64_t i = 1; i < filler_map_pages
                 && static_cast<long long>(fvas.size()) < opt.filler_pages; ++i) {
            const uintptr_t va = reinterpret_cast<uintptr_t>(filler_map)
                                 + i * 4096u;
            if (va < reinterpret_cast<uintptr_t>(filler_map) || va >= fmap_end)
                break;  // 双保险边界（原型 F3a）
            const uint32_t fs = tlc::set_index(opt.hypothesis, va);
            if (!opt.scatter && opt.nsets <= 0 && fs == opt.target)
                continue;   // P0-2：filler 不占目标 set
            if (opt.nsets <= 0 && opt.have_target2 && fs == opt.target2)
                continue;
            if (opt.nsets > 0 && fs < static_cast<uint32_t>(opt.nsets))
                continue;   // N-set 模式：filler 不占任何目标 set
            fvas.push_back(va);
        }
        if (static_cast<long long>(fvas.size()) < opt.filler_pages) {
            std::fprintf(stderr, "error: filler pool exhausted (%zu/%lld pages)\n",
                         fvas.size(), opt.filler_pages);
            munmap(filler_map, filler_map_pages * 4096u);
            munmap(reservation, reservation_pages * 4096u);
            return 1;
        }
        std::mt19937_64 fshuf(seed ^ 0x9e3779b97f4a7c15ULL);
        for (size_t i = fvas.size() - 1; i > 0; --i) {
            std::uniform_int_distribution<size_t> dist(0, i);
            const size_t j = dist(fshuf);
            const uintptr_t t = fvas[i]; fvas[i] = fvas[j]; fvas[j] = t;
        }
        build_chain(fvas);
    }

    // ---- PMU：PerfWindow GROUP 原子读（F5）+ window_delta 有效性（MB-05）----
    probe_common::PerfWindow window;
    {
        std::vector<probe_common::TypedEventSpec> specs;
        specs.reserve(pmu_requests.size());
        for (const auto& r : pmu_requests)
            specs.push_back({r.label.c_str(), r.type, r.config});
        if (!window.open_typed(specs.data(), specs.size(),
                               /*exclude_kernel*/ true, /*exclude_hv*/ true)) {
            std::fprintf(stderr, "error: PerfWindow open failed\n");
            munmap(filler_map, filler_map_pages * 4096u);
            munmap(reservation, reservation_pages * 4096u);
            return 1;
        }
        for (size_t i = 0; i < pmu_requests.size(); ++i) {
            if (window.failed(i)) {  // 三事件门控缺一角即协议无效（fail-closed）
                std::fprintf(stderr,
                             "error: tlb-set mode requires all events open; "
                             "event %s failed\n", window.name(i).c_str());
                munmap(filler_map, filler_map_pages * 4096u);
                munmap(reservation, reservation_pages * 4096u);
                return 1;
            }
        }
    }
    if (!window.enable()) {
        std::fprintf(stderr, "error: PerfWindow enable failed\n");
        munmap(filler_map, filler_map_pages * 4096u);
        munmap(reservation, reservation_pages * 4096u);
        return 1;
    }

    const size_t n_events = pmu_requests.size();
    std::vector<double> sum(n_events, 0.0);
    std::vector<long long> event_valid_rounds(n_events, 0);
    long long valid_rounds = 0, mux_rounds = 0, invalid_rounds = 0;
    double probe_ns_sum = 0.0;
    char* tp = opt.window > 0 ? reinterpret_cast<char*>(vas[0]) : nullptr;
    char* tp2 = (opt.have_target2 && opt.window > 0)
        ? reinterpret_cast<char*>(vas2[0]) : nullptr;
    char* fp = fvas.empty() ? nullptr : reinterpret_cast<char*>(fvas[0]);
    volatile char* sink = nullptr;
    asm volatile("" ::: "memory");
    for (long long r = 0; r < opt.rounds; ++r) {
        // 三段快照（原型 v2.3 协议）：s1 prime 前 / s2 prime 后（probe 段
        // 起点）/ s3 probe 后。估计量 = s3-s2（probe 段），s1 仅作整轮
        // mux 审计背景。s2/s3 任一读取失败 = 该轮无效（哨兵，不进均值）。
        // round 0 = 冷启动热身：跑但不进任何统计（原型口径，OI-14 固定
        // 开销登记的前因）。
        const bool count_stats = (r >= 1);
        probe_common::GroupSample s1{}, s2{}, s3{};
        bool ok = window.read_snapshot(&s1);
        if (fp != nullptr) {   // prime：驱逐 L1 驻留
            char* p = fp;
            for (size_t i = 0; i < fvas.size(); ++i)
                p = *reinterpret_cast<char* volatile*>(p);
            fp = p;
        }
        ok = window.read_snapshot(&s2) && ok;
        const double t0 = now_ns();
        if (opt.window > 0) {
            for (long long i = 0; i < opt.window; ++i)
                tp = *reinterpret_cast<char* volatile*>(tp);
        }
        const double seg_ns = now_ns() - t0;
        ok = window.read_snapshot(&s3) && ok;
        if (!ok) { if (count_stats) ++invalid_rounds; continue; }
        probe_common::WindowDelta delta{};
        if (!window_delta(s2, s3, n_events, &delta)) {
            if (count_stats) ++invalid_rounds;
            continue;
        }
        if (!count_stats) continue;   // round 0：热身，计时也不入统计
        if (delta.valid) {
            for (size_t i = 0; i < n_events; ++i) {
                const int pos = window.value_index(i);
                if (pos < 0 || static_cast<uint64_t>(pos) >= s3.nr) continue;
                sum[i] += static_cast<double>(delta.value_deltas[pos]);
                ++event_valid_rounds[i];
            }
            ++valid_rounds;
        } else if (std::strcmp(delta.reason, "mux-detected") == 0) {
            ++mux_rounds;   // F5：mux 轮计数披露，不进均值（减法后被污染的窗）
        } else {
            ++invalid_rounds;
        }
        probe_ns_sum += seg_ns;
        if (opt.have_target2 && opt.window > 0) {
            // T2 对照段（原型 P0-3：每轮交替）——独立 prime + 独立窗口差分
            probe_common::GroupSample u2{}, v2{};
            if (fp != nullptr) {
                char* p = fp;
                for (size_t i = 0; i < fvas.size(); ++i)
                    p = *reinterpret_cast<char* volatile*>(p);
                fp = p;
            }
            bool ok2 = window.read_snapshot(&u2);
            for (long long i = 0; i < opt.window; ++i)
                tp2 = *reinterpret_cast<char* volatile*>(tp2);
            ok2 = window.read_snapshot(&v2) && ok2;
            (void)ok2;  // T2 失败只丢该轮对照段，不影响 T 主体（不进均值池）
        }
    }
    asm volatile("" ::: "memory");
    sink = opt.have_target2 ? tp2 : tp;
    (void)sink;
    window.disable();

    // round 0 已在循环内跳过统计（count_stats = r>=1，冷启动剔除）；
    // 全部保留轮无效 = 无统计可报（fail-closed，不产出记录）。
    if (valid_rounds == 0) {
        std::fprintf(stderr, "error: no valid rounds (window=%lld rounds=%lld)\n",
                     opt.window, opt.rounds);
        munmap(filler_map, filler_map_pages * 4096u);
        munmap(reservation, reservation_pages * 4096u);
        return 1;
    }

    // PA-02 修订：全量无条件自描述——requested 实验条件参数一律输出
    //（含默认值与 0/1 旗标），realized 激励审计（active_regions/每区域
    // 节点数）随记录入档；scatter 恒输出 0/1，不再有"未打印=未请求"。
    std::printf("mode=tlbset set_hypothesis=%d set_target=%u set_window=%lld "
                "set_rounds=%lld set_pool_pages=%zu set_filler_pages=%lld "
                "set_regions=%d scatter=%d set_region_scope=%d set_nsets=%d "
                "set_active_regions=%d set_target_region_nodes=",
                opt.hypothesis, opt.target,
                opt.window, opt.rounds, opt.pool_pages, opt.filler_pages,
                opt.regions, opt.scatter ? 1 : 0, opt.region_scope, opt.nsets,
                active_regions);
    for (size_t i = 0; i < target_region_nodes.size(); ++i)
        std::printf("%s%d", i == 0 ? "" : ",", target_region_nodes[i]);
    if (opt.have_target2) {
        std::printf(" set_target2=%u set_t2_region_nodes=", opt.target2);
        for (size_t i = 0; i < t2_region_nodes.size(); ++i)
            std::printf("%s%d", i == 0 ? "" : ",", t2_region_nodes[i]);
    }
    // 实际高字段（RPA-05：预测表按实际 VA 计算，区域编号 k ≠ 实际 vpn_hi）。
    // purity：区域内每页 vpn_hi 与基址一致（64MiB 区域基址不对齐时可能
    // 跨 256MiB 窗口——已实证 25% 随机基址跨界）；purity=0 → 折叠类 H
    // 判别降级（命名，不静默）。
    bool vpn_hi_pure = true;
    std::printf(" set_region_vpn_hi=");
    for (size_t i = 0; i < regions.size(); ++i) {
        const uintptr_t rbase = reinterpret_cast<uintptr_t>(regions[i].base);
        const uintptr_t rend = rbase + (regions[i].pages - 1) * 4096u;
        if ((rbase >> 28) != (rend >> 28)) vpn_hi_pure = false;
        std::printf("%s%lu", i == 0 ? "" : ",",
                    static_cast<unsigned long>((rbase >> 28) & 0xFF));
    }
    std::printf(" set_region_vpn_hi_pure=%d", vpn_hi_pure ? 1 : 0);
    std::printf(" set_domain=%s page_kb=4 seed=%llu "
                "window_valid_rounds=%lld window_invalid_rounds=%lld "
                "window_mux_rounds=%lld valid_rounds=%lld probe_ns=%.0f",
                set_domain, static_cast<unsigned long long>(seed),
                valid_rounds, invalid_rounds, mux_rounds,
                valid_rounds, probe_ns_sum / (opt.rounds - 1));
    for (size_t i = 0; i < n_events; ++i) {
        const double mean = event_valid_rounds[i] > 0
            ? sum[i] / static_cast<double>(event_valid_rounds[i]) : 0.0;
        std::printf(" pmu_%s_count=%.1f pmu_%s_valid_rounds=%lld",
                    pmu_requests[i].label.c_str(), mean,
                    pmu_requests[i].label.c_str(), event_valid_rounds[i]);
    }
    std::putchar('\n');
    std::fprintf(stderr, "gate: L1D_TLB_REFILL(0x5) 应≈w=%lld 且 L2D_TLB(0x2f) 应≈w；"
                 "w≤%u 时 L2D_TLB_REFILL(0x2d) 应≈0，w≥%u 时应跳变\n",
                 opt.window, kTlbWaysTruth, kTlbWaysTruth + 1);

    munmap(filler_map, filler_map_pages * 4096u);
    munmap(reservation, reservation_pages * 4096u);
    return 0;
}
#else
int run_tlb_set_mode(const char*, const SetModeOptions&,
                     const std::vector<PmuEventRequest>&, uint64_t) {
    std::fprintf(stderr,
                 "unsupported: tlb-set mode requires Linux perf_event_open\n");
    return 2;
}
#endif

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
    // M0-4b：TLB set prime+probe 模式参数（--tlb-set-mode 触发）
    SetModeOptions set_opt;
    bool set_mode = false;
    bool legacy_geometry_set = false;  // -b/-s/-n/-w 显式给出（与 set 模式互斥）

    enum : int { kPmuEvent = 1000, kTlbSetMode, kSetHypothesis, kSetTarget,
                 kSetTarget2, kSetWindow, kSetRounds, kSetPoolPages,
                 kSetFiller, kSetRegions, kSetScatter, kSetRegionScope,
                 kSetNSets };
    const option long_options[] = {
        {"pmu-event", required_argument, nullptr, kPmuEvent},
        {"tlb-set-mode", no_argument, nullptr, kTlbSetMode},
        {"set-hypothesis", required_argument, nullptr, kSetHypothesis},
        {"set-target", required_argument, nullptr, kSetTarget},
        {"set-target2", required_argument, nullptr, kSetTarget2},
        {"set-window", required_argument, nullptr, kSetWindow},
        {"set-rounds", required_argument, nullptr, kSetRounds},
        {"set-pool-pages", required_argument, nullptr, kSetPoolPages},
        {"set-filler", required_argument, nullptr, kSetFiller},
        {"set-regions", required_argument, nullptr, kSetRegions},
        {"set-scatter", no_argument, nullptr, kSetScatter},
        {"set-region-scope", required_argument, nullptr, kSetRegionScope},
        {"set-nsets", required_argument, nullptr, kSetNSets},
        {nullptr, 0, nullptr, 0},
    };
    int opt;
    while ((opt = getopt_long(argc, argv, "b:s:n:w:hHTBS:",
                              long_options, nullptr)) != -1) {
        switch (opt) {
        case 'b': buffer_kb = std::strtoull(optarg, nullptr, 10);
            legacy_geometry_set = true; break;
        case 's': stride = std::strtoull(optarg, nullptr, 10);
            legacy_geometry_set = true; break;
        case 'n': loads = std::strtoll(optarg, nullptr, 10);
            legacy_geometry_set = true; break;
        case 'w': warmup = std::strtoll(optarg, nullptr, 10); warmup_set = true;
            legacy_geometry_set = true; break;
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
        case kTlbSetMode: set_mode = true; break;
        case kSetHypothesis:
            set_opt.hypothesis = std::atoi(optarg); break;
        case kSetTarget:
            set_opt.target = static_cast<uint32_t>(
                std::strtoul(optarg, nullptr, 0)); break;
        case kSetTarget2:
            set_opt.target2 = static_cast<uint32_t>(
                std::strtoul(optarg, nullptr, 0));
            set_opt.have_target2 = true; break;
        case kSetWindow:
            set_opt.window = std::strtoll(optarg, nullptr, 10); break;
        case kSetRounds:
            set_opt.rounds = std::strtoll(optarg, nullptr, 10); break;
        case kSetPoolPages:
            set_opt.pool_pages = std::strtoull(optarg, nullptr, 10); break;
        case kSetFiller:
            set_opt.filler_pages = std::strtoll(optarg, nullptr, 10); break;
        case kSetRegions:
            set_opt.regions = std::atoi(optarg); break;
        case kSetScatter: set_opt.scatter = true; break;
        case kSetRegionScope:
            set_opt.region_scope = std::atoi(optarg); break;
        case kSetNSets:
            set_opt.nsets = std::atoi(optarg); break;
        default: usage(argv[0]); return 1;
        }
    }
    if (optind != argc)
        die(argv[0], "unexpected positional argument");

    // M0-4b：set 模式分发（与 legacy 几何互斥；混合语义 = 证据危害）
    if (set_mode) {
        if (legacy_geometry_set)
            die(argv[0], "--tlb-set-mode is mutually exclusive with "
                         "legacy -b/-s/-n/-w geometry");
        if (want_hp || strict_hp || want_thp)
            die(argv[0], "--tlb-set-mode forces 4K base pages "
                         "(set index assumes 4K granule); -h/-H/-T not allowed");
#if defined(__linux__)
        return run_tlb_set_mode(argv[0], set_opt, pmu_requests, seed);
#else
        std::fprintf(stderr,
                     "unsupported: tlb-set mode requires Linux perf_event_open\n");
        return 2;
#endif
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
