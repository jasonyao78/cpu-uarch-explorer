/* SPDX-License-Identifier: Apache-2.0
 * Standalone A64 effective-window probe v0.2, not a physical ROB counter.
 * Contracts/design: docs/design/2026-10-09-minimal-tlb-rob-probes.md.
 * Same-address independent/serial chase graphs; exact N filler per gap;
 * explicit loop alignment; exported code; strict GROUP+ID PMU windows.
 * OI-ROB-PROBE-20261009：显式4k/实际2MiB THP；每窗前后验收，禁止静默fallback。
 * Encoded pointer contrast: docs/design/2026-10-09-encoded-load-qualification.md.
 * Explicit mask0 retains the same EOR instructions; default code is unchanged.
 * Zero immediate contrast: docs/design/2026-10-11-rob-zero-value.md.
 * Append-only class mov0: same MOVZ family/destinations as movi, immediate 0/1.
 * Anchor dependency: docs/design/2026-10-11-rob-anchor-dependency.md.
 * Optional FMOV bridge is present in both controls; only ADD Rn differs.
 * Host supports export/tests only. Measurement requires Linux AArch64.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <assert.h>
#include <errno.h>
#include <getopt.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/mman.h>
#include "perf_group_read.h"
#include "rob_backing.h"
#ifdef __linux__
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#endif

#define NOP 0xd503201fu
#define RET 0xd65f03c0u
#define ADD(d,n,m) (0x8b000000u|((m)<<16)|((n)<<5)|(d))
#define EOR(d,n,m) (0xca000000u|((m)<<16)|((n)<<5)|(d))
#define MOV(d,m) (0xaa0003e0u|((m)<<16)|(d))
#define MOVZ(d,v) (0xd2800000u|(((v)&65535u)<<5)|(d))
#define MOVK(d,v,s) (0xf2800000u|(((v)&65535u)<<5)|(((s)/16)<<21)|(d))
#define FADD(d,n,m) (0x1e602800u|((m)<<16)|((n)<<5)|(d))
#define FSQRT(d,n) (0x1e61c000u|((n)<<5)|(d))
#define FMOV_TO_GPR(d,n) (0x9e660000u|((n)<<5)|(d))
#define FMOV(d,n) (0x9e670000u|((n)<<5)|(d))
#define LDR(t,n,o) (0xf9400000u|(((o)/8)<<10)|((n)<<5)|(t))
#define STR(t,n,o) (0xf9000000u|(((o)/8)<<10)|((n)<<5)|(t))
#define SUBS(d,n) (0xf1000400u|((n)<<5)|(d))
#define BNE(w) (0x54000001u|(((uint32_t)(w)&0x7ffffu)<<5))
static const char *classes[]={"nop","add","movi","movr","fadd","ldr","str","mov0"};
struct options {
    unsigned cls,n,its,rounds,mb,align,chain,seed; int pin;
    unsigned pmu_type; bool have_type,serial,asymmetric,paired,thp2m,collapse,have_xor,have_link;
    bool dependent_link;
    uint64_t pointer_xor;
    enum { MISS, SQRT, NONE } anchor;
    const char *dump,*rawlog;
    uint64_t events[PG_MAX_EVENTS]; size_t ne;
};
struct code { uint32_t *words; size_t pos,cap,loop,branch; unsigned fillers,anchors; };
static void emit(struct code *c,uint32_t w) { assert(c->pos<c->cap); c->words[c->pos++]=w; }
static void imm(struct code *c,unsigned r,uint64_t v) {
    emit(c,MOVZ(r,(unsigned)v));
    for(unsigned s=16;s<64;s+=16) emit(c,MOVK(r,(unsigned)(v>>s),s));
}
static void filler(struct code *c,unsigned cls,unsigned j,unsigned source) {
    unsigned rd=4+(j&7u);
    switch(cls) {
    case 0: emit(c,NOP); break;
    case 1: emit(c,ADD(rd,source,17)); break;
    case 2: emit(c,MOVZ(rd,1)); break;
    case 3: emit(c,MOV(rd,16)); break;
    case 4: emit(c,FADD(4+(j&3u),16,17)); break; // v0 anchor; v8..15 ABI preserved
    case 5: emit(c,LDR(rd,14,8*(j&7u))); break;
    case 6: emit(c,STR(16,14,8*(j&7u))); break;
    case 7: emit(c,MOVZ(rd,0)); break; // zero value control, not an allocation claim
    default: abort();
    }
    ++c->fillers;
}
// Runtime arguments x0=A, x1=B, x2=hot, x3=iterations. No baked VA.
static struct code build(uint32_t *buf,size_t cap,const struct options *o) {
    struct code c={.words=buf,.cap=cap};
    emit(&c,MOV(14,2));
    imm(&c,16,o->have_link?UINT64_C(0x3ff0000000000000):0x1111); imm(&c,17,0x2222);
    if(o->have_xor) imm(&c,12,o->pointer_xor); // x12 caller-saved; no filler writes it
    if(o->anchor==SQRT || o->cls==4 || o->have_link) {
        imm(&c,15,UINT64_C(0x3ff0000000000000)); // exact stable sqrt(1.0)
        emit(&c,FMOV(0,15)); emit(&c,FMOV(16,15)); emit(&c,FMOV(17,15));
    }
    while ((c.pos*4)%64!=o->align) emit(&c,NOP);
    c.loop=c.pos;
    for(unsigned side=0;side<2;++side) {
        if(o->anchor==MISS) {
            unsigned r=o->serial?0:side; emit(&c,LDR(r,r,0)); ++c.anchors;
            if(o->have_xor) emit(&c,EOR(r,r,12)); // decode before the next dereference
        }
        if(o->anchor==SQRT) for(unsigned j=0;j<o->chain;++j) { emit(&c,FSQRT(0,0)); ++c.anchors; }
        // Both modes carry the same bridge; X12 has identical stable 1.0 bits.
        if(o->have_link) emit(&c,FMOV_TO_GPR(12,0));
        if(!side || !o->asymmetric) for(unsigned j=0;j<o->n;++j)
            filler(&c,o->cls,j,o->have_link && o->dependent_link?12:16);
    }
    emit(&c,SUBS(3,3)); c.branch=c.pos;
    const int64_t displacement=(int64_t)c.loop-(int64_t)c.branch; // instruction words, NOT bytes
    assert(displacement>=-262144 && displacement<262144);
    emit(&c,BNE(displacement)); emit(&c,RET); return c;
}
static int failure(const char *why) {
    fprintf(stderr,"error[%s]: %s\n",why,strerror(errno));
    printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",why);
    return 1;
}
static uint64_t number(const char *s,uint64_t lo,uint64_t hi) {
    char *end=NULL; errno=0;
    if(!s || *s=='-' || !*s) { fprintf(stderr,"invalid number\n"); exit(2); }
    unsigned long long n=strtoull(s,&end,0);
    if(errno || !end || *end || n<lo || n>hi) { fprintf(stderr,"number out of range: %s\n",s); exit(2); }
    return (uint64_t)n;
}
static void usage(void) {
    fprintf(stderr,"rob_window_probe -t nop|add|movi|movr|fadd|ldr|str|mov0 -n 0..4096 "
        "[-a miss|fsqrt|none] [-i iterations] [-r rounds] [-m MiB] "
        "[--serial|--paired] [--asymmetric] [--align 0|16|32|48] [--chain 1..256] "
        "[--seed positive] [--pin cpu --pmu-type type] [-e raw_event] "
        "[--backing 4k|thp2m] [--collapse] [--pointer-xor uint64] [--anchor-link independent|dependent] [--write-asm file] [--rawlog file]\n");
    exit(2);
}
static uint64_t rng(uint64_t *state) {
    uint64_t x=*state; x^=x>>12; x^=x<<25; x^=x>>27; *state=x; return x*UINT64_C(2685821657736338717);
}
// π[2j],π[2j+1] are A_j,B_j. Independent and serial modes read same addresses.
// Every node is one 64-byte line; whole permutation is explicitly checked.
static bool init_chase_encoded(char *mem,size_t bytes,bool serial,unsigned seed,uint64_t mask) {
    size_t nodes=bytes/64; uint32_t *order=malloc(nodes*sizeof(*order));
    if(!order) return false;
    for(size_t i=0;i<nodes;++i) order[i]=(uint32_t)i;
    uint64_t state=seed;
    for(size_t i=nodes-1;i>0;--i) { size_t j=rng(&state)%(i+1); uint32_t t=order[i]; order[i]=order[j]; order[j]=t; }
    for(size_t i=0;i<nodes;++i) {
        size_t next=serial?(i+1)%nodes:(i+2)%nodes;
        *(uintptr_t *)(void *)(mem+64*order[i])=(uintptr_t)(mem+64*order[next]) ^ mask;
    }
    // Inspect all links against the defining permutation, including wrap-around.
    bool ok=true;
    for(size_t i=0;i<nodes;++i) {
        size_t next=serial?(i+1)%nodes:(i+2)%nodes;
        if((*(uintptr_t *)(void *)(mem+64*order[i]) ^ mask)!=(uintptr_t)(mem+64*order[next])) ok=false;
    }
    // Put heads in a separate global pair; do not overwrite node contents.
    extern uintptr_t chase_heads[2];
    chase_heads[0]=(uintptr_t)(mem+64*order[0]); chase_heads[1]=(uintptr_t)(mem+64*order[1]);
    free(order); return ok;
}
// Legacy call shape: no mask, no graph change.
static bool init_chase(char *mem,size_t bytes,bool serial,unsigned seed) {
    return init_chase_encoded(mem,bytes,serial,seed,0);
}
uintptr_t chase_heads[2];
static uint64_t now_ns(void) {
    struct timespec t; if(clock_gettime(CLOCK_MONOTONIC_RAW,&t)) abort();
    return (uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec;
}
#ifdef __linux__
struct perf { int fd[PG_MAX_EVENTS]; uint64_t ids[PG_MAX_EVENTS]; size_t n; };
static bool perf_setup(struct perf *p,const struct options *o) {
    memset(p,0,sizeof(*p));
    for(size_t i=0;i<o->ne;++i) {
        struct perf_event_attr a; memset(&a,0,sizeof(a));
        a.size=sizeof(a); a.type=o->pmu_type; a.config=o->events[i];
        a.disabled=i==0; a.pinned=i==0; a.exclude_kernel=1; a.exclude_hv=1;
        a.read_format=PERF_FORMAT_GROUP|PERF_FORMAT_TOTAL_TIME_ENABLED|PERF_FORMAT_TOTAL_TIME_RUNNING|PERF_FORMAT_ID;
        int fd=(int)syscall(SYS_perf_event_open,&a,0,-1,i?p->fd[0]:-1,0);
        if(fd<0) return false;
        p->fd[p->n++]=fd;
        if(ioctl(fd,PERF_EVENT_IOC_ID,&p->ids[i])) return false;
    }
    return true;
}
static const char *snapshot(struct perf *p,struct pg_sample *s) {
    uint64_t wire[3+2*PG_MAX_EVENTS]; ssize_t bytes=read(p->fd[0],wire,sizeof(wire));
    if(bytes<=0 || bytes%8) return "group-read-failed";
    return pg_decode(wire,(size_t)bytes/8,p->ids,p->n,s);
}
/* 验收恰好本次mapping；madvise仅是请求，smaps检查始终在PMU窗外。 */
static bool backing(char *mem,size_t bytes,bool thp2m,size_t pmd_bytes,struct rob_backing_info *out,
        enum rob_backing_status *status) {
    FILE *f=fopen("/proc/self/smaps","r");
    *status=rob_backing_inspect(f,(uintptr_t)mem,bytes,thp2m,pmd_bytes,out);
    if(f && fclose(f)) *status=ROB_BACKING_CLOSE_FAILED;
    if(*status!=ROB_BACKING_VERIFIED) { errno=EINVAL; return false; }
    return true;
}
/* 观测失败分层，不把THP缺口、VMA/parser问题或I/O失败混成未知零值。 */
static int backing_failure(const char *why,size_t bytes,bool thp2m,size_t pmd_bytes,
        enum rob_backing_status status,const struct rob_backing_info *info) {
    fprintf(stderr,"error[%s]: backing observation status=%d\n",why,(int)status);
    rob_backing_failure_json(stdout,why,bytes,thp2m,pmd_bytes,status,info);
    return 1;
}
#endif
int main(int argc,char **argv) {
    struct options o={.its=131072,.rounds=3,.mb=16,.chain=8,.seed=42,.pin=-1,.anchor=MISS,.events={0x11,0x08},.ne=2};
    bool have_class=false,have_n=false;
    static const struct option opts[]={
        {"write-asm",1,0,1},{"rawlog",1,0,2},{"pin",1,0,3},{"pmu-type",1,0,4},
        {"serial",0,0,5},{"asymmetric",0,0,6},{"align",1,0,7},{"chain",1,0,8},
        {"seed",1,0,9},{"paired",0,0,10},{"backing",1,0,11},{"collapse",0,0,12},{"pointer-xor",1,0,13},{"anchor-link",1,0,14},{0,0,0,0}};
    int ch;
    while((ch=getopt_long(argc,argv,"t:n:a:i:r:m:e:h",opts,NULL))!=-1) {
        switch(ch) {
        case 't': {
            bool found=false; for(unsigned k=0;k<sizeof(classes)/sizeof(classes[0]);++k) if(!strcmp(optarg,classes[k])) { o.cls=k; found=true; }
            if(!found) usage(); have_class=true; break; }
        case 'n': o.n=(unsigned)number(optarg,0,4096); have_n=true; break;
        case 'a': if(!strcmp(optarg,"miss")) o.anchor=MISS; else if(!strcmp(optarg,"fsqrt")) o.anchor=SQRT;
                  else if(!strcmp(optarg,"none")) o.anchor=NONE; else usage(); break;
        case 'i': o.its=(unsigned)number(optarg,1,100000000); break;
        case 'r': o.rounds=(unsigned)number(optarg,1,1000); break;
        case 'm': o.mb=(unsigned)number(optarg,1,512); break;
        case 'e': {
            if(o.ne==PG_MAX_EVENTS) usage(); uint64_t e=number(optarg,0,UINT32_MAX);
            for(size_t k=0;k<o.ne;++k) if(o.events[k]==e) usage(); o.events[o.ne++]=e; break; }
        case 1: o.dump=optarg; break; case 2: o.rawlog=optarg; break;
        case 3: o.pin=(int)number(optarg,0,1023); break;
        case 4: o.pmu_type=(unsigned)number(optarg,1,UINT32_MAX); o.have_type=true; break;
        case 5: o.serial=true; break; case 6: o.asymmetric=true; break;
        case 7: o.align=(unsigned)number(optarg,0,48); if(o.align%16) usage(); break;
        case 8: o.chain=(unsigned)number(optarg,1,256); break;
        case 9: o.seed=(unsigned)number(optarg,1,UINT32_MAX); break;
        case 10: o.paired=true; break;
        case 11:
            if(!strcmp(optarg,"4k")) o.thp2m=false;
            else if(!strcmp(optarg,"thp2m")) o.thp2m=true;
            else { errno=EINVAL; return failure("backing-unknown"); }
            break;
        case 12: o.collapse=true; break;
        case 13: o.pointer_xor=number(optarg,0,UINT64_MAX); o.have_xor=true; break;
        case 14:
            if(!strcmp(optarg,"independent")) o.dependent_link=false;
            else if(!strcmp(optarg,"dependent")) o.dependent_link=true;
            else usage();
            o.have_link=true; break;
        default: usage();
        }
    }
    if(!have_class || !have_n || optind!=argc || ((o.serial || o.paired) && o.anchor!=MISS) || (o.serial && o.paired)) usage();
    if(o.have_link && (o.cls!=1 || o.anchor==MISS || o.serial || o.paired || o.asymmetric || o.have_xor)) usage();
    if(o.have_xor && o.anchor!=MISS) { errno=EINVAL; return failure("pointer-xor-requires-miss"); }
    if(o.collapse && (!o.thp2m || o.anchor!=MISS)) { errno=EINVAL; return failure("collapse-requires-thp2m-miss"); }
    if(o.thp2m && o.anchor!=MISS) { errno=EINVAL; return failure("backing-thp2m-requires-miss"); }
    if(o.thp2m && o.mb%2) { errno=EINVAL; return failure("backing-thp2m-requires-2m-multiple"); }
    const size_t capacity=65536;
    uint32_t *buf=mmap(NULL,capacity,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(buf==MAP_FAILED) return failure("code-mmap");
    struct code c=build(buf,capacity/4,&o);
    uint32_t *serial_buf=NULL;
    if(o.paired) {
        serial_buf=mmap(NULL,capacity,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        if(serial_buf==MAP_FAILED) return failure("serial-code-mmap");
        struct options so=o; so.serial=true;
        struct code sc=build(serial_buf,capacity/4,&so);
        assert(sc.loop==c.loop && sc.pos==c.pos);
    }
    const char *anchor=o.anchor==MISS?"miss":o.anchor==SQRT?"fsqrt":"none";
    printf("{\"type\":\"config\",\"version\":2,\"class\":\"%s\",\"anchor\":\"%s\",\"n\":%u,"
           "\"iterations\":%u,\"rounds\":%u,\"serial\":%s,\"paired\":%s,\"asymmetric\":%s,\"chain\":%u,\"fsqrt_operand_bits\":\"0x3ff0000000000000\","
           "\"loop_offset\":%zu,\"loop_mod64\":%u,\"branch_offset\":%zu,\"loop_instructions\":%zu,"
           "\"fillers_per_iteration\":%u,\"anchors_per_iteration\":%u,\"code_bytes\":%zu,"
           "\"memory_bytes\":%zu,\"backing_requested\":\"%s\",\"chase_seed\":%u,\"pmu_type\":%u,\"exclude_kernel\":true,\"exclude_hv\":true,\"events\":[",
           classes[o.cls],anchor,o.n,o.its,o.rounds,o.serial?"true":"false",o.paired?"true":"false",o.asymmetric?"true":"false",o.chain,
           c.loop*4,o.align,c.branch*4,c.branch-c.loop+1,c.fillers,c.anchors,c.pos*4,
           o.anchor==MISS?((size_t)o.mb<<20):0,o.thp2m?"thp2m":"4k",o.seed,o.pmu_type);
    for(size_t k=0;k<o.ne;++k) printf("%s%"PRIu64,k?",":"",o.events[k]);
    fputs("]",stdout); if(o.collapse) fputs(",\"collapse_requested\":true",stdout);
    if(o.have_xor) printf(",\"pointer_xor_requested\":true,\"pointer_xor\":\"0x%016"PRIx64"\",\"decode_instructions_per_iteration\":2",o.pointer_xor);
    if(o.have_link) printf(",\"anchor_link\":\"%s\",\"bridges_per_iteration\":2",o.dependent_link?"dependent":"independent");
    puts("}");
    if(o.dump) {
        if(o.paired) usage();
        FILE *f=fopen(o.dump,"wb"); if(!f) return failure("code-export-open");
        bool ok=fwrite(buf,4,c.pos,f)==c.pos; if(fclose(f)) ok=false;
        return ok?0:failure("code-export-write");
    }
#if !defined(__linux__) || !defined(__aarch64__)
    (void)now_ns; (void)init_chase; (void)serial_buf;
    return failure("measurement-requires-linux-aarch64");
#else
    if(o.pin<0 || !o.have_type || sysconf(_SC_PAGESIZE)!=4096) return failure("measurement-requires-pin-type-4k");
    cpu_set_t affinity; CPU_ZERO(&affinity); CPU_SET(o.pin,&affinity);
    if(sched_setaffinity(0,sizeof(affinity),&affinity) || sched_getcpu()!=o.pin) return failure("affinity");
    uint64_t fpcr; __asm__ volatile("mrs %0, fpcr":"=r"(fpcr));
    if(fpcr) return failure("fpcr-nonzero"); // no silent rounding/FZ/trap inheritance
    char *mem=NULL; size_t bytes=(size_t)o.mb<<20,pmd_bytes=0;
    struct rob_backing_info initial={0}; enum rob_backing_status backing_status;
    if(o.anchor==MISS) {
        if(o.thp2m) {
            FILE *f=fopen("/sys/kernel/mm/transparent_hugepage/hpage_pmd_size","r");
            if(!f) return failure("backing-thp2m-pmd-size");
            bool ok=rob_backing_read_pmd(f,&pmd_bytes);
            if(fclose(f)) return failure("backing-thp2m-pmd-size");
            if(!ok) { errno=EINVAL; return failure("backing-thp2m-pmd-size"); }
        }
        mem=o.thp2m?rob_backing_map_2m(bytes)
            :mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        if(mem==MAP_FAILED) return failure("chase-mapping");
        /* 必须在init_chase写节点触页之前请求；失败绝不退回4k。 */
        if(madvise(mem,bytes,o.thp2m?MADV_HUGEPAGE:MADV_NOHUGEPAGE)) return failure("chase-backing-madvise");
        if(!(o.have_xor?init_chase_encoded(mem,bytes,o.serial,o.seed,o.pointer_xor):init_chase(mem,bytes,o.serial,o.seed))) return failure("chase-ring-validation");
        if(o.collapse) {
            struct rob_backing_info before={0}; enum rob_backing_status before_status;
            if(!backing(mem,bytes,true,pmd_bytes,&before,&before_status)
                    && before_status!=ROB_BACKING_COVERAGE_MISMATCH)
                return backing_failure("collapse-before-unobservable",bytes,true,pmd_bytes,before_status,&before);
            /* Linux6.1 UAPI:25；每映射只一次，仅进程自身区域，任何PMU窗之外。
             * docs/design/2026-10-09-local-collapse-qualification.md；绝不回退或重试。
             */
            errno=0; int rc=madvise(mem,bytes,25); int call_errno=rc?errno:0;
            bool ok=backing(mem,bytes,true,pmd_bytes,&initial,&backing_status);
            printf("{\"type\":\"backing-collapse\",\"memory_bytes\":%zu,\"pmd_bytes\":%zu,"
                   "\"return_code\":%d,\"errno\":%d,\"before_status\":\"%s\",\"after_status\":\"%s\",\"before\":",
                   bytes,pmd_bytes,rc,call_errno,rob_backing_status_name(before_status),rob_backing_status_name(backing_status));
            rob_backing_json(stdout,&before); fputs(",\"after\":",stdout);
            rob_backing_json(stdout,(ok || backing_status==ROB_BACKING_COVERAGE_MISMATCH)?&initial:NULL); puts("}");
            if(rc) { errno=call_errno; return failure("collapse-syscall"); }
            if(!ok) return backing_failure("collapse-after-not-thp2m",bytes,true,pmd_bytes,backing_status,&initial);
        }
        if(!o.collapse && !backing(mem,bytes,o.thp2m,pmd_bytes,&initial,&backing_status))
            return backing_failure(o.thp2m?"chase-backing-not-thp2m":"chase-backing-not-4k",
                                   bytes,o.thp2m,pmd_bytes,backing_status,&initial);
    }
    uint64_t hot[8]={1,2,3,4,5,6,7,8};
    __builtin___clear_cache((char *)buf,(char *)(buf+c.pos));
    if(mprotect(buf,capacity,PROT_READ|PROT_EXEC)) return failure("code-w-to-x");
    if(serial_buf) {
        __builtin___clear_cache((char *)serial_buf,(char *)(serial_buf+c.pos));
        if(mprotect(serial_buf,capacity,PROT_READ|PROT_EXEC)) return failure("serial-code-w-to-x");
    }
    struct perf p; if(!perf_setup(&p,&o)) return failure("perf-open-or-id");
    typedef void (*routine_t)(uintptr_t,uintptr_t,void *,uint64_t);
    routine_t routine=(routine_t)(void *)buf;
    const uint64_t accesses=2*(uint64_t)o.its, nodes=bytes/64;
    printf("{\"type\":\"runtime\",\"fpcr\":%"PRIu64",\"cpu\":%d,\"loop_address_mod64\":%zu,"
           "\"ring_nodes\":%"PRIu64",\"distinct_lines_per_call\":%"PRIu64",\"mapping_4k_verified\":%s,"
           "\"backing_verified\":%s,\"backing_page_bytes\":%zu,\"backing_info\":",
           fpcr,sched_getcpu(),((uintptr_t)buf+c.loop*4)%64,o.anchor==MISS?nodes:0,
           o.anchor==MISS?(accesses<nodes?accesses:nodes):0,o.anchor==MISS?(o.thp2m?"false":"true"):"null",
           mem?"true":"null",mem?(o.thp2m?pmd_bytes:4096):0);
    rob_backing_json(stdout,mem?&initial:NULL); fputs(",\"event_ids\":[",stdout);
    for(size_t k=0;k<p.n;++k) printf("%s%"PRIu64,k?",":"",p.ids[k]); puts("]}");
    FILE *raw=o.rawlog?fopen(o.rawlog,"w"):NULL;
    if(o.rawlog && !raw) return failure("rawlog-open");
    for(unsigned round=0;round<o.rounds;++round) {
      for(unsigned step=0;step<(o.paired?2u:1u);++step) {
        bool is_serial=o.paired?((round+step)%2!=0):o.serial;
        if(o.paired) {
            if(!(o.have_xor?init_chase_encoded(mem,bytes,is_serial,o.seed,o.pointer_xor):init_chase(mem,bytes,is_serial,o.seed))) return failure("paired-ring-validation");
            routine=(routine_t)(void *)(is_serial?serial_buf:buf);
        }
        routine(chase_heads[0],chase_heads[1],hot,o.its); // same explicit warmup each round
        struct rob_backing_info before={0},after={0};
        if(mem && !backing(mem,bytes,o.thp2m,pmd_bytes,&before,&backing_status))
            return backing_failure("round-backing-before",bytes,o.thp2m,pmd_bytes,backing_status,&before);
        struct pg_sample a,b,d; const char *err=snapshot(&p,&a); if(err) return failure(err);
        if(ioctl(p.fd[0],PERF_EVENT_IOC_ENABLE,PERF_IOC_FLAG_GROUP)) return failure("group-enable");
        uint64_t t0=now_ns(); routine(chase_heads[0],chase_heads[1],hot,o.its); uint64_t ns=now_ns()-t0;
        if(ioctl(p.fd[0],PERF_EVENT_IOC_DISABLE,PERF_IOC_FLAG_GROUP)) return failure("group-disable");
        if((err=snapshot(&p,&b)) || (err=pg_delta(&a,&b,p.n,&d))) return failure(err);
        /* post不通过时不输出该窗的metrics；pre/post也不能证明窗内从未短暂拆页。 */
        if(mem && !backing(mem,bytes,o.thp2m,pmd_bytes,&after,&backing_status))
            return backing_failure("round-backing-after",bytes,o.thp2m,pmd_bytes,backing_status,&after);
        if(sched_getcpu()!=o.pin || !ns || !d.values[0]) return failure("round-cpu-or-timing");
        for(unsigned dest=0;dest<(raw?2u:1u);++dest) {
            FILE *f=dest?raw:stdout;
            fprintf(f,"{\"type\":\"round\",\"round\":%u,\"serial\":%s,\"pair_step\":%u,\"ns\":%"PRIu64",\"enabled\":%"PRIu64",\"running\":%"PRIu64",\"metrics\":{",round,is_serial?"true":"false",step,ns,d.enabled,d.running);
            for(size_t k=0;k<p.n;++k) fprintf(f,"%s\"0x%"PRIx64"\":%"PRIu64,k?",":"",o.events[k],d.values[k]);
            fprintf(f,"},\"backing_verified\":%s,\"backing_before\":",mem?"true":"null");
            rob_backing_json(f,mem?&before:NULL); fputs(",\"backing_after\":",f);
            rob_backing_json(f,mem?&after:NULL); fputs("}\n",f);
            if(fflush(f)) return failure("output-write");
        }
    }
      }
    if(raw && fclose(raw)) return failure("rawlog-close");
    for(size_t k=0;k<p.n;++k) close(p.fd[k]);
    if(mem) munmap(mem,bytes);
    if(serial_buf) munmap(serial_buf,capacity);
    munmap(buf,capacity); return 0;
#endif
}
