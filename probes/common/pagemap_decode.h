// SPDX-License-Identifier: Apache-2.0
// Linux pagemap bit layout; zero PFN is opaque, never visibility certification.
// Contract: docs/design/2026-10-12-pagemap-visibility.md.
#pragma once
#include <cstdint>
struct pagemap_bits {uint64_t pfn;bool present,swapped;};
inline pagemap_bits pagemap_decode(uint64_t entry) {
    return {entry&((uint64_t(1)<<55)-1),bool(entry&(uint64_t(1)<<63)),bool(entry&(uint64_t(1)<<62))};
}
