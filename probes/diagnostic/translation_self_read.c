/* SPDX-License-Identifier: Apache-2.0
 * Owned-process root descriptors only; no physical direct-map bias assumptions.
 * Protocol: docs/design/2026-10-12-translation-self-read.md.
 * All BPF objects are unpinned FD lifetimes; every exit closes link/program/map.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "translation_self_bpf.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#if defined(__linux__) && defined(__aarch64__)
#include <linux/bpf.h>
#include <sched.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <sys/wait.h>
_Static_assert(sizeof(struct bpf_insn)==sizeof(struct self_insn),"UAPI size");
static int call_bpf(enum bpf_cmd cmd,union bpf_attr *a){return (int)syscall(SYS_bpf,cmd,a,sizeof(*a));}
#endif
static void export_program(unsigned pid,unsigned i0,unsigned i1,int fd){
 struct self_program p=self_build(pid,i0,i1,fd);
 printf("{\"probe\":\"translation-self-read\",\"version\":1,\"owner_pid\":%u,\"map_fd\":%d,\"root_indices\":[%u,%u],\"task_mm\":1440,\"task_tgid\":1588,\"mm_pgd\":56,\"syscall_id\":172,\"instructions\":[",pid,fd,i0,i1);
 for(size_t j=0;j<p.n;++j){struct self_insn x=p.insn[j];printf("%s{\"code\":%u,\"dst\":%u,\"src\":%u,\"off\":%d,\"imm\":%d}",j?",":"",x.code,x.regs&15,x.regs>>4,x.off,x.imm);}printf("]}");
}
static int failure(const char *stage,int number){printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\",\"errno\":%d}}\n",stage,number);return 1;}
int main(int argc,char **argv){
 if(argc>=2&&!strcmp(argv[1],"--plan")){
  if(argc!=2&&argc!=6)return failure("plan-usage",0);
  unsigned v[4]={12345,3,4,7};if(argc==6)for(unsigned j=0;j<4;++j){char *end=NULL;errno=0;unsigned long x=strtoul(argv[j+2],&end,10);if(errno||!end||*end||x>2147483647ul)return failure("plan-value",0);v[j]=(unsigned)x;}
  if(!v[0]||v[1]>=512||v[2]>=512||v[1]==v[2])return failure("plan-value",0);
  export_program(v[0],v[1],v[2],(int)v[3]);puts("");return 0;
 }
 if(argc!=2||strcmp(argv[1],"--run"))return failure("usage",0);
#if !defined(__linux__) || !defined(__aarch64__)
 return failure("requires-linux-aarch64",0);
#else
 const char *stage="page-size";int number=0,map=-1,prog=-1,link=-1;void *arena=MAP_FAILED;char log[65536]={0};uint64_t before[8]={0},negative[8]={0},result[8]={0};unsigned pid=(unsigned)syscall(SYS_getpid),indices[2]={0};
 if(sysconf(_SC_PAGESIZE)!=4096)goto out;
 cpu_set_t cpu;CPU_ZERO(&cpu);CPU_SET(7,&cpu);stage="affinity";if(sched_setaffinity(0,sizeof(cpu),&cpu)||sched_getcpu()!=7){number=errno;goto out;}
 stage="owned-arena";arena=mmap(NULL,(size_t)2<<30,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_NORESERVE,-1,0);if(arena==MAP_FAILED){number=errno;goto out;}
 for(unsigned j=0;j<2;++j){void *page=(char*)arena+((size_t)j<<30);stage="owned-prefault";if(mprotect(page,4096,PROT_READ|PROT_WRITE)){number=errno;goto out;}*(volatile uint64_t*)page=UINT64_C(0x74b951ca21df0386)+j;indices[j]=(unsigned)((uintptr_t)page>>30)&511;}
 union bpf_attr a={0};a.map_type=BPF_MAP_TYPE_ARRAY;a.key_size=4;a.value_size=64;a.max_entries=1;stage="bpf-map-create";map=call_bpf(BPF_MAP_CREATE,&a);if(map<0){number=errno;goto out;}
 struct self_program p=self_build(pid,indices[0],indices[1],map);memset(&a,0,sizeof(a));a.prog_type=BPF_PROG_TYPE_RAW_TRACEPOINT;a.insn_cnt=(uint32_t)p.n;a.insns=(uintptr_t)p.insn;a.license=(uintptr_t)"GPL";a.log_level=1;a.log_size=sizeof(log);a.log_buf=(uintptr_t)log;stage="bpf-program-load";prog=call_bpf(BPF_PROG_LOAD,&a);if(prog<0){number=errno;goto out;}
 memset(&a,0,sizeof(a));a.raw_tracepoint.name=(uintptr_t)"sys_enter";a.raw_tracepoint.prog_fd=(uint32_t)prog;stage="bpf-raw-attach";link=call_bpf(BPF_RAW_TRACEPOINT_OPEN,&a);if(link<0){number=errno;goto out;}
 uint32_t key=0;memset(&a,0,sizeof(a));a.map_fd=(uint32_t)map;a.key=(uintptr_t)&key;a.value=(uintptr_t)before;stage="initial-map-read";if(call_bpf(BPF_MAP_LOOKUP_ELEM,&a)){number=errno;goto out;}
 for(unsigned j=0;j<3;++j)(void)syscall(SYS_gettid);
 stage="negative-child";pid_t child=fork();if(child<0){number=errno;goto out;}if(!child){for(unsigned j=0;j<3;++j)(void)syscall(SYS_getpid);_exit(0);}int status;if(waitpid(child,&status,0)!=child||!WIFEXITED(status)||WEXITSTATUS(status)){number=errno;goto out;}
 a.value=(uintptr_t)negative;stage="negative-map-read";if(call_bpf(BPF_MAP_LOOKUP_ELEM,&a)){number=errno;goto out;}
 for(unsigned j=0;j<3;++j)(void)syscall(SYS_getpid);
 a.value=(uintptr_t)result;stage="positive-map-read";if(call_bpf(BPF_MAP_LOOKUP_ELEM,&a)){number=errno;goto out;}
 close(link);link=-1;close(prog);prog=-1;close(map);map=-1;
 printf("{\"type\":\"self-read\",\"cpu\":%d,\"page_bytes\":4096,\"va\":[%"PRIuPTR",%"PRIuPTR"],\"program\":",sched_getcpu(),(uintptr_t)arena,(uintptr_t)arena+((uintptr_t)1<<30));export_program(pid,indices[0],indices[1],(int)p.insn[6].imm);
 const uint64_t *snapshots[]={before,negative,result};const char *names[]={"initial","negative","positive"};for(unsigned j=0;j<3;++j){printf(",\"%s\":[",names[j]);for(unsigned k=0;k<8;++k)printf("%s%"PRIu64,k?",":"",snapshots[j][k]);printf("]");}printf(",\"fds_closed\":true}\n");munmap(arena,(size_t)2<<30);return 0;
 out:
 if(link>=0)close(link);if(prog>=0)close(prog);if(map>=0)close(map);if(arena!=MAP_FAILED)munmap(arena,(size_t)2<<30);
 if(*log)fprintf(stderr,"verifier:%s\n",log);return failure(stage,number);
#endif
}
