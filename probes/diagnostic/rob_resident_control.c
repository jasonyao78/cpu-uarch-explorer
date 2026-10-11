/* SPDX-License-Identifier: Apache-2.0
 * Identical-code maintenance versus unchanged-code windows, not ROB entries.
 * Protocol: docs/design/2026-10-11-rob-resident-control.md.
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
#define WINDOWS 16u
static int fail(const char *reason) {
    fprintf(stderr,"error[%s]\n",reason);
    printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",reason);
    return 1;
}
/* Balancing is fixed before measurement; generation counts identical reinstalls. */
static void schedule(unsigned pos,bool reverse,unsigned *block,unsigned *slot,bool *rewrite) {
    unsigned index=reverse?WINDOWS-1-pos:pos;
    *block=index/2; *slot=index%2; *rewrite=((*block+*slot)%2)==1;
}
static void export_program(const struct code *c) {
    printf("{\"type\":\"program\",\"loop_offset\":%zu,\"branch_offset\":%zu,\"loop_instructions\":%zu,\"prologue_instructions\":%zu,\"code_bytes\":%zu,\"words\":[",4*c->loop,4*c->branch,c->branch-c->loop+1,c->loop,4*c->pos);
    for(size_t i=0;i<c->pos;++i)printf("%s%"PRIu32,i?",":"",c->words[i]);
    puts("]}");
}
#if defined(__linux__) && defined(__aarch64__)
struct perf {int fd[6];uint64_t ids[6];};
static bool open_perf(struct perf *p) {
    const uint64_t events[]={0x11,0x08,0x3a,0x3b,0x816d,0x23};
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
/* Same bytes reinstalled only outside the PMU window and before common warmup. */
static bool install(void *memory,size_t capacity,const struct code *c) {
    if(mprotect(memory,capacity,PROT_READ|PROT_WRITE))return false;
    memcpy(memory,c->words,4*c->pos);
    if(memcmp(memory,c->words,4*c->pos))return false;
    __builtin___clear_cache((char*)memory,(char*)memory+4*c->pos);
    return mprotect(memory,capacity,PROT_READ|PROT_EXEC)==0;
}
#endif
int main(int argc,char **argv) {
    if((argc!=8&&argc!=9)||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||strcmp(argv[2],"--anchor")||(strcmp(argv[3],"none")&&strcmp(argv[3],"fsqrt"))||strcmp(argv[4],"--link")||(strcmp(argv[5],"independent")&&strcmp(argv[5],"dependent"))||strcmp(argv[6],"--n")||(strcmp(argv[7],"0")&&strcmp(argv[7],"128"))||(argc==9&&strcmp(argv[8],"--reverse")))return fail("usage-resident-plan-run-anchor-link-n-reverse");
    bool fsqrt=!strcmp(argv[3],"fsqrt"),dep=!strcmp(argv[5],"dependent"),rev=argc==9;
    unsigned n=(unsigned)atoi(argv[7]);if(!n&&(fsqrt||dep))return fail("n0-only-none-independent");
    struct options o={.cls=1,.n=n,.its=ITERATIONS,.chain=16,.have_link=true,.dependent_link=dep,.anchor=fsqrt?SQRT:NONE};
    uint32_t words[1024];struct code c=build(words,1024,&o);
    printf("{\"type\":\"config\",\"version\":1,\"probe\":\"rob-resident-control\",\"class\":\"%s\",\"anchor\":\"%s\",\"link\":\"%s\",\"n\":%u,\"chain\":16,\"iterations\":131072,\"warmup_iterations\":131072,\"blocks\":8,\"windows\":16,\"reverse\":%s,\"events\":[17,8,58,59,33133,35],\"pmu_type\":8,\"loop_mod64\":0}\n",classes[1],argv[3],argv[5],n,rev?"true":"false");
    export_program(&c);unsigned generation=1;
    if(!strcmp(argv[1],"--plan")) {
        for(unsigned pos=0;pos<WINDOWS;++pos) {
            unsigned b,s;bool rewrite;schedule(pos,rev,&b,&s,&rewrite);generation+=rewrite;
            printf("{\"type\":\"schedule\",\"position\":%u,\"block\":%u,\"slot\":%u,\"preparation\":\"%s\",\"installation_generation\":%u}\n",pos,b,s,rewrite?"reinstall":"resident",generation);
        }
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
    typedef void(*routine_t)(uintptr_t,uintptr_t,void*,uint64_t);routine_t routine=(routine_t)memory;uint64_t hot[8]={1,2,3,4,5,6,7,8};
    for(unsigned pos=0;pos<WINDOWS;++pos) {
        unsigned b,s;bool rewrite;schedule(pos,rev,&b,&s,&rewrite);
        if(rewrite){if(!install(memory,capacity,&c))return fail("identical-code-reinstall");++generation;}
        if(memcmp(memory,c.words,4*c.pos))return fail("code-drift");
        routine(0,0,hot,ITERATIONS);
        struct pg_sample before,after,delta;const char *e=snapshot(&perf,&before);if(e)return fail(e);
        if(ioctl(perf.fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))return fail("perf-enable");
        uint64_t t=ns();routine(0,0,hot,ITERATIONS);t=ns()-t;
        if(ioctl(perf.fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))return fail("perf-disable");
        if((e=snapshot(&perf,&after))||(e=pg_delta(&before,&after,6,&delta)))return fail(e);
        if(sched_getcpu()!=7||!t||!delta.values[0])return fail("window-cpu-time");
        printf("{\"type\":\"round\",\"position\":%u,\"block\":%u,\"slot\":%u,\"preparation\":\"%s\",\"installation_generation\":%u,\"code_base\":%"PRIuPTR",\"code_matches_plan\":true,\"ns\":%"PRIu64",\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"counts\":[",pos,b,s,rewrite?"reinstall":"resident",generation,(uintptr_t)memory,t,delta.enabled,delta.running);
        for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",delta.values[j]);puts("]}");
        if(fflush(stdout))return fail("output-write");
    }
    for(unsigned j=0;j<6;++j)close(perf.fd[j]);munmap(memory,capacity);return 0;
#endif
}
