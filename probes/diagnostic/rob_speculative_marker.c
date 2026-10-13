/* SPDX-License-Identifier: Apache-2.0
 * One-shot delayed branch, own hot marker and SB-sealed wrong path; N0 only.
 * docs/design/2026-10-13-rob-speculative-marker.md. Never reads another address space.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "perf_group_read.h"
#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#define NOP 0xd503201fu
#define RET 0xd65f03c0u
struct code {uint32_t*words;size_t pos,cap;};
static void emit(struct code*c,uint32_t w){assert(c->pos<c->cap);c->words[c->pos++]=w;}
#include <inttypes.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#if defined(__linux__) && defined(__aarch64__)
#include <asm/hwcap.h>
#include <fcntl.h>
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/auxv.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#endif
static int fail(const char*reason){fprintf(stderr,"error[%s]\n",reason);printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",reason);return 1;}
static unsigned member(unsigned trial,unsigned pos){unsigned i=(trial+pos)%6;return (trial/6)%2?5-i:i;}
static const char*controls[]={"architect","bypass","speculate"};
static uint64_t test_bits(unsigned c){return c?UINT64_C(0x3ff0000000000000):0;}
static uint64_t train_bits(unsigned c){return c==1?UINT64_C(0x3ff0000000000000):0;}
static struct code marker_build(uint32_t*words,unsigned chain,unsigned load){struct code c={.words=words,.cap=128};emit(&c,0x9e670000u);for(unsigned j=0;j<chain;++j)emit(&c,0x1e61c000u);emit(&c,0x9e66000cu);emit(&c,0xb400004cu);emit(&c,0x14000002u);emit(&c,load?0xf9400029u:NOP);emit(&c,0xd50330ffu);emit(&c,0x9e660000u);emit(&c,0xd53b442cu);emit(&c,0xf900004cu);emit(&c,RET);return c;}
static void export_program(const struct code*c,unsigned load){printf("{\"type\":\"program\",\"marker\":\"%s\",\"code_bytes\":%zu,\"words\":[",load?"load":"nop",4*c->pos);for(size_t j=0;j<c->pos;++j)printf("%s%"PRIu32,j?",":"",c->words[j]);puts("]}");}
static void schedule(unsigned t,unsigned pos){unsigned i=member(t,pos),control=i/2,load=i%2;printf("{\"type\":\"schedule\",\"trial\":%u,\"position\":%u,\"control\":\"%s\",\"marker\":\"%s\",\"train_bits\":%"PRIu64",\"test_bits\":%"PRIu64"}\n",t,pos,controls[control],load?"load":"nop",train_bits(control),test_bits(control));}
#if defined(__linux__) && defined(__aarch64__)
struct perf{int fd[7];uint64_t ids[7];};
static bool open_perf(struct perf*p){const uint64_t events[]={17,8,112,6,34,59,1};for(unsigned j=0;j<7;++j)p->fd[j]=-1;for(unsigned j=0;j<7;++j){struct perf_event_attr a={0};a.size=sizeof(a);a.type=8;a.config=events[j];a.disabled=j==0;a.pinned=j==0;a.exclude_kernel=1;a.exclude_hv=1;a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING|PERF_FORMAT_ID;p->fd[j]=(int)syscall(SYS_perf_event_open,&a,0,-1,j?p->fd[0]:-1,0);if(p->fd[j]<0||ioctl(p->fd[j],PERF_EVENT_IOC_ID,&p->ids[j])){fprintf(stderr,"perf-open-id index=%u event=%"PRIu64" errno=%d\n",j,events[j],errno);return false;}}return true;}
static const char*snapshot(struct perf*p,struct pg_sample*s){uint64_t wire[17];ssize_t bytes=read(p->fd[0],wire,sizeof(wire));if(bytes<=0||bytes%8)return "perf-read";return pg_decode(wire,(size_t)bytes/8,p->ids,7,s);}
typedef uint64_t(*marker_routine_t)(uint64_t,uintptr_t,uintptr_t);
/* This exact window wrapper is also warmed with training input, outside reported data. */
static const char*measure_frame(struct perf*p,marker_routine_t routine,uint64_t bits,uint64_t*data,struct pg_sample*delta,uint64_t*result,uint64_t*status){struct pg_sample before,after;const char*e=snapshot(p,&before);if(e)return e;if(ioctl(p->fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))return "perf-enable";*result=routine(bits,(uintptr_t)data,(uintptr_t)(data+1));if(ioctl(p->fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))return "perf-disable";*status=data[1];if((e=snapshot(p,&after))||(e=pg_delta(&before,&after,7,delta)))return e;return NULL;}
static int one_page(int fd,uintptr_t va,uint64_t*out){return pread(fd,out,8,(off_t)(va/4096*8))==8?0:-1;}
#endif
int main(int argc,char**argv){
 if(argc!=4||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||strcmp(argv[2],"--chain")||(strcmp(argv[3],"16")&&strcmp(argv[3],"32")))return fail("usage-marker-plan-run-chain16-32");
 unsigned chain=(unsigned)atoi(argv[3]);uint32_t words[2][128];struct code programs[2];for(unsigned j=0;j<2;++j)programs[j]=marker_build(words[j],chain,j);
 printf("{\"type\":\"config\",\"version\":1,\"probe\":\"rob-speculative-marker\",\"chain\":%u,\"groups\":0,\"trials\":18,\"windows\":108,\"training_calls\":64,\"full_window_warmup_calls\":4,\"events\":[17,8,112,6,34,59,1],\"pmu_type\":8,\"schedule_reverse_block_trials\":6}\n",chain);for(unsigned j=0;j<2;++j)export_program(&programs[j],j);
 if(!strcmp(argv[1],"--plan")){for(unsigned t=0;t<18;++t)for(unsigned pos=0;pos<6;++pos)schedule(t,pos);return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
 return fail("requires-linux-aarch64");
#else
 if(sysconf(_SC_PAGESIZE)!=4096)return fail("page-size");if(!(getauxval(AT_HWCAP)&HWCAP_SB))return fail("SB-unavailable");cpu_set_t mask;CPU_ZERO(&mask);CPU_SET(7,&mask);if(sched_setaffinity(0,sizeof(mask),&mask)||sched_getcpu()!=7)return fail("affinity");uint64_t fpcr;__asm__ volatile("mrs %0,fpcr":"=r"(fpcr));if(fpcr)return fail("FPCR-nonzero");
 void*code=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);uint64_t*data=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(code==MAP_FAILED||data==MAP_FAILED)return fail("owned-mappings");data[0]=0x12345678;data[1]=0;
 int pm=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);if(pm<0)return fail("pagemap");struct perf p;if(!open_perf(&p))return fail("seven-PMU-unavailable");
 /* Install initially to fault code before the endpoint certificate. */
 memcpy(code,programs[0].words,4*programs[0].pos);uint64_t cb,db,ca,da;if(one_page(pm,(uintptr_t)code,&cb)||one_page(pm,(uintptr_t)data,&db))return fail("initial-pagemap");
 printf("{\"type\":\"runtime\",\"cpu\":7,\"fpcr\":0,\"hwcap_sb\":true,\"code_base\":%"PRIuPTR",\"marker_base\":%"PRIuPTR",\"code_pagemap_before\":%"PRIu64",\"marker_pagemap_before\":%"PRIu64",\"event_ids\":[",(uintptr_t)code,(uintptr_t)data,cb,db);for(unsigned j=0;j<7;++j)printf("%s%"PRIu64,j?",":"",p.ids[j]);puts("]}");
 marker_routine_t routine=(marker_routine_t)code;
 for(unsigned t=0;t<18;++t)for(unsigned pos=0;pos<6;++pos){unsigned i=member(t,pos),control=i/2,load=i%2;struct code*c=&programs[load];if(mprotect(code,4096,PROT_READ|PROT_WRITE))return fail("code-RW");memcpy(code,c->words,4*c->pos);__builtin___clear_cache(code,(char*)code+4*c->pos);if(mprotect(code,4096,PROT_READ|PROT_EXEC))return fail("code-RX");volatile uint64_t hot=data[0];(void)hot;__asm__ volatile("msr fpsr,xzr");
  for(unsigned warm=0;warm<64;++warm)if(routine(train_bits(control),(uintptr_t)data,(uintptr_t)(data+1))!=train_bits(control)||data[1])return fail("training-result");if(memcmp(code,c->words,4*c->pos))return fail("code-drift");
  struct pg_sample delta;uint64_t result,status;const char*e;for(unsigned warm=0;warm<4;++warm){if((e=measure_frame(&p,routine,train_bits(control),data,&delta,&result,&status)))return fail(e);if(result!=train_bits(control)||status)return fail("wrapper-warmup-result");}
  if((e=measure_frame(&p,routine,test_bits(control),data,&delta,&result,&status)))return fail(e);if(sched_getcpu()!=7||result!=test_bits(control)||status)return fail("original-result-FPSR-CPU");
  printf("{\"type\":\"round\",\"trial\":%u,\"position\":%u,\"control\":\"%s\",\"marker\":\"%s\",\"train_bits\":%"PRIu64",\"test_bits\":%"PRIu64",\"result_bits\":%"PRIu64",\"status_raw\":%"PRIu64",\"code_base\":%"PRIuPTR",\"code_matches_plan\":true,\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"counts\":[",t,pos,controls[control],load?"load":"nop",train_bits(control),test_bits(control),result,status,(uintptr_t)code,delta.enabled,delta.running);for(unsigned j=0;j<7;++j)printf("%s%"PRIu64,j?",":"",delta.values[j]);puts("]}");if(fflush(stdout))return fail("output-write");
 }
 if(one_page(pm,(uintptr_t)code,&ca)||one_page(pm,(uintptr_t)data,&da))return fail("final-pagemap");for(unsigned j=0;j<7;++j)close(p.fd[j]);close(pm);printf("{\"type\":\"final\",\"code_pagemap_after\":%"PRIu64",\"marker_pagemap_after\":%"PRIu64",\"fds_closed\":true}\n",ca,da);munmap(code,4096);munmap(data,4096);return 0;
#endif
}
