// SPDX-License-Identifier: Apache-2.0
// A1 生产共享布局的边界与采集契约；不执行 PMU，不把宿主 mmap 当手机证据。
// 锚点：docs/reviews/2026-10-08-a1-geometry-and-pilot-audit.md。
#include <cstdint>
#include <cstdio>
#include <limits>
#include <set>
#include <vector>
#include <sys/mman.h>

#include "tlb_set_layout.h"

namespace tlc = tlb_set_collect;
namespace tll = tlb_set_layout;
static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { \
    std::fprintf(stderr, "FAIL: %s\n", msg); ++failures; } } while (0)

// 独立核验布局结果，而不是用被测函数的中间计算充当断言。
static bool valid(uintptr_t base, size_t total, size_t pool,
                  const std::vector<tlc::Region>& regions) {
    size_t sum = 0;
    std::set<uintptr_t> hi;
    for (size_t k = 0; k < regions.size(); ++k) {
        const auto& r = regions[k];
        const uintptr_t start = reinterpret_cast<uintptr_t>(r.base);
        const uintptr_t end = start + r.pages * 4096u - 1;
        if (start < base || end >= base + total * 4096u ||
            (start >> 28) != (end >> 28)) return false;
        const uintptr_t first = reinterpret_cast<uintptr_t>(regions[0].base);
        if ((first & ((UINT64_C(1) << 28) - 1)) != 0 ||
            start - first != k * ((UINT64_C(1) << 28) + 8 * 4096u)) return false;
        sum += r.pages;
        hi.insert((start >> 28) & 255);
    }
    return sum == pool && hi.size() == regions.size();
}

// 用真实收集器核对 H×target×scope；目标页所属区域的高字段须保持不变。
static void check_collectors(const std::vector<tlc::Region>& regions) {
    for (int h = 1; h <= 4; ++h)
        for (uint32_t target : {7u, 42u, 100u, 200u})
            for (int scope : {-1, 0, 1, 2, 3})
                for (int w : {6, 8, 10, 12}) {
                    std::vector<tlc::Region> chosen = scope < 0 ? regions
                        : std::vector<tlc::Region>{regions[static_cast<size_t>(scope)]};
                    std::vector<uintptr_t> addresses;
                    std::vector<int> counts(4, 0);
                    const size_t offset = scope < 0 ? 0 : static_cast<size_t>(scope);
                    CHECK(tlc::collect_set_addrs(h, target, w, chosen, offset,
                                                &addresses, &counts) == w,
                          "H/target/scope collects requested W");
                    CHECK(addresses.size() == static_cast<size_t>(w), "target count");
                    for (size_t k = 0; k < 4; ++k) {
                        const int expected = scope < 0 ? w / 4 + (k == 3 ? w % 4 : 0)
                            : (k == static_cast<size_t>(scope) ? w : 0);
                        CHECK(counts[k] == expected, "quota or isolated slot");
                    }
                    for (auto va : addresses) {
                        CHECK(tlc::set_index(h, va) == target, "actual requested index");
                        bool contained = false;
                        for (const auto& r : chosen) {
                            const uintptr_t b = reinterpret_cast<uintptr_t>(r.base);
                            if (va >= b && va < b + r.pages * 4096u) {
                                contained = true;
                                CHECK((va >> 28) == (b >> 28), "selected node hi is pool hi");
                            }
                        }
                        CHECK(contained, "selected node belongs to chosen pool");
                    }
                    addresses.clear();
                    counts.assign(4, 0);
                    CHECK(tlc::collect_scatter_addrs(h, w, chosen, offset,
                                                    &addresses, &counts) == w,
                          "scatter collects W");
                    std::set<uint32_t> indices;
                    for (auto va : addresses) indices.insert(tlc::set_index(h, va));
                    CHECK(indices.size() == static_cast<size_t>(w), "scatter indices distinct");
                }
}

int main() {
    // 任意 4KiB 页偏移，而非依赖宿主 ASLR 恰好落在不跨界的位置。
    for (int n : {2, 4, 16}) {
        size_t total = 0;
        CHECK(tll::reservation_pages(n, 65536, &total), "reservation shape");
        for (size_t offset = 0; offset < 65536; ++offset) {
            const uintptr_t base = UINT64_C(0x1000000000) + offset * 4096u;
            std::vector<tlc::Region> regions;
            CHECK(tll::make_regions(base, total, n, 65536, &regions), "all offsets layout");
            CHECK(regions.size() == static_cast<size_t>(n) && valid(base, total, 65536, regions),
                  "bounded pure distinct regions, unchanged relative offsets");
        }
    }
    size_t total = 0;
    CHECK(!tll::reservation_pages(0, 65536, &total), "reject no regions");
    CHECK(!tll::reservation_pages(17, 65536, &total), "reject excessive regions");
    CHECK(!tll::reservation_pages(4, 7, &total), "reject insufficient pages");
    CHECK(!tll::reservation_pages(4, std::numeric_limits<size_t>::max(), &total), "reject overflow pool");
    CHECK(!tll::reservation_pages(4, 4 * 65536, &total), "reject pool crossing after skew");
    CHECK(!tll::reservation_pages(4, 65536, nullptr), "reject null size output");
    const size_t maximum_uniform_pool = 4 * (65536 - 3 * 8);
    CHECK(tll::reservation_pages(4, maximum_uniform_pool, &total), "accept boundary-sized pool");
    std::vector<tlc::Region> regions;
    CHECK(tll::make_regions(UINT64_C(0x100ffff000), total, 4, maximum_uniform_pool, &regions), "last byte at boundary");
    CHECK(valid(UINT64_C(0x100ffff000), total, maximum_uniform_pool, regions), "exact window end remains pure");
    CHECK(tll::reservation_pages(4, 65539, &total), "pool with remainder");
    CHECK(tll::make_regions(UINT64_C(0x100ffff000), total, 4, 65539, &regions), "remainder layout");
    CHECK(regions.size() == 4 && regions[3].pages == 16387, "last region owns remainder");
    CHECK(!tll::make_regions(1, total, 4, 65539, &regions) && regions.empty(), "reject unaligned base and clear output");
    CHECK(!tll::make_regions(0, total - 1, 4, 65539, &regions), "reject short reservation");
    CHECK(!tll::make_regions(std::numeric_limits<uintptr_t>::max() & ~uintptr_t(4095),
                            total, 4, 65539, &regions), "reject address overflow");
    CHECK(!tll::make_regions(0, std::numeric_limits<size_t>::max(), 4, 65539, &regions), "reject reservation overflow");
    CHECK(!tll::make_regions(0, total, 4, 65539, nullptr), "reject null region output");

    // 宿主仅 PROT_NONE 预约：验证真实返回地址布局及完整预约回收，不触发 PMU。
    CHECK(tll::reservation_pages(4, 65536, &total), "real reservation size");
    void* mapping = mmap(nullptr, total * 4096u, PROT_NONE,
                         MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    CHECK(mapping != MAP_FAILED, "host mmap succeeds");
    if (mapping != MAP_FAILED) {
        const uintptr_t base = reinterpret_cast<uintptr_t>(mapping);
        CHECK(tll::make_regions(base, total, 4, 65536, &regions), "real returned address layout");
        CHECK(valid(base, total, 65536, regions), "real reservation bounded and pure");
        if (regions.size() == 4) check_collectors(regions);
        CHECK(munmap(mapping, total * 4096u) == 0, "release complete original reservation");
    }
    if (failures) return 1;
    std::puts("tlb_set_layout_golden: 196608 offsets + bounds + real reservation + collectors PASS");
    return 0;
}
