/* SPDX-License-Identifier: Apache-2.0
 * Pure A64 effective-window generator, copied verbatim from rob_window_probe.c.
 * Original logic: 310fe961; extraction contract:
 * docs/design/2026-10-11-rob-same-address-pair.md.
 * No runtime PMU or physical allocation claims; legacy code words remain exact.
 */
#ifndef CPU_UARCH_ROB_CODEGEN_H
#define CPU_UARCH_ROB_CODEGEN_H
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include "perf_group_read.h"
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

#endif
