/* SPDX-License-Identifier: Apache-2.0
 * Paired blocked/interleaved FPSR anchor register schedule; original FP outputs captured before reset.
 * Protocol: docs/design/2026-10-13-rob-anchor-order.md.
 * Four RX pages and two layout slots per page; common opcodes plus independently assembled MRS. Original FP outputs and raw status are checked from the outside-loop buffer.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "rob_codegen.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/mman.h>
#ifdef __linux__
#include <fcntl.h>
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#endif
#define ITERATIONS 262144u
static int fail(const char *reason) {
    fprintf(stderr,"error[%s]\n",reason);
    printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",reason);
    return 1;
}
/* Phase/epoch ordering is outside the code; one fixed mapping per process. */
static struct code drain_build(uint32_t *words,size_t cap,unsigned g,unsigned anchor,unsigned pattern,unsigned chain) {
    uint32_t prologue[128];struct options o={.cls=0,.n=0,.chain=chain,.anchor=SQRT};
    struct code seed=build(prologue,128,&o);assert(seed.loop==16);assert(prologue[14]==FMOV(16,15));prologue[14]=FMOV(1,15);
    struct code c={.words=words,.cap=cap};for(unsigned j=0;j<16;++j)emit(&c,prologue[j]);c.loop=c.pos;
    for(unsigned side=0;side<2;++side){
        if(anchor)for(unsigned j=0;j<chain;++j)emit(&c,FSQRT(side&&anchor==2?1:0,side&&anchor==2?1:0));
        for(unsigned j=0;j<g;++j){emit(&c,NOP);emit(&c,NOP);}
    }
    /* Preserve completed original FP results before every reset. MRS mode is the only code difference. */
    emit(&c,FMOV_TO_GPR(13,0));emit(&c,FMOV_TO_GPR(14,1));emit(&c,pattern?0xd53b442cu:0xd53b440cu);
    emit(&c,MOV(16,12));emit(&c,EOR(12,12,15));emit(&c,FMOV(0,12));emit(&c,FMOV(1,12));
    emit(&c,SUBS(3,3));c.branch=c.pos;emit(&c,BNE((int64_t)c.loop-(int64_t)c.branch));
    /* These three buffer writes are outside the repeated loop, accounted in exact IR. */
    emit(&c,STR(13,2,0));emit(&c,STR(14,2,8));emit(&c,STR(16,2,16));emit(&c,MOVZ(0,0));emit(&c,RET);return c;
}

static void export_program(const struct code *c,unsigned condition,unsigned slot) {
    printf("{\"type\":\"program\",\"condition\":%u,\"page\":%u,\"slot\":%u,\"loop_offset\":%zu,\"branch_offset\":%zu,\"loop_instructions\":%zu,\"prologue_instructions\":%zu,\"code_bytes\":%zu,\"words\":[",condition,condition/2,slot,4*c->loop,4*c->branch,c->branch-c->loop+1,c->loop,4*c->pos);
    for(size_t i=0;i<c->pos;++i)printf("%s%"PRIu32,i?",":"",c->words[i]);
    puts("]}");
}
#if defined(__linux__) && defined(__aarch64__)
struct perf {int fd[6];uint64_t ids[6];};
static bool open_perf(struct perf *p) {
    const uint64_t events[]={0x11,0x08,0x3a,0x816d,0x23,0x01};
    for(unsigned i=0;i<6;++i)p->fd[i]=-1;
    for(unsigned i=0;i<6;++i) {
        struct perf_event_attr a={0};a.size=sizeof(a);a.type=8;a.config=events[i];
        a.disabled=i==0;a.pinned=i==0;a.exclude_kernel=1;a.exclude_hv=1;
        a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING|PERF_FORMAT_ID;
        p->fd[i]=(int)syscall(SYS_perf_event_open,&a,0,-1,i?p->fd[0]:-1,0);
        if(p->fd[i]<0||ioctl(p->fd[i],PERF_EVENT_IOC_ID,&p->ids[i]))return false;
    }
    return true;
}
static const char *snapshot(struct perf *p,struct pg_sample *s) {
    uint64_t wire[15];ssize_t n=read(p->fd[0],wire,sizeof(wire));
    if(n<=0||n%8)return "perf-read";
    return pg_decode(wire,(size_t)n/8,p->ids,6,s);
}
static uint64_t ns(void) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC_RAW,&t))abort();
    return (uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec;
}
#endif

