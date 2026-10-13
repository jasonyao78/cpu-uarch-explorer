/* SPDX-License-Identifier: Apache-2.0
 * Owned long64 metadata-guarded MRS qualification, never global control writes.
 * docs/design/2026-10-13-pmu-own-direct-counter.md; parent owns restored profile.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "../common/perf_group_read.h"
#include "../common/perf_user_counter.h"
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
#include <setjmp.h>
#include <signal.h>
#endif
#ifndef CPU_UARCH_PMU_BOUNDED
#define CPU_UARCH_PMU_BOUNDED 0
#endif
static void plan(unsigned e){printf("{\"probe\":\"pmu-own-counter\",\"version\":%u,\"epoch\":%u,\"events\":[17,8,112,113],\"config1\":3,\"iterations\":8192,\"rounds\":8,\"roles\":[\"nop\",\"load\",\"store\"],\"cpu\":7,\"pmu_type\":8,\"owned_direct_read\":true,\"global_policy_mutation\":false%s}\n",CPU_UARCH_PMU_BOUNDED?2:1,e,CPU_UARCH_PMU_BOUNDED?",\"invalid_window_budget\":1,\"attempts\":24":"");}
static int failure(const char*s){printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\",\"errno\":%d},\"fds_closed\":true}\n",s,errno);return 1;}
#if defined(__linux__) && defined(__aarch64__)
static sigjmp_buf trap;static volatile sig_atomic_t armed;
static void illegal(int sig){if(armed){armed=0;siglongjmp(trap,1);} _exit(128+sig);}
struct direct {struct pu_metadata meta;uint64_t hardware,total;unsigned attempted,register_read;};
/* Acquire loads and a full ordering barrier keep the MRS inside this seqlock.
 * Never retry changed metadata: preserve first failure, parent restores policy. */
