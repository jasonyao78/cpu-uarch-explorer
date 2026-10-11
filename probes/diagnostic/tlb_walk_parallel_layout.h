// SPDX-License-Identifier: Apache-2.0
// Frozen Q-D graph/footprint: docs/design/2026-10-11-tlb-walk-parallel.md.
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
namespace tlb_parallel {
struct Cell {
    std::string scope,layout;unsigned k,nodes,loads;
    uint64_t iterations,pages,line_bytes,span_bytes;
    std::string id() const {return k?scope+"-"+layout+"-k"+std::to_string(k)+"-l"+std::to_string(loads):"floor";}
};
// Exact finite plan, shared by --plan and target producer; floor reverses too.
inline std::vector<Cell> cells(bool reverse) {
    std::vector<Cell> out{{"floor","empty",0,0,0,0,0,0,0}};
    for(const char* scope:{"total","per-chain"})for(const char* layout:{"high","low"})
        for(unsigned k:{1u,2u,4u,8u})for(unsigned loads:{262144u,1048576u}) {
            const uint64_t n=8192u*(std::string(scope)=="per-chain"?k:1);
            const bool high=std::string(layout)=="high";
            const uint64_t pages=high?n:n/64,span=high?((n-1)*17+1)*4096:pages*4096;
            out.push_back({scope,layout,k,static_cast<unsigned>(n),loads,loads/k,pages,n*64,span});
        }
    if(reverse)std::reverse(out.begin(),out.end());return out;
}
using Chains=std::vector<std::vector<unsigned>>;
using Heads=std::array<uintptr_t,8>;
// Platform-independent unsigned modulo arithmetic; exact permutation audited
// independently in Python. Same seed, total nodes and K => same graph in low/high.
inline Chains indices(const Cell& c) {
    if(!c.k || c.k>8 || !c.nodes || c.nodes%c.k)throw std::runtime_error("chain-shape");
    std::vector<unsigned> order(c.nodes);for(unsigned i=0;i<c.nodes;++i)order[i]=i;
    uint64_t state=137;
    for(unsigned i=c.nodes-1;i>0;--i){state^=state<<13;state^=state>>7;state^=state<<17;std::swap(order[i],order[state%(i+1)]);}
    Chains chains;for(unsigned k=0;k<c.k;++k)chains.emplace_back(order.begin()+k*(c.nodes/c.k),order.begin()+(k+1)*(c.nodes/c.k));return chains;
}
// Different translation footprints, identical distinct data-line counts and
// offset distribution; neither physical cache-set nor PFN equality is claimed.
inline uint64_t offset(const Cell& c,unsigned i) {
    if(i>=c.nodes)throw std::runtime_error("node-index");
    return c.layout=="high"?uint64_t(i)*17*4096+uint64_t(i%64)*64:uint64_t(i)*64;
}
inline Heads link(char* memory,const Cell& c,const Chains& chains) {
    if(!memory || chains.size()!=c.k)throw std::runtime_error("chain-memory-shape");
    Heads heads{};
    for(unsigned k=0;k<c.k;++k) {
        const auto& chain=chains[k];if(chain.size()!=c.nodes/c.k)throw std::runtime_error("chain-length");
        for(size_t i=0;i<chain.size();++i)*reinterpret_cast<uintptr_t*>(memory+offset(c,chain[i]))=reinterpret_cast<uintptr_t>(memory+offset(c,chain[(i+1)%chain.size()]));
        heads[k]=reinterpret_cast<uintptr_t>(memory+offset(c,chain[0]));
    }
    return heads;
}
}
