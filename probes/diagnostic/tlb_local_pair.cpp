// SPDX-License-Identifier: Apache-2.0
// Standalone local diagnostic, NOT a runner record / formal A1 producer.
// Each process owns one mapping epoch; exact pages/offsets and all rounds emitted.
// Purpose/protocol: docs/design/2026-10-09-minimal-tlb-rob-probes.md.
#include "tlb_local_layout.h"
#include "page_policy.h"
#include "perf_window.h"
#include <cstdio>
#include <cstdlib>
#include <random>
#include <stdexcept>
#ifdef __linux__
#include <sched.h>
#endif
static void array(const tlb_local::Addresses& a) {
    std::printf("["); for(size_t i=0;i<a.size();++i) std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(a[i])); std::printf("]");
}
#ifdef __linux__
static void backing(const probe_common::GuardedMap& g,size_t bytes) {
    size_t huge=1;
    if(!probe_common::read_anon_huge_kb(g.buf,bytes,&huge) || huge)
        throw std::runtime_error("backing-not-base-4k");
}
#endif
int main(int argc,char **argv) {
    try {
        // Fixed small contract: cpu7, PMU type8, target supplied, two predefined seeds.
        if((argc!=2 && argc!=3) || (std::string(argv[1])!="100" && std::string(argv[1])!="200") || (argc==3 && std::string(argv[2])!="--reverse"))
            throw std::runtime_error("usage-tlb_local_pair-target-100-or-200");
#ifndef __linux__
        throw std::runtime_error("measurement-requires-linux-aarch64");
#else
#ifndef __aarch64__
        throw std::runtime_error("measurement-requires-aarch64");
#endif
        if(sysconf(_SC_PAGESIZE)!=4096) throw std::runtime_error("page-size");
        cpu_set_t set; CPU_ZERO(&set); CPU_SET(7,&set);
        if(sched_setaffinity(0,sizeof(set),&set) || sched_getcpu()!=7) throw std::runtime_error("affinity");
        const bool reverse=argc==3;
        constexpr size_t pool_bytes=65536ull*4096,filler_bytes=2048*4096;
        auto pool=probe_common::map_guarded_anonymous(pool_bytes,4096);
        auto fill=probe_common::map_guarded_anonymous(filler_bytes,4096);
        if(!pool.buf || !fill.buf || madvise(pool.buf,pool_bytes,MADV_NOHUGEPAGE) || madvise(fill.buf,filler_bytes,MADV_NOHUGEPAGE))
            throw std::runtime_error("mmap-or-page-policy");
        auto ts=tlb_local::targets(pool.buf,65536,static_cast<unsigned>(std::atoi(argv[1])));
        auto fpages=tlb_local::fillers(fill.buf,2048,ts);
        const probe_common::TypedEventSpec specs[]={
            {"cycles",8,0x11},{"l1d_tlb_refill",8,0x05},{"l2d_tlb_refill",8,0x2d},
            {"l2d_tlb",8,0x2f},{"dtlb_walk",8,0x34},{"itlb_walk",8,0x35}};
        probe_common::PerfWindow perf;
        if(!perf.open_typed(specs,6,true,true)) throw std::runtime_error("perf-open");
        for(unsigned i=0;i<6;++i) if(perf.failed(i) || perf.value_index(i)!=static_cast<int>(i)) throw std::runtime_error("perf-member-missing");
        std::printf("{\"type\":\"geometry\",\"target\":%s,\"pool_base\":%llu,\"filler_base\":%llu,\"target_pages\":[",argv[1],
            static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(pool.buf)),static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(fill.buf)));
        array(ts[0]); std::printf(","); array(ts[1]); std::printf("],\"filler_pages\":"); array(fpages); std::puts("}");
        if(!perf.enable()) throw std::runtime_error("group-enable");
        // Same physical filler pages for all H/W/offset. F128 is shuffled F512 prefix.
        for(unsigned seed: (reverse?std::vector<unsigned>{137,42}:std::vector<unsigned>{42,137})) {
            auto order=fpages; std::mt19937_64 gen(seed); std::shuffle(order.begin(),order.end(),gen);
            std::printf("{\"type\":\"filler_order\",\"seed\":%u,\"addresses\":",seed); array(order); std::puts("}");
            for(unsigned f: (reverse?std::vector<unsigned>{512,128}:std::vector<unsigned>{128,512})) {
                tlb_local::Addresses fs(order.begin(),order.begin()+f); tlb_local::chain(fs);
                for(unsigned block=0;block<4;++block) {
                    // floor -> four balanced cells at offset0/rotate -> floor.
                    const bool floor=block==0 || block==3; const bool rotate=!floor && (reverse?block==1:block==2);
                    const unsigned cells=floor?1:4;
                    for(unsigned pos=0;pos<cells;++pos) {
                        // Reverse all four cells for seed137. Order metadata remains explicit.
                        unsigned cell=((seed==42)!=reverse)?pos:3-pos;
                        unsigned h=floor?0:cell/2; unsigned w=floor?0:8+(cell%2);
                        auto ns=tlb_local::nodes(ts[h],w,rotate); tlb_local::chain(ns);
                        backing(pool,pool_bytes); backing(fill,filler_bytes);
                        std::printf("{\"type\":\"backing\",\"stage\":\"before\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n");
                        probe_common::WindowDelta saved[20]{};
                        for(unsigned r=0;r<20;++r) {
                            // Only current active target chain preheated; no all-nine warmup.
                            if(w) (void)tlb_local::chase(ns[0],w);
                            (void)tlb_local::chase(fs[0],f);
                            probe_common::GroupSample a{},b{};
                            if(!perf.read_snapshot(&a)) throw std::runtime_error("snapshot-before");
                            uintptr_t end=w?tlb_local::chase(ns[0],w):0;
                            asm volatile("" : : "r"(end) : "memory");
                            if(!perf.read_snapshot(&b)) throw std::runtime_error("snapshot-after");
                            probe_common::WindowDelta d{};
                            if(!probe_common::window_delta(a,b,6,&d) || !d.valid)
                                throw std::runtime_error(d.reason);
                            if(!d.values_monotonic) throw std::runtime_error("value-regressed");
                            saved[r]=d;
                        }
                        backing(pool,pool_bytes); backing(fill,filler_bytes);
                        std::printf("{\"type\":\"backing\",\"stage\":\"after\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n");
                        for(unsigned r=0;r<20;++r) {
                            const auto& d=saved[r];
                            std::printf("{\"type\":\"round\",\"seed\":%u,\"f\":%u,\"offset_rotate\":%s,\"h\":%u,\"w\":%u,\"block\":%u,\"position\":%u,\"round\":%u,\"retained\":%s,\"enabled\":%llu,\"running\":%llu,\"counts\":[",
                                seed,f,rotate?"true":"false",h+1,w,block,pos,r,r?"true":"false",static_cast<unsigned long long>(d.enabled_delta),static_cast<unsigned long long>(d.running_delta));
                            for(unsigned i=0;i<6;++i) std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(d.value_deltas[i])); std::puts("]}");
                        }
                        if(sched_getcpu()!=7) throw std::runtime_error("cpu-migrated");
                    }
                }
            }
        }
        if(!perf.disable()) throw std::runtime_error("group-disable");
        munmap(pool.mapping_base,pool.mapping_bytes); munmap(fill.mapping_base,fill.mapping_bytes);
#endif
        return 0;
    } catch(const std::exception& e) {
        std::fprintf(stderr,"error[%s]\n",e.what());
        std::printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",e.what()); return 1;
    }
}
