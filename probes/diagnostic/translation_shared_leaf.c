/* SPDX-License-Identifier: Apache-2.0
 * Read-only ptep argument from one shared-memfd read-to-write trigger; no guessed PA bias.
 * docs/design/2026-10-12-translation-shared-leaf.md. Event/program/map are unpinned FD lifetimes.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "translation_leaf_bpf.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#if defined(__linux__) && defined(__aarch64__)
#include <fcntl.h>
#include <linux/bpf.h>
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <sys/wait.h>
_Static_assert(sizeof(struct bpf_insn)==sizeof(struct leaf_insn),"UAPI wire");
static int bpf_call(enum bpf_cmd c,union bpf_attr*a){return(int)syscall(SYS_bpf,c,a,sizeof(*a));}
static int page_entries(int fd,const void *arena,uint64_t out[2]){for(unsigned j=0;j<2;++j){uintptr_t v=(uintptr_t)arena+4096*j;if(pread(fd,&out[j],8,(off_t)(v/4096*8))!=8)return-1;}return 0;}
#endif
static void export_plan(unsigned pid,uint64_t va,int fd){struct leaf_program p=leaf_build(pid,va,fd);printf("{\"probe\":\"translation-self-leaf\",\"version\":1,\"backing\":\"shared-memfd\",\"owner_pid\":%u,\"selected_va\":%"PRIu64",\"map_fd\":%d,\"kernel_hook\":\"ptep_set_access_flags\",\"instructions\":[",pid,va,fd);for(size_t j=0;j<p.n;++j){struct leaf_insn x=p.insn[j];printf("%s{\"code\":%u,\"dst\":%u,\"src\":%u,\"off\":%d,\"imm\":%d}",j?",":"",x.code,x.regs&15,x.regs>>4,x.off,x.imm);}printf("]}");}
static int fail(const char*s,int e){printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\",\"errno\":%d}}\n",s,e);return 1;}
int main(int argc,char**argv){
 if(argc>=2&&!strcmp(argv[1],"--plan")){if(argc!=2&&argc!=5)return fail("plan-usage",0);uint64_t v[3]={12345,UINT64_C(0x100000000),7};if(argc==5)for(unsigned j=0;j<3;++j){char*end=NULL;errno=0;v[j]=strtoull(argv[j+2],&end,10);if(errno||!end||*end)return fail("plan-value",0);}if(!v[0]||v[0]>=0x80000000u||!v[1]||v[1]>=(UINT64_C(1)<<39)||v[1]%4096||v[2]>2147483647)return fail("plan-value",0);export_plan((unsigned)v[0],v[1],(int)v[2]);puts("");return 0;}
 if(argc!=2||strcmp(argv[1],"--run"))return fail("usage",0);
#if !defined(__linux__) || !defined(__aarch64__)
 return fail("requires-linux-aarch64",0);
#else
 int map=-1,prog=-1,event=-1,pm=-1,mem=-1,number=0;void*arena=MAP_FAILED,*canonical=MAP_FAILED;const char*stage="page-size";char log[65536]={0};uint64_t c_before[2]={0},c_after[2]={0},before[2]={0},after[2]={0},initial[8]={0},negative[8]={0},positive[8]={0};unsigned pid=(unsigned)syscall(SYS_getpid),type=0;struct leaf_program program={0};
 if(sysconf(_SC_PAGESIZE)!=4096)goto done;
 cpu_set_t cpu;CPU_ZERO(&cpu);CPU_SET(7,&cpu);stage="affinity";if(sched_setaffinity(0,sizeof(cpu),&cpu)||sched_getcpu()!=7){number=errno;goto done;}
 stage="memfd";mem=(int)syscall(SYS_memfd_create,"shared-leaf",1);if(mem<0||ftruncate(mem,8192)){number=errno;goto done;}
 stage="canonical";canonical=mmap(NULL,8192,PROT_READ|PROT_WRITE,MAP_SHARED,mem,0);if(canonical==MAP_FAILED){number=errno;goto done;}
 stage="arena";arena=mmap(NULL,8192,PROT_READ|PROT_WRITE,MAP_SHARED,mem,0);if(arena==MAP_FAILED){number=errno;goto done;}
 for(unsigned j=0;j<2;++j){*(volatile uint64_t*)((char*)canonical+4096*j)=UINT64_C(0x4b2caf61248de970)+j;volatile uint64_t value=*(volatile uint64_t*)((char*)arena+4096*j);(void)value;}

 stage="pagemap";pm=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);if(pm<0||(page_entries(pm,arena,before)||page_entries(pm,canonical,c_before))){number=errno;goto done;}
 stage="kprobe-type";FILE*f=fopen("/sys/bus/event_source/devices/kprobe/type","r");if(!f){number=errno;goto done;}int scanned=fscanf(f,"%u",&type);fclose(f);if(scanned!=1||!type)goto done;
 union bpf_attr a={0};a.map_type=BPF_MAP_TYPE_ARRAY;a.key_size=4;a.value_size=64;a.max_entries=1;stage="bpf-map-create";map=bpf_call(BPF_MAP_CREATE,&a);if(map<0){number=errno;goto done;}
 program=leaf_build(pid,(uintptr_t)arena,map);memset(&a,0,sizeof(a));a.prog_type=BPF_PROG_TYPE_KPROBE;a.insn_cnt=(uint32_t)program.n;a.insns=(uintptr_t)program.insn;a.license=(uintptr_t)"GPL";a.log_level=1;a.log_size=sizeof(log);a.log_buf=(uintptr_t)log;stage="bpf-program-load";prog=bpf_call(BPF_PROG_LOAD,&a);if(prog<0){number=errno;goto done;}
 struct perf_event_attr pe={0};pe.size=sizeof(pe);pe.type=type;pe.config1=(uintptr_t)"ptep_set_access_flags";pe.sample_period=1;pe.wakeup_events=1;pe.disabled=1;stage="perf-kprobe-open";event=(int)syscall(SYS_perf_event_open,&pe,-1,7,-1,PERF_FLAG_FD_CLOEXEC);if(event<0){number=errno;goto done;}
 stage="perf-bpf-attach";if(ioctl(event,PERF_EVENT_IOC_SET_BPF,prog)||ioctl(event,PERF_EVENT_IOC_ENABLE,0)){number=errno;goto done;}
 uint32_t key=0;memset(&a,0,sizeof(a));a.map_fd=(uint32_t)map;a.key=(uintptr_t)&key;a.value=(uintptr_t)initial;stage="initial-map";if(bpf_call(BPF_MAP_LOOKUP_ELEM,&a)){number=errno;goto done;}
 stage="child-negative";pid_t child=fork();if(child<0){number=errno;goto done;}if(!child){*(volatile uint64_t*)arena^=1;_exit(0);}int status;if(waitpid(child,&status,0)!=child||!WIFEXITED(status)||WEXITSTATUS(status))goto done;
 *(volatile uint64_t*)((char*)arena+4096)^=1;a.value=(uintptr_t)negative;stage="negative-map";if(bpf_call(BPF_MAP_LOOKUP_ELEM,&a)){number=errno;goto done;}
 *(volatile uint64_t*)arena^=1;a.value=(uintptr_t)positive;stage="positive-map";if(bpf_call(BPF_MAP_LOOKUP_ELEM,&a)||(page_entries(pm,arena,after)||page_entries(pm,canonical,c_after))){number=errno;goto done;}
 close(event);event=-1;close(prog);prog=-1;close(map);map=-1;close(pm);pm=-1;close(mem);mem=-1;
 printf("{\"type\":\"leaf-read\",\"backing\":\"shared-memfd\",\"cpu\":%d,\"page_bytes\":4096,\"kprobe_type\":%u,\"program\":",sched_getcpu(),type);export_plan(pid,(uintptr_t)arena,program.insn[10].imm);
 const uint64_t*snapshots[]={initial,negative,positive,before,after,c_before,c_after};const char*names[]={"initial","negative","positive","pagemap_before","pagemap_after","canonical_before","canonical_after"};for(unsigned j=0;j<7;++j){printf(",\"%s\":[",names[j]);for(unsigned k=0;k<(j<3?8u:2u);++k)printf("%s%"PRIu64,k?",":"",snapshots[j][k]);printf("]");}puts(",\"fds_closed\":true}");munmap(arena,8192);munmap(canonical,8192);return 0;
 done:
 if(event>=0)close(event);if(prog>=0)close(prog);if(map>=0)close(map);if(pm>=0)close(pm);if(arena!=MAP_FAILED)munmap(arena,8192);if(canonical!=MAP_FAILED)munmap(canonical,8192);if(mem>=0)close(mem);if(*log)fprintf(stderr,"verifier:%s\n",log);return fail(stage,number);
#endif
}
