/* SPDX-License-Identifier: Apache-2.0
 * Own near load/far store issue markers; delayed branch and growing filler gap.
 * docs/design/2026-10-14-rob-admission-window.md. Never reads another address space.
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
static unsigned gap_length,filler_kind;
static struct code payload_build(uint32_t*words,unsigned chain,unsigned mode){unsigned taps=mode%2,pre=mode<2;
 struct code c={.words=words,.cap=1024};emit(&c,0xaa1f03e9u);emit(&c,0x9e670000u);emit(&c,0xaa0403e6u);
 for(unsigned j=0;j<chain;++j)emit(&c,0x1e61c000u);
 emit(&c,0x9e66000cu);emit(&c,0xb500000cu|((19+gap_length)<<5));emit(&c,pre?0xd50330ffu:NOP);
 for(unsigned j=0;j<8;++j)emit(&c,taps?(0xf9400029u+((j*8u)<<10)):NOP);
 const uint32_t filler[]={0x8b02003fu,0xd280000au,NOP};for(unsigned j=0;j<gap_length;j++)emit(&c,filler[filler_kind]);
 for(unsigned j=0;j<8;++j)emit(&c,taps?(0xf9000046u+((j*8u)<<10)):NOP);
 emit(&c,pre?NOP:0xd50330ffu);
 const uint32_t tail[]={0xd50330ffu,0x9e660000u,0xd53b442cu,0xf900006cu,0xf9000469u,RET};
 for(unsigned j=0;j<6;++j)emit(&c,tail[j]);return c;
}
static unsigned counter_indices[6];
static void counter_words(struct code*c,unsigned index,unsigned reg){
 emit(c,index==32?NOP:(0xd280000bu|((index-1)<<5)));emit(c,index==32?NOP:0xd51b9cabu);emit(c,0xd5033fdfu);emit(c,(index==32?0xd53b9d00u:0xd53b9d40u)|reg);
}
static struct code register_build(uint32_t*words,unsigned chain,unsigned mode){
 uint32_t body[1024];struct code b=payload_build(body,chain,mode),c={.words=words,.cap=1024};const uint32_t save[]={0xa9bc53f3,0xa9015bf5,0xa90263f7,0xa9036bf9,0xd5033b9f};for(unsigned j=0;j<5;j++)emit(&c,save[j]);for(unsigned j=0;j<6;j++)counter_words(&c,counter_indices[j],20+j);emit(&c,0xd50330ffu);for(size_t j=0;j+1<b.pos;j++)emit(&c,b.words[j]);const unsigned after[]={13,14,15,16,17,19};for(unsigned j=0;j<6;j++)counter_words(&c,counter_indices[j],after[j]);const uint32_t tail[]={0xd50330ffu,0xa90054b4,0xa9015cb6,0xa90264b8,0xa90338ad,0xa90440af,0xa9054cb1,0xa9436bf9,0xa94263f7,0xa9415bf5,0xa8c453f3,RET};for(unsigned j=0;j<12;j++)emit(&c,tail[j]);return c;
}
static struct code warm_build(uint32_t*words,const struct code*c){struct code w={.words=words,.pos=c->pos,.cap=1024};memcpy(words,c->words,4*c->pos);for(unsigned j=5;j<29;j++)words[j]=NOP;size_t suffix=c->pos-36;for(size_t j=suffix;j<suffix+24;j++)words[j]=NOP;for(size_t j=suffix+25;j<suffix+31;j++)words[j]=NOP;return w;}
static bool parse_indices(const char*text){char extra;if(sscanf(text,"%u,%u,%u,%u,%u,%u%c",counter_indices,counter_indices+1,counter_indices+2,counter_indices+3,counter_indices+4,counter_indices+5,&extra)!=6)return false;for(unsigned j=0;j<6;j++){if(counter_indices[j]<1||counter_indices[j]>32)return false;for(unsigned k=0;k<j;k++)if(counter_indices[j]==counter_indices[k])return false;}return true;}
static void index_array(void){putchar('[');for(unsigned j=0;j<6;j++)printf("%s%u",j?",":"",counter_indices[j]);putchar(']');}
static void export_program(const struct code*c,const struct code*w,unsigned mode){unsigned taps=mode%2;printf("{\"type\":\"program\",\"marker\":\"%s\",\"fence\":\"%s\",\"code_bytes\":%zu,\"words\":[",taps?"taps":"nop",mode<2?"pre":"post",4*c->pos);for(size_t j=0;j<c->pos;++j)printf("%s%"PRIu32,j?",":"",c->words[j]);printf("],\"counter_indices\":");index_array();printf(",\"warm_words\":[");for(size_t j=0;j<w->pos;j++)printf("%s%"PRIu32,j?",":"",w->words[j]);puts("]}");}
static void schedule(unsigned t,unsigned pos){unsigned i=member(t,pos),control=i/4,taps=i%2,mode=i%4;printf("{\"type\":\"schedule\",\"trial\":%u,\"position\":%u,\"control\":\"%s\",\"marker\":\"%s\",\"fence\":\"%s\",\"train_bits\":%"PRIu64",\"test_bits\":%"PRIu64"}\n",t,pos,controls[control],taps?"taps":"nop",mode<2?"pre":"post",train_bits(control),test_bits(control));}
#if defined(__linux__) && defined(__aarch64__)
struct perf{int fd[6];uint64_t ids[6];struct perf_event_mmap_page*page[6];};
struct roi_value{struct pu_metadata meta;uint64_t hardware,total;unsigned attempted;};
static struct {struct roi_value before[6],after[6];struct pg_sample kernel_before,kernel_after,delta;} trace;
static sigjmp_buf counter_trap;static volatile sig_atomic_t counter_armed;
static void counter_sigill(int sig){if(counter_armed){counter_armed=0;siglongjmp(counter_trap,1);} _exit(128+sig);}
static void value_array(const uint64_t*v){putchar('[');for(unsigned j=0;j<6;j++)printf("%s%"PRIu64,j?",":"",v[j]);putchar(']');}
static void roi_array(const struct roi_value*v){putchar('[');for(unsigned j=0;j<6;j++)printf("%s{\"sequence_before\":%u,\"sequence_after\":%u,\"index\":%u,\"width\":%u,\"cap\":%s,\"offset\":%"PRIu64",\"hardware\":%"PRIu64",\"total\":%"PRIu64"}",j?",":"",v[j].meta.first,v[j].meta.last,v[j].meta.index,v[j].meta.width,v[j].meta.cap?"true":"false",v[j].meta.offset,v[j].hardware,v[j].total);putchar(']');}
/* Metadata-only checks outside register ROI; actual reads are generated words. */
static const char*binding(struct perf*p,struct roi_value*out,bool fixed){
 for(unsigned j=0;j<6;j++){struct perf_event_mmap_page*q=p->page[j];struct pu_metadata*m=&out[j].meta;out[j].attempted=1;m->first=__atomic_load_n(&q->lock,__ATOMIC_ACQUIRE);__asm__ volatile("dmb ishld":::"memory");m->index=q->index;m->width=q->pmc_width;m->cap=q->cap_user_rdpmc;m->offset=q->offset;__asm__ volatile("dmb ishld":::"memory");m->last=__atomic_load_n(&q->lock,__ATOMIC_ACQUIRE);const char*e=pu_guard(1,m);if(e)return e;if(fixed&&m->index!=counter_indices[j])return "own-index-changed";for(unsigned k=0;k<j;k++)if(m->index==out[k].meta.index)return "duplicate-own-index";}return NULL;
}
static void binding_array(const struct roi_value*v){putchar('[');for(unsigned j=0;j<6;j++){if(j)putchar(',');if(!v[j].attempted){printf("null");continue;}printf("{\"sequence_before\":%u,\"sequence_after\":%u,\"index\":%u,\"width\":%u,\"cap\":%s,\"offset\":%"PRIu64"}",v[j].meta.first,v[j].meta.last,v[j].meta.index,v[j].meta.width,v[j].meta.cap?"true":"false",v[j].meta.offset);}putchar(']');}
static bool open_perf(struct perf*p){const uint64_t events[]={17,8,112,113,34,1};for(unsigned j=0;j<6;++j){p->fd[j]=-1;p->page[j]=MAP_FAILED;}for(unsigned j=0;j<6;++j){struct perf_event_attr a={0};a.size=sizeof(a);a.type=8;a.config=events[j];a.config1=3;a.disabled=j==0;a.pinned=j==0;a.exclude_kernel=1;a.exclude_hv=1;a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING|PERF_FORMAT_ID;p->fd[j]=(int)syscall(SYS_perf_event_open,&a,0,-1,j?p->fd[0]:-1,0);if(p->fd[j]<0||ioctl(p->fd[j],PERF_EVENT_IOC_ID,&p->ids[j])){fprintf(stderr,"perf-open-id index=%u event=%"PRIu64" errno=%d\n",j,events[j],errno);return false;}p->page[j]=mmap(NULL,4096,PROT_READ,MAP_SHARED,p->fd[j],0);if(p->page[j]==MAP_FAILED)return false;}return true;}
static const char*snapshot(struct perf*p,struct pg_sample*s){uint64_t wire[15];ssize_t bytes=read(p->fd[0],wire,sizeof(wire));if(bytes<=0||bytes%8)return "perf-read";return pg_decode(wire,(size_t)bytes/8,p->ids,6,s);}
typedef uint64_t(*marker_routine_t)(uint64_t,uintptr_t,uintptr_t,uintptr_t,uint64_t,uintptr_t);
/* Owned direct ROI, FD envelope and live metadata are separate boundaries. */
static const char*measure_frame(struct perf*p,marker_routine_t routine,uint64_t bits,uint64_t*near,uint64_t*far,uint64_t*out,struct pg_sample*delta,uint64_t*result){
 const char*e=NULL;unsigned completed=0;memset(&trace,0,sizeof(trace));
 if((e=snapshot(p,&trace.kernel_before))||(e=binding(p,trace.before,true)))goto rejected;
 __asm__ volatile("dsb ish\n isb":::"memory");if(sigsetjmp(counter_trap,0)){e="register-ROI-sigill";goto rejected;}counter_armed=1;*result=routine(bits,(uintptr_t)near,(uintptr_t)far,(uintptr_t)out,0x12345678,(uintptr_t)(out+8));counter_armed=0;completed=1;__asm__ volatile("dsb ish\n isb":::"memory");
 if((e=binding(p,trace.after,true)))goto rejected;for(unsigned j=0;j<6;j++){trace.before[j].hardware=out[8+j];trace.after[j].hardware=out[14+j];trace.before[j].total=pu_total(trace.before[j].meta.offset,trace.before[j].hardware);trace.after[j].total=pu_total(trace.after[j].meta.offset,trace.after[j].hardware);}
 for(unsigned j=0;j<6;j++)if(trace.before[j].meta.first!=trace.after[j].meta.first||trace.before[j].meta.index!=trace.after[j].meta.index||trace.before[j].meta.offset!=trace.after[j].meta.offset){e="ROI-metadata-changed";goto rejected;}
 if((e=snapshot(p,&trace.kernel_after))||(e=pg_delta(&trace.kernel_before,&trace.kernel_after,6,&trace.delta)))goto rejected;
 *delta=trace.delta;for(unsigned j=0;j<6;j++){delta->values[j]=pu_delta(trace.before[j].total,trace.after[j].total);if(trace.before[j].total<trace.kernel_before.values[j]||trace.after[j].total>trace.kernel_after.values[j]||delta->values[j]>trace.delta.values[j]){e="ROI-FD-envelope";goto rejected;}}
 return NULL;
 rejected:
 counter_armed=0;ioctl(p->fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP);printf("{\"type\":\"rejected-window\",\"metrics\":{},\"reason\":\"%s\",\"hardware_values_usable\":false,\"roi_before_metadata\":",e);binding_array(trace.before);printf(",\"roi_after_metadata\":");binding_array(trace.after);printf(",\"captured_register_words\":");if(completed){putchar('[');for(unsigned j=0;j<12;j++)printf("%s%"PRIu64,j?",":"",out[8+j]);putchar(']');}else printf("null");puts("}");return e;
}
static int one_page(int fd,uintptr_t va,uint64_t*out){return pread(fd,out,8,(off_t)(va/4096*8))==8?0:-1;}
static bool originals(uint64_t result,uint64_t bits,uint64_t*out,uint64_t*far,unsigned taps){unsigned active=taps&&!bits;if(result!=bits||out[0]||out[1]!=(active?0x12345678u:0))return false;for(unsigned j=0;j<8;++j)if(far[j*8]!=(active?0x12345678u:0))return false;return true;}
static void prepare(uint64_t*near,uint64_t*far,uint64_t*out){volatile uint64_t hot=0;for(unsigned j=0;j<8;++j){hot^=((volatile uint64_t*)near)[j*8];far[j*8]=0;}out[0]=out[1]=0;(void)hot;__asm__ volatile("dsb ish":::"memory");}
#endif
int main(int argc,char**argv){
 bool planned=argc==10&&!strcmp(argv[1],"--plan");bool running=argc==8&&!strcmp(argv[1],"--run");if((!planned&&!running)||strcmp(argv[2],"--chain")||(strcmp(argv[3],"16")&&strcmp(argv[3],"32"))||strcmp(argv[4],"--gap")||strcmp(argv[6],"--filler")||(strcmp(argv[7],"sink")&&strcmp(argv[7],"zero")&&strcmp(argv[7],"nop"))||(planned&&(strcmp(argv[8],"--indices")||!parse_indices(argv[9]))))return fail("usage-admission-plan-or-run-no-index-override");unsigned chain=(unsigned)atoi(argv[3]);char*end=NULL;unsigned long gap=strtoul(argv[5],&end,10);if(!*argv[5]||*end||gap>768||gap%128)return fail("unregistered-gap");gap_length=(unsigned)gap;filler_kind=!strcmp(argv[7],"sink")?0:!strcmp(argv[7],"zero")?1:2;
 printf("{\"type\":\"config\",\"version\":3,\"probe\":\"rob-admission-window\",\"chain\":%u,\"groups\":0,\"gap\":%u,\"filler\":\"%s\",\"trials\":32,\"windows\":256,\"training_calls\":64,\"routine_warmup_calls\":4,\"count_source\":\"owned-register-only-roi\",\"perf_config1\":3,\"events\":[17,8,112,113,34,1],\"pmu_type\":8,\"schedule_reverse_block_trials\":8}\n",chain,gap_length,argv[7]);
#if defined(__linux__) && defined(__aarch64__)
 struct perf p;struct roi_value initial_binding[6]={0};
 if(running){
 if(sysconf(_SC_PAGESIZE)!=4096)return fail("page-size");if(!(getauxval(AT_HWCAP)&HWCAP_SB))return fail("SB-unavailable");cpu_set_t mask;CPU_ZERO(&mask);CPU_SET(7,&mask);if(sched_setaffinity(0,sizeof(mask),&mask)||sched_getcpu()!=7)return fail("affinity");FILE*policy=fopen("/proc/sys/kernel/perf_user_access","r");if(!policy)return fail("user-profile-read");int actual=-1,parsed=fscanf(policy,"%d",&actual);fclose(policy);if(parsed!=1||actual!=1)return fail("user-profile-disabled");struct sigaction act={0};act.sa_handler=counter_sigill;sigemptyset(&act.sa_mask);if(sigaction(SIGILL,&act,NULL))return fail("SIGILL-guard");uint64_t fpcr;__asm__ volatile("mrs %0,fpcr":"=r"(fpcr));if(fpcr)return fail("FPCR-nonzero");
 if(!open_perf(&p))return fail("six-PMU-unavailable");if(ioctl(p.fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))return fail("perf-enable");const char*e=binding(&p,initial_binding,false);if(e)return fail(e);for(unsigned j=0;j<6;j++)counter_indices[j]=initial_binding[j].meta.index;
 }
#else
 if(running)return fail("requires-linux-aarch64");
#endif
 uint32_t words[4][1024],warm_words[4][1024];struct code programs[4],warm_programs[4];for(unsigned j=0;j<4;j++){programs[j]=register_build(words[j],chain,j);warm_programs[j]=warm_build(warm_words[j],programs+j);export_program(programs+j,warm_programs+j,j);}if(planned){for(unsigned t=0;t<32;t++)for(unsigned pos=0;pos<8;pos++)schedule(t,pos);return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
 return fail("requires-linux-aarch64");
#else
 void*code=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);uint64_t*near=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);uint64_t*far=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);uint64_t*out=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(code==MAP_FAILED||near==MAP_FAILED||far==MAP_FAILED||out==MAP_FAILED)return fail("owned-mappings");
 for(unsigned j=0;j<8;++j)near[j*8]=0x12345678;prepare(near,far,out);memcpy(code,programs[0].words,4*programs[0].pos);
 int pm=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);if(pm<0)return fail("pagemap");uint64_t pages[4],after[4];uintptr_t addr[4]={(uintptr_t)code,(uintptr_t)near,(uintptr_t)far,(uintptr_t)out};for(unsigned j=0;j<4;++j)if(one_page(pm,addr[j],pages+j))return fail("initial-pagemap");
 printf("{\"type\":\"runtime\",\"cpu\":7,\"fpcr\":0,\"hwcap_sb\":true,\"code_base\":%"PRIuPTR",\"near_base\":%"PRIuPTR",\"far_base\":%"PRIuPTR",\"output_base\":%"PRIuPTR",\"pagemap_before\":[",addr[0],addr[1],addr[2],addr[3]);for(unsigned j=0;j<4;++j)printf("%s%"PRIu64,j?",":"",pages[j]);printf("],\"counter_indices\":");index_array();printf(",\"initial_binding\":");binding_array(initial_binding);printf(",\"hardware_buffer_base\":%"PRIuPTR",\"event_ids\":[",(uintptr_t)(out+8));for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",p.ids[j]);puts("]}");marker_routine_t routine=(marker_routine_t)code;
 for(unsigned t=0;t<32;++t)for(unsigned pos=0;pos<8;++pos){unsigned i=member(t,pos),control=i/4,taps=i%2,mode=i%4;struct code*c=&programs[mode];if(mprotect(code,4096,PROT_READ|PROT_WRITE))return fail("code-RW");memcpy(code,warm_programs[mode].words,4*c->pos);__builtin___clear_cache(code,(char*)code+4*c->pos);if(mprotect(code,4096,PROT_READ|PROT_EXEC))return fail("code-RX");__asm__ volatile("msr fpsr,xzr");
  for(unsigned warm=0;warm<64;++warm){prepare(near,far,out);uint64_t result=routine(train_bits(control),(uintptr_t)near,(uintptr_t)far,(uintptr_t)out,0x12345678,(uintptr_t)(out+8));if(!originals(result,train_bits(control),out,far,taps))return fail("training-originals");}if(memcmp(code,warm_programs[mode].words,4*c->pos))return fail("warm-code-drift");
  struct pg_sample delta;uint64_t result;const char*e;for(unsigned warm=0;warm<4;++warm){prepare(near,far,out);result=routine(train_bits(control),(uintptr_t)near,(uintptr_t)far,(uintptr_t)out,0x12345678,(uintptr_t)(out+8));if(!originals(result,train_bits(control),out,far,taps))return fail("wrapper-warmup-originals");}
  if(mprotect(code,4096,PROT_READ|PROT_WRITE))return fail("measured-code-RW");size_t suffix=c->pos-36;memcpy((uint32_t*)code+5,c->words+5,24*4);memcpy((uint32_t*)code+suffix,c->words+suffix,31*4);__builtin___clear_cache((char*)code+20,(char*)code+116);__builtin___clear_cache((char*)code+4*suffix,(char*)code+4*(suffix+31));if(mprotect(code,4096,PROT_READ|PROT_EXEC))return fail("measured-code-RX");if(memcmp(code,c->words,4*c->pos))return fail("actual-code-drift");
  prepare(near,far,out);if((e=measure_frame(&p,routine,test_bits(control),near,far,out,&delta,&result)))return fail(e);if(sched_getcpu()!=7||!originals(result,test_bits(control),out,far,taps))return fail("measured-originals-CPU");
  printf("{\"type\":\"round\",\"trial\":%u,\"position\":%u,\"control\":\"%s\",\"marker\":\"%s\",\"fence\":\"%s\",\"train_bits\":%"PRIu64",\"test_bits\":%"PRIu64",\"result_bits\":%"PRIu64",\"status_raw\":%"PRIu64",\"near_architectural\":%"PRIu64",\"far_architectural_words\":[",t,pos,controls[control],taps?"taps":"nop",mode<2?"pre":"post",train_bits(control),test_bits(control),result,out[0],out[1]);for(unsigned j=0;j<8;++j)printf("%s%"PRIu64,j?",":"",far[j*8]);printf("],\"code_base\":%"PRIuPTR",\"code_matches_plan\":true,\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"counts\":[",addr[0],delta.enabled,delta.running);for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",delta.values[j]);putchar(']');printf(",\"roi_before\":");roi_array(trace.before);printf(",\"roi_after\":");roi_array(trace.after);printf(",\"kernel_before\":");value_array(trace.kernel_before.values);printf(",\"kernel_after\":");value_array(trace.kernel_after.values);printf(",\"fd_counts\":");value_array(trace.delta.values);puts("}");if(fflush(stdout))return fail("output-write");
 }
 for(unsigned j=0;j<4;++j)if(one_page(pm,addr[j],after+j))return fail("final-pagemap");ioctl(p.fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP);for(unsigned j=0;j<6;++j){munmap(p.page[j],4096);close(p.fd[j]);}close(pm);printf("{\"type\":\"final\",\"pagemap_after\":[");for(unsigned j=0;j<4;++j)printf("%s%"PRIu64,j?",":"",after[j]);puts("],\"fds_closed\":true}");munmap(code,4096);munmap(near,4096);munmap(far,4096);munmap(out,4096);return 0;
#endif
}
