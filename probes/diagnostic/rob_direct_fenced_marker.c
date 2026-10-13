/* SPDX-License-Identifier: Apache-2.0
 * Own near load/far store issue markers; sealed delayed branch; N0 only.
 * docs/design/2026-10-13-rob-direct-fenced-marker.md. Never reads another address space.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "perf_group_read.h"
#include "perf_user_counter.h"
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
#include <signal.h>
#include <setjmp.h>
#endif
static int fail(const char*reason){fprintf(stderr,"error[%s]\n",reason);printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",reason);return 1;}
static unsigned member(unsigned trial,unsigned pos){unsigned i=(trial+pos)%8;return (trial/8)%2?7-i:i;}
static const char*controls[]={"architect","speculate"};
static uint64_t test_bits(unsigned c){return c?UINT64_C(0x3ff0000000000000):0;}
static uint64_t train_bits(unsigned c){(void)c;return 0;}
static struct code marker_build(uint32_t*words,unsigned chain,unsigned mode){unsigned taps=mode%2,pre=mode<2;
 struct code c={.words=words,.cap=128};emit(&c,0xaa1f03e9u);emit(&c,0x9e670000u);emit(&c,0xaa0403e6u);
 for(unsigned j=0;j<chain;++j)emit(&c,0x1e61c000u);
 emit(&c,0x9e66000cu);emit(&c,0xb500026cu);emit(&c,pre?0xd50330ffu:NOP);
 for(unsigned j=0;j<8;++j)emit(&c,taps?(0xf9400029u+((j*8u)<<10)):NOP);
 for(unsigned j=0;j<8;++j)emit(&c,taps?(0xf9000046u+((j*8u)<<10)):NOP);
 emit(&c,pre?NOP:0xd50330ffu);
 const uint32_t tail[]={0xd50330ffu,0x9e660000u,0xd53b442cu,0xf900006cu,0xf9000469u,RET};
 for(unsigned j=0;j<6;++j)emit(&c,tail[j]);return c;
}
static void export_program(const struct code*c,unsigned mode){unsigned taps=mode%2;printf("{\"type\":\"program\",\"marker\":\"%s\",\"fence\":\"%s\",\"code_bytes\":%zu,\"words\":[",taps?"taps":"nop",mode<2?"pre":"post",4*c->pos);for(size_t j=0;j<c->pos;++j)printf("%s%"PRIu32,j?",":"",c->words[j]);puts("]}");}
static void schedule(unsigned t,unsigned pos){unsigned i=member(t,pos),control=i/4,taps=i%2,mode=i%4;printf("{\"type\":\"schedule\",\"trial\":%u,\"position\":%u,\"control\":\"%s\",\"marker\":\"%s\",\"fence\":\"%s\",\"train_bits\":%"PRIu64",\"test_bits\":%"PRIu64"}\n",t,pos,controls[control],taps?"taps":"nop",mode<2?"pre":"post",train_bits(control),test_bits(control));}
#if defined(__linux__) && defined(__aarch64__)
struct perf{int fd[6];uint64_t ids[6];struct perf_event_mmap_page*page[6];};
struct roi_value{struct pu_metadata meta;uint64_t hardware,total;};
static struct {struct roi_value before[6],after[6];struct pg_sample kernel_before,kernel_after,delta;} trace;
static sigjmp_buf counter_trap;static volatile sig_atomic_t counter_armed;
static void counter_sigill(int sig){if(counter_armed){counter_armed=0;siglongjmp(counter_trap,1);} _exit(128+sig);}
static void value_array(const uint64_t*v){putchar('[');for(unsigned j=0;j<6;j++)printf("%s%"PRIu64,j?",":"",v[j]);putchar(']');}
static void roi_array(const struct roi_value*v){putchar('[');for(unsigned j=0;j<6;j++)printf("%s{\"sequence_before\":%u,\"sequence_after\":%u,\"index\":%u,\"width\":%u,\"cap\":%s,\"offset\":%"PRIu64",\"hardware\":%"PRIu64",\"total\":%"PRIu64"}",j?",":"",v[j].meta.first,v[j].meta.last,v[j].meta.index,v[j].meta.width,v[j].meta.cap?"true":"false",v[j].meta.offset,v[j].hardware,v[j].total);putchar(']');}
/* One protected snapshot; current own metadata bounds every MRS, no retry. */
static const char*roi_snapshot(struct perf*p,struct roi_value*out){
 if(sigsetjmp(counter_trap,0))return "direct-counter-sigill";
 for(unsigned j=0;j<6;j++){
  struct perf_event_mmap_page*q=p->page[j];struct pu_metadata*m=&out[j].meta;m->first=__atomic_load_n(&q->lock,__ATOMIC_ACQUIRE);__asm__ volatile("dmb ishld":::"memory");m->index=q->index;m->width=q->pmc_width;m->cap=q->cap_user_rdpmc;m->offset=q->offset;__asm__ volatile("dmb ishld":::"memory");m->last=__atomic_load_n(&q->lock,__ATOMIC_ACQUIRE);const char*err=pu_guard(1,m);if(err)return err;
  counter_armed=1;uint64_t v=0;__asm__ volatile("isb":::"memory");if(m->index==32)__asm__ volatile("mrs %0,pmccntr_el0":"=r"(v)::"memory");else{uint64_t ix=m->index-1;__asm__ volatile("msr pmselr_el0,%1\n isb\n mrs %0,pmxevcntr_el0":"=r"(v):"r"(ix):"memory");}__asm__ volatile("isb\n dmb ishld":::"memory");counter_armed=0;m->last=__atomic_load_n(&q->lock,__ATOMIC_ACQUIRE);out[j].hardware=v;out[j].total=pu_total(m->offset,v);if((err=pu_guard(1,m)))return err;for(unsigned k=0;k<j;k++)if(m->index==out[k].meta.index)return "duplicate-own-counter";
 }
 return NULL;
}
static bool open_perf(struct perf*p){const uint64_t events[]={17,8,112,113,34,1};for(unsigned j=0;j<6;++j){p->fd[j]=-1;p->page[j]=MAP_FAILED;}for(unsigned j=0;j<6;++j){struct perf_event_attr a={0};a.size=sizeof(a);a.type=8;a.config=events[j];a.config1=3;a.disabled=j==0;a.pinned=j==0;a.exclude_kernel=1;a.exclude_hv=1;a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING|PERF_FORMAT_ID;p->fd[j]=(int)syscall(SYS_perf_event_open,&a,0,-1,j?p->fd[0]:-1,0);if(p->fd[j]<0||ioctl(p->fd[j],PERF_EVENT_IOC_ID,&p->ids[j])){fprintf(stderr,"perf-open-id index=%u event=%"PRIu64" errno=%d\n",j,events[j],errno);return false;}p->page[j]=mmap(NULL,4096,PROT_READ,MAP_SHARED,p->fd[j],0);if(p->page[j]==MAP_FAILED)return false;}return true;}
static const char*snapshot(struct perf*p,struct pg_sample*s){uint64_t wire[15];ssize_t bytes=read(p->fd[0],wire,sizeof(wire));if(bytes<=0||bytes%8)return "perf-read";return pg_decode(wire,(size_t)bytes/8,p->ids,6,s);}
typedef uint64_t(*marker_routine_t)(uint64_t,uintptr_t,uintptr_t,uintptr_t,uint64_t);
/* Owned direct ROI, FD envelope and live metadata are separate boundaries. */
static const char*measure_frame(struct perf*p,marker_routine_t routine,uint64_t bits,uint64_t*near,uint64_t*far,uint64_t*out,struct pg_sample*delta,uint64_t*result){
 const char*e=NULL;memset(&trace,0,sizeof(trace));if(ioctl(p->fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))return "perf-enable";
 if((e=snapshot(p,&trace.kernel_before))||(e=roi_snapshot(p,trace.before)))goto rejected;
 __asm__ volatile("dsb ish\n isb":::"memory");*result=routine(bits,(uintptr_t)near,(uintptr_t)far,(uintptr_t)out,0x12345678);__asm__ volatile("dsb ish\n isb":::"memory");
 if((e=roi_snapshot(p,trace.after)))goto rejected;
 for(unsigned j=0;j<6;j++)if(trace.before[j].meta.first!=trace.after[j].meta.first||trace.before[j].meta.index!=trace.after[j].meta.index||trace.before[j].meta.offset!=trace.after[j].meta.offset){e="ROI-metadata-changed";goto rejected;}
 if((e=snapshot(p,&trace.kernel_after))||(e=pg_delta(&trace.kernel_before,&trace.kernel_after,6,&trace.delta)))goto rejected;
 *delta=trace.delta;for(unsigned j=0;j<6;j++){delta->values[j]=pu_delta(trace.before[j].total,trace.after[j].total);if(trace.before[j].total<trace.kernel_before.values[j]||trace.after[j].total>trace.kernel_after.values[j]||delta->values[j]>trace.delta.values[j]){e="ROI-FD-envelope";goto rejected;}}
 if(ioctl(p->fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))return "perf-disable";return NULL;
 rejected:
 counter_armed=0;ioctl(p->fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP);printf("{\"type\":\"rejected-window\",\"metrics\":{},\"reason\":\"%s\",\"roi_before\":",e);roi_array(trace.before);printf(",\"roi_after\":");roi_array(trace.after);puts("}");return e;
}
static int one_page(int fd,uintptr_t va,uint64_t*out){return pread(fd,out,8,(off_t)(va/4096*8))==8?0:-1;}
static bool originals(uint64_t result,uint64_t bits,uint64_t*out,uint64_t*far,unsigned taps){unsigned active=taps&&!bits;if(result!=bits||out[0]||out[1]!=(active?0x12345678u:0))return false;for(unsigned j=0;j<8;++j)if(far[j*8]!=(active?0x12345678u:0))return false;return true;}
static void prepare(uint64_t*near,uint64_t*far,uint64_t*out){volatile uint64_t hot=0;for(unsigned j=0;j<8;++j){hot^=((volatile uint64_t*)near)[j*8];far[j*8]=0;}out[0]=out[1]=0;(void)hot;__asm__ volatile("dsb ish":::"memory");}
#endif
int main(int argc,char**argv){
 if(argc!=4||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||strcmp(argv[2],"--chain")||(strcmp(argv[3],"16")&&strcmp(argv[3],"32")))return fail("usage-issue-marker-plan-run-chain16-32");
 unsigned chain=(unsigned)atoi(argv[3]);uint32_t words[4][128];struct code programs[4];for(unsigned j=0;j<4;++j)programs[j]=marker_build(words[j],chain,j);
 printf("{\"type\":\"config\",\"version\":2,\"probe\":\"rob-direct-fenced-marker\",\"chain\":%u,\"groups\":0,\"trials\":32,\"windows\":256,\"training_calls\":64,\"routine_warmup_calls\":4,\"count_source\":\"owned-direct-roi\",\"perf_config1\":3,\"events\":[17,8,112,113,34,1],\"pmu_type\":8,\"schedule_reverse_block_trials\":8}\n",chain);for(unsigned j=0;j<4;++j)export_program(&programs[j],j);
 if(!strcmp(argv[1],"--plan")){for(unsigned t=0;t<32;++t)for(unsigned pos=0;pos<8;++pos)schedule(t,pos);return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
 return fail("requires-linux-aarch64");
#else
 if(sysconf(_SC_PAGESIZE)!=4096)return fail("page-size");if(!(getauxval(AT_HWCAP)&HWCAP_SB))return fail("SB-unavailable");cpu_set_t mask;CPU_ZERO(&mask);CPU_SET(7,&mask);if(sched_setaffinity(0,sizeof(mask),&mask)||sched_getcpu()!=7)return fail("affinity");FILE*policy=fopen("/proc/sys/kernel/perf_user_access","r");if(!policy)return fail("user-profile-read");int actual=-1,parsed=fscanf(policy,"%d",&actual);fclose(policy);if(parsed!=1||actual!=1)return fail("user-profile-disabled");struct sigaction act={0};act.sa_handler=counter_sigill;sigemptyset(&act.sa_mask);if(sigaction(SIGILL,&act,NULL))return fail("SIGILL-guard");uint64_t fpcr;__asm__ volatile("mrs %0,fpcr":"=r"(fpcr));if(fpcr)return fail("FPCR-nonzero");
 void*code=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);uint64_t*near=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);uint64_t*far=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);uint64_t*out=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(code==MAP_FAILED||near==MAP_FAILED||far==MAP_FAILED||out==MAP_FAILED)return fail("owned-mappings");
 for(unsigned j=0;j<8;++j)near[j*8]=0x12345678;prepare(near,far,out);memcpy(code,programs[0].words,4*programs[0].pos);
 int pm=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);if(pm<0)return fail("pagemap");struct perf p;if(!open_perf(&p))return fail("six-PMU-unavailable");uint64_t pages[4],after[4];uintptr_t addr[4]={(uintptr_t)code,(uintptr_t)near,(uintptr_t)far,(uintptr_t)out};for(unsigned j=0;j<4;++j)if(one_page(pm,addr[j],pages+j))return fail("initial-pagemap");
 printf("{\"type\":\"runtime\",\"cpu\":7,\"fpcr\":0,\"hwcap_sb\":true,\"code_base\":%"PRIuPTR",\"near_base\":%"PRIuPTR",\"far_base\":%"PRIuPTR",\"output_base\":%"PRIuPTR",\"pagemap_before\":[",addr[0],addr[1],addr[2],addr[3]);for(unsigned j=0;j<4;++j)printf("%s%"PRIu64,j?",":"",pages[j]);printf("],\"event_ids\":[");for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",p.ids[j]);puts("]}");marker_routine_t routine=(marker_routine_t)code;
 for(unsigned t=0;t<32;++t)for(unsigned pos=0;pos<8;++pos){unsigned i=member(t,pos),control=i/4,taps=i%2,mode=i%4;struct code*c=&programs[mode];if(mprotect(code,4096,PROT_READ|PROT_WRITE))return fail("code-RW");memcpy(code,c->words,4*c->pos);__builtin___clear_cache(code,(char*)code+4*c->pos);if(mprotect(code,4096,PROT_READ|PROT_EXEC))return fail("code-RX");__asm__ volatile("msr fpsr,xzr");
  for(unsigned warm=0;warm<64;++warm){prepare(near,far,out);uint64_t result=routine(train_bits(control),(uintptr_t)near,(uintptr_t)far,(uintptr_t)out,0x12345678);if(!originals(result,train_bits(control),out,far,taps))return fail("training-originals");}if(memcmp(code,c->words,4*c->pos))return fail("code-drift");
  struct pg_sample delta;uint64_t result;const char*e;for(unsigned warm=0;warm<4;++warm){prepare(near,far,out);result=routine(train_bits(control),(uintptr_t)near,(uintptr_t)far,(uintptr_t)out,0x12345678);if(!originals(result,train_bits(control),out,far,taps))return fail("wrapper-warmup-originals");}
  prepare(near,far,out);if((e=measure_frame(&p,routine,test_bits(control),near,far,out,&delta,&result)))return fail(e);if(sched_getcpu()!=7||!originals(result,test_bits(control),out,far,taps))return fail("measured-originals-CPU");
  printf("{\"type\":\"round\",\"trial\":%u,\"position\":%u,\"control\":\"%s\",\"marker\":\"%s\",\"fence\":\"%s\",\"train_bits\":%"PRIu64",\"test_bits\":%"PRIu64",\"result_bits\":%"PRIu64",\"status_raw\":%"PRIu64",\"near_architectural\":%"PRIu64",\"far_architectural_words\":[",t,pos,controls[control],taps?"taps":"nop",mode<2?"pre":"post",train_bits(control),test_bits(control),result,out[0],out[1]);for(unsigned j=0;j<8;++j)printf("%s%"PRIu64,j?",":"",far[j*8]);printf("],\"code_base\":%"PRIuPTR",\"code_matches_plan\":true,\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"counts\":[",addr[0],delta.enabled,delta.running);for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",delta.values[j]);putchar(']');printf(",\"roi_before\":");roi_array(trace.before);printf(",\"roi_after\":");roi_array(trace.after);printf(",\"kernel_before\":");value_array(trace.kernel_before.values);printf(",\"kernel_after\":");value_array(trace.kernel_after.values);printf(",\"fd_counts\":");value_array(trace.delta.values);puts("}");if(fflush(stdout))return fail("output-write");
 }
 for(unsigned j=0;j<4;++j)if(one_page(pm,addr[j],after+j))return fail("final-pagemap");for(unsigned j=0;j<6;++j){munmap(p.page[j],4096);close(p.fd[j]);}close(pm);printf("{\"type\":\"final\",\"pagemap_after\":[");for(unsigned j=0;j<4;++j)printf("%s%"PRIu64,j?",":"",after[j]);puts("],\"fds_closed\":true}");munmap(code,4096);munmap(near,4096);munmap(far,4096);munmap(out,4096);return 0;
#endif
}
