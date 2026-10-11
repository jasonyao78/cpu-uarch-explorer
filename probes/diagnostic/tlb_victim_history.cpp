// SPDX-License-Identifier: Apache-2.0
// 独立诊断：固定页集合的 victim 身份与准备次序对照。
// 协议/技术原理：docs/design/2026-10-11-tlb-victim-history.md（冻结 v1）。
// 圈内 walk 不能换算窗前缺失项；本组件保存全部窗口，不输出物理 ways。
#include "tlb_victim_history_layout.h"
#include "page_policy.h"
#include "perf_window.h"
#include <cstdio>
#include <random>
#ifdef __linux__
#include <sched.h>
#endif

// 原始几何只写入调用者保管的 JSONL；不改变目标页或指针槽。
static void array(const tlb_local::Addresses& addresses) {
    std::printf("[");
    for(size_t i=0;i<addresses.size();++i)
        std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(addresses[i]));
    std::printf("]");
}

// 冻结自描述，与 --plan 和实测共用；没有按测量结果派生的条件。
static void config(bool reverse) {
    std::printf("{\"type\":\"config\",\"version\":1,\"probe\":\"tlb-victim-history\",\"target\":100,\"seed\":137,\"max_w\":12,\"old_prefix\":9,\"offset_rotate\":true,\"link_slots\":5,\"f\":128,\"history\":12,\"w_grid\":[1,8,9],\"victim_ranks\":[\"first\",\"middle\",\"last\"],\"history_directions\":[0,1],\"passes\":8,\"rounds\":16,\"reverse\":%s,\"cells\":56,\"windows\":8064}\n",reverse?"true":"false");
}
// --plan uses the exact cells consumed by the actual Linux loop below.
static void plan(bool reverse) {
    config(reverse);auto cells=tlb_victim_history::cells(reverse);
    for(size_t i=0;i<cells.size();++i) {
        const auto& c=cells[i];
        std::printf("{\"type\":\"cell\",\"cell\":\"%s\",\"position\":%zu,\"h\":%u,\"w\":%u,\"victim\":%u,\"history_direction\":%u,\"direction\":%u,\"passes\":%u,\"rounds\":%u}\n",c.id().c_str(),i,c.h,c.w,c.victim,c.history_direction,c.direction,c.passes,c.rounds);
    }
}

#if defined(__linux__) && defined(__aarch64__)
// 与 history 的真实 4K 资格一致；不满足时抛异常，禁止继续采纳该 cell。
static void backing(const probe_common::GuardedMap& mapping,size_t bytes) {
    size_t huge=1;
    if(!probe_common::read_anon_huge_kb(mapping.buf,bytes,&huge) || huge)
        throw std::runtime_error("backing-not-base-4k");
}

// 独立调用边界使全部目标/竞争元数据在最后 F 前取得。窗内只沿已取得
// 的指针走 count 次；victim count1、slot0，floor count0。包装开销仍在。
// noinline 是冻结协议的防线，便于逐二进制核对最后 F 与 snapshot/load。
static __attribute__((noinline)) void measured_window(probe_common::PerfWindow& perf,
        uintptr_t start,unsigned count,unsigned slot,uintptr_t filler,unsigned f,
        probe_common::GroupSample* before,probe_common::GroupSample* after) {
    if(f) (void)tlb_history::walk(filler,f,f==128?1:0);
    if(!perf.read_snapshot(before)) throw std::runtime_error("snapshot-before");
    uintptr_t end=tlb_history::walk(start,count,slot);
    asm volatile(""::"r"(end):"memory");
    if(!perf.read_snapshot(after)) throw std::runtime_error("snapshot-after");
}
#endif

