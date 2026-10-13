/* SPDX-License-Identifier: Apache-2.0
 * L1 instruction/data reach with same backing PFNs and offset controls.
 * Contract: docs/design/2026-10-13-l1-tlb-reach.md. No profile writes.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "../common/perf_group_read.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if defined(__linux__) && defined(__aarch64__)
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <fcntl.h>
#endif
#define MAX_N 192
/* Compile-time grid changes are new protocols/binaries, never old raw relabels. */
#ifndef CPU_UARCH_L1_D_GRID
#define CPU_UARCH_L1_D_GRID 32,64,80,88,92,96,100,104,112,128,160,192
#define CPU_UARCH_L1_I_GRID 32,40,44,48,52,56,64,96,112,120,124,128,132,144,160,192
#define CPU_UARCH_L1_VERSION 1
#endif
static const unsigned dn[]={CPU_UARCH_L1_D_GRID};
static const unsigned in[]={CPU_UARCH_L1_I_GRID};

static int failure(const char *s){printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\",\"errno\":%d},\"fds_closed\":true}\n",s,errno);return 1;}
static void plan(char mode,unsigned epoch,int qual){
 printf("{\"probe\":\"l1-tlb-reach\",\"version\":%u,\"mode\":\"%c\",\"epoch\":%u,\"phase\":\"%s\",\"cpu\":7,\"pmu_type\":8,\"events\":%s,\"nodes\":[",CPU_UARCH_L1_VERSION,mode,epoch,qual?"qualification":"scan",mode=='i'?"[17,8,2,53,1,34]":"[17,8,5,52,3,1]");
 const unsigned *ns=mode=='i'?in:dn;unsigned count=qual?1:(unsigned)(mode=='i'?sizeof(in)/sizeof(*in):sizeof(dn)/sizeof(*dn));for(unsigned i=0;i<count;i++)printf("%s%u",i?",":"",ns[i]);
 puts("],\"strides\":[5,17],\"rounds\":3,\"empty_each_side\":3,\"target_hops\":1000000,\"global_policy_mutation\":false,\"backing_pages\":192,\"seed\":137,\"jit_slots_bytes\":[0,16,32,48]}");
}
#if defined(__linux__) && defined(__aarch64__)
static const unsigned st[]={5,17};
struct group {int fd[6];uint64_t ids[6];};
static int snap(struct group*g,struct pg_sample*s){uint64_t w[15];return read(g->fd[0],w,sizeof(w))!=(ssize_t)sizeof(w)||pg_decode(w,15,g->ids,6,s)!=NULL;}
static void numbers(const uint64_t*v,unsigned n){putchar('[');for(unsigned j=0;j<n;j++)printf("%s%"PRIu64,j?",":"",v[j]);putchar(']');}
__attribute__((noinline)) static uintptr_t data_walk(uintptr_t head,uint64_t hops,uintptr_t base,uint64_t stride,unsigned mask){
 register uintptr_t p __asm__("x0")=head;register uint64_t n __asm__("x8")=hops;register uint64_t s __asm__("x9")=stride;register uintptr_t b __asm__("x10")=base;register uint64_t m __asm__("x12")=mask;
 __asm__ volatile("1: ldr x0,[x0]\n and x11,x0,x12\n madd x0,x0,x9,x10\n add x0,x0,x11,lsl #6\n subs x8,x8,#1\n b.ne 1b" : "+r"(p),"+r"(n):"r"(s),"r"(b),"r"(m):"x11","cc","memory");return p;
}
static int pfn(int fd,uintptr_t addr,uint64_t*out){uint64_t x;if(pread(fd,&x,8,(off_t)(addr/4096*8))!=8)return 1;*out=x&((1ULL<<55)-1);return !(x>>63)||(x&(1ULL<<62))||!*out;}
static uint32_t branch(uintptr_t a,uintptr_t b){int64_t off=(int64_t)b-(int64_t)a;return 0x14000000u|((uint32_t)(off/4)&0x03ffffffu);}
static unsigned offset(unsigned ordinal,unsigned role){return role*16+((role&1)?(ordinal&63)*64:0);}
static void order(unsigned n,unsigned epoch,unsigned*out){for(unsigned i=0;i<n;i++)out[i]=i;uint32_t s=137;for(unsigned i=n-1;i;i--){s=1664525u*s+1013904223u;unsigned j=s%(i+1),v=out[i];out[i]=out[j];out[j]=v;}if(epoch==1)for(unsigned i=0;i<n/2;i++){unsigned v=out[i];out[i]=out[n-1-i];out[n-1-i]=v;}}
#endif
int main(int argc,char**argv){
 if(argc!=5||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||(strcmp(argv[2],"i")&&strcmp(argv[2],"d"))||(strcmp(argv[3],"0")&&strcmp(argv[3],"1")&&strcmp(argv[3],"2"))||(strcmp(argv[4],"qualification")&&strcmp(argv[4],"scan")))return failure("usage-l1-reach");
 char mode=argv[2][0];unsigned epoch=(unsigned)atoi(argv[3]);int qual=!strcmp(argv[4],"qualification");plan(mode,epoch,qual);if(!strcmp(argv[1],"--plan"))return 0;
#if !defined(__linux__) || !defined(__aarch64__)
 return failure("requires-linux-aarch64");
#else
 const char*stage="affinity";int rc=1,file=-1,pm=-1;void*back=MAP_FAILED;void*alias[2]={MAP_FAILED,MAP_FAILED};size_t span[2]={MAX_N*5*4096UL,MAX_N*17*4096UL};struct group g={{-1,-1,-1,-1,-1,-1},{0}};uint64_t pf[MAX_N];cpu_set_t cp;CPU_ZERO(&cp);CPU_SET(7,&cp);if(sched_setaffinity(0,sizeof(cp),&cp)||sched_getcpu()!=7||sysconf(_SC_PAGESIZE)!=4096)goto done;
 stage="own-memfd";file=(int)syscall(SYS_memfd_create,"l1-reach-own",MFD_CLOEXEC);if(file<0||ftruncate(file,MAX_N*4096))goto done;back=mmap(NULL,MAX_N*4096,PROT_READ|PROT_WRITE,MAP_SHARED,file,0);if(back==MAP_FAILED)goto done;memset(back,0,MAX_N*4096);
 stage="own-alias";for(unsigned a=0;a<2;a++){alias[a]=mmap(NULL,span[a],PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(alias[a]==MAP_FAILED)goto done;for(unsigned j=0;j<MAX_N;j++)if(mmap((char*)alias[a]+j*st[a]*4096UL,4096,mode=='i'?(PROT_READ|PROT_EXEC):PROT_READ,MAP_SHARED|MAP_FIXED,file,j*4096)!=((char*)alias[a]+j*st[a]*4096UL))goto done;}
 stage="pagemap";pm=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);if(pm<0)goto done;
 /* Fault aliases with reads, never write RX. PFN identity is checked again at end. */
 for(unsigned a=0;a<2;a++)for(unsigned j=0;j<MAX_N;j++){volatile uint64_t v=*(volatile uint64_t*)((char*)alias[a]+j*st[a]*4096UL);(void)v;}
 printf("{\"type\":\"mapping\",\"canonical_base\":%"PRIuPTR",\"alias_bases\":[%"PRIuPTR",%"PRIuPTR"],\"pfns\":[",(uintptr_t)back,(uintptr_t)alias[0],(uintptr_t)alias[1]);
 for(unsigned j=0;j<MAX_N;j++){uint64_t x,y;if(pfn(pm,(uintptr_t)back+j*4096,&pf[j])||pfn(pm,(uintptr_t)alias[0]+j*st[0]*4096UL,&x)||pfn(pm,(uintptr_t)alias[1]+j*st[1]*4096UL,&y)||x!=pf[j]||y!=pf[j])goto done;for(unsigned k=0;k<j;k++)if(pf[k]==pf[j])goto done;printf("%s%"PRIu64,j?",":"",pf[j]);}puts("]}");
 stage="perf-open";const unsigned ie[]={17,8,2,53,1,34},de[]={17,8,5,52,3,1};const unsigned*ev=mode=='i'?ie:de;
 for(unsigned j=0;j<6;j++){struct perf_event_attr a={0};a.size=sizeof(a);a.type=8;a.config=ev[j];a.disabled=j==0;a.pinned=j==0;a.exclude_kernel=1;a.exclude_hv=1;a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_ID|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING;g.fd[j]=(int)syscall(SYS_perf_event_open,&a,0,-1,j?g.fd[0]:-1,PERF_FLAG_FD_CLOEXEC);if(g.fd[j]<0||ioctl(g.fd[j],PERF_EVENT_IOC_ID,g.ids+j))goto done;}
 const unsigned*ns=mode=='i'?in:dn;unsigned count=qual?1:(unsigned)(mode=='i'?sizeof(in)/sizeof(*in):sizeof(dn)/sizeof(*dn));
 for(unsigned ni=0;ni<count;ni++){
  unsigned n=ns[epoch==1?count-1-ni:ni],o[MAX_N];order(n,epoch,o);uint64_t cycles=1000000/n,hops=cycles*n;uintptr_t start[4];
  for(unsigned role=0;role<4;role++){
   unsigned a=role/2;start[role]=(uintptr_t)alias[a]+o[0]*st[a]*4096UL+(mode=='i'?offset(o[0],role):((role&1)?(o[0]&63)*64:0));
   for(unsigned k=0;k<n;k++){
    unsigned j=o[k],next=o[(k+1)%n];
    if(mode=='d'){*(uint64_t*)((char*)back+j*4096)=next;*(uint64_t*)((char*)back+j*4096+(j&63)*64)=next;}
    else{uint32_t*w=(uint32_t*)((char*)back+j*4096+offset(j,role));uintptr_t here=(uintptr_t)alias[a]+j*st[a]*4096UL+offset(j,role),dest=(uintptr_t)alias[a]+next*st[a]*4096UL+offset(next,role);if(k+1<n)w[0]=branch(here,dest);else{w[0]=0xf1000400u;w[1]=0x54000040u;w[2]=branch(here+8,start[role]);w[3]=0xd65f03c0u;}}
   }
  }
  /* D-cache clean / I-cache invalidate every actual RX slot after all writes. */
  if(mode=='i')for(unsigned role=0;role<4;role++)for(unsigned j=0;j<n;j++){char*p=(char*)alias[role/2]+j*st[role/2]*4096UL+offset(j,role);__builtin___clear_cache(p,p+16);}
  printf("{\"type\":\"layout\",\"nodes\":%u,\"hops\":%"PRIu64",\"cycles\":%"PRIu64",\"order\":[",n,hops,cycles);for(unsigned j=0;j<n;j++)printf("%s%u",j?",":"",o[j]);printf("],\"words\":[");if(mode=='i')for(unsigned role=0;role<4;role++){printf("%s[",role?",":"");for(unsigned k=0;k<n;k++){unsigned j=o[k];uint32_t*w=(uint32_t*)((char*)back+j*4096+offset(j,role));printf("%s[%u,%u,%u,%u]",k?",":"",w[0],k+1==n?w[1]:0,k+1==n?w[2]:0,k+1==n?w[3]:0);}putchar(']');}puts("]}");
  /* Validate one full circuit and all roles; then warm before enabling perf. */
  stage="circuit";for(unsigned role=0;role<4;role++)if(mode=='d'){uintptr_t v=data_walk(start[role],n,(uintptr_t)alias[role/2],st[role/2]*4096UL,(role&1)?63:0);if(v!=start[role])goto done;}else ((void(*)(uint64_t))start[role])(1);
  if(ioctl(g.fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))goto done;
  for(unsigned role=0;role<4;role++)if(mode=='d')(void)data_walk(start[role],hops,(uintptr_t)alias[role/2],st[role/2]*4096UL,(role&1)?63:0);else ((void(*)(uint64_t))start[role])(cycles);
  for(unsigned w=0;w<18;w++){
   int role=-1;unsigned round=0;if(w>=3&&w<15){round=(w-3)/4;role=(int)((w-3)%4);if(epoch==1)role=3-role;}
   struct pg_sample a,b,delta;stage="perf-window";if(snap(&g,&a))goto done;__asm__ volatile("dsb ish\n isb":::"memory");
   if(role>=0){if(mode=='d'){uintptr_t v=data_walk(start[role],hops,(uintptr_t)alias[role/2],st[role/2]*4096UL,(role&1)?63:0);if(v!=start[role]){stage="payload-circuit";goto done;}}else ((void(*)(uint64_t))start[role])(cycles);}else __asm__ volatile("":::"memory");
   __asm__ volatile("dsb ish\n isb":::"memory");if(snap(&g,&b)||pg_delta(&a,&b,6,&delta))goto done;
   printf("{\"type\":\"window\",\"nodes\":%u,\"ordinal\":%u,\"role\":%d,\"round\":%u,\"cpu\":%d,\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"before\":",n,w,role,round,sched_getcpu(),delta.enabled,delta.running);numbers(a.values,6);printf(",\"after\":");numbers(b.values,6);puts("}");if(sched_getcpu()!=7){stage="cpu-drift";goto done;}
  }
  if(ioctl(g.fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))goto done;
  if(mode=='i')for(unsigned role=0;role<4;role++)for(unsigned k=0;k<n;k++){unsigned j=o[k],next=o[(k+1)%n],a=role/2;uintptr_t here=(uintptr_t)alias[a]+j*st[a]*4096UL+offset(j,role),dest=(uintptr_t)alias[a]+next*st[a]*4096UL+offset(next,role);uint32_t*w=(uint32_t*)((char*)back+j*4096+offset(j,role));if(w[0]!=(k+1<n?branch(here,dest):0xf1000400u)||(k+1==n&&(w[1]!=0x54000040u||w[2]!=branch(here+8,start[role])||w[3]!=0xd65f03c0u))){stage="code-drift";goto done;}}
 }
 stage="mapping-final";for(unsigned j=0;j<MAX_N;j++)for(unsigned a=0;a<2;a++){uint64_t x;if(pfn(pm,(uintptr_t)alias[a]+j*st[a]*4096UL,&x)||x!=pf[j])goto done;}rc=0;
 done:if(g.fd[0]>=0)ioctl(g.fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP);for(unsigned j=0;j<6;j++)if(g.fd[j]>=0)close(g.fd[j]);if(pm>=0)close(pm);if(file>=0)close(file);if(back!=MAP_FAILED)munmap(back,MAX_N*4096);for(unsigned a=0;a<2;a++)if(alias[a]!=MAP_FAILED)munmap(alias[a],span[a]);if(rc)return failure(stage);puts("{\"type\":\"final\",\"fds_closed\":true,\"mapping_unchanged\":true,\"code_checked\":true,\"global_policy_mutation\":false}");return 0;
#endif
}
