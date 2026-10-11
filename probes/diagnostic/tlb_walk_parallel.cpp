// SPDX-License-Identifier: Apache-2.0
// Q-D explicit independent register chains, GROUP+ID and raw windows.
// Contract: docs/design/2026-10-11-tlb-walk-parallel.md (frozen v1).
#include "tlb_walk_parallel_layout.h"
#include "page_policy.h"
#include "perf_group_read.h"
#include <cstdio>
#include <cstring>
#ifdef __linux__
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#endif
static void config(bool reverse) {
    std::printf("{\"type\":\"config\",\"version\":1,\"probe\":\"tlb-walk-parallel\",\"k_grid\":[1,2,4,8],\"seed\":137,\"base_nodes\":8192,\"load_grid\":[262144,1048576],\"warmup_loads\":1048576,\"rounds\":3,\"events\":[17,8,3,23,52,33064],\"pmu_type\":8,\"reverse\":%s,\"cells\":33,\"windows\":99}\n",reverse?"true":"false");
}
static void cell(const tlb_parallel::Cell& c,size_t position) {
    std::printf("{\"type\":\"cell\",\"cell\":\"%s\",\"position\":%zu,\"scope\":\"%s\",\"layout\":\"%s\",\"k\":%u,\"nodes\":%u,\"loads\":%u,\"iterations\":%llu,\"pages\":%llu,\"line_bytes\":%llu,\"span_bytes\":%llu,\"rounds\":3}\n",c.id().c_str(),position,c.scope.c_str(),c.layout.c_str(),c.k,c.nodes,c.loads,static_cast<unsigned long long>(c.iterations),static_cast<unsigned long long>(c.pages),static_cast<unsigned long long>(c.line_bytes),static_cast<unsigned long long>(c.span_bytes));
}
#if defined(__linux__) && defined(__aarch64__)
// heads loads/stores live outside each audited LDR/SUBS/B.NE loop. Each LDR's
// output is its own next address; no stack or metadata loads within loop.
extern "C" __attribute__((noinline)) void parallel_k1(uintptr_t* heads,uint64_t iterations) {
    asm volatile("ldr x0,[%[h]]\nmov x8,%[n]\n1: ldr x0,[x0]\nsubs x8,x8,#1\nb.ne 1b\nstr x0,[%[h]]"::[h]"r"(heads),[n]"r"(iterations):"x0","x8","cc","memory");
}
extern "C" __attribute__((noinline)) void parallel_k2(uintptr_t* heads,uint64_t iterations) {
    asm volatile("ldp x0,x1,[%[h]]\nmov x8,%[n]\n1: ldr x0,[x0]\nldr x1,[x1]\nsubs x8,x8,#1\nb.ne 1b\nstp x0,x1,[%[h]]"::[h]"r"(heads),[n]"r"(iterations):"x0","x1","x8","cc","memory");
}
extern "C" __attribute__((noinline)) void parallel_k4(uintptr_t* heads,uint64_t iterations) {
    asm volatile("ldp x0,x1,[%[h]]\nldp x2,x3,[%[h],#16]\nmov x8,%[n]\n1: ldr x0,[x0]\nldr x1,[x1]\nldr x2,[x2]\nldr x3,[x3]\nsubs x8,x8,#1\nb.ne 1b\nstp x0,x1,[%[h]]\nstp x2,x3,[%[h],#16]"::[h]"r"(heads),[n]"r"(iterations):"x0","x1","x2","x3","x8","cc","memory");
}
extern "C" __attribute__((noinline)) void parallel_k8(uintptr_t* heads,uint64_t iterations) {
    asm volatile("ldp x0,x1,[%[h]]\nldp x2,x3,[%[h],#16]\nldp x4,x5,[%[h],#32]\nldp x6,x7,[%[h],#48]\nmov x8,%[n]\n1: ldr x0,[x0]\nldr x1,[x1]\nldr x2,[x2]\nldr x3,[x3]\nldr x4,[x4]\nldr x5,[x5]\nldr x6,[x6]\nldr x7,[x7]\nsubs x8,x8,#1\nb.ne 1b\nstp x0,x1,[%[h]]\nstp x2,x3,[%[h],#16]\nstp x4,x5,[%[h],#32]\nstp x6,x7,[%[h],#48]"::[h]"r"(heads),[n]"r"(iterations):"x0","x1","x2","x3","x4","x5","x6","x7","x8","cc","memory");
}
// This small adapter adds kernel identity to the existing pure GROUP decoder.
// No reset: cumulative times/values are differenced and mux is rejected.
struct Perf {
    int fd[6]={-1,-1,-1,-1,-1,-1};uint64_t ids[6]{};
    ~Perf(){for(int f:fd)if(f>=0)close(f);}
    void open() {
        constexpr uint64_t events[]={0x11,0x08,0x03,0x17,0x34,0x8128};
        for(unsigned i=0;i<6;++i) {
            perf_event_attr a{};a.size=sizeof(a);a.type=8;a.config=events[i];a.disabled=i==0;a.pinned=i==0;a.exclude_kernel=1;a.exclude_hv=1;a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING|PERF_FORMAT_ID;
            fd[i]=static_cast<int>(syscall(SYS_perf_event_open,&a,0,-1,i?fd[0]:-1,0));
            if(fd[i]<0 || ioctl(fd[i],PERF_EVENT_IOC_ID,&ids[i]))throw std::runtime_error("perf-open-id");
        }
    }
    pg_sample read() {uint64_t wire[15];ssize_t n=::read(fd[0],wire,sizeof(wire));if(n<=0 || n%8)throw std::runtime_error("perf-read");pg_sample s{};const char* e=pg_decode(wire,n/8,ids,6,&s);if(e)throw std::runtime_error(e);return s;}
    void enable(){if(ioctl(fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))throw std::runtime_error("perf-enable");}
    void disable(){if(ioctl(fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))throw std::runtime_error("perf-disable");}
};
static void backing(const probe_common::GuardedMap& m,const tlb_parallel::Cell& c,const char* stage) {
    size_t huge=0;if(c.k && (!probe_common::read_anon_huge_kb(m.buf,c.span_bytes,&huge)||huge))throw std::runtime_error("backing-not-4k");
    std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"%s\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n",c.id().c_str(),stage);
}
static void geometry(const tlb_parallel::Cell& c,const probe_common::GuardedMap& m,const tlb_parallel::Chains& chains) {
    std::printf("{\"type\":\"geometry\",\"cell\":\"%s\",\"base\":%llu,\"chains\":[",c.id().c_str(),static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(m.buf)));
    for(unsigned k=0;k<c.k;++k){std::printf("%s[",k?",":"");for(size_t i=0;i<chains[k].size();++i)std::printf("%s%u",i?",":"",chains[k][i]);std::printf("]");}std::puts("]}");
}
#endif
int main(int argc,char** argv) {
    try {
        if((argc!=2&&argc!=3)||(std::string(argv[1])!="--run"&&std::string(argv[1])!="--plan")||(argc==3&&std::string(argv[2])!="--reverse"))throw std::runtime_error("usage-parallel-run-plan-reverse");
        const bool reverse=argc==3;auto cells=tlb_parallel::cells(reverse);
        if(std::string(argv[1])=="--plan"){config(reverse);for(size_t i=0;i<cells.size();++i)cell(cells[i],i);return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
        throw std::runtime_error("measurement-requires-linux-aarch64");
#else
        if(sysconf(_SC_PAGESIZE)!=4096)throw std::runtime_error("page-size");cpu_set_t cpus;CPU_ZERO(&cpus);CPU_SET(7,&cpus);if(sched_setaffinity(0,sizeof(cpus),&cpus)||sched_getcpu()!=7)throw std::runtime_error("affinity");
        Perf perf;perf.open();config(reverse);std::printf("{\"type\":\"pmu\",\"ids\":[");for(unsigned i=0;i<6;++i)std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(perf.ids[i]));std::puts("]}");perf.enable();
        using Kernel=void(*)(uintptr_t*,uint64_t);
        for(size_t i=0;i<cells.size();++i) {
            const auto& c=cells[i];probe_common::GuardedMap mapping{};tlb_parallel::Chains chains;tlb_parallel::Heads heads{},original{};Kernel kernel=nullptr;
            if(c.k) {
                mapping=probe_common::map_guarded_anonymous(c.span_bytes,4096);if(!mapping.buf||madvise(mapping.buf,c.span_bytes,MADV_NOHUGEPAGE))throw std::runtime_error("mapping-policy");
                chains=tlb_parallel::indices(c);heads=tlb_parallel::link(mapping.buf,c,chains);original=heads;kernel=c.k==1?parallel_k1:c.k==2?parallel_k2:c.k==4?parallel_k4:parallel_k8;
                kernel(heads.data(),1048576/c.k);if(heads!=original)throw std::runtime_error("warmup-graph-end");
            }
            cell(c,i);geometry(c,mapping,chains);backing(mapping,c,"before");std::array<pg_sample,3> saved{};
            for(unsigned round=0;round<3;++round) {
                auto a=perf.read();if(kernel)kernel(heads.data(),c.iterations);asm volatile("":::"memory");auto b=perf.read();const char* error=pg_delta(&a,&b,6,&saved[round]);if(error)throw std::runtime_error(error);if(heads!=original)throw std::runtime_error("measured-graph-end");
            }
            backing(mapping,c,"after");
            for(unsigned round=0;round<3;++round) {
                const auto& s=saved[round];std::printf("{\"type\":\"round\",\"cell\":\"%s\",\"position\":%zu,\"round\":%u,\"head_returned\":true,\"enabled\":%llu,\"running\":%llu,\"counts\":[",c.id().c_str(),i,round,static_cast<unsigned long long>(s.enabled),static_cast<unsigned long long>(s.running));for(unsigned e=0;e<6;++e)std::printf("%s%llu",e?",":"",static_cast<unsigned long long>(s.values[e]));std::puts("]}");
            }
            if(c.k)munmap(mapping.mapping_base,mapping.mapping_bytes);if(sched_getcpu()!=7)throw std::runtime_error("cpu-migrated");
        }
        perf.disable();
#endif
        return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"error[%s]\n",e.what());std::printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",e.what());return 1;}
}