// --plan 在 host 可执行；实测必须 Linux/AArch64、CPU7、4K backing、六事件。
// 任一失败只输出空 metrics 的结构化 failure，已输出原始窗口保留审计。
int main(int argc,char** argv) {
    try {
        if((argc!=2 && argc!=3) || (std::string(argv[1])!="100" && std::string(argv[1])!="--plan") ||
           (argc==3 && std::string(argv[2])!="--reverse"))
            throw std::runtime_error("usage-tlb_victim_history-100-or-plan-reverse");
        bool reverse=argc==3;
        if(std::string(argv[1])=="--plan") { plan(reverse);return 0; }
#if !defined(__linux__) || !defined(__aarch64__)
        (void)array;throw std::runtime_error("measurement-requires-linux-aarch64");
#else
        if(sysconf(_SC_PAGESIZE)!=4096) throw std::runtime_error("page-size");
        cpu_set_t cpus;CPU_ZERO(&cpus);CPU_SET(7,&cpus);
        if(sched_setaffinity(0,sizeof(cpus),&cpus) || sched_getcpu()!=7)
            throw std::runtime_error("affinity");
        constexpr size_t pool_bytes=65536ull*4096,fill_bytes=2048ull*4096;
        auto pool=probe_common::map_guarded_anonymous(pool_bytes,4096);
        auto fill=probe_common::map_guarded_anonymous(fill_bytes,4096);
        if(!pool.buf || !fill.buf || madvise(pool.buf,pool_bytes,MADV_NOHUGEPAGE) ||
           madvise(fill.buf,fill_bytes,MADV_NOHUGEPAGE))
            throw std::runtime_error("mapping-or-page-policy");
        auto targets=tlb_history::targets(pool.buf,65536,100);
        auto fillers=tlb_local::fillers(fill.buf,2048,targets);
        std::mt19937_64 rng(137);std::shuffle(fillers.begin(),fillers.end(),rng);
        tlb_history::link_filler(fillers);
        auto cells=tlb_victim_history::cells(reverse);
        const probe_common::TypedEventSpec specs[]={
            {"cycles",8,0x11},{"l1d_tlb_refill",8,0x05},{"l2d_tlb_refill",8,0x2d},
            {"l2d_tlb",8,0x2f},{"dtlb_walk",8,0x34},{"itlb_walk",8,0x35}};
        probe_common::PerfWindow perf;
        if(!perf.open_typed(specs,6,true,true)) throw std::runtime_error("perf-open");
        for(unsigned i=0;i<6;++i) if(perf.failed(i)||perf.value_index(i)!=static_cast<int>(i))
            throw std::runtime_error("perf-member-missing");
        config(reverse);
        std::printf("{\"type\":\"geometry\",\"target\":100,\"pool_base\":%llu,\"pool_pages\":65536,\"target_pages\":[",static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(pool.buf)));
        array(targets[0]);std::printf(",");array(targets[1]);
        std::printf("],\"filler_pages\":");array(fillers);std::puts("}");
        if(!perf.enable()) throw std::runtime_error("group-enable");
        for(size_t position=0;position<cells.size();++position) {
            const auto& c=cells[position];const auto& pages=targets[c.h-1];
            tlb_victim_history::link(pages,c);
            auto shots=tlb_victim_history::schedule(c);
            const uintptr_t history_start=tlb_victim_history::history_start(pages,c);
            const uintptr_t victim=tlb_history::node(pages,c.victim);
            const uintptr_t competitor=tlb_victim_history::competitor_start(pages,c);
            const uintptr_t filler=fillers[0];
            auto prime=[&](){(void)tlb_history::walk(filler,128,1);};
            backing(pool,pool_bytes);backing(fill,fill_bytes);
            std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"before\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n",c.id().c_str());
            std::vector<probe_common::WindowDelta> saved(shots.size());
            for(size_t i=0;i<shots.size();++i) {
                const auto& shot=shots[i];
                if(shot.pass_index==0) {
                    for(unsigned pass=0;pass<8;++pass){prime();(void)tlb_history::walk(history_start,12,3);}
                    prime();uintptr_t trained=tlb_history::walk(victim,1,0);
                    asm volatile(""::"r"(trained):"memory");
                }
                // Metadata resolved before the final F inside this noinline function.
                probe_common::GroupSample before{},after{};
                measured_window(perf,shot.victim?victim:competitor,shot.victim?1:c.w-1,
                                shot.victim?0:4,filler,128,&before,&after);
                auto& delta=saved[i];
                if(!probe_common::window_delta(before,after,6,&delta)||!delta.valid)
                    throw std::runtime_error(delta.reason);
                if(!delta.values_monotonic)throw std::runtime_error("value-regressed");
            }
            backing(pool,pool_bytes);backing(fill,fill_bytes);
            std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"after\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n",c.id().c_str());
            for(size_t i=0;i<shots.size();++i) {
                const auto& shot=shots[i];const auto& delta=saved[i];
                std::printf("{\"type\":\"round\",\"cell\":\"%s\",\"position\":%zu,\"h\":%u,\"w\":%u,\"victim\":%u,\"history_direction\":%u,\"direction\":%u,\"passes\":%u,\"round\":%u,\"role\":\"%s\",\"pass_index\":%u,\"enabled\":%llu,\"running\":%llu,\"counts\":[",c.id().c_str(),position,c.h,c.w,c.victim,c.history_direction,c.direction,c.passes,shot.round,shot.victim?"victim":"competition",shot.pass_index,static_cast<unsigned long long>(delta.enabled_delta),static_cast<unsigned long long>(delta.running_delta));
                for(unsigned j=0;j<6;++j)std::printf("%s%llu",j?",":"",static_cast<unsigned long long>(delta.value_deltas[j]));std::puts("]}");
            }
            if(sched_getcpu()!=7)throw std::runtime_error("cpu-migrated");
        }
        if(!perf.disable()) throw std::runtime_error("group-disable");
        munmap(pool.mapping_base,pool.mapping_bytes);munmap(fill.mapping_base,fill.mapping_bytes);
#endif
        return 0;
    }catch(const std::exception& error) {
        std::fprintf(stderr,"error[%s]\n",error.what());
        std::printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",error.what());
        return 1;
    }
}
