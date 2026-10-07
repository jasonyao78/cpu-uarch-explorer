// SPDX-License-Identifier: Apache-2.0
// tlb_set_collect.h — TLB set 地址收集器（RPA-02/PA-03 修复版）
//
// 从头文件提取的动机：收集器是评审复核的直接对象（生产选址函数提取
// 复现法），金样测试需要与探针**同源共享**本代码——各平台可编译、
// 不解引用任何地址（纯整数 VA 运算）。
//
// 契约：
//   - 每区域配额取样（need/K + 余数末区），跨高字段激励（PA-03）；
//   - per_region_counts 由调用点预分配 K 槽位，按 region_offset+局部序
//     **累加**（跨多次收集调用聚合，不追加）——RPA-02：调用次数 ≠ 区域数；
//   - region_offset：全域收集 = 0；隔离 scope k = k（槽位对齐原始区域 ID）。
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace tlb_set_collect {

constexpr uint32_t kSets = 256;  // X4 TRM Table 9-32（探测目标 set 空间）

// 候选索引假设 H1~H4：一律对最终虚拟地址计算（原型评审 R1/R3 修复口径）
inline uint32_t set_index(int hypothesis, uintptr_t va) {
    const uint64_t vpn = static_cast<uint64_t>(va) >> 12;  // 4K 粒度
    switch (hypothesis) {
    case 1:  return static_cast<uint32_t>(vpn & 0xFF);                    // H1 位选
    case 2:  return static_cast<uint32_t>((vpn ^ (vpn >> 8)) & 0xFF);     // H2 相邻 XOR
    case 3:  return static_cast<uint32_t>((vpn ^ (vpn >> 16)) & 0xFF);    // H3 高位折叠
    case 4:  return static_cast<uint32_t>((vpn ^ (vpn >> 8) ^ (vpn >> 16)) & 0xFF); // H4
    }
    return 0;  // 不可达：parse 期已校验 1..4
}

struct Region { char* base; size_t pages; };

// 跨多区域收集同 set 地址：need<=0 由调用点守卫（空窗模式不收集）；选
// 不足提前返回 found（< need），由调用点结构化失败。
inline int collect_set_addrs(int H, uint32_t target, int need,
                             const std::vector<Region>& regions,
                             size_t region_offset,
                             std::vector<uintptr_t>* vas,
                             std::vector<int>* per_region_counts) {
    if (need <= 0) return 0;
    const size_t k = regions.size();
    const int base_quota = need / static_cast<int>(k);
    const int remainder = need % static_cast<int>(k);
    int found = 0;
    for (size_t r = 0; r < k; ++r) {
        const int quota = base_quota + (r + 1 == k ? remainder : 0);
        if (quota <= 0) continue;
        const Region& region = regions[r];
        int region_found = 0;
        uint64_t bucket = region.pages / static_cast<uint64_t>(quota);
        if (bucket == 0) bucket = 1;
        for (uint64_t i = 1; i < region.pages && region_found < quota; ++i) {
            if (i < static_cast<uint64_t>(region_found) * bucket) continue;
            const uintptr_t va = reinterpret_cast<uintptr_t>(region.base)
                               + i * 4096u;
            if (set_index(H, va) != target) continue;
            int dup = 0;
            for (size_t q = 0; q < vas->size(); ++q)
                if ((*vas)[q] == va) { dup = 1; break; }
            if (!dup) { vas->push_back(va); ++found; ++region_found; }
        }
        (*per_region_counts)[region_offset + r] += region_found;
        if (region_found < quota) return found;  // 早退：调用点按 found<need 失败
    }
    return found;
}

// 无冲突负控（G0-3）：每页落不同 set，配额跨区域取样，used[] 全域去重。
inline int collect_scatter_addrs(int H, int need,
                                 const std::vector<Region>& regions,
                                 size_t region_offset,
                                 std::vector<uintptr_t>* vas,
                                 std::vector<int>* per_region_counts) {
    if (need <= 0) return 0;
    bool used[kSets] = {};
    const size_t k = regions.size();
    const int base_quota = need / static_cast<int>(k);
    const int remainder = need % static_cast<int>(k);
    int found = 0;
    for (size_t r = 0; r < k; ++r) {
        const int quota = base_quota + (r + 1 == k ? remainder : 0);
        if (quota <= 0) continue;
        const Region& region = regions[r];
        int region_found = 0;
        for (uint64_t i = 1; i < region.pages && region_found < quota; ++i) {
            const uintptr_t va = reinterpret_cast<uintptr_t>(region.base)
                               + i * 4096u;
            const uint32_t s = set_index(H, va);
            if (used[s]) continue;
            used[s] = true;
            vas->push_back(va);
            ++found;
            ++region_found;
        }
        (*per_region_counts)[region_offset + r] += region_found;
        if (region_found < quota) return found;
    }
    return found;
}

}  // namespace tlb_set_collect
