// SPDX-License-Identifier: Apache-2.0
// TLB set 收集器金样（RPA-02/PA-03）：与探针同源共享实现
// （probes/common/tlb_set_collect.h），纯整数 VA 运算、不解引用任何地址。
// 覆盖评审复现法的全部消费场景：单目标配额、N-set 跨调用累加、T2 独立
// 审计、单区域隔离、跨界布局。
#include <cstdint>
#include <cstdio>
#include <vector>
#include <sys/mman.h>

#include "tlb_set_collect.h"
#include "tlb_set_layout.h"

namespace tlc = tlb_set_collect;

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { std::fprintf(stderr, "FAIL: %s\n", msg); ++failures; } \
} while (0)

// 与探针同源的预约内对齐布局；不解引用，完整原预约长度用于回收。
struct Layout {
    char* res = nullptr;
    size_t total = 0;
    std::vector<tlc::Region> regions;
    explicit Layout(int n_regions, size_t pool_pages) {
        if (!tlb_set_layout::reservation_pages(n_regions, pool_pages, &total)) return;
        res = static_cast<char*>(mmap(nullptr, total * 4096u, PROT_NONE,
                                      MAP_PRIVATE | MAP_ANONYMOUS
#ifdef MAP_NORESERVE
                                      | MAP_NORESERVE
#endif
                                      , -1, 0));
        if (res == MAP_FAILED) { std::perror("mmap"); return; }
        tlb_set_layout::make_regions(reinterpret_cast<uintptr_t>(res), total,
                                     n_regions, pool_pages, &regions);
    }
    ~Layout() {
        if (res && res != MAP_FAILED) munmap(res, total * 4096u);
    }
};

static int active_count(const std::vector<int>& v) {
    int n = 0; for (int x : v) if (x > 0) ++n; return n;
}
static long long node_sum(const std::vector<int>& v) {
    long long s = 0; for (int x : v) s += x; return s;
}

int main() {
    // 场景 1：单目标配额——16 输入全域 4 区域、与隔离不同（PA-03 基线）
    {
        Layout lo(4, 65536);
        CHECK(lo.regions.size() == 4, "4-region layout built");
        for (int h = 1; h <= 4; ++h)
            for (uint32_t t : {7u, 42u, 100u, 200u}) {
                std::vector<uintptr_t> vas;
                std::vector<int> counts(4, 0);
                const int got = tlc::collect_set_addrs(h, t, 12, lo.regions,
                                                       0, &vas, &counts);
                CHECK(got == 12, "single-target collects 12");
                CHECK(counts.size() == 4, "audit slots == regions");
                CHECK(active_count(counts) == 4, "all 4 regions active");
                CHECK(node_sum(counts) == 12, "audit sum == 12");
                std::vector<uintptr_t> iso;
                std::vector<int> ic(4, 0);
                tlc::collect_set_addrs(h, t, 12, {lo.regions[0]}, 0,
                                       &iso, &ic);
                int same = iso.size() == vas.size();
                if (same) for (size_t i = 0; i < vas.size(); ++i)
                    if (vas[i] != iso[i]) same = 0;
                CHECK(!same, "multi-region != region-0 isolated");
            }
    }
    // 场景 2：N-set 跨调用累加（RPA-02 反例场景）——槽位恒 4、active=4、
    // 总和 = N×W（修复前实现此处 active=N×4）
    for (int nsets : {4, 96, 256}) {
        Layout lo(4, 65536);
        std::vector<uintptr_t> vas;
        std::vector<int> counts(4, 0);
        const int w = 12;
        int got = 0;
        bool enough = true;
        for (int s = 0; s < nsets; ++s) {
            const int g = tlc::collect_set_addrs(1, (uint32_t)s, w,
                                                 lo.regions, 0, &vas, &counts);
            if (g < w) { enough = false; break; }
            got += g;
        }
        CHECK(enough, "nsets collects enough");
        CHECK(counts.size() == 4, "nsets audit slots stay == regions");
        CHECK(active_count(counts) == 4, "nsets active regions == 4");
        CHECK(node_sum(counts) == (long long)nsets * w,
              "nsets audit sum == N*W");
        CHECK((int)vas.size() == got, "nsets node total consistent");
    }
    // 场景 3：T2 独立审计向量——目标链与 T2 各自累加不串扰
    {
        Layout lo(4, 65536);
        std::vector<uintptr_t> vas, vas2;
        std::vector<int> c1(4, 0), c2(4, 0);
        tlc::collect_set_addrs(1, 7, 12, lo.regions, 0, &vas, &c1);
        tlc::collect_set_addrs(1, 42, 12, lo.regions, 0, &vas2, &c2);
        CHECK(node_sum(c1) == 12 && node_sum(c2) == 12, "T2 sums independent");
        CHECK(active_count(c1) == 4 && active_count(c2) == 4, "T2 slots full");
    }
    // 场景 4：隔离 scope（offset 寻址）——仅 slot[k] 非零
    for (int k = 0; k < 4; ++k) {
        Layout lo(4, 65536);
        std::vector<uintptr_t> vas;
        std::vector<int> counts(4, 0);
        tlc::collect_set_addrs(1, 7, 12, {lo.regions[(size_t)k]},
                               (size_t)k, &vas, &counts);
        CHECK(node_sum(counts) == 12, "isolated sum == 12");
        CHECK(counts[(size_t)k] == 12, "isolated fills only own slot");
        CHECK(active_count(counts) == 1, "isolated active == 1");
    }
    // 场景 5：窗口内平移——共享布局已保证池不跨窗；收集器按实际地址
    // 计算索引，合法的额外窗口内偏移不改变区域槽位审计。跨窗反例另由
    // probes/tests/tlb_set_layout_golden.cpp 的全部页偏移覆盖。
    {
        Layout lo(4, 65536);
        // 对齐后再平移 1234 页，此处池末端仍在同一 256MiB 窗口内。
        lo.regions[1].base += 1234 * 4096u;
        std::vector<uintptr_t> vas;
        std::vector<int> counts(4, 0);
        const int got = tlc::collect_set_addrs(3, 100, 12, lo.regions,
                                               0, &vas, &counts);
        CHECK(got == 12, "cross-boundary layout collects");
        CHECK(counts.size() == 4 && active_count(counts) >= 1,
              "cross-boundary audit sane");
    }

    if (failures) {
        std::fprintf(stderr, "tlb_set_collect_golden: %d FAILURES\n", failures);
        return 1;
    }
    std::printf("tlb_set_collect_golden: all scenarios pass\n");
    return 0;
}
