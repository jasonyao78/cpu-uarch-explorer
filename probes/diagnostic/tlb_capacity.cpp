// SPDX-License-Identifier: Apache-2.0
// 独立诊断：固定准备历史下的局部工作集轨迹及单 victim 竞争响应。
// 协议/技术原理：docs/design/2026-10-09-tlb-local-capacity.md（冻结 v1）。
// 圈内 walk 不能换算窗前缺失项；本组件保存全部窗口，不输出物理 ways。
#include "tlb_capacity_layout.h"
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
    std::printf("{\"type\":\"config\",\"version\":1,\"target\":100,\"seed\":137,\"max_w\":12,\"old_prefix\":9,\"offset_rotate\":true,\"link_slots\":5,\"reverse\":%s,\"cells\":94,\"windows\":2080}\n",reverse?"true":"false");
}

// 唯一生产计划：条内 rounds 正序，--reverse 只反转整个 cell 序列。
static void plan(bool reverse) {
    config(reverse);
    auto cells=tlb_capacity::cells(reverse);
    for(size_t i=0;i<cells.size();++i) {
        const auto& c=cells[i];
        std::printf("{\"type\":\"cell\",\"cell\":\"%s\",\"position\":%zu,\"kind\":%d,\"h\":%u,\"w\":%u,\"f\":%u,\"history\":%u,\"direction\":%u,\"k\":%u,\"victim\":%d,\"block\":%d,\"rounds\":%u}\n",c.id().c_str(),i,c.kind,c.h,c.w,c.f,c.history,c.direction,c.k,c.victim,c.block,c.rounds);
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
            throw std::runtime_error("usage-tlb_capacity-100-or-plan-reverse");
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
        auto cells=tlb_capacity::cells(reverse);
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
            // 每条件只建链一次；round 内的准备/训练/竞争均只读 target。
            if(c.kind) tlb_capacity::link(pages,c.w,c.k,c.direction);
            backing(pool,pool_bytes);backing(fill,fill_bytes);
            std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"before\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n",c.id().c_str());
            const uintptr_t history_start=c.kind?tlb_history::node(pages,0):0;
            const uintptr_t probe_start=c.kind==1?tlb_history::node(pages,c.direction?c.w-1:0):history_start;
            const uintptr_t competitors=c.kind==2?tlb_capacity::competitor_start(pages,c.k,c.direction):0;
            const uintptr_t filler=fillers[0];
            auto prime=[&](){if(c.f) (void)tlb_history::walk(filler,c.f,c.f==128?1:0);};
            auto prepare=[&](){
                for(unsigned pass=0;pass<8;++pass) {
                    prime();(void)tlb_history::walk(history_start,12,3);
                }
            };
            if(c.kind==1) prepare();
            probe_common::WindowDelta saved[32]{};
            for(unsigned round=0;round<c.rounds;++round) {
                probe_common::GroupSample before{},after{};
                if(c.kind==2) {
                    prepare();prime();
                    uintptr_t trained=tlb_history::walk(history_start,1,0);
                    asm volatile(""::"r"(trained):"memory");
                    prime();(void)tlb_capacity::walk_competitors(competitors,c.k);
                }
                // 最后 F 在 measured_window 内，调用参数/元数据在此之前取得。
                measured_window(perf,probe_start,c.kind?c.w:0,c.kind==1?c.direction:0,
                                filler,c.f,&before,&after);
                probe_common::WindowDelta delta{};
                if(!probe_common::window_delta(before,after,6,&delta)||!delta.valid)
                    throw std::runtime_error(delta.reason);
                if(!delta.values_monotonic) throw std::runtime_error("value-regressed");
                saved[round]=delta;
            }
            backing(pool,pool_bytes);backing(fill,fill_bytes);
            std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"after\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n",c.id().c_str());
            for(unsigned round=0;round<c.rounds;++round) {
                const auto& delta=saved[round];
                std::printf("{\"type\":\"round\",\"cell\":\"%s\",\"position\":%zu,\"kind\":%d,\"h\":%u,\"w\":%u,\"f\":%u,\"history\":%u,\"direction\":%u,\"k\":%u,\"victim\":%d,\"block\":%d,\"round\":%u,\"trial_position\":0,\"enabled\":%llu,\"running\":%llu,\"counts\":[",c.id().c_str(),position,c.kind,c.h,c.w,c.f,c.history,c.direction,c.k,c.victim,c.block,round,static_cast<unsigned long long>(delta.enabled_delta),static_cast<unsigned long long>(delta.running_delta));
                for(unsigned i=0;i<6;++i)
                    std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(delta.value_deltas[i]));
                std::puts("]}");
            }
            if(sched_getcpu()!=7) throw std::runtime_error("cpu-migrated");
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
