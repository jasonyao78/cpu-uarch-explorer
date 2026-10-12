// SPDX-License-Identifier: Apache-2.0
// Frozen finite geometry: docs/design/2026-10-12-tlb-balanced-reach.md.
// All three families have page_id%256=i%256. VA bins are not hardware sets.
#pragma once
#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
namespace tlb_reach {
inline std::vector<unsigned> permutation(unsigned n,uint64_t state) {
    std::vector<unsigned> v(n);for(unsigned i=0;i<n;++i)v[i]=i;
    for(unsigned i=n? n-1:0;i>0;--i){state^=state<<13;state^=state>>7;state^=state<<17;std::swap(v[i],v[state%(i+1)]);}return v;
}
inline std::vector<unsigned> pages(const std::string& shape,unsigned n) {
    if(n>3072 || (shape!="dense"&&shape!="spaced"&&shape!="balanced-random"))throw std::runtime_error("page-set-request");
    static const auto groups=permutation(4096,271);std::vector<unsigned> out;
    for(unsigned i=0;i<n;++i)out.push_back(shape=="dense"?i:shape=="spaced"?257*i:256*groups[i]+i%256);return out;
}
struct Cell {
    std::string shape,offset,order;unsigned n,loads;uint64_t span_bytes,line_bytes;
    std::string id()const{return n?shape+"-"+offset+"-"+order+"-n"+std::to_string(n):"floor";}
};
inline std::vector<Cell> cells(bool reverse) {
    std::vector<Cell> out{{"floor","empty","empty",0,0,0,0}};
    for(const char* shape:{"dense","spaced","balanced-random"})for(const char* order:{"random","reverse-random"})for(unsigned n:{512u,1024u,1280u,1536u,1792u,2048u,2304u,2560u,3072u}) {
        auto p=pages(shape,n);auto bounds=std::minmax_element(p.begin(),p.end());out.push_back({shape,"rotated",order,n,(1048576/n)*n,uint64_t(*bounds.second-*bounds.first+1)*4096,uint64_t(n)*64});
    }
    if(reverse)std::reverse(out.begin(),out.end());return out;
}
inline std::vector<unsigned> order(const Cell& c) {auto out=permutation(c.n,137);if(c.order=="reverse-random")std::reverse(out.begin(),out.end());return out;}
// Stable page identity determines the offset, independent of visit order.
inline unsigned offset(unsigned page) {return 64*(page%64);}
inline uintptr_t link(char* base,const Cell& c,const std::vector<unsigned>& p,const std::vector<unsigned>& o) {
    if(!base || !c.n || p.size()!=c.n || o.size()!=c.n)throw std::runtime_error("graph-shape");
    auto node=[&](unsigned index){if(index>=c.n || p[index]>=1048576)throw std::runtime_error("graph-node");return reinterpret_cast<uintptr_t>(base)+uint64_t(p[index])*4096+offset(p[index]);};
    for(unsigned i=0;i<c.n;++i)*reinterpret_cast<uintptr_t*>(node(o[i]))=node(o[(i+1)%c.n]);return node(o[0]);
}
}
