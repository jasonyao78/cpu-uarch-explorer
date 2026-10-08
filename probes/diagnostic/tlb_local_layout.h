// SPDX-License-Identifier: Apache-2.0
// Fixed maximum set, then prefixes: W never participates in address collection.
#pragma once
#include "tlb_set_collect.h"
#include <algorithm>
#include <stdexcept>
#include <vector>
namespace tlb_local {
using Addresses=std::vector<uintptr_t>;
inline std::vector<Addresses> targets(char *base,size_t pages,unsigned target) {
    std::vector<Addresses> result(2);
    for(int h=1;h<=2;++h) {
        std::vector<int> counts(1);
        if(tlb_set_collect::collect_set_addrs(h,target,9,{{base,pages}},0,&result[h-1],&counts)!=9)
            throw std::runtime_error("target-collection");
        bool seen[256]={}; unsigned distinct=0;
        for(auto va:result[h-1]) {
            if(tlb_set_collect::set_index(h,va)!=target) throw std::runtime_error("target-signature");
            unsigned other=tlb_set_collect::set_index(3-h,va);
            if(!seen[other]) { seen[other]=true; ++distinct; }
        }
        if(distinct<8) throw std::runtime_error("target-control-not-dispersed");
    }
    return result;
}
// A/C share one filler pool. Exclude all occupied candidate leaf sets in both Hs.
inline Addresses fillers(char *base,size_t pages,const std::vector<Addresses>& ts) {
    bool used[2][256]={};
    for(auto& family:ts) for(auto va:family) for(int h=1;h<=2;++h)
        used[h-1][tlb_set_collect::set_index(h,va)]=true;
    Addresses f;
    for(size_t p=0;p<pages && f.size()<512;++p) {
        uintptr_t va=reinterpret_cast<uintptr_t>(base)+p*4096;
        if(!used[0][tlb_set_collect::set_index(1,va)] && !used[1][tlb_set_collect::set_index(2,va)])
            f.push_back(va);
    }
    if(f.size()!=512) throw std::runtime_error("filler-collection");
    return f;
}
inline Addresses nodes(const Addresses& pages,unsigned w,bool rotate) {
    if(w>pages.size()) throw std::runtime_error("prefix-too-large");
    Addresses out;
    for(unsigned i=0;i<w;++i) out.push_back(pages[i]+(rotate?64*i:0));
    return out;
}
inline void chain(const Addresses& nodes) {
    for(size_t i=0;i<nodes.size();++i) *reinterpret_cast<uintptr_t*>(nodes[i])=nodes[(i+1)%nodes.size()];
}
inline uintptr_t chase(uintptr_t p,size_t n) {
    for(size_t i=0;i<n;++i) p=*reinterpret_cast<volatile uintptr_t*>(p);
    return p;
}
}
