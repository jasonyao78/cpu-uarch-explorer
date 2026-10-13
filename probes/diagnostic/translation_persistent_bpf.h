/* SPDX-License-Identifier: Apache-2.0
 * BTF-bound own descriptor entry/return reads, no guessed PA-to-VA conversion.
 * Contract: docs/design/2026-10-12-translation-persistent-read.md.
 * 136-byte result/request layout is private; outputs are sanitized by the typed reader.
 */
#ifndef TRANSLATION_PERSISTENT_BPF_H
#define TRANSLATION_PERSISTENT_BPF_H
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
struct persistent_insn{uint8_t code,regs;int16_t off;int32_t imm;};
_Static_assert(sizeof(struct persistent_insn)==8,"BPF wire");
enum persistent_label{PERSISTENT_EXIT,PERSISTENT_FRESH,PERSISTENT_DUP};
struct persistent_program{struct persistent_insn insn[256];size_t n,jump[48],nj;unsigned label[48];size_t targets[3];};
static void ins(struct persistent_program*p,unsigned c,unsigned d,unsigned s,int o,int i){assert(p->n<256&&d<=10&&s<=10);p->insn[p->n++]=(struct persistent_insn){(uint8_t)c,(uint8_t)(d|(s<<4)),(int16_t)o,i};}
static void jump(struct persistent_program*p,unsigned c,unsigned d,unsigned s,int i,unsigned lab){assert(p->nj<48);p->jump[p->nj]=p->n;p->label[p->nj++]=lab;ins(p,c,d,s,0,i);}
static void persistent_read(struct persistent_program*p,unsigned stage,unsigned out,unsigned reg,unsigned offset){ins(p,0x7a,6,0,0,(int)stage);ins(p,0xbf,1,6,0,0);ins(p,0x07,1,0,0,(int)out);ins(p,0xb7,2,0,0,8);ins(p,0xbf,3,reg,0,0);ins(p,0x07,3,0,0,(int)offset);ins(p,0x85,0,0,0,113);ins(p,0x7b,6,0,104,0);jump(p,0x55,0,0,0,PERSISTENT_EXIT);}
static void finish(struct persistent_program*p){p->targets[PERSISTENT_EXIT]=p->n;ins(p,0xb7,0,0,0,0);ins(p,0x95,0,0,0,0);for(size_t j=0;j<p->nj;++j){size_t at=p->jump[j],to=p->targets[p->label[j]];assert(to>at&&to-at-1<=32767);p->insn[at].off=(int16_t)(to-at-1);}}
static struct persistent_program persistent_build(unsigned pid,int fd,int returning){
 assert(pid&&pid<0x80000000u&&fd>=0);struct persistent_program p={0};
 ins(&p,0xbf,9,1,0,0);ins(&p,0x85,0,0,0,14);ins(&p,0x77,0,0,0,32);jump(&p,0x55,0,0,(int)pid,PERSISTENT_EXIT);ins(&p,0xbf,8,0,0,0);
 ins(&p,0x62,10,0,-64,0);ins(&p,0x18,1,1,0,fd);ins(&p,0,0,0,0,0);ins(&p,0xbf,2,10,0,0);ins(&p,0x07,2,0,0,-64);ins(&p,0x85,0,0,0,1);jump(&p,0x15,0,0,0,PERSISTENT_EXIT);ins(&p,0xbf,6,0,0,0);
 /* Read only private request selection before the exact context-VA filter. */
 if(!returning){ins(&p,0x79,0,9,16,0);ins(&p,0x79,7,6,128,0);jump(&p,0x5d,0,7,0,PERSISTENT_EXIT);}
 if(returning){
  ins(&p,0x79,0,6,0,0);jump(&p,0x55,0,0,11,PERSISTENT_EXIT);ins(&p,0x79,0,6,8,0);jump(&p,0x55,0,0,1,PERSISTENT_EXIT);ins(&p,0x79,7,6,56,0);jump(&p,0x15,7,0,0,PERSISTENT_EXIT);ins(&p,0x7a,6,0,16,1);persistent_read(&p,12,96,7,0);ins(&p,0x7a,6,0,0,13);
 }else{
  ins(&p,0x79,0,6,8,0);jump(&p,0x15,0,0,0,PERSISTENT_FRESH);ins(&p,0x79,0,6,104,0);jump(&p,0x55,0,0,0,PERSISTENT_EXIT);ins(&p,0x79,0,6,0,0);jump(&p,0x15,0,0,11,PERSISTENT_DUP);jump(&p,0x15,0,0,13,PERSISTENT_DUP);jump(&p,0x05,0,0,0,PERSISTENT_EXIT);
  p.targets[PERSISTENT_DUP]=p.n;ins(&p,0x7a,6,0,0,99);ins(&p,0x7a,6,0,104,-17);jump(&p,0x05,0,0,0,PERSISTENT_EXIT);
  p.targets[PERSISTENT_FRESH]=p.n;ins(&p,0x7a,6,0,8,1);ins(&p,0x7b,6,8,24,0);ins(&p,0x79,0,9,16,0);ins(&p,0x7b,6,0,32,0);ins(&p,0x79,7,9,0,0);ins(&p,0x7b,6,7,40,0);
  persistent_read(&p,1,48,7,48);persistent_read(&p,2,56,7,88);ins(&p,0x79,7,6,48,0);jump(&p,0x15,7,0,0,PERSISTENT_EXIT);persistent_read(&p,3,64,7,0);
  ins(&p,0x85,0,0,0,35);ins(&p,0xbf,7,0,0,0);persistent_read(&p,4,72,7,1440);ins(&p,0x79,7,6,72,0);jump(&p,0x15,7,0,0,PERSISTENT_EXIT);persistent_read(&p,5,80,7,56);ins(&p,0x79,7,6,80,0);jump(&p,0x15,7,0,0,PERSISTENT_EXIT);/* Dynamic offset remains within this task's pgd page. All helper113 reads follow both filters. */
  ins(&p,0x79,0,6,128,0);ins(&p,0x77,0,0,0,30);ins(&p,0x57,0,0,0,511);ins(&p,0x67,0,0,0,3);
  ins(&p,0x7a,6,0,0,6);ins(&p,0xbf,3,7,0,0);ins(&p,0x0f,3,0,0,0);ins(&p,0xbf,1,6,0,0);ins(&p,0x07,1,0,0,88);ins(&p,0xb7,2,0,0,8);ins(&p,0x85,0,0,0,113);ins(&p,0x7b,6,0,104,0);jump(&p,0x55,0,0,0,PERSISTENT_EXIT);ins(&p,0x7a,6,0,0,11);
 }
 finish(&p);return p;
}
#endif
