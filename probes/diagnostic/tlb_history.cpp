// SPDX-License-Identifier: Apache-2.0
// Standalone diagnostic, not runner schema. Purpose/protocol:
// docs/design/2026-10-09-tlb-history-discrimination.md.
#include "tlb_history_layout.h"
#include "page_policy.h"
#include "perf_window.h"
#include <cstdio>
#include <cstdlib>
#include <random>
#ifdef __linux__
#include <sched.h>
#endif
static void array(const tlb_local::Addresses& a) {
    std::printf("[");for(size_t i=0;i<a.size();++i) std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(a[i]));std::printf("]");
}
static void config(bool reverse) {
    std::printf("{\"type\":\"config\",\"version\":1,\"target\":100,\"seed\":137,\"max_w\":12,\"old_prefix\":9,\"offset_rotate\":true,\"link_slots\":4,\"reverse\":%s,\"cells\":38,\"windows\":800}\n",reverse?"true":"false");
}
static void plan(bool reverse) {
    config(reverse);
    auto cs=tlb_history::cells(reverse);
    for(size_t i=0;i<cs.size();++i) {
        auto c=cs[i];
        std::printf("{\"type\":\"cell\",\"cell\":\"%s\",\"position\":%zu,\"kind\":%d,\"h\":%u,\"w\":%u,\"f\":%u,\"history\":%u,\"direction\":%u,\"victim\":%d,\"block\":%d,\"rounds\":%u}\n",c.id().c_str(),i,c.kind,c.h,c.w,c.f,c.history,c.direction,c.victim,c.block,c.rounds);
    }
}
#ifdef __linux__
static void backing(const probe_common::GuardedMap& g,size_t bytes) {
    size_t huge=1;
    if(!probe_common::read_anon_huge_kb(g.buf,bytes,&huge) || huge) throw std::runtime_error("backing-not-base-4k");
}
#endif
int main(int argc,char**argv) {
    try {
        if((argc!=2 && argc!=3) || (std::string(argv[1])!="100" && std::string(argv[1])!="--plan") || (argc==3 && std::string(argv[2])!="--reverse")) throw std::runtime_error("usage-tlb_history-100-or-plan-reverse");
        if(std::string(argv[1])=="--plan") { plan(argc==3);return 0; }
#if !defined(__linux__) || !defined(__aarch64__)
        (void)array;throw std::runtime_error("measurement-requires-linux-aarch64");
#else
        if(sysconf(_SC_PAGESIZE)!=4096) throw std::runtime_error("page-size");
        cpu_set_t cpus;CPU_ZERO(&cpus);CPU_SET(7,&cpus);
        if(sched_setaffinity(0,sizeof(cpus),&cpus) || sched_getcpu()!=7) throw std::runtime_error("affinity");
        constexpr size_t pool_bytes=65536ull*4096,fill_bytes=2048ull*4096;
        auto pool=probe_common::map_guarded_anonymous(pool_bytes,4096),fill=probe_common::map_guarded_anonymous(fill_bytes,4096);
        if(!pool.buf || !fill.buf || madvise(pool.buf,pool_bytes,MADV_NOHUGEPAGE) || madvise(fill.buf,fill_bytes,MADV_NOHUGEPAGE)) throw std::runtime_error("mapping-or-page-policy");
        auto ts=tlb_history::targets(pool.buf,65536,100);
        auto fs=tlb_local::fillers(fill.buf,2048,ts);
        std::mt19937_64 rng(137);std::shuffle(fs.begin(),fs.end(),rng);tlb_history::link_filler(fs);
        auto cells=tlb_history::cells(argc==3);
        const probe_common::TypedEventSpec specs[]={{"cycles",8,0x11},{"l1d_tlb_refill",8,0x05},{"l2d_tlb_refill",8,0x2d},{"l2d_tlb",8,0x2f},{"dtlb_walk",8,0x34},{"itlb_walk",8,0x35}};
        probe_common::PerfWindow perf;
        if(!perf.open_typed(specs,6,true,true)) throw std::runtime_error("perf-open");
        for(unsigned i=0;i<6;++i) if(perf.failed(i)||perf.value_index(i)!=static_cast<int>(i)) throw std::runtime_error("perf-member-missing");
        config(argc==3);
        std::printf("{\"type\":\"geometry\",\"target\":100,\"pool_base\":%llu,\"pool_pages\":65536,\"target_pages\":[",static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(pool.buf)));array(ts[0]);std::printf(",");array(ts[1]);std::printf("],\"filler_pages\":");array(fs);std::puts("}");
        if(!perf.enable()) throw std::runtime_error("group-enable");
        unsigned prior_h=0,prior_w=0;
        for(size_t cell_index=0;cell_index<cells.size();++cell_index) {
            const auto& c=cells[cell_index];const auto& pages=ts[c.h-1];
            if(c.w && (prior_h!=c.h || prior_w!=c.w)) { tlb_history::link(pages,c.w);prior_h=c.h;prior_w=c.w; }
            backing(pool,pool_bytes);backing(fill,fill_bytes);
            std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"before\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n",c.id().c_str());
            auto prime=[&](){if(c.f) (void)tlb_history::walk(fs[0],c.f,c.f==128?1:0);};
            auto prepare=[&](){
                for(unsigned pass=0;pass<8;++pass) { prime();(void)tlb_history::walk(tlb_history::node(pages,0),12,3); }
                for(unsigned pass=0;pass<8;++pass) { prime();(void)tlb_history::walk(tlb_history::node(pages,0),c.history,c.history==6?2:3); }
            };
            if(c.kind==1) prepare();
            probe_common::WindowDelta saved[64]{};
            for(unsigned r=0;r<c.rounds;++r) {
                if(c.kind==2) prepare();
                prime();
                probe_common::GroupSample a{},b{};
                if(!perf.read_snapshot(&a)) throw std::runtime_error("snapshot-before");
                uintptr_t end=0;
                if(c.kind==1) end=tlb_history::walk(tlb_history::node(pages,c.direction?c.w-1:0),c.w,c.direction);
                if(c.kind==2) end=tlb_history::walk(tlb_history::node(pages,tlb_history::victim_index(r/8,r%8)),1,0);
                asm volatile(""::"r"(end):"memory");
                if(!perf.read_snapshot(&b)) throw std::runtime_error("snapshot-after");
                probe_common::WindowDelta d{};
                if(!probe_common::window_delta(a,b,6,&d)||!d.valid) throw std::runtime_error(d.reason);
                if(!d.values_monotonic) throw std::runtime_error("value-regressed");
                saved[r]=d;
            }
            backing(pool,pool_bytes);backing(fill,fill_bytes);
            std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"after\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n",c.id().c_str());
            for(unsigned r=0;r<c.rounds;++r) {
                const auto& d=saved[r];
                std::printf("{\"type\":\"round\",\"cell\":\"%s\",\"position\":%zu,\"kind\":%d,\"h\":%u,\"w\":%u,\"f\":%u,\"history\":%u,\"direction\":%u,\"victim\":%d,\"block\":%d,\"round\":%u,\"trial_position\":%u,\"enabled\":%llu,\"running\":%llu,\"counts\":[",c.id().c_str(),cell_index,c.kind,c.h,c.w,c.f,c.history,c.direction,c.kind==2?static_cast<int>(tlb_history::victim_index(r/8,r%8)):-1,c.block,c.kind==2?r/8:r,c.kind==2?r%8:0,static_cast<unsigned long long>(d.enabled_delta),static_cast<unsigned long long>(d.running_delta));
                for(unsigned i=0;i<6;++i) std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(d.value_deltas[i]));std::puts("]}");
            }
            if(sched_getcpu()!=7) throw std::runtime_error("cpu-migrated");
        }
        if(!perf.disable()) throw std::runtime_error("group-disable");
        munmap(pool.mapping_base,pool.mapping_bytes);munmap(fill.mapping_base,fill.mapping_bytes);
#endif
        return 0;
    }catch(const std::exception&e){std::fprintf(stderr,"error[%s]\n",e.what());std::printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",e.what());return 1;}
}
