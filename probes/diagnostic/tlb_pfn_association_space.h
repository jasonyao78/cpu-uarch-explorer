// SPDX-License-Identifier: Apache-2.0
// 仅在自有guarded arena内重映射同memfd；实际页身份由producer的pagemap证书验证。
// 契约：docs/design/2026-10-12-tlb-pfn-association.md。
#pragma once
#include "tlb_pfn_association_layout.h"
#include "page_policy.h"
#include "tlb_balanced_reach_layout.h"
#include <memory>
namespace tlb_association {
constexpr unsigned max_nodes=4096;
constexpr uint64_t mask=UINT64_C(0x9e3779b97f4a7c15);
struct Cell {std::string assignment,order;unsigned n,loads;std::string id()const{return n?assignment+"-"+order+"-n"+std::to_string(n):"floor";}};
// 固定矩阵；order是物理节点顺序，不能借改映射偷偷改变物理需求轨迹。
inline std::vector<Cell> cells(bool reverse){std::vector<Cell> out{{"none","empty",0,0}};for(const char* a:{"natural","no-adjacent"})for(const char* o:{"random","reverse-random"})for(unsigned n:{1024u,1280u,1536u,1792u,2048u,2304u,2560u,3072u})out.push_back({a,o,n,(1048576/n)*n});if(reverse)std::reverse(out.begin(),out.end());return out;}
inline std::vector<unsigned> order(const Cell& c){auto o=tlb_reach::permutation(c.n,137);if(c.order=="reverse-random")std::reverse(o.begin(),o.end());return o;}
struct Region {
    probe_common::GuardedMap g;
    Region(size_t bytes,size_t page):g(probe_common::map_guarded_anonymous(bytes,page)){if(!g.buf)throw std::runtime_error("association-reserve");}
    ~Region(){munmap(g.mapping_base,g.mapping_bytes);}Region(const Region&)=delete;Region& operator=(const Region&)=delete;
};
struct OwnedFd {int fd;explicit OwnedFd(int f):fd(f){if(f<0)throw std::runtime_error("association-fd");}~OwnedFd(){close(fd);}OwnedFd(const OwnedFd&)=delete;OwnedFd& operator=(const OwnedFd&)=delete;};
// fd所有权即使构造失败也释放；page参数仅用于真实host测试，目标只接受4096。
inline size_t checked_page(size_t p){if(p<4096||p>65536||(p&(p-1)))throw std::runtime_error("association-page-size");return p;}
struct Space {
    OwnedFd file;size_t page;Region canonical,arena;char* base;std::vector<unsigned> inverse;
    explicit Space(int fd,size_t p):file(fd),page(checked_page(p)),canonical(max_nodes*page,page),arena((max_nodes+512)*page,page){
        if(p<4096||p>65536||(p&(p-1))||ftruncate(fd,max_nodes*p))throw std::runtime_error("association-page-size");
        if(mmap(canonical.g.buf,max_nodes*p,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,fd,0)!=canonical.g.buf)throw std::runtime_error("association-canonical-map");
        uintptr_t start=reinterpret_cast<uintptr_t>(arena.g.buf),align=512*p;base=reinterpret_cast<char*>((start+align-1)/align*align);
        if(uintptr_t(base)+max_nodes*p>start+(max_nodes+512)*p)throw std::runtime_error("association-owned-bounds");
        if(mmap(base,max_nodes*p,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,fd,0)!=base)throw std::runtime_error("association-arena-map");
        policy();for(unsigned i=0;i<max_nodes;++i){*reinterpret_cast<volatile uintptr_t*>(canonical_node(i))=i+1;volatile uintptr_t value=*reinterpret_cast<volatile uintptr_t*>(base+i*p+64*(i%64));(void)value;}
    }
    // 此建议不替代smaps前后证书；不改变设备全局THP设置。
    void policy(){
#ifdef __linux__
        if(madvise(canonical.g.buf,max_nodes*page,MADV_NOHUGEPAGE)||madvise(base,max_nodes*page,MADV_NOHUGEPAGE))throw std::runtime_error("association-page-policy");
#endif
    }
    uintptr_t canonical_node(unsigned i)const{if(i>=max_nodes)throw std::runtime_error("association-node-bounds");return reinterpret_cast<uintptr_t>(canonical.g.buf)+i*page+64*(i%64);}
    uintptr_t node(unsigned i)const{if(i>=inverse.size())throw std::runtime_error("association-active-bounds");return reinterpret_cast<uintptr_t>(base)+inverse[i]*page+64*(i%64);}
    // 返回实际使用的VA位置→节点，逆映射同时用于实际链接与pagemap取证。
    std::vector<unsigned> remap(const Cell& c,const std::vector<uint64_t>& canonical_pfns){
        if(!c.n){inverse.clear();return {};}
        if(c.n>max_nodes||canonical_pfns.size()!=max_nodes)throw std::runtime_error("association-remap-dimension");
        std::vector<uint64_t> active(canonical_pfns.begin(),canonical_pfns.begin()+c.n);std::vector<unsigned> positions(c.n);std::iota(positions.begin(),positions.end(),0u);
        if(c.assignment=="no-adjacent")positions=weave(active);else if(c.assignment!="natural")throw std::runtime_error("association-assignment");
        validate(active,positions,c.assignment=="no-adjacent");inverse.resize(c.n);
        // 前一cell较大N的置换不能残留在inactive区域；逐页恢复保持其它PTE有效，
        // 不以整arena unmap假装PTE物理页已受控。真实空间反例由生产映射测试守住。
        for(unsigned j=c.n;j<max_nodes;++j){char* dest=base+j*page;if(mmap(dest,page,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,file.fd,j*page)!=dest)throw std::runtime_error("association-inactive-restore");}

        for(unsigned j=0;j<c.n;++j){unsigned i=positions[j];inverse[i]=j;char* dest=base+j*page;if(mmap(dest,page,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,file.fd,i*page)!=dest)throw std::runtime_error("association-active-remap");volatile uintptr_t value=*reinterpret_cast<volatile uintptr_t*>(dest+64*(i%64));(void)value;}
        policy();return positions;
    }
    uintptr_t link(const Cell& c){if(!c.n)throw std::runtime_error("association-empty-link");auto o=order(c);for(unsigned j=0;j<c.n;++j)*reinterpret_cast<uintptr_t*>(canonical_node(o[j]))=node(o[(j+1)%c.n])^mask;return node(o[0]);}
};
}
