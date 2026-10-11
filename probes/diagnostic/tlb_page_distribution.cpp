// SPDX-License-Identifier: Apache-2.0
// Frozen Q-A: docs/design/2026-10-11-tlb-page-distribution.md.
// Full set/order/offset evidence; never infer hardware aggregation from THP=0.
#include "tlb_page_distribution_layout.h"
#include "page_policy.h"
#include "perf_group_read.h"
#include <cstdio>
#include <array>
#include <set>
#ifdef __linux__
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#endif
static void arr(const std::vector<unsigned>& a){std::printf("[");for(size_t i=0;i<a.size();++i)std::printf("%s%u",i?",":"",a[i]);std::printf("]");}
static void config(bool reverse){std::printf("{\"type\":\"config\",\"version\":1,\"probe\":\"tlb-page-distribution\",\"pool_pages\":262144,\"page_set_seed\":271,\"order_seed\":137,\"n_grid\":[32,64,80,96,112,128,160,192,256,512,1024,2048],\"load_budget\":1048576,\"rounds\":3,\"events\":[17,8,5,3,52,53],\"pmu_type\":8,\"reverse\":%s,\"cells\":145,\"windows\":435}\n",reverse?"true":"false");}
static void cell(const tlb_distribution::Cell& c,size_t i){std::printf("{\"type\":\"cell\",\"cell\":\"%s\",\"position\":%zu,\"shape\":\"%s\",\"offset\":\"%s\",\"order\":\"%s\",\"n\":%u,\"loads\":%u,\"span_bytes\":%llu,\"line_bytes\":%llu,\"rounds\":3}\n",c.id().c_str(),i,c.shape.c_str(),c.offset.c_str(),c.order.c_str(),c.n,c.loads,static_cast<unsigned long long>(c.span_bytes),static_cast<unsigned long long>(c.line_bytes));}
#if defined(__linux__) && defined(__aarch64__)
// Same single register chain algorithm as Q-D K1. Only LDR/SUBS/B.NE in loop;
// head preparation/storage is outside loop but inside the PMU read bracket.
extern "C" __attribute__((noinline)) void distribution_k1(uintptr_t* head,uint64_t iterations){asm volatile("ldr x0,[%[h]]\nmov x8,%[n]\n1: ldr x0,[x0]\nsubs x8,x8,#1\nb.ne 1b\nstr x0,[%[h]]"::[h]"r"(head),[n]"r"(iterations):"x0","x8","cc","memory");}
// GROUP+ID uses the shared pure wire decoder, never software value position.
struct Perf {
    int fd[6]={-1,-1,-1,-1,-1,-1};uint64_t ids[6]{};
    ~Perf(){for(int f:fd)if(f>=0)close(f);}
    void open() {
        constexpr uint64_t events[]={0x11,0x08,0x05,0x03,0x34,0x35};
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

static void backing(const probe_common::GuardedMap& m,const tlb_distribution::Cell& c,const char* stage){size_t huge=0;if(!probe_common::read_anon_huge_kb(m.buf,262144ull*4096,&huge)||huge)throw std::runtime_error("backing-not-4k");std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"%s\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n",c.id().c_str(),stage);}
#endif
int main(int argc,char** argv){
    try{
        if((argc!=2&&argc!=3)||(std::string(argv[1])!="--run"&&std::string(argv[1])!="--plan")||(argc==3&&std::string(argv[2])!="--reverse"))throw std::runtime_error("usage-distribution-run-plan-reverse");bool reverse=argc==3;auto cells=tlb_distribution::cells(reverse);
        if(std::string(argv[1])=="--plan"){config(reverse);for(size_t i=0;i<cells.size();++i)cell(cells[i],i);return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
        (void)arr;throw std::runtime_error("measurement-requires-linux-aarch64");
#else
        if(sysconf(_SC_PAGESIZE)!=4096)throw std::runtime_error("page-size");cpu_set_t cpus;CPU_ZERO(&cpus);CPU_SET(7,&cpus);if(sched_setaffinity(0,sizeof(cpus),&cpus)||sched_getcpu()!=7)throw std::runtime_error("affinity");
        auto mapping=probe_common::map_guarded_anonymous(262144ull*4096,4096);if(!mapping.buf||madvise(mapping.buf,262144ull*4096,MADV_NOHUGEPAGE))throw std::runtime_error("mapping-policy");std::set<unsigned> prefaulted;
        for(const char* shape:{"contiguous","sparse","random-set"})for(unsigned p:tlb_distribution::pages(shape,2048)){prefaulted.insert(p);*reinterpret_cast<uintptr_t*>(mapping.buf+uint64_t(p)*4096)=0;*reinterpret_cast<uintptr_t*>(mapping.buf+uint64_t(p)*4096+64*(p%64))=0;}
        Perf perf;perf.open();config(reverse);std::printf("{\"type\":\"pmu\",\"ids\":[");for(unsigned i=0;i<6;++i)std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(perf.ids[i]));std::puts("]}");std::printf("{\"type\":\"mapping\",\"base\":%llu,\"pool_pages\":262144,\"hpa_state\":\"UNKNOWN\",\"pte_cont_state\":\"UNKNOWN\",\"prefaulted_page_ids\":",static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(mapping.buf)));arr(std::vector<unsigned>(prefaulted.begin(),prefaulted.end()));std::puts("}");perf.enable();
        for(size_t i=0;i<cells.size();++i){const auto& c=cells[i];std::vector<unsigned> pages,order,offsets;uintptr_t head=0,original=0;if(c.n){pages=tlb_distribution::pages(c.shape,c.n);order=tlb_distribution::order(c);for(unsigned p:pages)offsets.push_back(tlb_distribution::offset(c,p));head=tlb_distribution::link(mapping.buf,c,pages,order);original=head;distribution_k1(&head,c.loads);if(head!=original)throw std::runtime_error("warmup-graph-end");}
            cell(c,i);std::printf("{\"type\":\"geometry\",\"cell\":\"%s\",\"page_ids\":",c.id().c_str());arr(pages);std::printf(",\"order_indices\":");arr(order);std::printf(",\"offsets\":");arr(offsets);std::puts("}");backing(mapping,c,"before");std::array<pg_sample,3> saved{};
            for(unsigned t=0;t<3;++t){auto a=perf.read();if(c.n)distribution_k1(&head,c.loads);asm volatile("":::"memory");auto b=perf.read();const char* error=pg_delta(&a,&b,6,&saved[t]);if(error)throw std::runtime_error(error);if(head!=original)throw std::runtime_error("measured-graph-end");}
            backing(mapping,c,"after");for(unsigned t=0;t<3;++t){const auto& s=saved[t];std::printf("{\"type\":\"round\",\"cell\":\"%s\",\"position\":%zu,\"round\":%u,\"head_returned\":true,\"enabled\":%llu,\"running\":%llu,\"counts\":[",c.id().c_str(),i,t,static_cast<unsigned long long>(s.enabled),static_cast<unsigned long long>(s.running));for(unsigned e=0;e<6;++e)std::printf("%s%llu",e?",":"",static_cast<unsigned long long>(s.values[e]));std::puts("]}");}if(sched_getcpu()!=7)throw std::runtime_error("cpu-migrated");
        }
        perf.disable();munmap(mapping.mapping_base,mapping.mapping_bytes);
#endif
        return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"error[%s]\n",e.what());std::printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",e.what());return 1;}
}