/* All programs are installed once; each layout pair has one actual code PFN. */
static unsigned anchor_for(unsigned i){return i/2==1?1:i/2==2?2:0;}
static unsigned groups_for(unsigned i){return i/2==3?64:0;}
static unsigned condition_at(unsigned trial,unsigned pos,bool reverse){unsigned i=(trial+pos)%8;return reverse?7-i:i;}
#if defined(__linux__) && defined(__aarch64__)
static bool code_pages(int fd,const void *memory,uint64_t values[4]) {
 for(unsigned j=0;j<4;++j)if(pread(fd,&values[j],8,(off_t)(((uintptr_t)memory/4096+j)*8))!=8)return false;
 return true;
}
#endif
int main(int argc,char **argv){
 if((argc!=6&&argc!=7)||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||strcmp(argv[2],"--chain")||strcmp(argv[4],"--slots")||(argc==7&&strcmp(argv[6],"--reverse")))return fail("usage-order-chain-slots");
 if((strcmp(argv[3],"16")&&strcmp(argv[3],"32"))||(strcmp(argv[5],"normal")&&strcmp(argv[5],"swapped")))return fail("outside-order-grid");
 unsigned k=(unsigned)atoi(argv[3]);bool swap=!strcmp(argv[5],"swapped"),reverse=argc==7;uint32_t words[8][1024];struct code code[8];unsigned slot[8];
 printf("{\"type\":\"config\",\"version\":1,\"probe\":\"rob-anchor-order\",\"chain\":%u,\"slots\":\"%s\",\"reverse\":%s,\"iterations\":262144,\"warmup_iterations\":262144,\"trials\":8,\"windows\":64,\"trial_sleep_s\":3,\"drain\":\"fpsr\",\"events\":[17,8,58,33133,35,1],\"pmu_type\":8}\n",k,argv[5],reverse?"true":"false");
 for(unsigned i=0;i<8;++i){code[i]=drain_build(words[i],1024,groups_for(i),anchor_for(i),1,k);slot[i]=2048*((i%2)^(unsigned)swap);
  if(i==5)for(unsigned j=0;j<2*k;++j)words[i][code[i].loop+j]=FSQRT(j%2,j%2);
  if(4*code[i].pos>=2048)return fail("code-slot-overflow");export_program(&code[i],i,slot[i]);
 }
 if(!strcmp(argv[1],"--plan")){for(unsigned t=0;t<8;++t)for(unsigned pos=0;pos<8;++pos)printf("{\"type\":\"schedule\",\"trial\":%u,\"position\":%u,\"condition\":%u}\n",t,pos,condition_at(t,pos,reverse));return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
 return fail("measurement-requires-linux-aarch64");
#else
 if(sysconf(_SC_PAGESIZE)!=4096)return fail("page-size");cpu_set_t cpu;CPU_ZERO(&cpu);CPU_SET(7,&cpu);
 if(sched_setaffinity(0,sizeof(cpu),&cpu)||sched_getcpu()!=7)return fail("affinity");
 uint64_t fpcr;__asm__ volatile("mrs %0,fpcr":"=r"(fpcr));if(fpcr)return fail("fpcr-nonzero");
 void *memory=mmap(NULL,16384,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(memory==MAP_FAILED)return fail("code-map");
 memset(memory,0,16384);for(unsigned i=0;i<8;++i){void *p=(char*)memory+4096*(i/2)+slot[i];memcpy(p,code[i].words,4*code[i].pos);if(memcmp(p,code[i].words,4*code[i].pos))return fail("install-code-copy");}
 __builtin___clear_cache(memory,(char*)memory+16384);if(mprotect(memory,16384,PROT_READ|PROT_EXEC))return fail("code-rx");
 int pm=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);uint64_t before[4],after[4];if(pm<0||!code_pages(pm,memory,before))return fail("code-pagemap");
 struct perf perf;if(!open_perf(&perf))return fail("perf-open-id");printf("{\"type\":\"runtime\",\"cpu\":7,\"fpcr\":0,\"code_base\":%"PRIuPTR",\"code_pagemap_before\":[",(uintptr_t)memory);
 for(unsigned j=0;j<4;++j)printf("%s%"PRIu64,j?",":"",before[j]);printf("],\"event_ids\":[");for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",perf.ids[j]);puts("]}");
 typedef uint64_t(*routine_t)(uintptr_t,uintptr_t,void*,uint64_t);uint64_t hot[8]={1,2,3,4,5,6,7,8};
 for(unsigned t=0;t<8;++t){if(t)sleep(3);for(unsigned pos=0;pos<8;++pos){unsigned i=condition_at(t,pos,reverse);void *entry=(char*)memory+4096*(i/2)+slot[i];routine_t routine=(routine_t)entry;
  if(memcmp(entry,code[i].words,4*code[i].pos))return fail("code-drift");__asm__ volatile("msr fpsr,xzr");routine(0,0,hot,ITERATIONS);
  struct pg_sample b,a,d;const char*e=snapshot(&perf,&b);if(e)return fail(e);if(ioctl(perf.fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))return fail("perf-enable");
  uint64_t time=ns(),checksum=routine(0,0,hot,ITERATIONS),d0=hot[0],d1=hot[1],status=hot[2];time=ns()-time;
  if(ioctl(perf.fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))return fail("perf-disable");if((e=snapshot(&perf,&a))||(e=pg_delta(&b,&a,6,&d)))return fail(e);
  if(sched_getcpu()!=7||!time||!d.values[0])return fail("window-cpu-time");if(checksum||d0!=UINT64_C(0x3ff0000000000000)||d1!=d0||status)return fail("original-fp-status-gpr");
  printf("{\"type\":\"round\",\"trial\":%u,\"position\":%u,\"condition\":%u,\"code_address\":%"PRIuPTR",\"code_matches_plan\":true,\"result_bits\":[%"PRIu64",%"PRIu64"],\"status_raw\":%"PRIu64",\"gpr_result\":%"PRIu64",\"ns\":%"PRIu64",\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"counts\":[",t,pos,i,(uintptr_t)entry,d0,d1,status,checksum,time,d.enabled,d.running);
  for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",d.values[j]);puts("]}");if(fflush(stdout))return fail("output-write");
 }}
 for(unsigned i=0;i<8;++i)if(memcmp((char*)memory+4096*(i/2)+slot[i],code[i].words,4*code[i].pos))return fail("final-code-drift");if(!code_pages(pm,memory,after))return fail("final-code-pagemap");
 printf("{\"type\":\"code-final\",\"code_base\":%"PRIuPTR",\"code_pagemap_after\":[",(uintptr_t)memory);for(unsigned j=0;j<4;++j)printf("%s%"PRIu64,j?",":"",after[j]);puts("]}");
 for(unsigned j=0;j<6;++j)close(perf.fd[j]);close(pm);munmap(memory,16384);return 0;
#endif
}
