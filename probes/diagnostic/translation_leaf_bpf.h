/* SPDX-License-Identifier: Apache-2.0
 * Owned PID+VA dominate the single ptep read; protocol translation-self-leaf.md.
 * Separate emitter preserves the immutable root-probe source/build history.
 */
#ifndef TRANSLATION_LEAF_BPF_H
#define TRANSLATION_LEAF_BPF_H
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
struct leaf_insn{uint8_t code,regs;int16_t off;int32_t imm;};
_Static_assert(sizeof(struct leaf_insn)==8,"BPF wire");
struct leaf_program{struct leaf_insn insn[96];size_t n,jumps[16],nj;};
static void leaf_emit(struct leaf_program *p,unsigned code,unsigned dst,unsigned src,int off,int imm){assert(p->n<96&&dst<=10&&src<=10);p->insn[p->n++]=(struct leaf_insn){(uint8_t)code,(uint8_t)(dst|(src<<4)),(int16_t)off,imm};}
static void leaf_exit_if(struct leaf_program*p,unsigned code,unsigned dst,unsigned src,int imm){assert(p->nj<16);p->jumps[p->nj++]=p->n;leaf_emit(p,code,dst,src,0,imm);}
static struct leaf_program leaf_build(unsigned pid,uint64_t va,int mapfd){
 assert(pid&&pid<0x80000000u&&va&&va<(UINT64_C(1)<<39)&&!(va%4096)&&mapfd>=0);struct leaf_program p={0};
 leaf_emit(&p,0xbf,9,1,0,0);leaf_emit(&p,0x85,0,0,0,14);leaf_emit(&p,0x77,0,0,0,32);leaf_exit_if(&p,0x55,0,0,(int)pid);leaf_emit(&p,0xbf,7,0,0,0);
 leaf_emit(&p,0x79,0,9,8,0);leaf_emit(&p,0x18,8,0,0,(int)(uint32_t)va);leaf_emit(&p,0,0,0,0,(int)(uint32_t)(va>>32));leaf_exit_if(&p,0x5d,0,8,0);
 leaf_emit(&p,0x62,10,0,-64,0);leaf_emit(&p,0x18,1,1,0,mapfd);leaf_emit(&p,0,0,0,0,0);leaf_emit(&p,0xbf,2,10,0,0);leaf_emit(&p,0x07,2,0,0,-64);leaf_emit(&p,0x85,0,0,0,1);leaf_exit_if(&p,0x15,0,0,0);leaf_emit(&p,0xbf,6,0,0,0);
 /* Incomplete first capture locks its failure, rather than being overwritten. */
 leaf_emit(&p,0x79,0,6,48,0);leaf_emit(&p,0x15,0,0,4,0);leaf_emit(&p,0x79,0,6,0,0);leaf_exit_if(&p,0x55,0,0,6);leaf_emit(&p,0x79,0,6,40,0);leaf_exit_if(&p,0x55,0,0,0);
 leaf_emit(&p,0x79,0,6,48,0);leaf_emit(&p,0x07,0,0,0,1);leaf_emit(&p,0x7b,6,0,48,0);leaf_emit(&p,0x7b,6,7,56,0);leaf_emit(&p,0x7a,6,0,0,1);
 leaf_emit(&p,0x79,0,9,8,0);leaf_emit(&p,0x7b,6,0,8,0);leaf_emit(&p,0x79,7,9,16,0);leaf_emit(&p,0x7b,6,7,16,0);leaf_exit_if(&p,0x15,7,0,0);leaf_emit(&p,0x79,0,9,24,0);leaf_emit(&p,0x7b,6,0,32,0);
 leaf_emit(&p,0xbf,1,6,0,0);leaf_emit(&p,0x07,1,0,0,24);leaf_emit(&p,0xb7,2,0,0,8);leaf_emit(&p,0xbf,3,7,0,0);leaf_emit(&p,0x85,0,0,0,113);leaf_emit(&p,0x7b,6,0,40,0);leaf_exit_if(&p,0x55,0,0,0);leaf_emit(&p,0x7a,6,0,0,6);
 size_t end=p.n;leaf_emit(&p,0xb7,0,0,0,0);leaf_emit(&p,0x95,0,0,0,0);for(size_t j=0;j<p.nj;++j){size_t at=p.jumps[j];assert(end>at);p.insn[at].off=(int16_t)(end-at-1);}return p;
}
#endif
