// SPDX-License-Identifier: Apache-2.0
// 同VA/PFN关联干预：实际PFN/链接/页策略前后取证，不把聚合或容量假设当观测。
// 冻结：docs/design/2026-10-12-tlb-pfn-association.md。
#include "tlb_pfn_association_space.h"
#include "pagemap_decode.h"
#include "perf_group_read.h"
#include <array>
#include <cstdio>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#ifdef __linux__
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#endif
using tlb_association::Cell;
[[maybe_unused]] static void u64arr(const std::vector<uint64_t>& v){std::printf("[");for(size_t i=0;i<v.size();++i)std::printf("%s%llu",i?",":"",static_cast<unsigned long long>(v[i]));std::printf("]");}
static void arr(const std::vector<unsigned>& v){std::printf("[");for(size_t i=0;i<v.size();++i)std::printf("%s%u",i?",":"",v[i]);std::printf("]");}
static void config(bool reverse){std::printf("{\"type\":\"config\",\"version\":1,\"probe\":\"tlb-pfn-association\",\"backing_pages\":4096,\"pool_pages\":4096,\"alignment_bytes\":2097152,\"order_seed\":137,\"n_grid\":[1024,1280,1536,1792,2048,2304,2560,3072],\"load_budget\":1048576,\"rounds\":3,\"events\":[17,8,5,52,33108,33109],\"pmu_type\":8,\"reverse\":%s,\"cells\":33,\"windows\":99,\"decode_loop_instructions\":4}\n",reverse?"true":"false");}
static void cell(const Cell& c,size_t i){std::printf("{\"type\":\"cell\",\"cell\":\"%s\",\"position\":%zu,\"assignment\":\"%s\",\"order\":\"%s\",\"n\":%u,\"loads\":%u,\"span_bytes\":%llu,\"line_bytes\":%llu,\"rounds\":3,\"mask\":%llu}\n",c.id().c_str(),i,c.assignment.c_str(),c.order.c_str(),c.n,c.loads,static_cast<unsigned long long>(c.n)*4096,static_cast<unsigned long long>(c.n)*64,static_cast<unsigned long long>(c.n?tlb_association::mask:0));}
// 同一positions用于真实remap与导出；consumer按原始canonical PFN独立复验选择。
static void geometry(const Cell& c,uintptr_t base,const std::vector<unsigned>& positions){std::vector<unsigned> inverse(c.n),offsets,hist(256);std::set<uint64_t> parents;for(unsigned j=0;j<c.n;++j){inverse[positions[j]]=j;++hist[(base/4096+j)%256];parents.insert((base/4096+j)>>9);}for(unsigned i=0;i<c.n;++i)offsets.push_back(64*(i%64));std::printf("{\"type\":\"geometry\",\"cell\":\"%s\",\"position_nodes\":",c.id().c_str());arr(positions);std::printf(",\"node_positions\":");arr(inverse);std::printf(",\"order_indices\":");arr(tlb_association::order(c));std::printf(",\"offsets\":");arr(offsets);std::printf(",\"vpn_low8_hist\":");arr(hist);std::printf(",\"l3_parent_count\":%zu,\"l3_parent_ids\":[",parents.size());size_t k=0;for(auto p:parents)std::printf("%s%llu",k++?",":"",static_cast<unsigned long long>(p));std::puts("]}");}
static std::vector<unsigned> positions(const Cell& c,const std::vector<uint64_t>& cp){std::vector<unsigned> pp(c.n);std::iota(pp.begin(),pp.end(),0u);if(c.assignment=="no-adjacent")pp=tlb_association::weave({cp.begin(),cp.begin()+c.n});return pp;}
#if defined(__linux__) && defined(__aarch64__)
// 四ISA与前批逐字相同；动态全位mask，调用点也在NDK二进制中核验。
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

