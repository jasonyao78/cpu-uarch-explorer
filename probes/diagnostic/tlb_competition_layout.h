// SPDX-License-Identifier: Apache-2.0
// Contract: docs/design/2026-10-10-tlb-competition-observation.md.
// Every competing pass gets its own observed window; victim is trained only once.
#pragma once
#include "tlb_capacity_layout.h"
namespace tlb_competition {
struct Cell {
    unsigned h,k,direction,passes,rounds;
    std::string id() const {return "lookup-h"+std::to_string(h)+"-k"+std::to_string(k)+"-d"+std::to_string(direction)+"-p"+std::to_string(passes);}
};
struct Shot {unsigned round,pass_index;bool victim;};
// This fixed production sequence drives both --plan and actual measurement.
inline std::vector<Cell> cells(bool reverse) {
    std::vector<Cell> out;
    for(unsigned h:{1u,2u})for(unsigned k:{0u,7u,8u,9u,10u,11u})
        for(unsigned d:{0u,1u})for(unsigned p:{1u,2u,4u,8u})out.push_back({h,k,d,p,16});
    if(reverse)std::reverse(out.begin(),out.end());return out;
}
// Each trial completes all competitor passes, then one victim observation.
inline std::vector<Shot> schedule(const Cell& c) {
    if(c.h<1 || c.h>2 || (c.k!=0 && (c.k<7 || c.k>11)) || c.direction>1 ||
       (c.passes!=1 && c.passes!=2 && c.passes!=4 && c.passes!=8) || c.rounds!=16)
        throw std::runtime_error("competition-cell-shape");
    std::vector<Shot> out;
    for(unsigned t=0;t<c.rounds;++t)for(unsigned p=0;p<=c.passes;++p)out.push_back({t,p,p==c.passes});
    return out;
}
}
