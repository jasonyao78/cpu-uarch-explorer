// SPDX-License-Identifier: Apache-2.0
// Frozen Q-A: docs/design/2026-10-12-tlb-balanced-reach.md.
// Full set/order/offset evidence; never infer hardware aggregation from THP=0.
#include "tlb_balanced_reach_layout.h"
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
static void config(bool reverse){std::printf("{\"type\":\"config\",\"version\":1,\"probe\":\"tlb-balanced-reach\",\"pool_pages\":1048576,\"page_set_seed\":271,\"order_seed\":137,\"n_grid\":[512,1024,1280,1536,1792,2048,2304,2560,3072],\"load_budget\":1048576,\"rounds\":3,\"events\":[17,8,5,45,47,52],\"pmu_type\":8,\"reverse\":%s,\"cells\":55,\"windows\":165}\n",reverse?"true":"false");}
static void cell(const tlb_reach::Cell& c,size_t i){std::printf("{\"type\":\"cell\",\"cell\":\"%s\",\"position\":%zu,\"shape\":\"%s\",\"offset\":\"%s\",\"order\":\"%s\",\"n\":%u,\"loads\":%u,\"span_bytes\":%llu,\"line_bytes\":%llu,\"rounds\":3}\n",c.id().c_str(),i,c.shape.c_str(),c.offset.c_str(),c.order.c_str(),c.n,c.loads,static_cast<unsigned long long>(c.span_bytes),static_cast<unsigned long long>(c.line_bytes));}
// These exporters serve both --layout and actual measurement: no parallel
// metadata-only selector. Parent IDs are VA proxies for 512-descriptor regions.
static std::vector<unsigned> prefaulted(){std::set<unsigned> out;for(const char* shape:{"dense","spaced","balanced-random"})for(unsigned p:tlb_reach::pages(shape,3072))out.insert(p);return std::vector<unsigned>(out.begin(),out.end());}
static void mapping(uintptr_t base){std::printf("{\"type\":\"mapping\",\"base\":%llu,\"pool_pages\":1048576,\"hpa_state\":\"UNKNOWN\",\"pte_cont_state\":\"UNKNOWN\",\"pfn_state\":\"UNKNOWN\",\"data_cache_state\":\"UNKNOWN\",\"prefaulted_page_ids\":",static_cast<unsigned long long>(base));arr(prefaulted());std::puts("}");}
static void geometry(const tlb_reach::Cell& c,uintptr_t base){std::vector<unsigned> pp,oo,offsets,hist(256);std::set<uint64_t> parents;if(c.n){pp=tlb_reach::pages(c.shape,c.n);oo=tlb_reach::order(c);for(unsigned p:pp){offsets.push_back(tlb_reach::offset(p));uint64_t vpn=base/4096+p;++hist[vpn%256];parents.insert(vpn>>9);}}
    std::printf("{\"type\":\"geometry\",\"cell\":\"%s\",\"page_ids\":",c.id().c_str());arr(pp);std::printf(",\"order_indices\":");arr(oo);std::printf(",\"offsets\":");arr(offsets);std::printf(",\"vpn_low8_hist\":");arr(hist);std::printf(",\"l3_parent_count\":%zu,\"l3_parent_ids\":[",parents.size());size_t i=0;for(auto p:parents)std::printf("%s%llu",i++?",":"",static_cast<unsigned long long>(p));std::puts("]}");}
