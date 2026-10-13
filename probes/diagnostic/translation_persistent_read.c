/* SPDX-License-Identifier: Apache-2.0
 * Private exact-VA registration and sticky first-error observer, eight owned nodes.
 * Contract docs/design/2026-10-13-translation-persistent-read.md. All FDs unpinned.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "translation_persistent_bpf.h"
#include "translation_persistent_gate.h"
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
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
_Static_assert(sizeof(struct bpf_insn)==sizeof(struct persistent_insn),"BPF UAPI wire");
static int call(enum bpf_cmd c,union bpf_attr*a){return(int)syscall(SYS_bpf,c,a,sizeof(*a));}
static int page(int fd,uintptr_t va,uint64_t*out){return pread(fd,out,8,(off_t)(va/4096*8))==8?0:-1;}
static int lookup(int map,uint64_t*out){uint32_t key=0;union bpf_attr a={0};a.map_fd=(uint32_t)map;a.key=(uintptr_t)&key;a.value=(uintptr_t)out;return call(BPF_MAP_LOOKUP_ELEM,&a);}
static int update(int map,uint64_t*value){uint32_t key=0;union bpf_attr a={0};a.map_fd=(uint32_t)map;a.key=(uintptr_t)&key;a.value=(uintptr_t)value;a.flags=BPF_ANY;return call(BPF_MAP_UPDATE_ELEM,&a);}
static void vector(const uint64_t*v,unsigned n){putchar('[');for(unsigned i=0;i<n;++i)printf("%s%"PRIu64,i?",":"",v[i]);putchar(']');}
#endif
static int fail(const char*r,int e){printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\",\"errno\":%d}}\n",r,e);return 1;}
static void words(const struct persistent_program*p){putchar('[');for(size_t j=0;j<p->n;++j){struct persistent_insn x=p->insn[j];printf("%s{\"code\":%u,\"dst\":%u,\"src\":%u,\"off\":%d,\"imm\":%d}",j?",":"",x.code,x.regs&15,x.regs>>4,x.off,x.imm);}putchar(']');}
static void plan(unsigned pid,int fd){struct persistent_program e=persistent_build(pid,fd,0),r=persistent_build(pid,fd,1);printf("{\"probe\":\"translation-persistent-read\",\"version\":1,\"owner_pid\":%u,\"map_fd\":%d,\"value_bytes\":136,\"request_word\":16,\"kernel_hook\":\"do_set_pte\",\"vmf_pmd\":48,\"vmf_pte\":88,\"task_mm\":1440,\"mm_pgd\":56,\"entry_instructions\":",pid,fd);words(&e);printf(",\"return_instructions\":");words(&r);puts("}");}
int main(int argc,char**argv){if(argc>=2&&!strcmp(argv[1],"--plan")){if(argc!=2&&argc!=4)return fail("plan-usage",0);uint64_t v[2]={12345,7};if(argc==4)for(unsigned j=0;j<2;++j){char*end;errno=0;v[j]=strtoull(argv[j+2],&end,10);if(errno||!*argv[j+2]||*end)return fail("plan-value",0);}if(!v[0]||v[0]>=0x80000000u||v[1]>2147483647)return fail("plan-value",0);plan((unsigned)v[0],(int)v[1]);return 0;}if(argc!=2||strcmp(argv[1],"--run"))return fail("usage-plan-run",0);
#if !defined(__linux__) || !defined(__aarch64__)
return fail("requires-linux-aarch64",0);
#else
int rc=1,map=-1,prog[2]={-1,-1},event[2]={-1,-1},pm=-1,mem=-1,number=0;void*canonical=MAP_FAILED,*arena=MAP_FAILED,*scratch=MAP_FAILED;const char*stage="page-size";char log[65536]={0};unsigned pid=(unsigned)syscall(SYS_getpid),type=0;if(sysconf(_SC_PAGESIZE)!=4096)goto done;cpu_set_t cp;CPU_ZERO(&cp);CPU_SET(7,&cp);stage="affinity";if(sched_setaffinity(0,sizeof(cp),&cp)||sched_getcpu()!=7)goto done;mem=(int)syscall(SYS_memfd_create,"persistent-own",1);stage="memfd";if(mem<0||ftruncate(mem,8*4096))goto done;canonical=mmap(NULL,8*4096,PROT_READ|PROT_WRITE,MAP_SHARED,mem,0);arena=mmap(NULL,16*4096,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);scratch=mmap(NULL,3*4096,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);stage="owned-mappings";if(canonical==MAP_FAILED||arena==MAP_FAILED||scratch==MAP_FAILED)goto done;for(unsigned n=0;n<8;++n){*(uint64_t*)((char*)canonical+4096*n)=UINT64_C(0x12340000)+n;void*t=(char*)arena+8192*n;if(mmap(t,4096,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,mem,4096*n)!=t)goto done;}pm=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);stage="pagemap";if(pm<0)goto done;uint64_t whole_before[8],whole_after[8];for(unsigned n=0;n<8;++n)if(page(pm,(uintptr_t)canonical+4096*n,whole_before+n))goto done;FILE*f=fopen("/sys/bus/event_source/devices/kprobe/type","r");stage="kprobe-type";if(!f)goto done;int parsed=fscanf(f,"%u",&type);fclose(f);if(parsed!=1||!type)goto done;f=fopen("/sys/bus/event_source/devices/kprobe/format/retprobe","r");if(!f)goto done;char fmt[32];char*line=fgets(fmt,sizeof(fmt),f);fclose(f);if(!line||strcmp(fmt,"config:0\n"))goto done;union bpf_attr a={0};a.map_type=BPF_MAP_TYPE_ARRAY;a.key_size=4;a.value_size=136;a.max_entries=1;stage="bpf-map-create";map=call(BPF_MAP_CREATE,&a);if(map<0)goto done;
for(unsigned j=0;j<2;++j){struct persistent_program p=persistent_build(pid,map,(int)j);memset(&a,0,sizeof(a));a.prog_type=BPF_PROG_TYPE_KPROBE;a.insn_cnt=(uint32_t)p.n;a.insns=(uintptr_t)p.insn;a.license=(uintptr_t)"GPL";a.log_level=1;a.log_size=sizeof(log);a.log_buf=(uintptr_t)log;stage="bpf-program-load";prog[j]=call(BPF_PROG_LOAD,&a);if(prog[j]<0)goto done;struct perf_event_attr pe={0};pe.size=sizeof(pe);pe.type=type;pe.config=j;pe.config1=(uintptr_t)"do_set_pte";pe.sample_period=1;pe.wakeup_events=1;pe.disabled=1;stage="perf-kprobe-open";event[j]=(int)syscall(SYS_perf_event_open,&pe,-1,7,-1,PERF_FLAG_FD_CLOEXEC);if(event[j]<0)goto done;stage="perf-bpf-attach";if(ioctl(event[j],PERF_EVENT_IOC_SET_BPF,prog[j]))goto done;}for(unsigned j=0;j<2;++j)if(ioctl(event[j],PERF_EVENT_IOC_ENABLE,0))goto done;
plan(pid,map);printf("{\"type\":\"mapping\",\"cpu\":7,\"page_bytes\":4096,\"nodes\":8,\"kprobe_type\":%u,\"alias_base\":%"PRIuPTR",\"canonical_base\":%"PRIuPTR",\"scratch_base\":%"PRIuPTR"}\n",type,(uintptr_t)arena,(uintptr_t)canonical,(uintptr_t)scratch);printf("{\"type\":\"canonical-before\",\"entries\":");vector(whole_before,8);puts("}");
for(unsigned n=0;n<8;++n){uintptr_t va=(uintptr_t)arena+8192*n;uint64_t previous[17],initial[17]={0},foreign[17]={0},negative[17]={0},positive[17]={0},cb[2],ca[2],before[2],after[2];stage="request-registration";if(lookup(map,previous)||persistent_registration_gate(previous,n==0))goto done;initial[16]=va;if(update(map,initial)||lookup(map,initial))goto done;void*t=scratch;if(mmap(t,4096,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,mem,4096*(n^1u))!=t)goto done;stage="node-pagemap";if(page(pm,(uintptr_t)canonical+4096*n,cb)||page(pm,(uintptr_t)canonical+4096*(n^1u),cb+1)||page(pm,va,before)||page(pm,(uintptr_t)scratch,before+1))goto done;
if(n==0){stage="foreign-negative";pid_t child=fork();if(child<0)goto done;if(!child){volatile uint64_t v=*(volatile uint64_t*)va;(void)v;_exit(0);}int status;if(waitpid(child,&status,0)!=child||!WIFEXITED(status)||WEXITSTATUS(status)||lookup(map,foreign)||memcmp(foreign,initial,sizeof(foreign)))goto done;}
volatile uint64_t wrong=*(volatile uint64_t*)scratch;(void)wrong;stage="wrong-va-negative";if(lookup(map,negative))goto done;uint64_t word=*(volatile uint64_t*)va;stage="capture-pagemap";if(lookup(map,positive)||page(pm,(uintptr_t)canonical+4096*n,ca)||page(pm,(uintptr_t)canonical+4096*(n^1u),ca+1)||page(pm,va,after)||page(pm,(uintptr_t)scratch,after+1))goto done;
printf("{\"type\":\"persistent-read\",\"node\":%u,\"selected_va\":%"PRIuPTR",\"node_word\":%"PRIu64",\"cpu\":%d,\"observer_active\":true,\"foreign\":",n,va,word,sched_getcpu());if(n==0)vector(foreign,17);else printf("null");const uint64_t*values[]={previous,initial,negative,positive,cb,ca,before,after};const char*names[]={"previous","initial","negative","positive","canonical_before","canonical_after","alias_before","alias_after"};for(unsigned j=0;j<8;++j){printf(",\"%s\":",names[j]);vector(values[j],j<4?17:2);}puts("}");unsigned good=persistent_capture_gate(pid,va,UINT64_C(0x12340000)+n,word,cb,ca,before,after,initial,negative,positive);if(good==1){stage="persistent-capture-not-qualified";goto done;}if(good==2){printf("{\"type\":\"stop\",\"reason\":\"not-excited\",\"captures\":%u}\n",n+1);rc=0;goto cleanup;}if(fflush(stdout))goto done;}
for(unsigned n=0;n<8;++n)if(page(pm,(uintptr_t)canonical+4096*n,whole_after+n))goto done;for(unsigned j=0;j<2;++j){close(event[j]);event[j]=-1;close(prog[j]);prog[j]=-1;}close(map);map=-1;close(pm);pm=-1;close(mem);mem=-1;printf("{\"type\":\"final\",\"fds_closed\":true,\"canonical_after\":");vector(whole_after,8);puts("}");rc=0;goto cleanup;
done:number=errno;if(*log)fprintf(stderr,"verifier:%s\n",log);rc=fail(stage,number);
cleanup:for(unsigned j=0;j<2;++j){if(event[j]>=0)close(event[j]);if(prog[j]>=0)close(prog[j]);}if(map>=0)close(map);if(pm>=0)close(pm);if(mem>=0)close(mem);if(canonical!=MAP_FAILED)munmap(canonical,8*4096);if(arena!=MAP_FAILED)munmap(arena,16*4096);if(scratch!=MAP_FAILED)munmap(scratch,3*4096);return rc;
#endif
}
