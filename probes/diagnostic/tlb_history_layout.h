// SPDX-License-Identifier: Apache-2.0
// Protocol: docs/design/2026-10-09-tlb-history-discrimination.md.
// Four closed pointer rings share each page's one cache line; link before history.
#pragma once
#include "tlb_local_layout.h"
#include <string>
namespace tlb_history {
using tlb_local::Addresses;
inline std::vector<Addresses> targets(char* base,size_t pages,unsigned target) {
    auto result=tlb_local::targets(base,pages,target); // preserve the old nine
    for(int h=1;h<=2;++h) {
        bool other[256]={};
        for(auto va:result[h-1]) other[tlb_set_collect::set_index(3-h,va)]=true;
        Addresses extra; std::vector<int> counts(1);
        if(tlb_set_collect::collect_set_addrs(h,target,12,{{base,pages}},0,&extra,&counts)!=12)
            throw std::runtime_error("history-extra-collection");
        for(auto va:extra) {
            unsigned key=tlb_set_collect::set_index(3-h,va);
            if(result[h-1].size()<12 && !other[key]) { result[h-1].push_back(va);other[key]=true; }
        }
        if(result[h-1].size()!=12) throw std::runtime_error("history-extra-signature");
    }
    return result;
}
inline uintptr_t node(const Addresses& pages,unsigned i) { return pages.at(i)+64*i; }
inline void link(const Addresses& pages,unsigned w) {
    if(pages.size()!=12 || w==0 || w>12) throw std::runtime_error("history-link-shape");
    for(unsigned i=0;i<12;++i) {
        auto p=reinterpret_cast<uintptr_t*>(node(pages,i));
        p[0]=node(pages,i<w?(i+1)%w:i);
        p[1]=node(pages,i<w?(i+w-1)%w:i);
        p[2]=node(pages,i<6?(i+1)%6:i);
        p[3]=node(pages,(i+1)%12);
    }
}
inline uintptr_t walk(uintptr_t p,unsigned n,unsigned slot) {
    for(unsigned i=0;i<n;++i) p=*reinterpret_cast<volatile uintptr_t*>(p+8*slot);
    return p;
}
// Two closed filler prefixes share one cache line, avoiding F128 -> page129 speculation.
inline void link_filler(const Addresses& pages) {
    if(pages.size()!=512) throw std::runtime_error("history-filler-shape");
    for(unsigned i=0;i<512;++i) {
        auto p=reinterpret_cast<uintptr_t*>(pages[i]);
        p[0]=pages[(i+1)%512];
        p[1]=pages[i<128?(i+1)%128:i];
    }
}
struct Cell {
    unsigned f,h,w,history,direction,rounds; int victim,kind,block;
    std::string id() const {
        if(kind==0) return "floor-b"+std::to_string(block)+"-f"+std::to_string(f);
        std::string id=(kind==1?"trace-h":"victim-h")+std::to_string(h)+"-w"+std::to_string(w)+"-f"+std::to_string(f)+"-hist"+std::to_string(history)+"-d"+std::to_string(direction);
        return id;
    }
};
inline unsigned victim_index(unsigned trial,unsigned position) { return (trial+position)%8; }
inline std::vector<Cell> cells(bool reverse) {
    std::vector<Cell> out;
    for(unsigned f:{0u,128u,512u}) out.push_back({f,1,0,0,0,16,-1,0,0});
    for(unsigned h:{1u,2u}) for(unsigned w:{8u,9u,12u}) {
        if(w<=9) {
            for(unsigned history:{6u,12u}) for(unsigned d:{0u,1u}) out.push_back({128,h,w,history,d,16,-1,1,0});
            for(unsigned d:{0u,1u}) out.push_back({512,h,w,12,d,16,-1,1,0});
        }
        if(w==8 || w==12) out.push_back({0,h,w,12,0,16,-1,1,0});
        if(w==8) for(unsigned history:{6u,12u}) out.push_back({128,h,w,history,0,64,-1,2,0});
    }
    for(unsigned f:{0u,128u,512u}) out.push_back({f,1,0,0,0,16,-1,0,1});
    if(reverse) std::reverse(out.begin(),out.end());
    return out;
}
}
