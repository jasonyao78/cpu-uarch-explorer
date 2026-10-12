// SPDX-License-Identifier: Apache-2.0
// Own-process PFN visibility only, no PMU or physical capacity inference.
// Frozen protocol: docs/design/2026-10-12-pagemap-visibility.md.
#include "tlb_balanced_reach_layout.h"
#include "pagemap_decode.h"
#include "page_policy.h"
#include <cstdio>
#include <set>
#include <array>
#include <fcntl.h>
#ifdef __linux__
#include <sched.h>
#endif
static std::vector<unsigned> selected(){std::set<unsigned> out;for(const char* shape:{"dense","spaced","balanced-random"})for(unsigned p:tlb_reach::pages(shape,16))out.insert(p);return std::vector<unsigned>(out.begin(),out.end());}
static void plan(){std::puts("{\"type\":\"config\",\"version\":1,\"probe\":\"pagemap-visibility\",\"pool_pages\":1048576,\"family_nodes\":16,\"snapshots\":2,\"page_set_seed\":271}");std::printf("{\"type\":\"selection\",\"page_ids\":[");auto pp=selected();for(size_t i=0;i<pp.size();++i)std::printf("%s%u",i?",":"",pp[i]);std::puts("]}");}
#if defined(__linux__) && defined(__aarch64__)
static void backing(const probe_common::GuardedMap& m,const char* stage){size_t huge=0;if(!probe_common::read_anon_huge_kb(m.buf,1048576ull*4096,&huge)||huge)throw std::runtime_error("backing-not-4k");std::printf("{\"type\":\"backing\",\"stage\":\"%s\",\"base_page_bytes\":4096,\"anon_huge_kb\":0}\n",stage);}
#endif
int main(int argc,char** argv){try{
    if(argc!=2||(std::string(argv[1])!="--plan"&&std::string(argv[1])!="--run"))throw std::runtime_error("usage-pagemap-plan-run");plan();if(std::string(argv[1])=="--plan")return 0;
#if !defined(__linux__) || !defined(__aarch64__)
    throw std::runtime_error("requires-linux-aarch64");
#else
    if(sysconf(_SC_PAGESIZE)!=4096)throw std::runtime_error("page-size");cpu_set_t cpus;CPU_ZERO(&cpus);CPU_SET(7,&cpus);if(sched_setaffinity(0,sizeof(cpus),&cpus)||sched_getcpu()!=7)throw std::runtime_error("affinity");auto m=probe_common::map_guarded_anonymous(1048576ull*4096,4096);if(!m.buf||madvise(m.buf,1048576ull*4096,MADV_NOHUGEPAGE))throw std::runtime_error("mapping-policy");auto pp=selected();for(unsigned p:pp)*reinterpret_cast<volatile uint64_t*>(m.buf+uint64_t(p)*4096+tlb_reach::offset(p))=p+1;
    int fd=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);if(fd<0)throw std::runtime_error("pagemap-open-blocked");std::printf("{\"type\":\"runtime\",\"cpu\":7,\"base\":%llu}\n",static_cast<unsigned long long>(reinterpret_cast<uintptr_t>(m.buf)));backing(m,"before");
    std::array<std::vector<uint64_t>,2> snapshots;
    for(auto& ss:snapshots)for(unsigned p:pp){uint64_t entry=0;uint64_t vpn=(reinterpret_cast<uintptr_t>(m.buf)/4096)+p;if(pread(fd,&entry,8,static_cast<off_t>(8*vpn))!=8)throw std::runtime_error("pagemap-read-blocked");auto d=pagemap_decode(entry);(void)d;ss.push_back(entry);}
    for(unsigned stage=0;stage<2;++stage)for(size_t i=0;i<pp.size();++i)std::printf("{\"type\":\"pagemap\",\"stage\":\"%s\",\"page_id\":%u,\"entry\":%llu}\n",stage?"after":"before",pp[i],static_cast<unsigned long long>(snapshots[stage][i]));backing(m,"after");close(fd);munmap(m.mapping_base,m.mapping_bytes);if(sched_getcpu()!=7)throw std::runtime_error("cpu-migrated");
#endif
    return 0;
}catch(const std::exception& e){std::fprintf(stderr,"error[%s]\n",e.what());std::printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",e.what());return 1;}}
