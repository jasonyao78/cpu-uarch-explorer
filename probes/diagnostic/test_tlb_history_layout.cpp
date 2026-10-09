// SPDX-License-Identifier: Apache-2.0
// Production layout and real traversal checks; no PMU/device claims.
#include "tlb_history_layout.h"
#include <cassert>
#include <algorithm>
int main() {
    for(uintptr_t hi: {1ull,123ull,65535ull}) {
        auto base=reinterpret_cast<char*>((hi<<28)+123*4096);
        auto old=tlb_local::targets(base,65536,100);
        auto full=tlb_history::targets(base,65536,100);
        for(unsigned h=0;h<2;++h) {
            assert(full[h].size()==12 && std::equal(old[h].begin(),old[h].end(),full[h].begin()));
            bool distinct[256]={};
            for(auto va:full[h]) { assert(tlb_set_collect::set_index(h+1,va)==100);distinct[tlb_set_collect::set_index(2-h,va)]=true; }
            assert(std::count(distinct,distinct+256,true)==12);
        }
    }
    alignas(4096) char memory[12*4096]{};
    tlb_local::Addresses pages;
    for(unsigned i=0;i<12;++i) pages.push_back(reinterpret_cast<uintptr_t>(memory)+i*4096);
    for(unsigned w: {6u,7u,8u,9u,10u,11u,12u}) {
        tlb_history::link(pages,w);
        for(unsigned slot=0;slot<4;++slot) {
            unsigned count=slot<2?w:slot==2?6:12;
            bool reverse=slot==1;
            auto start=tlb_history::node(pages,reverse?count-1:0),p=start;
            for(unsigned i=0;i<count;++i) {
                assert(p==tlb_history::node(pages,reverse?count-1-i:i));
                assert((p&4095)==64*(reverse?count-1-i:i));
                p=tlb_history::walk(p,1,slot);
            }
            assert(p==start);
            auto before=std::vector<char>(memory,memory+sizeof(memory));
            for(unsigned pass=0;pass<8;++pass) (void)tlb_history::walk(start,count,slot);
            assert(std::equal(before.begin(),before.end(),memory));
        }
    }
    alignas(4096) static char filler_memory[512*4096]{};
    tlb_local::Addresses filler;
    for(unsigned i=0;i<512;++i) filler.push_back(reinterpret_cast<uintptr_t>(filler_memory)+i*4096);
    tlb_history::link_filler(filler);
    for(unsigned f:{128u,512u}) {
        auto p=filler[0];for(unsigned i=0;i<f;++i) { assert(p==filler[i]);p=tlb_history::walk(p,1,f==128?1:0); }
        assert(p==filler[0]);
    }
    auto cells=tlb_history::cells(false), reversed=tlb_history::cells(true);
    assert(cells.size()==38);
    unsigned windows=0;for(auto& c:cells) { windows+=c.rounds;
        if(c.kind==2) for(unsigned trial=0;trial<8;++trial) {
            bool seen[8]={};for(unsigned pos=0;pos<8;++pos) { auto v=tlb_history::victim_index(trial,pos);assert(v<8 && !seen[v]);seen[v]=true; }
        }
    }
    assert(windows==800);std::reverse(reversed.begin(),reversed.end());
    for(size_t i=0;i<cells.size();++i) assert(cells[i].id()==reversed[i].id());
}
