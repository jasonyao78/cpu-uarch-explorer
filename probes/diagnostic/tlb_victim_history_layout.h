// SPDX-License-Identifier: Apache-2.0
// Contract: docs/design/2026-10-11-tlb-victim-history.md (frozen v1).
// Same active page set, variable victim and history; no physical ways claim.
#pragma once
#include "tlb_history_layout.h"
namespace tlb_victim_history {
using tlb_local::Addresses;
struct Cell {
 unsigned h,w,victim,history_direction,direction,passes,rounds;
 std::string id() const {return "victim-h"+std::to_string(h)+"-w"+std::to_string(w)+"-v"+std::to_string(victim)+"-hist"+std::to_string(history_direction)+"-d"+std::to_string(direction);}
};
struct Shot {unsigned round,pass_index;bool victim;};
inline void validate(const Cell& c) {
 if(c.h<1 || c.h>2 || (c.w!=1 && c.w!=8 && c.w!=9) || (c.victim!=0 && c.victim!=c.w/2 && c.victim!=c.w-1) || c.victim>=c.w || c.history_direction>1 || c.direction>1 || c.passes!=8 || c.rounds!=16)throw std::runtime_error("victim-history-cell-shape");
}
// Single finite production sequence for --plan and actual measurement.
inline std::vector<Cell> cells(bool reverse) {
 std::vector<Cell> out;
 for(unsigned hd:{0u,1u})for(unsigned w:{1u,8u,9u}) {
  std::vector<unsigned> victims=w==1?std::vector<unsigned>{0}:std::vector<unsigned>{0,w/2,w-1};
  for(unsigned v:victims)for(unsigned d:{0u,1u})for(unsigned h:{1u,2u})out.push_back({h,w,v,hd,d,8,16});
 }
 if(reverse)std::reverse(out.begin(),out.end());return out;
}
// Exactly [0,W) minus victim. Direction changes order, never page membership.
inline std::vector<unsigned> competitor_indices(const Cell& c) {
 validate(c);std::vector<unsigned> out;for(unsigned i=0;i<c.w;++i)if(i!=c.victim)out.push_back(i);if(c.direction)std::reverse(out.begin(),out.end());return out;
}
// Write once per cell, outside trials; all three slots share each node cacheline.
inline void link(const Addresses& pages,const Cell& c) {
 validate(c);if(pages.size()!=12)throw std::runtime_error("victim-history-pages");
 auto order=competitor_indices(c);
 for(unsigned i=0;i<12;++i) {
  auto p=reinterpret_cast<uintptr_t*>(tlb_history::node(pages,i));
  p[0]=tlb_history::node(pages,i);p[3]=tlb_history::node(pages,(i+(c.history_direction?11:1))%12);p[4]=tlb_history::node(pages,i);
 }
 for(size_t i=0;i<order.size();++i)reinterpret_cast<uintptr_t*>(tlb_history::node(pages,order[i]))[4]=tlb_history::node(pages,order[(i+1)%order.size()]);
}
inline uintptr_t history_start(const Addresses& pages,const Cell& c) {validate(c);return tlb_history::node(pages,c.history_direction?11:0);}
// Zero competitor path reads no page or metadata pointer.
inline uintptr_t competitor_start(const Addresses& pages,const Cell& c) {
 auto order=competitor_indices(c);return order.empty()?0:tlb_history::node(pages,order.front());
}
inline std::vector<Shot> schedule(const Cell& c) {
 validate(c);std::vector<Shot> out;for(unsigned t=0;t<c.rounds;++t)for(unsigned p=0;p<=c.passes;++p)out.push_back({t,p,p==c.passes});return out;
}
}