// 实际canonical和整arena的smaps覆盖；VMA数变化不能冒充PTE物理身份不变。
static void backing(const tlb_association::Space& sp,const Cell& c,const char* stage){
    std::array<uintptr_t,2> begins{reinterpret_cast<uintptr_t>(sp.canonical.g.buf),reinterpret_cast<uintptr_t>(sp.base)};std::array<uint64_t,2> bytes{4096ull*4096,4096ull*4096},covered{};
    std::ifstream file("/proc/self/smaps");if(!file)throw std::runtime_error("association-smaps-open");std::string line;bool overlap=false;unsigned seen=0;auto finish=[&](){if(overlap&&seen!=31)throw std::runtime_error("association-smaps-field-missing");};
    while(std::getline(file,line)){unsigned long long b=0,e=0;size_t value=0;if(std::sscanf(line.c_str(),"%llx-%llx",&b,&e)==2){finish();overlap=false;seen=0;for(unsigned i=0;i<2;++i){uintptr_t lo=std::max(uintptr_t(b),begins[i]),hi=std::min(uintptr_t(e),begins[i]+bytes[i]);if(hi>lo){covered[i]+=hi-lo;overlap=true;}}continue;}if(!overlap)continue;
        if(std::sscanf(line.c_str(),"KernelPageSize: %zu kB",&value)==1){seen|=1;if(value!=4)throw std::runtime_error("association-kernel-page");}
        else if(std::sscanf(line.c_str(),"MMUPageSize: %zu kB",&value)==1){seen|=2;if(value!=4)throw std::runtime_error("association-mmu-page");}
        else if(std::sscanf(line.c_str(),"AnonHugePages: %zu kB",&value)==1){seen|=4;if(value)throw std::runtime_error("association-anon-huge");}
        else if(std::sscanf(line.c_str(),"ShmemPmdMapped: %zu kB",&value)==1){seen|=8;if(value)throw std::runtime_error("association-shmem-pmd");}
        else if(std::sscanf(line.c_str(),"FilePmdMapped: %zu kB",&value)==1){seen|=16;if(value)throw std::runtime_error("association-file-pmd");}
    }finish();if(covered!=bytes)throw std::runtime_error("association-smaps-coverage");std::printf("{\"type\":\"backing\",\"cell\":\"%s\",\"stage\":\"%s\",\"kernel_page_kb\":4,\"mmu_page_kb\":4,\"anon_huge_kb\":0,\"shmem_pmd_kb\":0,\"file_pmd_kb\":0}\n",c.id().c_str(),stage);
}

