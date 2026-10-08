// SPDX-License-Identifier: Apache-2.0
// tlb_set_layout.h — TLB set 区域预约内对齐（纯整数 VA，不执行映射）。
// 依据 docs/reviews/2026-10-08-a1-geometry-and-pilot-audit.md：旧任意 mmap
// 基址使 64MiB 池可能跨 256MiB 高位窗口，实际 pilot 有 14/50 purity=0。
// 探针与黄金测试共用本实现；不改变区域相对偏移或候选索引假设。
#pragma once

#include <limits>
#include <utility>
#include <vector>

#include "tlb_set_collect.h"

namespace tlb_set_layout {

constexpr size_t kPageBytes = 4096;
constexpr size_t kWindowPages = 65536;  // VA[35:28] 的一个 256MiB 窗口
constexpr size_t kSkewPages = 8;        // 保留历史 k×8 页的区域低字段差异

// 多区域形状合法时返回最坏对齐所需预约页数；失败不修改输出。
// 每区至少两页且整个池必须装进该区高位窗口；2..16 区域对应现有协议。
inline bool reservation_pages(int count, size_t pool_pages, size_t* result) {
    if (!result || count < 2 || count > 16) return false;
    const size_t n = static_cast<size_t>(count);
    const size_t per = pool_pages / n;
    const size_t last = pool_pages - per * (n - 1);
    if (per < 2) return false;
    for (size_t k = 0; k < n; ++k) {
        const size_t pages = k + 1 == n ? last : per;
        if (pages > kWindowPages - k * kSkewPages) return false;
    }
    // 前置形状检查使这些操作有界；额外一窗减一页覆盖任意页对齐基址。
    const size_t needed = (n - 1) * (kWindowPages + kSkewPages) + last
                        + kWindowPages - 1;
    if (needed > std::numeric_limits<size_t>::max() / kPageBytes ||
        needed > std::numeric_limits<uintptr_t>::max() / kPageBytes) return false;
    *result = needed;
    return true;
}

// 在调用方拥有的预约内布局；不 mmap、不读写地址、不改变内核映射。
// 成功给出全部区域，失败清空输出。调用方须用原预约起点/全长 munmap，
// 不能用对齐后的内部起点释放；不允许越界或地址/尺寸回绕。
inline bool make_regions(uintptr_t base, size_t reserved_pages, int count,
                         size_t pool_pages,
                         std::vector<tlb_set_collect::Region>* result) {
    if (!result) return false;
    result->clear();
    size_t needed = 0;
    if (!reservation_pages(count, pool_pages, &needed) || reserved_pages < needed ||
        base % kPageBytes != 0 ||
        reserved_pages > std::numeric_limits<uintptr_t>::max() / kPageBytes ||
        reserved_pages * kPageBytes > std::numeric_limits<uintptr_t>::max() - base)
        return false;
    const size_t page_offset = (base / kPageBytes) % kWindowPages;
    const size_t padding = (kWindowPages - page_offset) % kWindowPages;
    const size_t n = static_cast<size_t>(count);
    const size_t per = pool_pages / n;
    std::vector<tlb_set_collect::Region> regions;
    for (size_t k = 0; k < n; ++k) {
        const size_t off = padding + k * (kWindowPages + kSkewPages);
        const size_t pages = k + 1 == n ? pool_pages - per * (n - 1) : per;
        if (off > reserved_pages || pages > reserved_pages - off) return false;
        const uintptr_t start = base + off * kPageBytes;
        const uintptr_t end = start + pages * kPageBytes - 1;
        if ((start >> 28) != (end >> 28)) return false;
        regions.push_back({reinterpret_cast<char*>(start), pages});
    }
    *result = std::move(regions);
    return true;
}

}  // namespace tlb_set_layout
