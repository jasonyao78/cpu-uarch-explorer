// SPDX-License-Identifier: Apache-2.0
// Contract: docs/design/2026-10-11-tlb-address-geometry.md (frozen v1).
// VA group spacing is an observable geometry, not a certified hardware index.
#pragma once
#include "tlb_victim_history_layout.h"
namespace tlb_geometry {
using tlb_local::Addresses;
struct Cell : tlb_victim_history::Cell {
 unsigned target,step;
 std::string id() const {return "t"+std::to_string(target)+"-s"+std::to_string(step)+"-h"+std::to_string(h)+"-w"+std::to_string(w)+"-d"+std::to_string(direction);}
};
inline size_t family(unsigned target,unsigned step,unsigned h) {
 unsigned ti=target==7?0:target==100?1:target==200?2:3,si=step==1?0:step==2?1:step==16?2:3;
 if(ti==3 || si==3 || h<1 || h>2)throw std::runtime_error("geometry-family-identity");
 return ti*6+si*2+h-1;
}
// q is the high VPN group: preserve C signature while varying high-bit spacing.
inline std::vector<Addresses> targets(char* base,size_t pages,unsigned target,unsigned step) {
 (void)family(target,step,1);uintptr_t first=reinterpret_cast<uintptr_t>(base),limit=first+pages*4096,q0=((first>>12)+255)/256;
 std::vector<Addresses> out(2);
 for(unsigned h=1;h<=2;++h) {
  bool other[256]={};
  for(unsigned i=0;i<12;++i){uintptr_t q=q0+i*step,vpn=(q<<8)|(h==1?target:target^(q&255)),va=vpn<<12;unsigned key=tlb_set_collect::set_index(3-h,va);
   if(va<first || va>=limit || tlb_set_collect::set_index(h,va)!=target || other[key])throw std::runtime_error("geometry-address-shape");
   other[key]=true;out[h-1].push_back(va);
  }
 }
 return out;
}
inline std::vector<Addresses> families(char* base,size_t pages) {
 std::vector<Addresses> out;for(unsigned t:{7u,100u,200u})for(unsigned s:{1u,2u,16u}){auto p=targets(base,pages,t,s);out.push_back(p[0]);out.push_back(p[1]);}return out;
}
// Production planner, independent of PMU results; reverse changes order only.
inline std::vector<Cell> cells(bool reverse) {
 std::vector<Cell> out;for(unsigned t:{7u,100u,200u})for(unsigned s:{1u,2u,16u})for(unsigned d:{0u,1u})for(unsigned h:{1u,2u})for(unsigned w:{1u,8u,9u})out.push_back({{h,w,w==1?0u:4u,0,d,8,16},t,s});
 if(reverse)std::reverse(out.begin(),out.end());return out;
}
}
