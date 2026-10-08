#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""提取生产区域预约块，用确定性 mmap 返回地址复现高位跨窗；不执行 PMU。

仅替换 mmap/mprotect/madvise/munmap 外部调用，布局算法保持生产源码。
覆盖接近窗口尾部的地址以及所有 4KiB 页偏移；退出 0 表示几何断言通过。
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    """编译提取块并运行断言；编译/运行失败原样传播退出码。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', required=True, type=Path)
    args = parser.parse_args()
    root = args.tree.resolve()
    source = (root / 'probes/cache-mem/ptr_chase.cpp').read_text()
    block = source.split('// ---- 目标池：', 1)[1].split('// ---- 目标地址收集', 1)[0]
    block = block[block.index('    std::vector<tlc::Region> regions;'):]
    for name in ('mmap', 'mprotect', 'madvise', 'munmap'):
        block = block.replace(name + '(', 'fake_' + name + '(')
    includes = '#include "tlb_set_collect.h"\n'
    if '"tlb_set_layout.h"' in source:
        includes += '#include "tlb_set_layout.h"\nnamespace tll = tlb_set_layout;\n'
    harness = r'''
#include <cstdint>
#include <cstdio>
#include <limits>
#include <vector>
#include <sys/mman.h>
#ifndef MAP_NORESERVE
#define MAP_NORESERVE 0
#endif
''' + includes + r'''
namespace tlc = tlb_set_collect;
constexpr size_t kRegionStridePages = 65536;
struct Options { int regions; size_t pool_pages; };
static uintptr_t fake_base;
static size_t reserved_bytes;
static bool protect_outside;
static void* fake_mmap(void*, size_t bytes, int, int, int, long long) {
    reserved_bytes = bytes;
    return reinterpret_cast<void*>(fake_base);
}
static int fake_mprotect(void* base, size_t bytes, int) {
    const uintptr_t start = reinterpret_cast<uintptr_t>(base);
    if (start < fake_base || bytes > reserved_bytes ||
        start - fake_base > reserved_bytes - bytes) protect_outside = true;
    return 0;
}
static int fake_madvise(void*, size_t, int) { return 0; }
static int fake_munmap(void*, size_t) { return 0; }
static int check(int n, size_t pages, size_t offset) {
    Options opt{n, pages};
    fake_base = UINT64_C(0x1000000000) + offset * 4096u;
    reserved_bytes = 0;
    protect_outside = false;
''' + block + r'''
    if (protect_outside || regions.size() != static_cast<size_t>(n)) return 1;
    for (size_t k = 0; k < regions.size(); ++k) {
        const auto& r = regions[k];
        const uintptr_t first = reinterpret_cast<uintptr_t>(r.base);
        const uintptr_t last = first + r.pages * 4096u - 1;
        if ((first >> 28) != (last >> 28)) {
            std::fprintf(stderr, "vpn-hi-impure: regions=%d offset_pages=%zu region=%zu\n", n, offset, k);
            return 1;
        }
    }
    return 0;
}
int main() {
    if (check(4, 65536, 65535)) return 1;
    for (size_t off = 0; off < 65536; ++off)
        for (int n : {2, 4, 16})
            if (check(n, 65536, off)) return 1;
    std::puts("production layout: 196608 page-offset/region combinations PASS");
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='tlb-region-boundary-') as tmp:
        cpp, binary = Path(tmp) / 'check.cpp', Path(tmp) / 'check'
        cpp.write_text(harness)
        built = subprocess.run(['c++', '-std=c++17', '-O2', '-I', str(root / 'probes/common'),
                                str(cpp), '-o', str(binary)])
        if built.returncode:
            return built.returncode
        return subprocess.run([str(binary)]).returncode


if __name__ == '__main__':
    raise SystemExit(main())
