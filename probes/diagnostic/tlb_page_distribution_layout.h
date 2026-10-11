// SPDX-License-Identifier: Apache-2.0
// Q-A separates page set, visit order and offset(page ID).
// Contract: docs/design/2026-10-11-tlb-page-distribution.md (v1).
#pragma once
#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
namespace tlb_distribution {
inline std::vector<unsigned> permutation(unsigned n,uint64_t state) {
    std::vector<unsigned> v(n);for(unsigned i=0;i<n;++i)v[i]=i;
    for(unsigned i=n-1;i>0;--i){state^=state<<13;state^=state>>7;state^=state<<17;std::swap(v[i],v[state%(i+1)]);}return v;
}
inline std::vector<unsigned> pages(const std::string& shape,unsigned n) {
    if(n>2048 || (shape!="contiguous"&&shape!="sparse"&&shape!="random-set"))throw std::runtime_error("page-set-request");
    static const auto groups=permutation(4096,271);std::vector<unsigned> out;
    for(unsigned i=0;i<n;++i)out.push_back(shape=="contiguous"?i:shape=="sparse"?65*i:64*groups[i]+i%64);return out;
}
struct Cell {
    std::string shape,offset,order;unsigned n,loads;uint64_t span_bytes,line_bytes;
    std::string id()const{return n?shape+"-"+offset+"-"+order+"-n"+std::to_string(n):"floor";}
};
inline std::vector<Cell> cells(bool reverse) {
    std::vector<Cell> out{{"floor","empty","empty",0,0,0,0}};
    for(const char* shape:{"contiguous","sparse","random-set"})for(const char* offset:{"constant","rotated"})for(const char* order:{"random","reverse-random"})for(unsigned n:{32u,64u,80u,96u,112u,128u,160u,192u,256u,512u,1024u,2048u}) {
        auto p=pages(shape,n);auto bounds=std::minmax_element(p.begin(),p.end());out.push_back({shape,offset,order,n,(1048576/n)*n,uint64_t(*bounds.second-*bounds.first+1)*4096,uint64_t(n)*64});
    }
    if(reverse)std::reverse(out.begin(),out.end());return out;
}
inline std::vector<unsigned> order(const Cell& c) {
    auto out=permutation(c.n,137);if(c.order=="reverse-random")std::reverse(out.begin(),out.end());return out;
}
// Offset is a function of stable page ID, not visit-order index. All three sets
// have page_id%64 == i%64, giving exactly matched offset histograms at any N.
inline unsigned offset(const Cell& c,unsigned page) {return c.offset=="constant"?0:64*(page%64);}
inline uintptr_t link(char* base,const Cell& c,const std::vector<unsigned>& p,const std::vector<unsigned>& o) {
    if(!base || !c.n || p.size()!=c.n || o.size()!=c.n)throw std::runtime_error("graph-shape");
    auto node=[&](unsigned index){if(index>=c.n || p[index]>=262144)throw std::runtime_error("graph-node");return reinterpret_cast<uintptr_t>(base)+uint64_t(p[index])*4096+offset(c,p[index]);};
    for(unsigned i=0;i<c.n;++i)*reinterpret_cast<uintptr_t*>(node(o[i]))=node(o[(i+1)%c.n]);return node(o[0]);
}
}
