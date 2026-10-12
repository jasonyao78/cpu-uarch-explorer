/* SPDX-License-Identifier: Apache-2.0
 * Architectural live/discard ADD destinations, not a ROB allocation certificate.
 * Protocol: docs/design/2026-10-12-rob-destination-control.md.
 * One program/mapping per process; opcode rules live only in rob_codegen.h.
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
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#endif
#define ITERATIONS 131072u
#define WINDOWS 8u
static int fail(const char *reason) {
    fprintf(stderr,"error[%s]\n",reason);
    printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",reason);
    return 1;
}
/* Phase/epoch ordering is outside the code; one fixed mapping per process. */
static struct code destination_build(uint32_t *words,size_t cap,unsigned g,unsigned anchor,unsigned pattern) {
    uint32_t prologue[128];struct options o={.cls=0,.n=0,.chain=16,.anchor=anchor?SQRT:NONE};
    struct code seed=build(prologue,128,&o);assert(seed.loop==16);
    if(anchor){assert(prologue[14]==FMOV(16,15));prologue[14]=FMOV(1,15);}
    struct code c={.words=words,.cap=cap};for(unsigned j=0;j<16;++j)emit(&c,prologue[j]);c.loop=c.pos;
    for(unsigned side=0;side<2;++side) {
        if(anchor)for(unsigned j=0;j<16;++j)emit(&c,FSQRT(side&&anchor==2?1:0,side&&anchor==2?1:0));
        for(unsigned j=0;j<g;++j) {
            if(pattern!=1&&pattern!=3)emit(&c,NOP);
            emit(&c,pattern?ADD(pattern==1||pattern==2?4+(j&7u):31,16,17):NOP);
        }
    }
    emit(&c,SUBS(3,3));c.branch=c.pos;emit(&c,BNE((int64_t)c.loop-(int64_t)c.branch));
    emit(&c,(pattern==1||pattern==2)&&g?MOV(0,4):MOVZ(0,0));emit(&c,RET);return c;
}
static void export_program(const struct code *c) {
    printf("{\"type\":\"program\",\"loop_offset\":%zu,\"branch_offset\":%zu,\"loop_instructions\":%zu,\"prologue_instructions\":%zu,\"code_bytes\":%zu,\"words\":[",4*c->loop,4*c->branch,c->branch-c->loop+1,c->loop,4*c->pos);
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
/* One initial installation only; fixed RX code for all warmup and measured calls. */
static bool install(void *memory,size_t capacity,const struct code *c) {
    if(mprotect(memory,capacity,PROT_READ|PROT_WRITE))return false;
    memcpy(memory,c->words,4*c->pos);
    if(memcmp(memory,c->words,4*c->pos))return false;
    __builtin___clear_cache((char*)memory,(char*)memory+4*c->pos);
    return mprotect(memory,capacity,PROT_READ|PROT_EXEC)==0;
}
#endif
int main(int argc,char **argv) {
    if((argc!=8&&argc!=9)||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||strcmp(argv[2],"--anchor")||strcmp(argv[4],"--pattern")||strcmp(argv[6],"--g")||(argc==9&&strcmp(argv[8],"--reverse")))return fail("usage-destination-plan-run-anchor-pattern-g-reverse");
    unsigned anchor=!strcmp(argv[3],"none")?0:!strcmp(argv[3],"serial")?1:!strcmp(argv[3],"independent")?2:3;
    unsigned pattern=!strcmp(argv[5],"nop-pair")?0:!strcmp(argv[5],"add-live")?1:!strcmp(argv[5],"nop-add-live")?2:!strcmp(argv[5],"add-discard")?3:!strcmp(argv[5],"nop-add-discard")?4:5;
    if(anchor==3||pattern==5)return fail("anchor-pattern-invalid");
    const char *grid[]={"0","64"};bool valid=false;
    for(unsigned j=0;j<2;++j)if(!strcmp(argv[7],grid[j]))valid=true;
    if(!valid)return fail("g-outside-frozen-grid");
    unsigned g=(unsigned)atoi(argv[7]);bool rev=argc==9;
    uint32_t words[4096];struct code c=destination_build(words,4096,g,anchor,pattern);
    printf("{\"type\":\"config\",\"version\":1,\"probe\":\"rob-destination-control\",\"pattern\":\"%s\",\"anchor\":\"%s\",\"groups\":%u,\"instructions_per_group\":%u,\"chain\":16,\"iterations\":131072,\"warmup_iterations\":131072,\"windows\":8,\"reverse\":%s,\"events\":[17,8,58,33133,35,1],\"pmu_type\":8,\"loop_mod64\":0}\n",argv[5],argv[3],g,pattern==1||pattern==3?1:2,rev?"true":"false");
    export_program(&c);
    if(!strcmp(argv[1],"--plan")) {
        for(unsigned pos=0;pos<WINDOWS;++pos)printf("{\"type\":\"schedule\",\"position\":%u,\"round\":%u}\n",pos,rev?WINDOWS-1-pos:pos);
        return 0;
    }
#if !defined(__linux__) || !defined(__aarch64__)
    return fail("measurement-requires-linux-aarch64");
#else
    if(sysconf(_SC_PAGESIZE)!=4096)return fail("page-size");
    cpu_set_t mask;CPU_ZERO(&mask);CPU_SET(7,&mask);
    if(sched_setaffinity(0,sizeof(mask),&mask)||sched_getcpu()!=7)return fail("affinity");
    uint64_t fpcr;asm volatile("mrs %0, fpcr":"=r"(fpcr));if(fpcr)return fail("fpcr-nonzero");
    const size_t capacity=65536;void *memory=mmap(NULL,capacity,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(memory==MAP_FAILED||!install(memory,capacity,&c))return fail("initial-code-install");
    struct perf perf;if(!open_perf(&perf))return fail("perf-open-id");
    printf("{\"type\":\"runtime\",\"cpu\":7,\"fpcr\":0,\"code_base\":%"PRIuPTR",\"event_ids\":[",(uintptr_t)memory);
    for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",perf.ids[j]);puts("]}");
    typedef uint64_t(*routine_t)(uintptr_t,uintptr_t,void*,uint64_t);routine_t routine=(routine_t)memory;uint64_t hot[8]={1,2,3,4,5,6,7,8};
    for(unsigned pos=0;pos<WINDOWS;++pos) {
        if(memcmp(memory,c.words,4*c.pos))return fail("code-drift");
        routine(0,0,hot,ITERATIONS);
        struct pg_sample before,after,delta;const char *e=snapshot(&perf,&before);if(e)return fail(e);
        if(ioctl(perf.fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))return fail("perf-enable");
        uint64_t d0=0,d1=0,t=ns();uint64_t checksum=routine(0,0,hot,ITERATIONS);
        /* Capture before any libc call, outside the generated iteration loop. */
        if(anchor)asm volatile("fmov %0,d0\nfmov %1,d1":"=r"(d0),"=r"(d1));
        t=ns()-t;
        if(ioctl(perf.fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))return fail("perf-disable");
        if((e=snapshot(&perf,&after))||(e=pg_delta(&before,&after,6,&delta)))return fail(e);
        if(sched_getcpu()!=7||!t||!delta.values[0])return fail("window-cpu-time");
        if(checksum!=((pattern==1||pattern==2)&&g?UINT64_C(0x3333):0))return fail("gpr-result");
        if(anchor&&(d0!=UINT64_C(0x3ff0000000000000)||d1!=d0))return fail("sqrt-result-bits");
        printf("{\"type\":\"round\",\"position\":%u,\"round\":%u,\"code_base\":%"PRIuPTR",\"code_matches_plan\":true,\"result_bits\":",pos,rev?WINDOWS-1-pos:pos,(uintptr_t)memory);
        if(anchor)printf("[%"PRIu64",%"PRIu64"]",d0,d1);else printf("null");
        printf(",\"gpr_result\":%"PRIu64",\"ns\":%"PRIu64",\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"counts\":[",checksum,t,delta.enabled,delta.running);
        for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",delta.values[j]);puts("]}");
        if(fflush(stdout))return fail("output-write");
    }
    for(unsigned j=0;j<6;++j)close(perf.fd[j]);munmap(memory,capacity);return 0;
#endif
}
