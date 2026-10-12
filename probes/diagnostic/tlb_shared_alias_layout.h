// SPDX-License-Identifier: Apache-2.0
// Same backing node i in all VA shapes; MAP_FIXED stays inside owned mappings.
// Contract: docs/design/2026-10-12-tlb-shared-alias.md.
#pragma once
#include "tlb_balanced_reach_layout.h"
#include "page_policy.h"
#include <memory>
#include <array>
namespace tlb_alias {
constexpr unsigned max_nodes=2560;
inline size_t checked_page(size_t p){if(p<4096||p>65536||(p&(p-1)))throw std::runtime_error("alias-page-size");return p;}
inline unsigned shape_index(const std::string& s){if(s=="dense")return 0;if(s=="spaced")return 1;if(s=="balanced-random")return 2;throw std::runtime_error("alias-shape");}
inline std::vector<tlb_reach::Cell> cells(bool reverse){auto all=tlb_reach::cells(false);std::vector<tlb_reach::Cell> out;for(auto c:all)if(!c.n||c.n==1024||c.n==1536||c.n==1792||c.n==2048||c.n==2560)out.push_back(c);if(reverse)std::reverse(out.begin(),out.end());return out;}
struct OwnedFd {int value;explicit OwnedFd(int f):value(f){if(f<0)throw std::runtime_error("alias-fd");}~OwnedFd(){close(value);}OwnedFd(const OwnedFd&)=delete;OwnedFd& operator=(const OwnedFd&)=delete;};
struct Region {
    probe_common::GuardedMap g;
    Region(size_t bytes,size_t page):g(probe_common::map_guarded_anonymous(bytes,page)){if(!g.buf)throw std::runtime_error("alias-reservation");}
    ~Region(){munmap(g.mapping_base,g.mapping_bytes);}Region(const Region&)=delete;Region& operator=(const Region&)=delete;
};
// Takes fd ownership even on construction failure. Host-granule parameter is
// only for real software mapping tests; the Android producer requires 4096.
struct Space {
    OwnedFd fd;size_t page_bytes;Region canonical;std::array<std::unique_ptr<Region>,3> pools;std::array<char*,3> bases{};std::array<std::vector<unsigned>,3> page_ids;
    explicit Space(int f,size_t page):fd(f),page_bytes(checked_page(page)),canonical(size_t(max_nodes)*page_bytes,page_bytes){
        if(!page||page%4096||ftruncate(fd.value,off_t(max_nodes)*page))throw std::runtime_error("alias-backing-size");
        if(mmap(canonical.g.buf,size_t(max_nodes)*page,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,fd.value,0)!=canonical.g.buf)throw std::runtime_error("alias-canonical-map");
#ifdef __linux__
        if(madvise(canonical.g.buf,size_t(max_nodes)*page,MADV_NOHUGEPAGE))throw std::runtime_error("alias-canonical-policy");
#endif
        for(unsigned i=0;i<max_nodes;++i)*reinterpret_cast<volatile uintptr_t*>(canonical_node(i))=i+1;
        for(const char* sh:{"dense","spaced","balanced-random"}){
            unsigned j=shape_index(sh);size_t span=1048576ull*page,align=256*page;pools[j]=std::make_unique<Region>(span+align,page);uintptr_t start=reinterpret_cast<uintptr_t>(pools[j]->g.buf);bases[j]=reinterpret_cast<char*>((start+align-1)/align*align);if(reinterpret_cast<uintptr_t>(bases[j])+span>start+span+align)throw std::runtime_error("alias-owned-bounds");page_ids[j]=tlb_reach::pages(sh,max_nodes);
            for(unsigned i=0;i<max_nodes;++i){char* addr=bases[j]+uint64_t(page_ids[j][i])*page;if(mmap(addr,page,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,fd.value,off_t(i)*page)!=addr)throw std::runtime_error("alias-node-map");
#ifdef __linux__
                if(madvise(addr,page,MADV_NOHUGEPAGE))throw std::runtime_error("alias-node-policy");
#endif
                if(*reinterpret_cast<volatile uintptr_t*>(node(sh,i))!=i+1)throw std::runtime_error("alias-prefault-value");
            }
        }
    }
    uintptr_t canonical_node(unsigned i)const{if(i>=max_nodes)throw std::runtime_error("alias-canonical-index");return reinterpret_cast<uintptr_t>(canonical.g.buf)+size_t(i)*page_bytes+64*(i%64);}
    uintptr_t node(const std::string& shape,unsigned i)const{unsigned j=shape_index(shape);if(i>=max_nodes)throw std::runtime_error("alias-node-index");return reinterpret_cast<uintptr_t>(bases[j])+uint64_t(page_ids[j][i])*page_bytes+64*(i%64);}
    uintptr_t link(const tlb_reach::Cell& c)const{if(!c.n||c.n>max_nodes)throw std::runtime_error("alias-graph-n");auto o=tlb_reach::order(c);for(unsigned i=0;i<c.n;++i)*reinterpret_cast<uintptr_t*>(node(c.shape,o[i]))=node(c.shape,o[(i+1)%c.n]);return node(c.shape,o[0]);}
};
}
