// SPDX-License-Identifier: Apache-2.0
// Frozen representation intervention: docs/design/2026-10-12-tlb-pointer-representation.md.
// Full set/order/offset evidence; never infer hardware aggregation from THP=0.
#include "tlb_pointer_repr_layout.h"
#include "pagemap_decode.h"
#include <fcntl.h>
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
static void config(bool reverse){std::printf("{\"type\":\"config\",\"version\":1,\"probe\":\"tlb-pointer-representation\",\"pool_pages\":1048576,\"page_set_seed\":271,\"order_seed\":137,\"n_grid\":[1024,1792,2048],\"load_budget\":1048576,\"rounds\":3,\"events\":[17,8,5,52,33108,33109],\"pmu_type\":8,\"reverse\":%s,\"cells\":37,\"windows\":111,\"decode_loop_instructions\":4}\n",reverse?"true":"false");}
static void cell(const tlb_repr::Cell& c,size_t i){std::printf("{\"type\":\"cell\",\"cell\":\"%s\",\"position\":%zu,\"shape\":\"%s\",\"offset\":\"%s\",\"order\":\"%s\",\"n\":%u,\"loads\":%u,\"span_bytes\":%llu,\"line_bytes\":%llu,\"rounds\":3,\"representation\":\"%s\",\"mask\":%llu}\n",c.id().c_str(),i,c.trace.shape.c_str(),c.trace.offset.c_str(),c.trace.order.c_str(),c.trace.n,c.trace.loads,static_cast<unsigned long long>(c.trace.span_bytes),static_cast<unsigned long long>(c.trace.line_bytes),c.representation.c_str(),static_cast<unsigned long long>(c.mask));}
// These exporters serve both --layout and actual measurement: no parallel
// metadata-only selector. Parent IDs are VA proxies for 512-descriptor regions.
static void mapping(const std::array<uintptr_t,3>& bases){std::printf("{\"type\":\"physical-backing\",\"backing_pages\":2560,\"pool_pages\":1048576,\"pte_cont_state\":\"UNKNOWN\",\"arena_bases\":[");for(unsigned i=0;i<3;++i)std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(bases[i]));std::puts("]}");}
static void geometry(const tlb_repr::Cell& c,uintptr_t base){std::vector<unsigned> pp,oo,offsets,hist(256);std::set<uint64_t> parents;if(c.trace.n){pp=tlb_reach::pages(c.trace.shape,c.trace.n);oo=tlb_reach::order(c.trace);for(unsigned p:pp){offsets.push_back(tlb_reach::offset(p));uint64_t vpn=base/4096+p;++hist[vpn%256];parents.insert(vpn>>9);}}
    std::printf("{\"type\":\"geometry\",\"cell\":\"%s\",\"page_ids\":",c.id().c_str());arr(pp);std::printf(",\"order_indices\":");arr(oo);std::printf(",\"offsets\":");arr(offsets);std::printf(",\"vpn_low8_hist\":");arr(hist);std::printf(",\"l3_parent_count\":%zu,\"l3_parent_ids\":[",parents.size());size_t i=0;for(auto p:parents)std::printf("%s%llu",i++?",":"",static_cast<unsigned long long>(p));std::puts("]}");}
