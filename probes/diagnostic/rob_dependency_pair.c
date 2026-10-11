/* SPDX-License-Identifier: Apache-2.0
 * Same process/code VA paired dependency response, no physical ROB counting.
 * Frozen protocol: docs/design/2026-10-11-rob-same-address-pair.md.
 * Legacy generator is shared through rob_codegen.h, never a second rule set.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "rob_codegen.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
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
#define PAIR_ITERATIONS 131072u
#define PAIR_BLOCKS 8u
static const char *variants[]={"i0","d0","i128","d128"};
struct program { uint32_t words[1024];struct code c;struct options options; };
static int failure(const char *why){fprintf(stderr,"error[%s]\n",why);printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",why);return 1;}
// Common same-value bridge; zero/code identity and Rn-only differences are
// checked by independent exported-code tests before any target launch.
static void programs(struct program *p,bool fsqrt,unsigned chain){
    for(unsigned i=0;i<4;++i){struct options o={.cls=1,.n=i>=2?128:0,.its=PAIR_ITERATIONS,.chain=chain,.have_link=true,.dependent_link=(i%2)!=0,.anchor=fsqrt?SQRT:NONE};p[i].options=o;p[i].c=build(p[i].words,1024,&o);}
}
static void config(bool fsqrt,unsigned chain,bool reverse){printf("{\"type\":\"config\",\"version\":1,\"probe\":\"rob-same-address-pair\",\"class\":\"%s\",\"anchor\":\"%s\",\"chain\":%u,\"iterations\":131072,\"warmup_iterations\":131072,\"blocks\":8,\"windows\":32,\"reverse\":%s,\"events\":[17,8,58,59,33133,35],\"pmu_type\":8,\"loop_mod64\":0}\n",classes[1],fsqrt?"fsqrt":"none",chain,reverse?"true":"false");}
static void program(const struct program *p,unsigned i){printf("{\"type\":\"program\",\"variant\":\"%s\",\"n\":%u,\"link\":\"%s\",\"loop_offset\":%zu,\"branch_offset\":%zu,\"loop_instructions\":%zu,\"prologue_instructions\":%zu,\"code_bytes\":%zu,\"words\":[",variants[i],p->options.n,p->options.dependent_link?"dependent":"independent",4*p->c.loop,4*p->c.branch,p->c.branch-p->c.loop+1,p->c.loop,4*p->c.pos);for(size_t j=0;j<p->c.pos;++j)printf("%s%"PRIu32,j?",":"",p->words[j]);puts("]}");}
static void schedule(unsigned position,bool reverse,unsigned *block,unsigned *slot,unsigned *variant){unsigned index=reverse?31-position:position;*block=index/4;*slot=index%4;*variant=(*block%2)?3-*slot:*slot;}
#if defined(__linux__) && defined(__aarch64__)
struct perf {int fd[6];uint64_t ids[6];};
static bool setup(struct perf *p){const uint64_t events[]={0x11,0x08,0x3a,0x3b,0x816d,0x23};for(unsigned i=0;i<6;++i)p->fd[i]=-1;for(unsigned i=0;i<6;++i){struct perf_event_attr a={0};a.size=sizeof(a);a.type=8;a.config=events[i];a.disabled=i==0;a.pinned=i==0;a.exclude_kernel=1;a.exclude_hv=1;a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING|PERF_FORMAT_ID;p->fd[i]=(int)syscall(SYS_perf_event_open,&a,0,-1,i?p->fd[0]:-1,0);if(p->fd[i]<0||ioctl(p->fd[i],PERF_EVENT_IOC_ID,&p->ids[i]))return false;}return true;}
static const char* snapshot(struct perf *p,struct pg_sample *s){uint64_t wire[15];ssize_t n=read(p->fd[0],wire,sizeof(wire));if(n<=0||n%8)return "perf-read";return pg_decode(wire,(size_t)n/8,p->ids,6,s);}
static uint64_t ns(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC_RAW,&t))abort();return (uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec;}
#endif
int main(int argc,char** argv){
    if((argc!=6&&argc!=7)||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||strcmp(argv[2],"--anchor")||(strcmp(argv[3],"none")&&strcmp(argv[3],"fsqrt"))||strcmp(argv[4],"--chain")||(strcmp(argv[5],"8")&&strcmp(argv[5],"16"))||(argc==7&&strcmp(argv[6],"--reverse")))return failure("usage-pair-plan-run-anchor-chain-reverse");
    bool fsqrt=!strcmp(argv[3],"fsqrt"),reverse=argc==7;unsigned chain=(unsigned)atoi(argv[5]);if(!fsqrt&&chain!=16)return failure("none-chain-must-be16");struct program p[4];programs(p,fsqrt,chain);config(fsqrt,chain,reverse);for(unsigned i=0;i<4;++i)program(&p[i],i);
    if(!strcmp(argv[1],"--plan")){for(unsigned pos=0;pos<32;++pos){unsigned b,s,v;schedule(pos,reverse,&b,&s,&v);printf("{\"type\":\"schedule\",\"position\":%u,\"block\":%u,\"slot\":%u,\"variant\":\"%s\"}\n",pos,b,s,variants[v]);}return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
    return failure("measurement-requires-linux-aarch64");
#else
    if(sysconf(_SC_PAGESIZE)!=4096)return failure("page-size");cpu_set_t mask;CPU_ZERO(&mask);CPU_SET(7,&mask);if(sched_setaffinity(0,sizeof(mask),&mask)||sched_getcpu()!=7)return failure("affinity");uint64_t fpcr;asm volatile("mrs %0, fpcr":"=r"(fpcr));if(fpcr)return failure("fpcr-nonzero");
    const size_t capacity=65536;void *memory=mmap(NULL,capacity,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(memory==MAP_FAILED)return failure("code-map");struct perf perf;if(!setup(&perf))return failure("perf-open-id");printf("{\"type\":\"runtime\",\"cpu\":7,\"fpcr\":0,\"code_base\":%"PRIuPTR",\"event_ids\":[",(uintptr_t)memory);for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",perf.ids[j]);puts("]}");typedef void(*routine_t)(uintptr_t,uintptr_t,void*,uint64_t);routine_t routine=(routine_t)memory;uint64_t hot[8]={1,2,3,4,5,6,7,8};
    for(unsigned pos=0;pos<32;++pos){unsigned b,s,v;schedule(pos,reverse,&b,&s,&v);struct program *q=&p[v];if(mprotect(memory,capacity,PROT_READ|PROT_WRITE))return failure("code-x-to-w");memcpy(memory,q->words,4*q->c.pos);if(memcmp(memory,q->words,4*q->c.pos))return failure("code-copy-drift");__builtin___clear_cache((char*)memory,(char*)memory+4*q->c.pos);if(mprotect(memory,capacity,PROT_READ|PROT_EXEC))return failure("code-w-to-x");routine(0,0,hot,PAIR_ITERATIONS);
        struct pg_sample before,after,delta;const char *e=snapshot(&perf,&before);if(e)return failure(e);if(ioctl(perf.fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))return failure("perf-enable");uint64_t t=ns();routine(0,0,hot,PAIR_ITERATIONS);t=ns()-t;if(ioctl(perf.fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))return failure("perf-disable");if((e=snapshot(&perf,&after))||(e=pg_delta(&before,&after,6,&delta)))return failure(e);if(sched_getcpu()!=7||!t||!delta.values[0])return failure("window-cpu-time");
        printf("{\"type\":\"round\",\"position\":%u,\"block\":%u,\"slot\":%u,\"variant\":\"%s\",\"code_base\":%"PRIuPTR",\"code_matches_plan\":true,\"ns\":%"PRIu64",\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"counts\":[",pos,b,s,variants[v],(uintptr_t)memory,t,delta.enabled,delta.running);for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",delta.values[j]);puts("]}");if(fflush(stdout))return failure("output-write");
    }
    for(unsigned j=0;j<6;++j)close(perf.fd[j]);munmap(memory,capacity);return 0;
#endif
}
