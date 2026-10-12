/* SPDX-License-Identifier: Apache-2.0
 * Retirement-boundary FPSR/FPCR control; original FP outputs captured before reset.
 * Protocol: docs/design/2026-10-12-rob-retirement-drain-next.md.
 * One RX program per process; common opcodes plus independently assembled MRS. Original FP outputs and raw status are checked from the outside-loop buffer.
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
#define ITERATIONS 1048576u
#define WINDOWS 8u
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
    if((argc!=10&&argc!=11)||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||strcmp(argv[2],"--anchor")||strcmp(argv[4],"--drain")||strcmp(argv[6],"--g")||strcmp(argv[8],"--chain")||(argc==11&&strcmp(argv[10],"--reverse")))return fail("usage-drain-anchor-mode-g-chain-reverse");
    unsigned anchor=!strcmp(argv[3],"none")?0:!strcmp(argv[3],"serial")?1:!strcmp(argv[3],"independent")?2:3;
    unsigned pattern=!strcmp(argv[5],"fpcr")?0:!strcmp(argv[5],"fpsr")?1:2;
    if(anchor==3||pattern==2)return fail("anchor-pattern-invalid");
    bool valid=!strcmp(argv[7],"0")||(!strcmp(argv[7],"64")&&anchor==0);
    if(!valid||(strcmp(argv[9],"16")&&strcmp(argv[9],"32")))return fail("outside-drain-qualification-grid");
    unsigned g=(unsigned)atoi(argv[7]),chain=(unsigned)atoi(argv[9]);bool rev=argc==11;
    uint32_t words[4096];struct code c=drain_build(words,4096,g,anchor,pattern,chain);
    printf("{\"type\":\"config\",\"version\":1,\"probe\":\"rob-retirement-drain\",\"drain\":\"%s\",\"anchor\":\"%s\",\"groups\":%u,\"instructions_per_group\":%u,\"chain\":%u,\"iterations\":1048576,\"warmup_iterations\":1048576,\"windows\":8,\"reverse\":%s,\"events\":[17,8,58,33133,35,1],\"pmu_type\":8,\"loop_mod64\":0}\n",argv[5],argv[3],g,2u,chain,rev?"true":"false");
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
    uint64_t fpcr;__asm__ volatile("mrs %0, fpcr":"=r"(fpcr));if(fpcr)return fail("fpcr-nonzero");
    const size_t capacity=65536;void *memory=mmap(NULL,capacity,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(memory==MAP_FAILED||!install(memory,capacity,&c))return fail("initial-code-install");
    struct perf perf;if(!open_perf(&perf))return fail("perf-open-id");
    printf("{\"type\":\"runtime\",\"cpu\":7,\"fpcr\":0,\"code_base\":%"PRIuPTR",\"event_ids\":[",(uintptr_t)memory);
    for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",perf.ids[j]);puts("]}");
    typedef uint64_t(*routine_t)(uintptr_t,uintptr_t,void*,uint64_t);routine_t routine=(routine_t)memory;uint64_t hot[8]={1,2,3,4,5,6,7,8};
    for(unsigned pos=0;pos<WINDOWS;++pos) {
        if(memcmp(memory,c.words,4*c.pos))return fail("code-drift");
        __asm__ volatile("msr fpsr,xzr");routine(0,0,hot,ITERATIONS);
        struct pg_sample before,after,delta;const char *e=snapshot(&perf,&before);if(e)return fail(e);
        if(ioctl(perf.fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))return fail("perf-enable");
        uint64_t t=ns();uint64_t checksum=routine(0,0,hot,ITERATIONS);
        /* Read generated original-result stores before libc; D0/D1 have already been reset. */
        uint64_t d0=hot[0],d1=hot[1],status_raw=hot[2];
        t=ns()-t;
        if(ioctl(perf.fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))return fail("perf-disable");
        if((e=snapshot(&perf,&after))||(e=pg_delta(&before,&after,6,&delta)))return fail(e);
        if(sched_getcpu()!=7||!t||!delta.values[0])return fail("window-cpu-time");
        if(checksum!=0)return fail("gpr-result");
        if(d0!=UINT64_C(0x3ff0000000000000)||d1!=d0||status_raw!=0)return fail("sqrt-result-bits");
        printf("{\"type\":\"round\",\"position\":%u,\"round\":%u,\"code_base\":%"PRIuPTR",\"code_matches_plan\":true,\"result_bits\":",pos,rev?WINDOWS-1-pos:pos,(uintptr_t)memory);
        printf("[%"PRIu64",%"PRIu64"],\"status_raw\":%"PRIu64,d0,d1,status_raw);
        printf(",\"gpr_result\":%"PRIu64",\"ns\":%"PRIu64",\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"counts\":[",checksum,t,delta.enabled,delta.running);
        for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",delta.values[j]);puts("]}");
        if(fflush(stdout))return fail("output-write");
    }
    for(unsigned j=0;j<6;++j)close(perf.fd[j]);munmap(memory,capacity);return 0;
#endif
}
