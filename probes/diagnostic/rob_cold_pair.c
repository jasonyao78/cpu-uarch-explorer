/* SPDX-License-Identifier: Apache-2.0
 * Single-shot dual-line mechanism, never a physical ROB-entry counter.
 * Contract: docs/design/2026-10-09-cold-pair-qualification.md.
 * Internal CNTVCT time is distinct from whole user PMU wrapper counts.
 * All cache maintenance is on this process's own two nodes, outside the window.
 * Host builds export real generated code/map tests; Linux AArch64 measures.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <getopt.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <sys/mman.h>
#include "perf_group_read.h"
#include "rob_backing.h"
#if defined(__linux__) && defined(__aarch64__)
#include <linux/perf_event.h>
#include <sched.h>
#include <setjmp.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#endif

#define NOP UINT32_C(0xd503201f)
#define DSB UINT32_C(0xd5033f9f)
#define ISB UINT32_C(0xd5033fdf)
enum member { P, S, E };
static const char *const names[]={"P","S","E"};
struct pair_mapping { char *reservation,*data; size_t reserved; };
struct cell { unsigned mask,swap; enum member member; bool cold; };

/* Own PROT_NONE guards prevent a neighboring VMA from merging the data range. */
static bool map_pair(struct pair_mapping *p) {
    long page=sysconf(_SC_PAGESIZE); if(page<=0)return false;
    p->reserved=6*(size_t)page;
    p->reservation=mmap(NULL,p->reserved,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(p->reservation==MAP_FAILED) return false;
    uintptr_t address=((uintptr_t)p->reservation+(size_t)page+8191)&~(uintptr_t)8191;
    p->data=(char *)address;
    if(mprotect(p->data,(size_t)page>8192?(size_t)page:8192,PROT_READ|PROT_WRITE))return false;
#ifdef __linux__
    if(madvise(p->data,8192,MADV_NOHUGEPAGE))return false;
#endif
    return true;
}
/* Includes both link checks. mask4096 must be raw self pointers, not a label. */
static bool fill_pair(const struct pair_mapping *p,unsigned mask) {
    uintptr_t a=(uintptr_t)p->data,b=a+4096;
    *(uintptr_t *)a=b^mask; *(uintptr_t *)b=a^mask;
    if((*(uintptr_t *)a^mask)!=b || (*(uintptr_t *)b^mask)!=a) return false;
    return !mask || (*(uintptr_t *)a==a && *(uintptr_t *)b==b);
}
/* Left rotation then optional reversal: same function drives every actual call. */
static struct cell cell_at(unsigned epoch,unsigned trial,unsigned position) {
    unsigned j=((trial+epoch)%2 ? 23-position : position);
    j=(j+trial%24)%24;
    struct cell c={.mask=(j/12)*4096,.swap=(j/6)%2,.member=(enum member)((j/2)%3),.cold=j%2!=0};
    return c;
}
/* x0/x1=actual node heads; x12 mask; x13/14 clocks. Only caller-saved regs. */
static size_t build(uint32_t *buf,size_t capacity,unsigned n,unsigned mask,enum member member) {
    size_t words=29+2*(size_t)n; if(words>capacity) return 0;
    size_t p=0;buf[p++]=UINT32_C(0xd280000c)|(mask<<5);
    buf[p++]=UINT32_C(0xf2a0000c);buf[p++]=UINT32_C(0xf2c0000c);buf[p++]=UINT32_C(0xf2e0000c);
    while(p<16)buf[p++]=NOP;
    buf[p++]=DSB;buf[p++]=ISB;buf[p++]=UINT32_C(0xd53be04d);buf[p++]=ISB;
    for(unsigned side=0;side<2;++side){
        unsigned r=member==S?0:side;
        buf[p++]=member==E?NOP:(UINT32_C(0xf9400000)|(r<<5)|r);
        buf[p++]=member==E?NOP:(UINT32_C(0xca0c0000)|(r<<5)|r);
        for(unsigned j=0;j<n;++j)buf[p++]=NOP;
    }
    buf[p++]=DSB;buf[p++]=ISB;buf[p++]=UINT32_C(0xd53be04e);
    buf[p++]=UINT32_C(0xcb0d01c0);buf[p++]=UINT32_C(0xd65f03c0);
    return p==words?p:0;
}
static int failure(const char *why) {
    fprintf(stderr,"error[%s]: %s\n",why,strerror(errno));
    printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",why);
    return 1;
}
static unsigned number(const char *s,unsigned lo,unsigned hi){
    char *end;errno=0;if(!s || !*s || *s=='-')exit(2);
    unsigned long v=strtoul(s,&end,0);if(errno || *end || v<lo || v>hi)exit(2);return (unsigned)v;
}
static void config(unsigned n,unsigned epoch,int pin,unsigned type,const char *dump,unsigned mask,enum member member){
    printf("{\"type\":\"config\",\"version\":1,\"probe\":\"rob-cold-pair\",\"n\":%u,\"trials\":64,\"epoch\":%u,"
      "\"matrix_cells_per_trial\":24,\"windows\":1536,\"memory_bytes\":8192,\"mapping_alignment\":8192,"
      "\"node_offsets\":[0,4096],\"masks\":[0,4096],\"members\":[\"P\",\"S\",\"E\"],\"states\":[\"hot\",\"cold\"],"
      "\"warmup_calls\":128,\"internal_clock\":\"cntvct_el0\",\"code_bytes\":%u,\"kernel_instructions\":%u,"
      "\"pin\":%d,\"pmu_type\":%u,\"events\":[17,8,3,23,52,55],\"exclude_kernel\":true,\"exclude_hv\":true,"
      "\"backing_requested\":\"4k\"",n,epoch,4*(29+2*n),29+2*n,pin,type);
    if(dump)printf(",\"export\":{\"mask\":%u,\"member\":\"%s\"}",mask,names[member]);puts("}");
}
#if defined(__linux__) && defined(__aarch64__)
struct perf { int fd[6];uint64_t ids[6]; };
static const uint64_t events[]={17,8,3,23,52,55};
static bool perf_open(struct perf *p,unsigned type){
    for(size_t j=0;j<6;++j){
        struct perf_event_attr a;memset(&a,0,sizeof(a));a.size=sizeof(a);a.type=type;a.config=events[j];
        a.disabled=j==0;a.pinned=j==0;a.exclude_kernel=1;a.exclude_hv=1;
        a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING|PERF_FORMAT_ID;
        p->fd[j]=(int)syscall(SYS_perf_event_open,&a,0,-1,j?p->fd[0]:-1,0);
        if(p->fd[j]<0 || ioctl(p->fd[j],PERF_EVENT_IOC_ID,&p->ids[j]))return false;
    }return true;
}
static const char *snapshot(const struct perf *p,struct pg_sample *s){
    uint64_t wire[15];ssize_t len=read(p->fd[0],wire,sizeof(wire));
    if(len<=0 || len%8)return "group-read-failed";
    return pg_decode(wire,(size_t)len/8,p->ids,6,s);
}
static bool backing(const struct pair_mapping *p,struct rob_backing_info *info){
    FILE *f=fopen("/proc/self/smaps","r");enum rob_backing_status status=rob_backing_inspect(f,(uintptr_t)p->data,8192,false,0,info);
    if(f && fclose(f))return false;return status==ROB_BACKING_VERIFIED;
}
static void barrier(void){__asm__ volatile("dsb sy":::"memory");}
static void flush_pair(uintptr_t a,uintptr_t b){__asm__ volatile("dc civac,%0\n\tdc civac,%1\n\tdsb sy"::"r"(a),"r"(b):"memory");}
static sigjmp_buf capability_jump;static volatile sig_atomic_t checking;
static void signal_failure(int sig){
    if(checking)siglongjmp(capability_jump,sig);
    static const char message[]="{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"measurement-signal\"}}\n";
    (void)write(STDOUT_FILENO,message,sizeof(message)-1);_exit(128+sig);
}
typedef uint64_t (*routine_t)(uintptr_t,uintptr_t);
static volatile uint64_t sink;
/* This establishes availability/completion, not native-vs-emulated DC semantics. */
static bool capabilities(uintptr_t a,uintptr_t b,routine_t fn,uint64_t *freq,size_t *line){
    struct sigaction action;memset(&action,0,sizeof(action));action.sa_handler=signal_failure;sigemptyset(&action.sa_mask);
    if(sigaction(SIGILL,&action,NULL) || sigaction(SIGSEGV,&action,NULL) || sigaction(SIGBUS,&action,NULL))return false;
    checking=1;if(sigsetjmp(capability_jump,1)){checking=0;return false;}
    uint64_t ctr,t0,t1;__asm__ volatile("mrs %0,cntfrq_el0\n\tmrs %1,ctr_el0\n\tisb\n\tmrs %2,cntvct_el0":"=r"(*freq),"=r"(ctr),"=r"(t0)::"memory");
    *line=(size_t)4<<((ctr>>16)&15);flush_pair(a,b);
    for(unsigned i=0;i<128;++i)sink=fn(a,b);
    __asm__ volatile("isb\n\tmrs %0,cntvct_el0":"=r"(t1)::"memory");checking=0;
    return *freq>0 && *freq<=UINT64_C(1000000000) && *line==64 && t1>t0;
}
#endif
int main(int argc,char **argv){
    unsigned n=0,epoch=0,mask=0,type=0;enum member member=P;int pin=-1;const char *dump=NULL;bool member_set=false,mask_set=false;
    static const struct option opts[]={{"epoch",1,0,1},{"trials",1,0,2},{"pin",1,0,3},{"pmu-type",1,0,4},
      {"mask",1,0,5},{"member",1,0,6},{"write-asm",1,0,7},{0,0,0,0}};int ch;
    while((ch=getopt_long(argc,argv,"n:",opts,NULL))!=-1){
        switch(ch){
        case 'n':n=number(optarg,0,4096);break;case 1:epoch=number(optarg,0,1);break;
        case 2:if(number(optarg,64,64)!=64)return 2;break;case 3:pin=(int)number(optarg,0,1023);break;
        case 4:type=number(optarg,1,UINT32_MAX);break;
        case 5:mask=number(optarg,0,4096);if(mask!=0 && mask!=4096)return 2;mask_set=true;break;
        case 6:member_set=true;{bool ok=false;for(unsigned i=0;i<3;++i)if(!strcmp(optarg,names[i])){member=(enum member)i;ok=true;}if(!ok)return 2;}break;
        case 7:dump=optarg;break;default:return 2;
        }
    }
    if(optind!=argc || (!dump && (member_set || mask_set)))return 2;
    config(n,epoch,pin,type,dump,mask,member);
    if(dump){
        uint32_t buf[8221];size_t words=build(buf,8221,n,mask,member);if(!words)return failure("code-capacity");
        FILE *f=fopen(dump,"wb");if(!f)return failure("code-export-open");bool ok=fwrite(buf,4,words,f)==words;if(fclose(f))ok=false;return ok?0:failure("code-export-write");
    }
#if !defined(__linux__) || !defined(__aarch64__)
    (void)map_pair;(void)fill_pair;(void)cell_at;return failure("measurement-requires-linux-aarch64");
#else
    if(n || pin<0 || !type || sysconf(_SC_PAGESIZE)!=4096)return failure("qualification-requires-n0-pin-type-4k");
    cpu_set_t affinity;CPU_ZERO(&affinity);CPU_SET(pin,&affinity);
    if(sched_setaffinity(0,sizeof(affinity),&affinity) || sched_getcpu()!=pin)return failure("affinity");
    struct pair_mapping data={0};if(!map_pair(&data) || !fill_pair(&data,0))return failure("node-mapping-or-graph");
    struct rob_backing_info before={0},after={0};if(!backing(&data,&before))return failure("initial-backing");
    uint32_t *codes[2][3];routine_t routines[2][3];
    for(unsigned m=0;m<2;++m)for(unsigned j=0;j<3;++j){
        codes[m][j]=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        if(codes[m][j]==MAP_FAILED || build(codes[m][j],1024,0,m*4096,(enum member)j)!=29)return failure("code-mapping");
        __builtin___clear_cache((char *)codes[m][j],(char *)(codes[m][j]+29));
        if(mprotect(codes[m][j],4096,PROT_READ|PROT_EXEC))return failure("code-w-to-x");
        routines[m][j]=(routine_t)(void *)codes[m][j];
    }
    uintptr_t a=(uintptr_t)data.data,b=a+4096;uint64_t freq=0;size_t line=0;
    if(!capabilities(a,b,routines[0][P],&freq,&line))return failure("clock-or-cache-maintenance-capability");
    if(!fill_pair(&data,4096))return failure("self-pointer-geometry");
    struct perf perf;if(!perf_open(&perf,type))return failure("perf-open-or-id");
    printf("{\"type\":\"runtime\",\"cpu\":%d,\"cntfrq_hz\":%"PRIu64",\"cache_line_bytes\":%zu,"
      "\"mapping_alignment_verified\":true,\"raw_self_pointer_verified\":true,\"code_address_mod64\":0,"
      "\"cache_maintenance_completed\":true,\"initial_backing\":",sched_getcpu(),freq,line);
    rob_backing_json(stdout,&before);fputs(",\"event_ids\":[",stdout);for(unsigned j=0;j<6;++j)printf("%s%"PRIu64,j?",":"",perf.ids[j]);puts("]}");
    for(unsigned trial=0;trial<64;++trial)for(unsigned pos=0;pos<24;++pos){
        struct cell c=cell_at(epoch,trial,pos);if(!fill_pair(&data,c.mask))return failure("round-graph");
        uintptr_t head0=c.swap?b:a,head1=c.swap?a:b;routine_t fn=routines[c.mask/4096][c.member];
        for(unsigned j=0;j<128;++j)sink=fn(head0,head1);barrier();
        if(c.cold)flush_pair(a,b);else{sink=*(volatile uintptr_t *)a;sink=*(volatile uintptr_t *)b;barrier();}
        struct pg_sample start,end,delta;const char *error=snapshot(&perf,&start);if(error)return failure(error);
        if(ioctl(perf.fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP))return failure("group-enable");
        uint64_t ticks=fn(head0,head1);
        if(ioctl(perf.fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP))return failure("group-disable");
        if((error=snapshot(&perf,&end)) || (error=pg_delta(&start,&end,6,&delta)))return failure(error);
        if(sched_getcpu()!=pin || delta.values[1]<29 || delta.values[1]>1029)return failure("cpu-or-retired-count");
        printf("{\"type\":\"round\",\"epoch\":%u,\"trial\":%u,\"mask\":%u,\"swap\":%u,\"member\":\"%s\","
          "\"state\":\"%s\",\"ticks\":%"PRIu64",\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"metrics\":{",
          epoch,trial,c.mask,c.swap,names[c.member],c.cold?"cold":"hot",ticks,delta.enabled,delta.running);
        for(unsigned j=0;j<6;++j)printf("%s\"0x%"PRIx64"\":%"PRIu64,j?",":"",events[j],delta.values[j]);puts("}}");
        if(fflush(stdout))return failure("output-write");
    }
    if(!backing(&data,&after))return failure("final-backing");
    fputs("{\"type\":\"backing-final\",\"backing\":",stdout);rob_backing_json(stdout,&after);puts("}");
    for(unsigned j=0;j<6;++j)close(perf.fd[j]);
    for(unsigned m=0;m<2;++m)for(unsigned j=0;j<3;++j)munmap(codes[m][j],4096);
    munmap(data.reservation,data.reserved);return 0;
#endif
}
