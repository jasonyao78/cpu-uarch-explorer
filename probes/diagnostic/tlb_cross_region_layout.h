// SPDX-License-Identifier: Apache-2.0
// Frozen arithmetic/real links: docs/design/2026-10-11-tlb-cross-region.md.
// Model indices are candidates; no physical TLB set or PTE/PFN certification.
#pragma once
#include "tlb_victim_history_layout.h"
namespace tlb_region {
using tlb_local::Addresses;
using Shot=tlb_victim_history::Shot;
struct Cell {
 unsigned target,group,direction,w, victim=0,history_direction=0,passes=8,rounds=16;
 std::string id() const {return "t"+std::to_string(target)+"-g"+std::to_string(group)+"-w"+std::to_string(w)+"-d"+std::to_string(direction);}
};
inline size_t family(unsigned t,unsigned group) {
 if((t!=7&&t!=100)||group>2)throw std::runtime_error("region-family-identity");
 return (t==7?0:3)+group;
}
inline uintptr_t start(char *base,size_t pages) {
 uintptr_t b=reinterpret_cast<uintptr_t>(base),g=1ull<<30;
 if(!b||b%4096||pages!=524288||b>UINTPTR_MAX-2*g)throw std::runtime_error("region-pool-shape");
 return (b+g-1)&~(g-1);
}
// The global folded family shares page0 with the low-only and isolated families.
inline std::vector<Addresses> families(char *base,size_t pages) {
 uintptr_t a=start(base,pages),vpn0=a>>12,q0=vpn0>>8,hi0=(vpn0>>16)&255;
 std::vector<Addresses> out;
 for(unsigned t:{7u,100u})for(unsigned g=0;g<3;++g) {
  Addresses pp;
  for(unsigned i=0;i<12;++i) {
   uintptr_t region=g?i%4:0,j=g?i/4:i,q=q0+256*region+16*j,hi=(q>>8)&255;
   uintptr_t low=g==2?t^hi^hi0:t,vpn=(q<<8)|low,va=vpn<<12;
   if(va<a||va>=a+(1ull<<30))throw std::runtime_error("region-address-shape");
   pp.push_back(va);
  }
  out.push_back(pp);
 }
 return out;
}
// Exclude every occupied signature in all four candidate models, not just C1/C2.
inline Addresses fillers(char *base,size_t pages,const std::vector<Addresses>& ts) {
 bool used[4][256]={};
 for(const auto& pp:ts)for(auto va:pp)for(unsigned h=1;h<=4;++h)used[h-1][tlb_set_collect::set_index(h,va)]=true;
 Addresses out;
 for(size_t i=0;i<pages&&out.size()<512;++i) {
  uintptr_t va=reinterpret_cast<uintptr_t>(base)+i*4096;bool okay=true;
  for(unsigned h=1;h<=4;++h)if(used[h-1][tlb_set_collect::set_index(h,va)])okay=false;
  if(okay)out.push_back(va);
 }
 if(out.size()!=512)throw std::runtime_error("region-filler-collection");
 return out;
}
inline void validate(const Cell& c) {
 (void)family(c.target,c.group);
 if((c.w!=1&&c.w!=8&&c.w!=9&&c.w!=12)||c.victim!=0||c.direction>1||c.history_direction!=0||c.passes!=8||c.rounds!=16)throw std::runtime_error("region-cell-shape");
}
inline std::vector<Cell> cells(bool reverse) {
 std::vector<Cell> out;for(unsigned t:{7u,100u})for(unsigned g=0;g<3;++g)for(unsigned d:{0u,1u})for(unsigned w:{1u,8u,9u,12u})out.push_back({t,g,d,w});if(reverse)std::reverse(out.begin(),out.end());return out;
}
inline std::vector<unsigned> competitor_indices(const Cell& c) {
 validate(c);std::vector<unsigned> out;for(unsigned i=1;i<c.w;++i)out.push_back(i);if(c.direction)std::reverse(out.begin(),out.end());return out;
}
inline void link(const Addresses& pp,const Cell& c) {
 validate(c);if(pp.size()!=12)throw std::runtime_error("region-page-coverage");auto order=competitor_indices(c);
 for(unsigned i=0;i<12;++i){auto p=reinterpret_cast<uintptr_t*>(tlb_history::node(pp,i));p[0]=tlb_history::node(pp,i);p[3]=tlb_history::node(pp,(i+1)%12);p[4]=tlb_history::node(pp,i);}
 for(size_t i=0;i<order.size();++i)reinterpret_cast<uintptr_t*>(tlb_history::node(pp,order[i]))[4]=tlb_history::node(pp,order[(i+1)%order.size()]);
}
inline uintptr_t history_start(const Addresses& pp,const Cell& c) {validate(c);return tlb_history::node(pp,0);}
inline uintptr_t competitor_start(const Addresses& pp,const Cell& c) {auto order=competitor_indices(c);return order.empty()?0:tlb_history::node(pp,order.front());}
inline std::vector<Shot> schedule(const Cell& c) {validate(c);std::vector<Shot> out;for(unsigned t=0;t<16;++t)for(unsigned p=0;p<=8;++p)out.push_back({t,p,p==8});return out;}
}
