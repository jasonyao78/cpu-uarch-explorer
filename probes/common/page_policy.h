// SPDX-License-Identifier: Apache-2.0
// page_policy.h — 探针共享页策略与 backing 审计支撑（M0-1 从 ptr_chase 抬升）
//
// 内容（与 ptr_chase v1 战役版逐字同语义，仅做命名空间包装）：
//   - hugetlb 映射（strict/fallback，退出码语义不变）
//   - PROT_NONE 守卫 VMA 的匿名映射（Android VMA 合并规避，smaps 精确归属前提）
//   - /proc/self/smaps 的 AnonHugePages 端点解析（归属精确性保守规则）
//   - backing 分类（base / thp / mixed）
//
// 行为契约（对 runner/protocol guard 不可见部分的约束）：
//   - 任何失败路径的退出码与 ptr_chase 原实现一致（1=环境错误，2=能力不支持）
//   - 不向 stdout 输出任何东西（探针 stdout 是 record 通道）
//
// 提取来源：probes/cache-mem/ptr_chase.cpp（commit 9316853 状态，第一次战役硬化版）
#pragma once

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <unistd.h>
#include <sys/mman.h>

// MAP_HUGETLB 为 Linux 专有；无此能力的平台请求 hugepage 时以退出码 2 回应。
#ifndef MAP_HUGETLB
#define PROBE_COMMON_NO_HUGEPAGE 1
#else
#define PROBE_COMMON_NO_HUGEPAGE 0
#endif

namespace probe_common {

inline unsigned base_page_kb() {
    const long bytes = sysconf(_SC_PAGESIZE);
    return bytes > 0 ? static_cast<unsigned>(bytes / 1024) : 0;
}

// hugetlb 分配：尺寸向上取整到 2MB 对齐 + MAP_HUGETLB；缺页池时 strict 退出 2、
// 非 strict 回退普通匿名映射（返回 nullptr，实际 backing 由调用方独立观测）。
inline char* map_hugetlb_buffer(size_t bytes, bool want_hp, bool strict_hp) {
#if PROBE_COMMON_NO_HUGEPAGE
    (void)bytes; (void)strict_hp;
    if (want_hp) {
        std::fprintf(stderr, "unsupported: MAP_HUGETLB not available on this platform\n");
        std::exit(2);
    }
    return nullptr;
#else
    if (!want_hp)
        return nullptr;
    constexpr size_t kHp = 2 * 1024 * 1024;
    const size_t hp_bytes = (bytes + kHp - 1) / kHp * kHp;
    char* buf = static_cast<char*>(mmap(nullptr, hp_bytes, PROT_READ | PROT_WRITE,
                                        MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB, -1, 0));
    if (buf != MAP_FAILED) {
        return buf;
    }
    if (strict_hp) {
        std::fprintf(stderr, "unsupported: hugepage pool unavailable (strict mode)\n");
        std::exit(2);
    }
    std::fprintf(stderr, "warning: hugepage pool unavailable, falling back to a "
                         "default anonymous mapping; actual backing will be inspected\n");
    return nullptr;
#endif
}

// PROT_NONE 守卫映射：两侧 guard page 强制目标 RW 段成为边界精确的独立 VMA
// （匿名 mmap 可与邻接同属性 VMA 合并，Android 实测无法把 VMA 级 AnonHugePages
// 精确归到目标 buffer）。调用方负责 Linux 基础页尺寸前置校验。
// 失败返回 buf == nullptr（mapping_base 亦 nullptr），调用方按 perror 语义处理。
struct GuardedMap { char* mapping_base; char* buf; size_t mapping_bytes; };

inline GuardedMap map_guarded_anonymous(size_t bytes, size_t base_page_bytes) {
    GuardedMap g { nullptr, nullptr, 0 };
    const size_t normal = (bytes + base_page_bytes - 1) / base_page_bytes * base_page_bytes;
    g.mapping_bytes = normal + 2 * base_page_bytes;
    g.mapping_base = static_cast<char*>(mmap(
        nullptr, g.mapping_bytes, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
    if (g.mapping_base == MAP_FAILED) {
        g.mapping_base = nullptr;
        g.mapping_bytes = 0;
        return g;
    }
    g.buf = g.mapping_base + base_page_bytes;
    if (mprotect(g.buf, normal, PROT_READ | PROT_WRITE) != 0) {
        munmap(g.mapping_base, g.mapping_bytes);
        g.mapping_base = nullptr;
        g.buf = nullptr;
        g.mapping_bytes = 0;
        return g;
    }
    return g;
}

// 解析 /proc/self/smaps 中目标映射的 AnonHugePages 总量。
// 归属精确性保守规则：VMA 超出目标映射时只有整段 AnonHugePages=0 才可
// 无歧义判 base；覆盖不足或归属不精确且总量>0 时返回 false（拒绝猜测）。
inline bool read_anon_huge_kb(const char* buf, size_t bytes, size_t* anon_huge_kb) {
    std::ifstream smaps("/proc/self/smaps");
    if (!smaps)
        return false;

    const uintptr_t target_begin = reinterpret_cast<uintptr_t>(buf);
    const uintptr_t target_end = target_begin + bytes;
    bool overlaps = false;
    bool saw_target_vma = false;
    bool attribution_exact = true;
    size_t covered_bytes = 0;
    size_t total = 0;
    std::string line;
    while (std::getline(smaps, line)) {
        unsigned long long begin = 0, end = 0;
        if (std::sscanf(line.c_str(), "%llx-%llx", &begin, &end) == 2) {
            overlaps = static_cast<uintptr_t>(end) > target_begin
                    && static_cast<uintptr_t>(begin) < target_end;
            if (overlaps) {
                if (static_cast<uintptr_t>(begin) < target_begin
                        || static_cast<uintptr_t>(end) > target_end)
                    attribution_exact = false;
                saw_target_vma = true;
                const uintptr_t overlap_begin =
                    static_cast<uintptr_t>(begin) > target_begin
                        ? static_cast<uintptr_t>(begin) : target_begin;
                const uintptr_t overlap_end =
                    static_cast<uintptr_t>(end) < target_end
                        ? static_cast<uintptr_t>(end) : target_end;
                covered_bytes += static_cast<size_t>(overlap_end - overlap_begin);
            }
            continue;
        }
        if (overlaps) {
            size_t value = 0;
            if (std::sscanf(line.c_str(), "AnonHugePages: %zu kB", &value) == 1)
                total += value;
        }
    }
    if (!saw_target_vma || covered_bytes < bytes)
        return false;
    if (total > 0 && !attribution_exact)
        return false;
    *anon_huge_kb = total;
    return true;
}

struct PageBackingClass {
    const char* actual;
    unsigned page_kb;
};

inline PageBackingClass classify_page_backing(size_t anon_huge_kb, size_t mapping_bytes) {
    if (anon_huge_kb == 0)
        return {"base", base_page_kb()};
    const size_t fully_backed_kb = (mapping_bytes + 1023) / 1024;
    if (anon_huge_kb >= fully_backed_kb)
        return {"thp", 2048};
    return {"mixed", 0};
}

} // namespace probe_common