#if defined(__linux__) && defined(__aarch64__)
// Identical four-ISA decode body for zero and nonzero dynamic masks.
// A zero mask is still passed in X17; hardware elimination is not excluded.
extern "C" __attribute__((noinline)) void repr_k1(uintptr_t* head,uint64_t iterations,uint64_t mask){asm volatile("ldr x0,[%[h]]\nmov x8,%[n]\nmov x17,%[mask]\n1: ldr x0,[x0]\neor x0,x0,x17\nsubs x8,x8,#1\nb.ne 1b\nstr x0,[%[h]]"::[h]"r"(head),[n]"r"(iterations),[mask]"r"(mask):"x0","x8","x17","cc","memory");}
// GROUP+ID uses the shared pure wire decoder, never software value position.
struct Perf {
    int fd[6]={-1,-1,-1,-1,-1,-1};uint64_t ids[6]{};
    ~Perf(){for(int f:fd)if(f>=0)close(f);}
    void open() {
        constexpr uint64_t events[]={0x11,0x08,0x05,0x34,0x8154,0x8155};
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

// One smaps pass checks all four regions, including shmem/file PMD fields.
static void backing(const tlb_alias::Space& sp,const tlb_repr::Cell& c,const char* stage){
    std::array<uintptr_t,4> begins{reinterpret_cast<uintptr_t>(sp.canonical.g.buf),reinterpret_cast<uintptr_t>(sp.bases[0]),reinterpret_cast<uintptr_t>(sp.bases[1]),reinterpret_cast<uintptr_t>(sp.bases[2])};std::array<uint64_t,4> bytes{2560ull*4096,1048576ull*4096,1048576ull*4096,1048576ull*4096},covered{};
    std::ifstream file("/proc/self/smaps");if(!file)throw std::runtime_error("alias-smaps-open");std::string line;bool overlap=false;unsigned seen=0;auto finish=[&](){if(overlap&&seen!=31)throw std::runtime_error("alias-smaps-field-missing");};
    while(std::getline(file,line)){unsigned long long b=0,e=0;size_t value=0;if(std::sscanf(line.c_str(),"%llx-%llx",&b,&e)==2){finish();overlap=false;seen=0;for(unsigned i=0;i<4;++i){uintptr_t lo=std::max(uintptr_t(b),begins[i]),hi=std::min(uintptr_t(e),begins[i]+bytes[i]);if(hi>lo){covered[i]+=hi-lo;overlap=true;}}continue;}if(!overlap)continue;
        if(std::sscanf(line.c_str(),"KernelPageSize: %zu kB",&value)==1){seen|=1;if(value!=4)throw std::runtime_error("alias-kernel-page");}
        else if(std::sscanf(line.c_str(),"MMUPageSize: %zu kB",&value)==1){seen|=2;if(value!=4)throw std::runtime_error("alias-mmu-page");}
        else if(std::sscanf(line.c_str(),"AnonHugePages: %zu kB",&value)==1){seen|=4;if(value)throw std::runtime_error("alias-anon-huge");}
        else if(std::sscanf(line.c_str(),"ShmemPmdMapped: %zu kB",&value)==1){seen|=8;if(value)throw std::runtime_error("alias-shmem-pmd");}
        else if(std::sscanf(line.c_str(),"FilePmdMapped: %zu kB",&value)==1){seen|=16;if(value)throw std::runtime_error("alias-file-pmd");}
    }finish();if(covered!=bytes)throw std::runtime_error("alias-smaps-coverage");std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"%s\",\"kernel_page_kb\":4,\"mmu_page_kb\":4,\"anon_huge_kb\":0,\"shmem_pmd_kb\":0,\"file_pmd_kb\":0}\n",c.id().c_str(),stage);
}
struct PfnSnapshot{std::vector<uint64_t> values,entries;};
static PfnSnapshot pfns(int fd,const tlb_alias::Space& sp,const tlb_repr::Cell& c,bool canonical){PfnSnapshot out;for(unsigned i=0;i<c.trace.n;++i){uintptr_t addr=canonical?sp.canonical_node(i):sp.node(c.trace.shape,i);uint64_t entry=0;if(pread(fd,&entry,8,off_t(addr/4096)*8)!=8)throw std::runtime_error("alias-pagemap-read");auto d=pagemap_decode(entry);if(!d.present||d.swapped||!d.pfn)throw std::runtime_error("alias-pfn-not-visible");out.values.push_back(d.pfn);out.entries.push_back(entry);}return out;}
static void u64arr(const std::vector<uint64_t>& v){std::printf("[");for(size_t i=0;i<v.size();++i)std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(v[i]));std::printf("]");}
static void certificate(const tlb_repr::Cell& c,const char* stage,const PfnSnapshot& snapshot){std::printf("{\"type\":\"pfn-certificate\",\"cell\":\"%s\",\"stage\":\"%s\",\"alias_pfns\":",c.id().c_str(),stage);u64arr(snapshot.values);std::printf(",\"pagemap_entries\":");u64arr(snapshot.entries);std::puts("}");}
// Read actual shared backing contents before and after, never export only
// intended graph words. Raw addresses/words stay private; consumer decodes all.
static void graph(const tlb_repr::Cell& c,const tlb_alias::Space& sp,const char* stage,uintptr_t head){std::vector<uint64_t> words;for(unsigned i=0;i<c.trace.n;++i)words.push_back(*reinterpret_cast<volatile uintptr_t*>(sp.canonical_node(i)));std::printf("{\"type\":\"graph-certificate\",\"cell\":\"%s\",\"stage\":\"%s\",\"head\":%llu,\"stored_words\":",c.id().c_str(),stage,static_cast<unsigned long long>(head));u64arr(words);std::puts("}");}
#endif
int main(int argc,char** argv){
    try{
        if(argc<2)throw std::runtime_error("usage-reach-run-plan-layout-reverse");std::string mode=argv[1];bool layout=mode=="--layout",reverse=false;uintptr_t base=0;
        if(layout){if(argc!=3&&argc!=4)throw std::runtime_error("usage-layout");std::string value=argv[2];if(value.empty()||value.find_first_not_of("0123456789")!=std::string::npos)throw std::runtime_error("layout-base");base=std::stoull(value);if(!base||base%4096||base%1048576||base>UINTPTR_MAX-(3*1048576ull*4096-1))throw std::runtime_error("layout-base");if(argc==4){if(std::string(argv[3])!="--reverse")throw std::runtime_error("usage-layout-reverse");reverse=true;}}
        else{if((mode!="--run"&&mode!="--plan")||(argc!=2&&argc!=3))throw std::runtime_error("usage-reach");if(argc==3){if(std::string(argv[2])!="--reverse")throw std::runtime_error("usage-reverse");reverse=true;}}
        auto cells=tlb_repr::cells(reverse);
        if(mode=="--plan"||layout){config(reverse);std::array<uintptr_t,3> bases{base,base+1048576ull*4096,base+2*1048576ull*4096};if(layout)mapping(bases);for(size_t i=0;i<cells.size();++i){cell(cells[i],i);if(layout)geometry(cells[i],cells[i].trace.n?bases[tlb_alias::shape_index(cells[i].trace.shape)]:0);}return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
        throw std::runtime_error("measurement-requires-linux-aarch64");
#else
        if(sysconf(_SC_PAGESIZE)!=4096)throw std::runtime_error("page-size");cpu_set_t cpus;CPU_ZERO(&cpus);CPU_SET(7,&cpus);if(sched_setaffinity(0,sizeof(cpus),&cpus)||sched_getcpu()!=7)throw std::runtime_error("affinity");
        int fd=static_cast<int>(syscall(SYS_memfd_create,"tlb-alias-control",1));tlb_alias::Space sp(fd,4096);int pagemap=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);if(pagemap<0)throw std::runtime_error("alias-pagemap-open");tlb_repr::Cell maximum{{"dense","rotated","random",2560,0,0,0},"plain",0};auto canonical_snapshot=pfns(pagemap,sp,maximum,true);const auto& canonical=canonical_snapshot.values;if(std::set<uint64_t>(canonical.begin(),canonical.end()).size()!=2560)throw std::runtime_error("alias-canonical-not-unique");
        Perf perf;perf.open();config(reverse);std::printf("{\"type\":\"pmu\",\"ids\":[");for(unsigned i=0;i<6;++i)std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(perf.ids[i]));std::puts("]}");std::printf("{\"type\":\"physical-backing\",\"canonical_base\":%llu,\"canonical_pfns\":",static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(sp.canonical.g.buf)));u64arr(canonical);std::printf(",\"canonical_entries\":");u64arr(canonical_snapshot.entries);std::printf(",\"backing_pages\":2560,\"pool_pages\":1048576,\"pte_cont_state\":\"UNKNOWN\",\"arena_bases\":[");for(unsigned i=0;i<3;++i)std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(sp.bases[i])));std::puts("]}");perf.enable();
        for(size_t i=0;i<cells.size();++i){const auto& c=cells[i];uintptr_t head=c.trace.n?tlb_repr::link(sp,c):0,original=head;auto before=pfns(pagemap,sp,c,false);if(!std::equal(before.values.begin(),before.values.end(),canonical.begin()))throw std::runtime_error("alias-pfn-before-conflict");cell(c,i);geometry(c,c.trace.n?reinterpret_cast<uintptr_t>(sp.bases[tlb_alias::shape_index(c.trace.shape)]):0);backing(sp,c,"before");certificate(c,"before",before);graph(c,sp,"before",original);if(c.trace.n){repr_k1(&head,c.trace.loads,c.mask);if(head!=original)throw std::runtime_error("alias-warmup-graph");}std::array<pg_sample,3> saved{};
            for(unsigned t=0;t<3;++t){auto a=perf.read();if(c.trace.n)repr_k1(&head,c.trace.loads,c.mask);asm volatile("":::"memory");auto b=perf.read();const char* error=pg_delta(&a,&b,6,&saved[t]);if(error)throw std::runtime_error(error);if(head!=original)throw std::runtime_error("measured-graph-end");}
            auto after=pfns(pagemap,sp,c,false);if(!std::equal(after.values.begin(),after.values.end(),canonical.begin()))throw std::runtime_error("alias-pfn-after-conflict");backing(sp,c,"after");certificate(c,"after",after);graph(c,sp,"after",head);for(unsigned t=0;t<3;++t){const auto& s=saved[t];std::printf("{\"type\":\"round\",\"cell\":\"%s\",\"position\":%zu,\"round\":%u,\"head_returned\":true,\"enabled\":%llu,\"running\":%llu,\"counts\":[",c.id().c_str(),i,t,static_cast<unsigned long long>(s.enabled),static_cast<unsigned long long>(s.running));for(unsigned e=0;e<6;++e)std::printf("%s%llu",e?",":"",static_cast<unsigned long long>(s.values[e]));std::puts("]}");}if(sched_getcpu()!=7)throw std::runtime_error("cpu-migrated");
        }
        perf.disable();close(pagemap);
#endif
        return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"error[%s]\n",e.what());std::printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",e.what());return 1;}
}