static int one(struct perf_event_mmap_page*p,struct direct*out){
 struct pu_metadata m={0};out->attempted=1;out->register_read=0;m.first=__atomic_load_n(&p->lock,__ATOMIC_ACQUIRE);__asm__ volatile("dmb ishld":::"memory");m.index=p->index;m.width=p->pmc_width;m.cap=p->cap_user_rdpmc;m.offset=p->offset;__asm__ volatile("dmb ishld":::"memory");m.last=__atomic_load_n(&p->lock,__ATOMIC_ACQUIRE);out->meta=m;if(pu_guard(1,&m))return (!m.cap||m.width!=64||m.index>32)?3:1;
 uint64_t value=0;if(sigsetjmp(trap,0))return 2;armed=1;__asm__ volatile("isb":::"memory");
 if(m.index==32)__asm__ volatile("mrs %0,pmccntr_el0":"=r"(value)::"memory");else{uint64_t select=m.index-1;__asm__ volatile("msr pmselr_el0,%1\n isb\n mrs %0,pmxevcntr_el0":"=r"(value):"r"(select):"memory");}
 __asm__ volatile("isb\n dmb ishld":::"memory");armed=0;m.last=__atomic_load_n(&p->lock,__ATOMIC_ACQUIRE);out->meta=m;out->hardware=value;out->total=pu_total(m.offset,value);out->register_read=1;if(pu_guard(1,&m))return 1;return 0;
}
static int four(struct perf_event_mmap_page**p,struct direct*out){for(unsigned i=0;i<4;i++){int r=one(p[i],out+i);if(r)return r;for(unsigned j=0;j<i;j++)if(out[i].meta.index==out[j].meta.index)return 3;}return 0;}
__attribute__((noinline)) static void nop_work(uint64_t n){__asm__ volatile("1: nop\n subs %0,%0,#1\n b.ne 1b":"+r"(n)::"cc","memory");}
__attribute__((noinline)) static void load_work(uint64_t n,uint64_t*p){__asm__ volatile("1: ldr xzr,[%1]\n subs %0,%0,#1\n b.ne 1b":"+r"(n):"r"(p):"cc","memory");}
__attribute__((noinline)) static void store_work(uint64_t n,uint64_t*p){uint64_t v=0x1234;__asm__ volatile("1: str %2,[%1]\n subs %0,%0,#1\n b.ne 1b":"+r"(n):"r"(p),"r"(v):"cc","memory");}
static void array(const uint64_t*v){putchar('[');for(unsigned i=0;i<4;i++)printf("%s%"PRIu64,i?",":"",v[i]);putchar(']');}
static void direct_json(const struct direct*v){putchar('[');for(unsigned i=0;i<4;i++){printf("%s{\"sequence_before\":%u,\"sequence_after\":%u,\"index\":%u,\"width\":%u,\"cap\":%s,\"offset\":%"PRIu64",\"hardware\":%"PRIu64",\"total\":%"PRIu64,i?",":"",v[i].meta.first,v[i].meta.last,v[i].meta.index,v[i].meta.width,v[i].meta.cap?"true":"false",v[i].meta.offset,v[i].hardware,v[i].total);if(CPU_UARCH_PMU_BOUNDED)printf(",\"attempted\":%s,\"register_read\":%s",v[i].attempted?"true":"false",v[i].register_read?"true":"false");putchar('}');}putchar(']');}
static int kernel_read(int fd,const uint64_t*ids,struct pg_sample*s){uint64_t w[11];return read(fd,w,sizeof(w))!=(ssize_t)sizeof(w)||pg_decode(w,11,ids,4,s)!=NULL;}
#endif
int main(int argc,char**argv){
 if(argc!=3||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||(strcmp(argv[2],"0")&&strcmp(argv[2],"1")&&strcmp(argv[2],"2")))return failure("usage-own-counter");unsigned epoch=(unsigned)atoi(argv[2]);plan(epoch);if(!strcmp(argv[1],"--plan"))return 0;
#if !defined(__linux__) || !defined(__aarch64__)
 return failure("requires-linux-aarch64");
#else
 int fd[4]={-1,-1,-1,-1},rc=1,policy=-1,handler=0;uint64_t ids[4]={0};struct perf_event_mmap_page*p[4]={MAP_FAILED,MAP_FAILED,MAP_FAILED,MAP_FAILED};const char*stage="affinity";struct sigaction old,act={0};cpu_set_t cp;CPU_ZERO(&cp);CPU_SET(7,&cp);if(sched_setaffinity(0,sizeof(cp),&cp)||sched_getcpu()!=7||sysconf(_SC_PAGESIZE)!=4096)goto done;
 stage="user-access-disabled";FILE*f=fopen("/proc/sys/kernel/perf_user_access","r");if(!f)goto done;int parsed=fscanf(f,"%d",&policy);fclose(f);if(parsed!=1||policy!=1)goto done;puts("{\"type\":\"policy\",\"actual\":1,\"read_only\":true}");
 const unsigned ev[]={17,8,112,113};stage="perf-own-open";for(unsigned j=0;j<4;j++){struct perf_event_attr a={0};a.size=sizeof(a);a.type=8;a.config=ev[j];a.config1=3;a.disabled=j==0;a.pinned=j==0;a.exclude_kernel=1;a.exclude_hv=1;a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_ID|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING;fd[j]=(int)syscall(SYS_perf_event_open,&a,0,-1,j?fd[0]:-1,PERF_FLAG_FD_CLOEXEC);if(fd[j]<0||ioctl(fd[j],PERF_EVENT_IOC_ID,ids+j))goto done;p[j]=mmap(NULL,4096,PROT_READ,MAP_SHARED,fd[j],0);if(p[j]==MAP_FAILED)goto done;}
 stage="sigill-guard";act.sa_handler=illegal;sigemptyset(&act.sa_mask);if(sigaction(SIGILL,&act,&old))goto done;handler=1;stage="perf-enable";if(ioctl(fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))goto done;
 unsigned invalid_count=0;(void)invalid_count;_Alignas(64) uint64_t own[8]={0};nop_work(8192);load_work(8192,own);store_work(8192,own);
 for(unsigned round=0;round<8;round++)for(unsigned k=0;k<3;k++){
  unsigned role=epoch==1?2-k:k;struct direct a[4]={0},b[4]={0};unsigned payload_ran=0;(void)payload_ran;struct pg_sample before,after,delta;stage="kernel-before";if(kernel_read(fd[0],ids,&before))goto done;stage="direct-before";int r=four(p,a);if(r){stage=r==2?"user-counter-sigill":"user-counter-metadata";if(CPU_UARCH_PMU_BOUNDED&&r==1)goto invalid;goto done;}
  __asm__ volatile("dsb ish\n isb":::"memory");payload_ran=1;if(role==0)nop_work(8192);else if(role==1)load_work(8192,own);else store_work(8192,own);__asm__ volatile("dsb ish\n isb":::"memory");stage="direct-after";r=four(p,b);if(r){stage=r==2?"user-counter-sigill":"user-counter-metadata";if(CPU_UARCH_PMU_BOUNDED&&r==1)goto invalid;goto done;}
  stage="kernel-after";if(kernel_read(fd[0],ids,&after)||pg_delta(&before,&after,4,&delta))goto done;stage="metadata-changed";for(unsigned j=0;j<4;j++)if(a[j].meta.first!=b[j].meta.first||a[j].meta.index!=b[j].meta.index||a[j].meta.offset!=b[j].meta.offset){if(CPU_UARCH_PMU_BOUNDED)goto invalid;goto done;}
  printf("{\"type\":\"window\",\"round\":%u,\"role\":%u,\"cpu\":%d,\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"kernel_before\":",round,role,sched_getcpu(),delta.enabled,delta.running);array(before.values);printf(",\"kernel_after\":");array(after.values);printf(",\"direct_before\":");direct_json(a);printf(",\"direct_after\":");direct_json(b);puts("}");if(sched_getcpu()!=7){stage="cpu-drift";goto done;}continue;
  invalid:
  if(!CPU_UARCH_PMU_BOUNDED)goto done;
  if(kernel_read(fd[0],ids,&after)||pg_delta(&before,&after,4,&delta)){stage="invalid-kernel-read";goto done;}
  ++invalid_count;printf("{\"type\":\"invalid-window\",\"round\":%u,\"role\":%u,\"cpu\":%d,\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"metrics\":{},\"failure\":{\"reason\":\"%s\"},\"payload_ran\":%s,\"kernel_before\":",round,role,sched_getcpu(),delta.enabled,delta.running,stage,payload_ran?"true":"false");array(before.values);printf(",\"kernel_after\":");array(after.values);printf(",\"direct_before\":");direct_json(a);printf(",\"direct_after\":");direct_json(b);puts("}");if(sched_getcpu()!=7){stage="cpu-drift";goto done;}
 }
 rc=0;
 done:armed=0;if(fd[0]>=0)ioctl(fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP);for(unsigned j=0;j<4;j++){if(p[j]!=MAP_FAILED)munmap(p[j],4096);if(fd[j]>=0)close(fd[j]);}if(handler)sigaction(SIGILL,&old,NULL);if(rc)return failure(stage);printf("{\"type\":\"final\",\"fds_closed\":true,\"global_policy_mutation\":false,\"owned_direct_read\":true");if(CPU_UARCH_PMU_BOUNDED)printf(",\"invalid_windows\":%u",invalid_count);puts("}");return 0;
#endif
}
