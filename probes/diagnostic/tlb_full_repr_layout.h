// SPDX-License-Identifier: Apache-2.0
// Same backing demand graph, different stored representation.
// Contract: docs/design/2026-10-12-tlb-full-pointer-representation.md.
#pragma once
#include "tlb_shared_alias_layout.h"
namespace tlb_fullrepr {
constexpr uint64_t high_mask=UINT64_C(0x00a5000000000000),full_mask=UINT64_C(0x9e3779b97f4a7c15);
struct Cell {tlb_reach::Cell trace;std::string representation;uint64_t mask;std::string id()const{return trace.n?trace.id()+"-"+representation:"floor";}};
inline std::vector<Cell> cells(bool reverse){std::vector<Cell> out;for(auto c:tlb_alias::cells(false)){if(!c.n){out.push_back({c,"none",0});continue;}if(c.n!=1024&&c.n!=1792&&c.n!=2048)continue;out.push_back({c,"plain",0});out.push_back({c,"xor-high",high_mask});out.push_back({c,"xor-full",full_mask});}if(reverse)std::reverse(out.begin(),out.end());return out;}
// Each backing node contains encoded next VA. Accessed VA/order/offset is identical
// after decode; no statement about invisible speculation or zero-XOR elimination.
inline uintptr_t link(const tlb_alias::Space& sp,const Cell& c){if(!c.trace.n||c.trace.n>tlb_alias::max_nodes)throw std::runtime_error("repr-graph-n");if(!((c.representation=="plain"&&!c.mask)||(c.representation=="xor-high"&&c.mask==high_mask)||(c.representation=="xor-full"&&c.mask==full_mask)))throw std::runtime_error("repr-mask");auto o=tlb_reach::order(c.trace);for(unsigned i=0;i<c.trace.n;++i)*reinterpret_cast<uintptr_t*>(sp.node(c.trace.shape,o[i]))=sp.node(c.trace.shape,o[(i+1)%c.trace.n])^c.mask;return sp.node(c.trace.shape,o[0]);}
}
