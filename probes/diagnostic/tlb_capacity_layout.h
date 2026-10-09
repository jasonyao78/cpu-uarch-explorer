// SPDX-License-Identifier: Apache-2.0
// 固定最大页集合上的工作集轨迹与单 victim 竞争矩阵。
// 设计锚点：docs/design/2026-10-09-tlb-local-capacity.md（冻结 v1）。
// 复用 history 的旧九页前缀和四槽；第五槽仅用于不含 victim 的竞争闭环。
#pragma once
#include "tlb_history_layout.h"

namespace tlb_capacity {
using tlb_local::Addresses;

// 建链只在条件开始时执行；形状无效时抛 runtime_error，且不写目标页。
// slot4 的有效集合固定为 1..K，方向只改变顺序，K0 时没有竞争访问。
inline void link(const Addresses& pages,unsigned w,unsigned k,unsigned direction) {
    if(pages.size()!=12 || w==0 || w>12 || k>11 || direction>1)
        throw std::runtime_error("capacity-link-shape");
    tlb_history::link(pages,w);
    for(unsigned i=0;i<12;++i) {
        unsigned next=i;
        if(i>=1 && i<=k) next=direction?(i==1?k:i-1):(i==k?1:i+1);
        reinterpret_cast<uintptr_t*>(tlb_history::node(pages,i))[4]=tlb_history::node(pages,next);
    }
}

// 返回闭环起点；K0 不读取 pages，保证零竞争条件不接触目标或元数据。
inline uintptr_t competitor_start(const Addresses& pages,unsigned k,unsigned direction) {
    if(k>11 || direction>1) throw std::runtime_error("capacity-competitor-shape");
    if(k==0) return 0;
    if(pages.size()!=12) throw std::runtime_error("capacity-competitor-shape");
    return tlb_history::node(pages,direction?k:1);
}

// 只沿第五槽读取 count 次，返回末指针；count0 不解引用 p，不修改内存。
inline uintptr_t walk_competitors(uintptr_t p,unsigned count) {
    return tlb_history::walk(p,count,4);
}

// 与 history JSON 字段同义；k 只在 kind2 使用，direction 此时表示竞争顺序。
struct Cell {
    unsigned f,h,w,history,direction,rounds,k;
    int victim,kind,block;
    // 稳定唯一标识供生产计划和原始窗口配对，不包含映射地址。
    std::string id() const {
        if(kind==0) return "floor-b"+std::to_string(block)+"-f"+std::to_string(f);
        auto id=std::string(kind==1?"trace-h":"victim-h")+std::to_string(h)+"-w"+std::to_string(w)+"-f"+std::to_string(f)+"-hist"+std::to_string(history)+"-d"+std::to_string(direction);
        if(kind==2) id+="-k"+std::to_string(k);
        return id;
    }
};

// 唯一生产矩阵：94 条/2080 窗；reverse 只完整反转条目，条内轮次不反转。
// 计数来自冻结 v1：896+256+64+768+96，不按设备结果改变条件或顺序。
inline std::vector<Cell> cells(bool reverse) {
    std::vector<Cell> out;
    for(unsigned f:{0u,128u,512u}) out.push_back({f,1,0,0,0,16,0,-1,0,0});
    for(unsigned h:{1u,2u}) for(unsigned w=6;w<=12;++w) for(unsigned d:{0u,1u})
        out.push_back({128,h,w,12,d,32,0,-1,1,0});
    for(unsigned h:{1u,2u}) for(unsigned w:{7u,8u,9u,10u})
        out.push_back({512,h,w,12,0,32,0,-1,1,0});
    for(unsigned h:{1u,2u}) for(unsigned w:{8u,12u})
        out.push_back({0,h,w,12,0,16,0,-1,1,0});
    for(unsigned h:{1u,2u}) for(unsigned k=0;k<=11;++k) for(unsigned d:{0u,1u})
        out.push_back({128,h,1,12,d,16,k,0,2,0});
    for(unsigned f:{0u,128u,512u}) out.push_back({f,1,0,0,0,16,0,-1,0,1});
    if(reverse) std::reverse(out.begin(),out.end());
    return out;
}
}
