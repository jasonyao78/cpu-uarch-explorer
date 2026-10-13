/* SPDX-License-Identifier: Apache-2.0
 * Own shared graph descriptor binding with exact-VA installation reads; no guessed PA bias.
 * docs/design/2026-10-13-tlb-descriptor-graph.md. Event/program/map are unpinned FD lifetimes.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "translation_install_bpf.h"
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
_Static_assert(sizeof(struct bpf_insn)==sizeof(struct install_insn),"UAPI wire");
static int bpf_call(enum bpf_cmd c,union bpf_attr*a){return(int)syscall(SYS_bpf,c,a,sizeof(*a));}
#endif
static void export_words(const struct install_program*p){printf("[");for(size_t j=0;j<p->n;++j){struct install_insn x=p->insn[j];printf("%s{\"code\":%u,\"dst\":%u,\"src\":%u,\"off\":%d,\"imm\":%d}",j?",":"",x.code,x.regs&15,x.regs>>4,x.off,x.imm);}printf("]");}
static void export_plan(unsigned pid,uint64_t va,int fd){struct install_program entry=install_build(pid,va,fd,0),ret=install_build(pid,va,fd,1);printf("{\"probe\":\"translation-installation-read\",\"version\":1,\"owner_pid\":%u,\"selected_va\":%"PRIu64",\"map_fd\":%d,\"kernel_hook\":\"do_set_pte\",\"vmf_pmd\":48,\"vmf_pte\":88,\"task_mm\":1440,\"mm_pgd\":56,\"entry_instructions\":",pid,va,fd);export_words(&entry);printf(",\"return_instructions\":");export_words(&ret);printf("}");}
static int fail(const char*s,int e){printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\",\"errno\":%d}}\n",s,e);return 1;}

#define NODES 32u
static void cycle(unsigned order[NODES],unsigned next[NODES]){uint32_t seed=137;for(unsigned i=0;i<NODES;++i)order[i]=i;for(unsigned i=NODES-1;i;--i){seed=1664525u*seed+1013904223u;unsigned j=seed%(i+1),v=order[i];order[i]=order[j];order[j]=v;}for(unsigned i=0;i<NODES;++i)next[order[i]]=order[(i+1)%NODES];}
static void ints(const unsigned*v){putchar('[');for(unsigned j=0;j<NODES;++j)printf("%s%u",j?",":"",v[j]);putchar(']');}
static void plan(void){unsigned order[NODES],next[NODES];cycle(order,next);printf("{\"probe\":\"tlb-descriptor-graph\",\"version\":1,\"nodes\":32,\"captures\":64,\"seed\":137,\"loads\":512,\"packed_stride\":8192,\"spaced_stride\":2105344,\"base_alignment\":2147483648,\"base_gap\":1073741824,\"observer\":\"do_set_pte-entry-return-99-32\",\"kernel_words\":[4181721088,2601068544,4043310344,1426063265],\"order\":");ints(order);printf(",\"next\":");ints(next);puts("}");}
/* Pure gate used by the actual capture loop: first bad state cannot advance to the next node. */
unsigned graph_capture_gate(uint64_t va,unsigned pid,uint64_t expected_word,uint64_t word,const uint64_t cb[2],const uint64_t ca[2],const uint64_t before[2],const uint64_t after[2],const uint64_t initial[16],const uint64_t negative[16],const uint64_t p[16]){
 const uint64_t pfn=(UINT64_C(1)<<55)-1,pa=(UINT64_C(1)<<48)-4096;
 for(unsigned i=0;i<16;++i)if(initial[i]||negative[i])return 1;
 if(word!=expected_word||(cb[0]&pfn)==(cb[1]&pfn))return 1;
 for(unsigned i=0;i<2;++i){if((before[i]>>63)||(before[i]&(UINT64_C(1)<<62))||(before[i]&pfn))return 1;
  if(!(cb[i]>>63)||!(ca[i]>>63)||!(after[i]>>63)||((cb[i]|ca[i]|after[i])&(UINT64_C(1)<<62))||!(cb[i]&pfn)||(cb[i]&pfn)!=(ca[i]&pfn)||(cb[i]&pfn)!=(after[i]&pfn))return 1;}
 unsigned nonzero=0;for(unsigned i=0;i<16;++i)nonzero|=p[i]!=0;if(!nonzero)return 2;
 if(p[0]!=13||p[1]!=1||p[2]!=1||p[3]!=pid||p[4]!=va||p[13]||p[14]||p[15])return 1;
 const unsigned pointers[]={5,6,7,9,10};for(unsigned i=0;i<5;++i)if(!p[pointers[i]]||p[pointers[i]]%8)return 1;
 if(p[6]%4096!=8*((va>>21)&511)||p[7]%4096!=8*((va>>12)&511))return 1;
 if((p[8]&3)!=3||(p[11]&3)!=3||(p[12]&3)!=3||!(p[8]&pa)||!(p[11]&pa)||!(p[12]&pa)||(p[12]&pa)/4096!=(cb[0]&pfn))return 1;
 uint64_t a=(p[6]&~UINT64_C(4095))-(p[11]&pa),b=(p[7]&~UINT64_C(4095))-(p[8]&pa);return a&&a==b?0:1;
}
#if defined(__linux__) && defined(__aarch64__)
static int one_page(int fd,uintptr_t v,uint64_t *out){return pread(fd,out,8,(off_t)(v/4096*8))==8?0:-1;}
static void u64s(const uint64_t*v,unsigned n){putchar('[');for(unsigned j=0;j<n;++j)printf("%s%"PRIu64,j?",":"",v[j]);putchar(']');}
/* Return 2 only for an exact no-capture; every bad captured state is retained and stops. */
static int capture(unsigned pid,uintptr_t va,uintptr_t negative_va,uintptr_t canonical,unsigned node,unsigned expected_word,int pm,unsigned type,unsigned shape){
 int map=-1,prog[2]={-1,-1},event[2]={-1,-1},mapid=-1,number=0;const char*stage="pagemap";char log[65536]={0};uint64_t cb[2],ca[2],before[2],after[2],initial[16]={0},negative[16]={0},positive[16]={0},word=0;
 if(one_page(pm,canonical+4096*node,&cb[0])||one_page(pm,canonical+4096*(node^1u),&cb[1])||one_page(pm,va,&before[0])||one_page(pm,negative_va,&before[1])){number=errno;goto done;}
 union bpf_attr a={0};a.map_type=BPF_MAP_TYPE_ARRAY;a.key_size=4;a.value_size=128;a.max_entries=1;stage="bpf-map-create";map=bpf_call(BPF_MAP_CREATE,&a);if(map<0){number=errno;goto done;}mapid=map;
 for(unsigned j=0;j<2;++j){struct install_program p=install_build(pid,va,map,(int)j);memset(&a,0,sizeof(a));a.prog_type=BPF_PROG_TYPE_KPROBE;a.insn_cnt=(uint32_t)p.n;a.insns=(uintptr_t)p.insn;a.license=(uintptr_t)"GPL";a.log_level=1;a.log_size=sizeof(log);a.log_buf=(uintptr_t)log;stage="bpf-program-load";prog[j]=bpf_call(BPF_PROG_LOAD,&a);if(prog[j]<0){number=errno;goto done;}
  struct perf_event_attr pe={0};pe.size=sizeof(pe);pe.type=type;pe.config=j;pe.config1=(uintptr_t)"do_set_pte";pe.sample_period=1;pe.wakeup_events=1;pe.disabled=1;stage="perf-kprobe-open";event[j]=(int)syscall(SYS_perf_event_open,&pe,-1,7,-1,PERF_FLAG_FD_CLOEXEC);if(event[j]<0){number=errno;goto done;}stage="perf-bpf-attach";if(ioctl(event[j],PERF_EVENT_IOC_SET_BPF,prog[j])){number=errno;goto done;}}
 for(unsigned j=0;j<2;++j)if(ioctl(event[j],PERF_EVENT_IOC_ENABLE,0)){number=errno;goto done;}
 uint32_t key=0;memset(&a,0,sizeof(a));a.map_fd=(uint32_t)map;a.key=(uintptr_t)&key;a.value=(uintptr_t)initial;stage="initial-map";if(bpf_call(BPF_MAP_LOOKUP_ELEM,&a)){number=errno;goto done;}
 stage="child-negative";pid_t child=fork();if(child<0){number=errno;goto done;}if(!child){volatile uint64_t value=*(volatile uint64_t*)va;(void)value;_exit(0);}int status;if(waitpid(child,&status,0)!=child||!WIFEXITED(status)||WEXITSTATUS(status))goto done;
 volatile uint64_t neg=*(volatile uint64_t*)negative_va;(void)neg;a.value=(uintptr_t)negative;stage="negative-map";if(bpf_call(BPF_MAP_LOOKUP_ELEM,&a)){number=errno;goto done;}
 word=*(volatile uint64_t*)va;a.value=(uintptr_t)positive;stage="positive-map";if(bpf_call(BPF_MAP_LOOKUP_ELEM,&a)||one_page(pm,canonical+4096*node,&ca[0])||one_page(pm,canonical+4096*(node^1u),&ca[1])||one_page(pm,va,&after[0])||one_page(pm,negative_va,&after[1])){number=errno;goto done;}
 for(unsigned j=0;j<2;++j){close(event[j]);event[j]=-1;close(prog[j]);prog[j]=-1;}close(map);map=-1;
 printf("{\"type\":\"install-read\",\"shape\":%u,\"node\":%u,\"node_word\":%"PRIu64",\"cpu\":%d,\"page_bytes\":4096,\"kprobe_type\":%u,\"program\":",shape,node,word,sched_getcpu(),type);export_plan(pid,va,mapid);
 const uint64_t *values[]={initial,negative,positive,before,after,cb,ca};const char*names[]={"initial","negative","positive","alias_before","alias_after","canonical_before","canonical_after"};for(unsigned j=0;j<7;++j){printf(",\"%s\":",names[j]);u64s(values[j],j<3?16:2);}puts(",\"fds_closed\":true}");
 unsigned qualified=graph_capture_gate(va,pid,expected_word,word,cb,ca,before,after,initial,negative,positive);if(qualified==1)return fail("graph-capture-not-qualified",0);return (int)qualified;
 done:
 for(unsigned j=0;j<2;++j){if(event[j]>=0)close(event[j]);if(prog[j]>=0)close(prog[j]);}if(map>=0)close(map);if(*log)fprintf(stderr,"verifier:%s\n",log);return fail(stage,number);
}
/* Exactly this one function runs both shapes; ordinal and physical visit order are shared. */
__attribute__((noinline)) void graph_walk(uintptr_t *head,uint64_t n,uint64_t stride,uintptr_t base){__asm__ volatile("ldr x0,[%[h]]\nmov x8,%[n]\nmov x9,%[s]\nmov x10,%[b]\n1: ldr x0,[x0]\nmadd x0,x0,x9,x10\nsubs x8,x8,#1\nb.ne 1b\nstr x0,[%[h]]"::[h]"r"(head),[n]"r"(n),[s]"r"(stride),[b]"r"(base):"x0","x8","x9","x10","cc","memory");}
#endif
int main(int argc,char **argv){
 if(argc==2&&!strcmp(argv[1],"--plan")){plan();return 0;}
 if(argc==5&&!strcmp(argv[1],"--bpf-plan")){uint64_t v[3];for(unsigned j=0;j<3;++j){char*end;errno=0;v[j]=strtoull(argv[j+2],&end,10);if(errno||!*argv[j+2]||*end)return fail("plan-value",0);}if(!v[0]||v[0]>=0x80000000u||!v[1]||v[1]>=(UINT64_C(1)<<39)||v[1]%4096||v[2]>2147483647)return fail("plan-value",0);export_plan((unsigned)v[0],v[1],(int)v[2]);puts("");return 0;}
 if(argc!=2||strcmp(argv[1],"--run"))return fail("usage-graph-plan-bpf-plan-run",0);
#if !defined(__linux__) || !defined(__aarch64__)
 return fail("requires-linux-aarch64",0);
#else
 int rc=1,mem=-1,pm=-1;void*canonical=MAP_FAILED,*arena=MAP_FAILED,*scratch=MAP_FAILED;const uint64_t reserve=UINT64_C(1)<<32;const char*stage="page-size";if(sysconf(_SC_PAGESIZE)!=4096)goto done;
 cpu_set_t cpu;CPU_ZERO(&cpu);CPU_SET(7,&cpu);stage="affinity";if(sched_setaffinity(0,sizeof(cpu),&cpu)||sched_getcpu()!=7)goto done;
 stage="memfd";mem=(int)syscall(SYS_memfd_create,"descriptor-graph",1);if(mem<0||ftruncate(mem,NODES*4096))goto done;canonical=mmap(NULL,NODES*4096,PROT_READ|PROT_WRITE,MAP_SHARED,mem,0);arena=mmap(NULL,reserve,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);scratch=mmap(NULL,12288,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);stage="owned-mapping";if(canonical==MAP_FAILED||arena==MAP_FAILED||scratch==MAP_FAILED)goto done;
 uintptr_t base[2];base[0]=((uintptr_t)arena+(UINT64_C(1)<<31)-1)&~((UINT64_C(1)<<31)-1);base[1]=base[0]+(UINT64_C(1)<<30);uint64_t stride[2]={8192,2105344};unsigned order[NODES],next[NODES];cycle(order,next);for(unsigned j=0;j<NODES;++j)*(uint64_t*)((char*)canonical+4096*j)=next[j];
 stage="alias-map";for(unsigned s=0;s<2;++s)for(unsigned j=0;j<NODES;++j){void*t=(void*)(base[s]+stride[s]*j);if(mmap(t,4096,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,mem,4096*j)!=t)goto done;}
 pm=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);stage="pagemap";if(pm<0)goto done;unsigned type=0;FILE*f=fopen("/sys/bus/event_source/devices/kprobe/type","r");stage="kprobe-type";if(!f)goto done;int parsed=fscanf(f,"%u",&type);fclose(f);if(parsed!=1||!type)goto done;f=fopen("/sys/bus/event_source/devices/kprobe/format/retprobe","r");if(!f)goto done;char fmt[32]={0};char*line=fgets(fmt,sizeof(fmt),f);fclose(f);if(!line||strcmp(fmt,"config:0\n"))goto done;
 plan();unsigned pid=(unsigned)syscall(SYS_getpid);printf("{\"type\":\"mapping\",\"owner_pid\":%u,\"bases\":[%"PRIuPTR",%"PRIuPTR"],\"canonical_base\":%"PRIuPTR",\"nodes\":32}\n",pid,base[0],base[1],(uintptr_t)canonical);
 uint64_t cb[NODES],ca[NODES];for(unsigned j=0;j<NODES;++j)if(one_page(pm,(uintptr_t)canonical+4096*j,&cb[j]))goto done;printf("{\"type\":\"canonical-before\",\"entries\":");u64s(cb,NODES);puts("}");
 for(unsigned s=0;s<2;++s){for(unsigned j=0;j<NODES;++j){stage="negative-map-install";if(mmap(scratch,4096,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,mem,4096*(j^1u))!=scratch)goto done;
   int k=capture(pid,base[s]+stride[s]*j,(uintptr_t)scratch,(uintptr_t)canonical,j,next[j],pm,type,s);if(k==1){rc=1;goto cleanup;}if(k==2){printf("{\"type\":\"stop\",\"reason\":\"not-excited\",\"captures\":%u}\n",s*NODES+j+1);rc=0;goto cleanup;}
  }
  uintptr_t head=base[s]+stride[s]*order[0],initial=head;graph_walk(&head,512,stride[s],base[s]);stage="graph-head";if(head!=initial)goto done;
  uint64_t entries[NODES],words[NODES];for(unsigned j=0;j<NODES;++j){uintptr_t v=base[s]+stride[s]*j;words[j]=*(uint64_t*)v;if(one_page(pm,v,&entries[j]))goto done;}
  printf("{\"type\":\"graph-final\",\"shape\":%u,\"loads\":512,\"head_returned\":true,\"entries\":",s);u64s(entries,NODES);printf(",\"words\":");u64s(words,NODES);puts("}");
 }
 for(unsigned j=0;j<NODES;++j)if(one_page(pm,(uintptr_t)canonical+4096*j,&ca[j]))goto done;printf("{\"type\":\"canonical-after\",\"entries\":");u64s(ca,NODES);puts("}");rc=0;goto cleanup;
 done:rc=fail(stage,errno);
 cleanup:if(pm>=0)close(pm);if(mem>=0)close(mem);if(canonical!=MAP_FAILED)munmap(canonical,NODES*4096);if(arena!=MAP_FAILED)munmap(arena,reserve);if(scratch!=MAP_FAILED)munmap(scratch,12288);return rc;
#endif
}