#if defined(__linux__) && defined(__aarch64__)
// Same single register chain algorithm as Q-D K1. Only LDR/SUBS/B.NE in loop;
// head preparation/storage is outside loop but inside the PMU read bracket.
extern "C" __attribute__((noinline)) void reach_k1(uintptr_t* head,uint64_t iterations){asm volatile("ldr x0,[%[h]]\nmov x8,%[n]\n1: ldr x0,[x0]\nsubs x8,x8,#1\nb.ne 1b\nstr x0,[%[h]]"::[h]"r"(head),[n]"r"(iterations):"x0","x8","cc","memory");}
// GROUP+ID uses the shared pure wire decoder, never software value position.
struct Perf {
    int fd[6]={-1,-1,-1,-1,-1,-1};uint64_t ids[6]{};
    ~Perf(){for(int f:fd)if(f>=0)close(f);}
    void open() {
        constexpr uint64_t events[]={0x11,0x08,0x05,0x2d,0x2f,0x34};
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

static void backing(const probe_common::GuardedMap& m,const tlb_reach::Cell& c,const char* stage){size_t huge=0;if(!probe_common::read_anon_huge_kb(m.buf,1048576ull*4096,&huge)||huge)throw std::runtime_error("backing-not-4k");std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"%s\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n",c.id().c_str(),stage);}
#endif
int main(int argc,char** argv){
    try{
        if(argc<2)throw std::runtime_error("usage-reach-run-plan-layout-reverse");std::string mode=argv[1];bool layout=mode=="--layout",reverse=false;uintptr_t base=0;
        if(layout){if(argc!=3&&argc!=4)throw std::runtime_error("usage-layout");std::string value=argv[2];if(value.empty()||value.find_first_not_of("0123456789")!=std::string::npos)throw std::runtime_error("layout-base");base=std::stoull(value);if(!base||base%4096||base>UINTPTR_MAX-(1048576ull*4096-1))throw std::runtime_error("layout-base");if(argc==4){if(std::string(argv[3])!="--reverse")throw std::runtime_error("usage-layout-reverse");reverse=true;}}
        else{if((mode!="--run"&&mode!="--plan")||(argc!=2&&argc!=3))throw std::runtime_error("usage-reach");if(argc==3){if(std::string(argv[2])!="--reverse")throw std::runtime_error("usage-reverse");reverse=true;}}
        auto cells=tlb_reach::cells(reverse);
        if(mode=="--plan"||layout){config(reverse);if(layout)mapping(base);for(size_t i=0;i<cells.size();++i){cell(cells[i],i);if(layout)geometry(cells[i],base);}return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
        throw std::runtime_error("measurement-requires-linux-aarch64");
#else
        if(sysconf(_SC_PAGESIZE)!=4096)throw std::runtime_error("page-size");cpu_set_t cpus;CPU_ZERO(&cpus);CPU_SET(7,&cpus);if(sched_setaffinity(0,sizeof(cpus),&cpus)||sched_getcpu()!=7)throw std::runtime_error("affinity");
        auto mapping=probe_common::map_guarded_anonymous(1048576ull*4096,4096);if(!mapping.buf||madvise(mapping.buf,1048576ull*4096,MADV_NOHUGEPAGE))throw std::runtime_error("mapping-policy");for(unsigned p:prefaulted())*reinterpret_cast<uintptr_t*>(mapping.buf+uint64_t(p)*4096+tlb_reach::offset(p))=0;
        Perf perf;perf.open();config(reverse);std::printf("{\"type\":\"pmu\",\"ids\":[");for(unsigned i=0;i<6;++i)std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(perf.ids[i]));std::puts("]}");::mapping(reinterpret_cast<uintptr_t>(mapping.buf));perf.enable();
        for(size_t i=0;i<cells.size();++i){const auto& c=cells[i];std::vector<unsigned> pages,order;uintptr_t head=0,original=0;if(c.n){pages=tlb_reach::pages(c.shape,c.n);order=tlb_reach::order(c);head=tlb_reach::link(mapping.buf,c,pages,order);original=head;reach_k1(&head,c.loads);if(head!=original)throw std::runtime_error("warmup-graph-end");}
            cell(c,i);geometry(c,reinterpret_cast<uintptr_t>(mapping.buf));backing(mapping,c,"before");std::array<pg_sample,3> saved{};
            for(unsigned t=0;t<3;++t){auto a=perf.read();if(c.n)reach_k1(&head,c.loads);asm volatile("":::"memory");auto b=perf.read();const char* error=pg_delta(&a,&b,6,&saved[t]);if(error)throw std::runtime_error(error);if(head!=original)throw std::runtime_error("measured-graph-end");}
            backing(mapping,c,"after");for(unsigned t=0;t<3;++t){const auto& s=saved[t];std::printf("{\"type\":\"round\",\"cell\":\"%s\",\"position\":%zu,\"round\":%u,\"head_returned\":true,\"enabled\":%llu,\"running\":%llu,\"counts\":[",c.id().c_str(),i,t,static_cast<unsigned long long>(s.enabled),static_cast<unsigned long long>(s.running));for(unsigned e=0;e<6;++e)std::printf("%s%llu",e?",":"",static_cast<unsigned long long>(s.values[e]));std::puts("]}");}if(sched_getcpu()!=7)throw std::runtime_error("cpu-migrated");
        }
        perf.disable();munmap(mapping.mapping_base,mapping.mapping_bytes);
#endif
        return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"error[%s]\n",e.what());std::printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",e.what());return 1;}
}
