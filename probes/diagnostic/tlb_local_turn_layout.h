// SPDX-License-Identifier: Apache-2.0
// Contract: docs/design/2026-10-11-tlb-local-turn.md (frozen v1).
// New W grid has its own validation; old geometry/victim contracts stay fixed.
#pragma once
#include "tlb_address_geometry_layout.h"
namespace tlb_turn {
using tlb_local::Addresses;
using Shot=tlb_victim_history::Shot;
struct Cell : tlb_victim_history::Cell {
 unsigned target,step;
 std::string id() const {return "t"+std::to_string(target)+"-s"+std::to_string(step)+"-h"+std::to_string(h)+"-w"+std::to_string(w)+"-d"+std::to_string(direction);}
};
inline size_t family(unsigned target,unsigned step,unsigned h) {
 unsigned ti=target==7?0:target==100?1:2,si=step==1?0:step==16?1:2;
 if(ti==2 || si==2 || h<1 || h>2)throw std::runtime_error("turn-family-identity");
 return ti*4+si*2+h-1;
}
inline std::vector<Addresses> targets(char* base,size_t pages,unsigned target,unsigned step) {
 (void)family(target,step,1);return tlb_geometry::targets(base,pages,target,step);
}
inline std::vector<Addresses> families(char* base,size_t pages) {
 std::vector<Addresses> out;for(unsigned t:{7u,100u})for(unsigned s:{1u,16u}){auto p=targets(base,pages,t,s);out.push_back(p[0]);out.push_back(p[1]);}return out;
}
inline void validate(const Cell& c) {
 (void)family(c.target,c.step,c.h);
 if((c.w!=1 && (c.w<6 || c.w>10)) || c.victim!=(c.w==1?0u:4u) || c.direction>1 || c.history_direction!=0 || c.passes!=8 || c.rounds!=16)throw std::runtime_error("turn-cell-shape");
}
inline std::vector<Cell> cells(bool reverse) {
 std::vector<Cell> out;for(unsigned t:{7u,100u})for(unsigned s:{1u,16u})for(unsigned d:{0u,1u})for(unsigned h:{1u,2u})for(unsigned w:{1u,6u,7u,8u,9u,10u})out.push_back({{h,w,w==1?0u:4u,0,d,8,16},t,s});if(reverse)std::reverse(out.begin(),out.end());return out;
}
inline std::vector<unsigned> competitor_indices(const Cell& c) {
 validate(c);std::vector<unsigned> out;for(unsigned i=0;i<c.w;++i)if(i!=c.victim)out.push_back(i);if(c.direction)std::reverse(out.begin(),out.end());return out;
}
// Same actual nodes and slot positions for every W; only competitor prefix changes.
inline void link(const Addresses& pages,const Cell& c) {
 validate(c);if(pages.size()!=12)throw std::runtime_error("turn-pages");auto order=competitor_indices(c);
 for(unsigned i=0;i<12;++i){auto p=reinterpret_cast<uintptr_t*>(tlb_history::node(pages,i));p[0]=tlb_history::node(pages,i);p[3]=tlb_history::node(pages,(i+1)%12);p[4]=tlb_history::node(pages,i);}
 for(size_t i=0;i<order.size();++i)reinterpret_cast<uintptr_t*>(tlb_history::node(pages,order[i]))[4]=tlb_history::node(pages,order[(i+1)%order.size()]);
}
inline uintptr_t history_start(const Addresses& pages,const Cell& c) {validate(c);return tlb_history::node(pages,0);}
inline uintptr_t competitor_start(const Addresses& pages,const Cell& c) {auto order=competitor_indices(c);return order.empty()?0:tlb_history::node(pages,order.front());}
inline std::vector<Shot> schedule(const Cell& c) {validate(c);std::vector<Shot> out;for(unsigned r=0;r<c.rounds;++r)for(unsigned p=0;p<=c.passes;++p)out.push_back({r,p,p==c.passes});return out;}
}
