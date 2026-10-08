// SPDX-License-Identifier: Apache-2.0
// Integer-only VA checks call production selection; no fake PMU/device claims.
#include "tlb_local_layout.h"
#include <cassert>
int main() {
    for(unsigned target: {100u,200u}) for(uintptr_t hi: {1ull,7ull,123ull,65535ull}) for(uintptr_t low: {0ull,4096ull,123ull*4096}) {
        auto ts=tlb_local::targets(reinterpret_cast<char*>((hi<<28)+low),65536,target);
        auto f=tlb_local::fillers(reinterpret_cast<char*>(((hi+2)<<28)+low),2048,ts);
        assert(f.size()==512);
        for(auto family:ts) for(auto target:family) for(auto fv:f) for(int h=1;h<=2;++h)
            assert(tlb_set_collect::set_index(h,target)!=tlb_set_collect::set_index(h,fv));
        for(auto family:ts) for(bool rotate: {false,true}) {
            auto eight=tlb_local::nodes(family,8,rotate),nine=tlb_local::nodes(family,9,rotate);
            assert(std::equal(eight.begin(),eight.end(),nine.begin()));
            for(size_t i=0;i<9;++i) {
                assert((nine[i]>>12)==(family[i]>>12));
                assert((nine[i]&4095)==(rotate?64*i:0));
            }
        }
    }
    alignas(4096) char mem[9*4096]{};
    tlb_local::Addresses pages;
    for(unsigned i=0;i<9;++i) pages.push_back(reinterpret_cast<uintptr_t>(mem)+i*4096);
    for(unsigned w: {9u,8u,9u}) for(bool rotate: {false,true}) {
        auto ns=tlb_local::nodes(pages,w,rotate); tlb_local::chain(ns);
        uintptr_t p=ns[0];
        for(unsigned i=0;i<w;++i) { assert(p==ns[i]); p=tlb_local::chase(p,1); }
        assert(p==ns[0]);
    }
}