struct PfnSnapshot{std::vector<uint64_t> values,entries;};
static PfnSnapshot pfns(int fd,const tlb_association::Space& sp,unsigned n,bool canonical){PfnSnapshot out;for(unsigned i=0;i<n;++i){uintptr_t address=canonical?sp.canonical_node(i):sp.node(i);uint64_t entry=0;if(pread(fd,&entry,8,off_t(address/4096)*8)!=8)throw std::runtime_error("association-pagemap-read");auto d=pagemap_decode(entry);if(!d.present||d.swapped||!d.pfn)throw std::runtime_error("association-pfn-not-visible");out.values.push_back(d.pfn);out.entries.push_back(entry);}return out;}
static void certificate(const Cell& c,const char* stage,const PfnSnapshot& alias,const PfnSnapshot& canonical){std::printf("{\"type\":\"pfn-certificate\",\"cell\":\"%s\",\"stage\":\"%s\",\"alias_pfns\":",c.id().c_str(),stage);u64arr(alias.values);std::printf(",\"alias_entries\":");u64arr(alias.entries);std::printf(",\"canonical_pfns\":");u64arr(canonical.values);std::printf(",\"canonical_entries\":");u64arr(canonical.entries);std::puts("}");}
// actual words从canonical物理节点读取；不能仅导出意图图来掩盖错误链接。
static void graph(const Cell& c,const tlb_association::Space& sp,const char* stage,uintptr_t head){std::vector<uint64_t> words;for(unsigned i=0;i<c.n;++i){uint64_t word=*reinterpret_cast<volatile uintptr_t*>(sp.canonical_node(i));words.push_back(word);}std::printf("{\"type\":\"graph-certificate\",\"cell\":\"%s\",\"stage\":\"%s\",\"head\":%llu,\"stored_words\":",c.id().c_str(),stage,static_cast<unsigned long long>(head));u64arr(words);std::puts("}");}
#endif
int main(int argc,char** argv){try{
    if(argc<2)throw std::runtime_error("association-usage");std::string mode=argv[1];bool reverse=false;uintptr_t base=0;std::vector<uint64_t> cp;
    if(mode=="--layout"){
        if(argc!=3&&argc!=4)throw std::runtime_error("association-layout-usage");std::string value=argv[2];if(value.empty()||value.find_first_not_of("0123456789")!=std::string::npos)throw std::runtime_error("association-base");base=std::stoull(value);if(!base||base%2097152||base>UINTPTR_MAX-4096ull*4096)throw std::runtime_error("association-base");if(argc==4){if(std::string(argv[3])!="--reverse")throw std::runtime_error("association-reverse");reverse=true;}cp.resize(4096);for(auto& p:cp)if(!(std::cin>>p))throw std::runtime_error("association-layout-pfns");std::string extra;if(std::cin>>extra)throw std::runtime_error("association-layout-extra");std::vector<unsigned> all(4096);std::iota(all.begin(),all.end(),0u);tlb_association::validate(cp,all,false);
    }else{
        if((mode!="--plan"&&mode!="--run")||(argc!=2&&argc!=3))throw std::runtime_error("association-usage");if(argc==3){if(std::string(argv[2])!="--reverse")throw std::runtime_error("association-reverse");reverse=true;}
    }
    auto cells=tlb_association::cells(reverse);
    if(mode=="--plan"||mode=="--layout"){config(reverse);if(mode=="--layout")std::printf("{\"type\":\"physical-backing\",\"arena_base\":%llu,\"backing_pages\":4096,\"pool_pages\":4096,\"pte_cont_state\":\"UNKNOWN\"}\n",static_cast<unsigned long long>(base));for(size_t i=0;i<cells.size();++i){cell(cells[i],i);if(mode=="--layout")geometry(cells[i],base,positions(cells[i],cp));}return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
    throw std::runtime_error("measurement-requires-linux-aarch64");
#else
    if(sysconf(_SC_PAGESIZE)!=4096)throw std::runtime_error("page-size");cpu_set_t cpu;CPU_ZERO(&cpu);CPU_SET(7,&cpu);if(sched_setaffinity(0,sizeof(cpu),&cpu)||sched_getcpu()!=7)throw std::runtime_error("affinity");int fd=int(syscall(SYS_memfd_create,"tlb-association",1));tlb_association::Space sp(fd,4096);int pagemap=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);if(pagemap<0)throw std::runtime_error("association-pagemap-open");auto canonical=pfns(pagemap,sp,4096,true);cp=canonical.values;std::vector<unsigned> all(4096);std::iota(all.begin(),all.end(),0u);tlb_association::validate(cp,all,false);Perf perf;perf.open();config(reverse);std::printf("{\"type\":\"pmu\",\"ids\":[");for(unsigned j=0;j<6;++j)std::printf("%s%llu",j?",":"",static_cast<unsigned long long>(perf.ids[j]));std::puts("]}");std::printf("{\"type\":\"physical-backing\",\"arena_base\":%llu,\"backing_pages\":4096,\"pool_pages\":4096,\"pte_cont_state\":\"UNKNOWN\",\"canonical_base\":%llu,\"canonical_pfns\":",static_cast<unsigned long long>(uintptr_t(sp.base)),static_cast<unsigned long long>(uintptr_t(sp.canonical.g.buf)));u64arr(cp);std::printf(",\"canonical_entries\":");u64arr(canonical.entries);std::puts("}");perf.enable();
    for(size_t i=0;i<cells.size();++i){const auto& c=cells[i];auto pp=sp.remap(c,cp);uintptr_t head=c.n?sp.link(c):0,original=head;auto before=pfns(pagemap,sp,c.n,false),cbefore=pfns(pagemap,sp,c.n,true);if(!std::equal(before.values.begin(),before.values.end(),cp.begin())||before.values!=cbefore.values)throw std::runtime_error("association-pfn-before");cell(c,i);geometry(c,uintptr_t(sp.base),pp);backing(sp,c,"before");certificate(c,"before",before,cbefore);graph(c,sp,"before",head);if(c.n){repr_k1(&head,c.loads,tlb_association::mask);if(head!=original)throw std::runtime_error("association-warm-graph");}std::array<pg_sample,3> samples{};
        for(unsigned t=0;t<3;++t){auto a=perf.read();if(c.n)repr_k1(&head,c.loads,tlb_association::mask);asm volatile("":::"memory");auto b=perf.read();const char* error=pg_delta(&a,&b,6,&samples[t]);if(error)throw std::runtime_error(error);if(head!=original)throw std::runtime_error("association-window-graph");}
        auto after=pfns(pagemap,sp,c.n,false),cafter=pfns(pagemap,sp,c.n,true);if(!std::equal(after.values.begin(),after.values.end(),cp.begin())||after.values!=cafter.values)throw std::runtime_error("association-pfn-after");backing(sp,c,"after");certificate(c,"after",after,cafter);graph(c,sp,"after",head);
        for(unsigned t=0;t<3;++t){const auto& s=samples[t];std::printf("{\"type\":\"round\",\"cell\":\"%s\",\"position\":%zu,\"round\":%u,\"head_returned\":true,\"enabled\":%llu,\"running\":%llu,\"counts\":[",c.id().c_str(),i,t,static_cast<unsigned long long>(s.enabled),static_cast<unsigned long long>(s.running));for(unsigned j=0;j<6;++j)std::printf("%s%llu",j?",":"",static_cast<unsigned long long>(s.values[j]));std::puts("]}");}if(sched_getcpu()!=7)throw std::runtime_error("association-cpu-migrated");
    }
    perf.disable();close(pagemap);
#endif
    return 0;
}catch(const std::exception& e){std::fprintf(stderr,"error[%s]\n",e.what());std::printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",e.what());return 1;}}
