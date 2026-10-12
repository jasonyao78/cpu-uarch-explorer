// SPDX-License-Identifier: Apache-2.0
// 同VA line集合的PFN邻接干预；纯函数，不观测或编造实际PFN。
// 契约与有限停止证明：docs/design/2026-10-12-tlb-pfn-association.md。
#pragma once
#include <algorithm>
#include <cstdint>
#include <numeric>
#include <set>
#include <stdexcept>
#include <vector>
namespace tlb_association {
// 返回VA相邻active页的±1 PFN邻接数；调用方先验证唯一可见PFN/全排列。
inline unsigned adjacent(const std::vector<uint64_t>& pfns,const std::vector<unsigned>& positions){
    unsigned count=0;
    for(size_t i=1;i<positions.size();++i){uint64_t a=pfns.at(positions[i-1]),b=pfns.at(positions[i]);if(a+1==b||b+1==a)++count;}
    return count;
}
// 校验输入和输出的全排列/mod64；zero_adjacent为真时拒绝任何实际邻接。
// PFN值必须是pagemap可表达的非零55位值，重复PFN不能当独立页。
inline void validate(const std::vector<uint64_t>& pfns,const std::vector<unsigned>& positions,bool zero_adjacent){
    const size_t n=pfns.size();
    if(n<1024||n>4096||n%64||positions.size()!=n)throw std::runtime_error("association-dimension");
    std::set<uint64_t> seen_pfns;
    for(uint64_t p:pfns)if(!p||p>=(UINT64_C(1)<<55)||!seen_pfns.insert(p).second)throw std::runtime_error("association-pfn");
    std::vector<bool> seen(n);
    for(size_t j=0;j<n;++j){unsigned i=positions[j];if(i>=n||seen[i]||i%64!=j%64)throw std::runtime_error("association-permutation");seen[i]=true;}
    if(zero_adjacent&&adjacent(pfns,positions))throw std::runtime_error("association-adjacent");
}
// 输出VA位置→物理节点。交换仅在mod64相同的节点之间，保持两侧line集合。
// 每bin≥16；每次修边最多8候选受±1关系排除，另排除自身；没有候选即拒绝，
// 禁止fallback到仍有邻接的近似图。已合格输入返回identity，不能虚报激励。
inline std::vector<unsigned> weave(const std::vector<uint64_t>& pfns){
    const size_t n=pfns.size();std::vector<unsigned> out(n);std::iota(out.begin(),out.end(),0u);validate(pfns,out,false);
    auto bad=[&](size_t i){uint64_t a=pfns[out[i]],b=pfns[out[i+1]];return a+1==b||b+1==a;};
    for(size_t a=0;a+1<n;++a){
        if(!bad(a))continue;
        const size_t b=a+1;bool repaired=false;
        for(size_t c=b%64;c<n;c+=64){
            if(c==b)continue;
            std::swap(out[b],out[c]);bool good=true;
            for(size_t pos:{b,c}){if((pos&&bad(pos-1))||(pos+1<n&&bad(pos)))good=false;}
            if(good){repaired=true;break;}
            std::swap(out[b],out[c]);
        }
        if(!repaired)throw std::runtime_error("association-no-candidate");
    }
    validate(pfns,out,true);return out;
}
}
