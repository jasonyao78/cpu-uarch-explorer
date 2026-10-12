/* SPDX-License-Identifier: Apache-2.0
 * Straight-line self-only BPF reads; docs/design/2026-10-12-translation-self-read.md.
 * Offsets are bound to the target BTF digest by the launcher, never guessed.
 * This emitter has no kernel calls; actual UAPI layout is checked in the Linux CLI.
 */
#ifndef TRANSLATION_SELF_BPF_H
#define TRANSLATION_SELF_BPF_H
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
struct self_insn {uint8_t code,regs;int16_t off;int32_t imm;};
_Static_assert(sizeof(struct self_insn)==8,"BPF instruction wire size");
struct self_program {struct self_insn insn[128];size_t n,jumps[16],nj;};
static void self_emit(struct self_program *p,unsigned code,unsigned dst,unsigned src,int off,int imm){assert(p->n<128&&dst<=10&&src<=10);p->insn[p->n++]=(struct self_insn){(uint8_t)code,(uint8_t)(dst|(src<<4)),(int16_t)off,imm};}
static void self_stop_if(struct self_program *p,unsigned code,unsigned reg,int value){assert(p->nj<16);p->jumps[p->nj++]=p->n;self_emit(p,code,reg,0,0,value);}
/* r6 map survives helpers. Destination is an 8-byte map field, or zeroed 4-byte TGID field. */
static void self_read(struct self_program *p,unsigned stage,unsigned out,unsigned src,unsigned source_offset,unsigned bytes){
 self_emit(p,0x7a,6,0,0,(int)stage);self_emit(p,0xbf,1,6,0,0);self_emit(p,0x07,1,0,0,(int)out);self_emit(p,0xb7,2,0,0,(int)bytes);self_emit(p,0xbf,3,src,0,0);self_emit(p,0x07,3,0,0,(int)source_offset);self_emit(p,0x85,0,0,0,113);self_emit(p,0x7b,6,0,48,0);self_stop_if(p,0x55,0,0);
}
static struct self_program self_build(unsigned pid,unsigned index0,unsigned index1,int mapfd){
 assert(pid>0&&pid<0x80000000u&&index0<512&&index1<512&&index0!=index1&&mapfd>=0);
 struct self_program p={0};
 self_emit(&p,0x79,0,1,8,0);self_stop_if(&p,0x55,0,172); /* raw sys_enter arg1 */
 self_emit(&p,0x85,0,0,0,14);self_emit(&p,0x77,0,0,0,32);self_stop_if(&p,0x55,0,(int)pid);
 self_emit(&p,0x62,10,0,-64,0);self_emit(&p,0x18,1,1,0,mapfd);self_emit(&p,0,0,0,0,0);self_emit(&p,0xbf,2,10,0,0);self_emit(&p,0x07,2,0,0,-64);self_emit(&p,0x85,0,0,0,1);self_stop_if(&p,0x15,0,0);self_emit(&p,0xbf,6,0,0,0);
 self_emit(&p,0x79,0,6,56,0);self_emit(&p,0x07,0,0,0,1);self_emit(&p,0x7b,6,0,56,0);
 self_emit(&p,0x85,0,0,0,35);self_emit(&p,0xbf,7,0,0,0);
 self_read(&p,1,8,7,1588,4);self_emit(&p,0x61,0,6,8,0);self_stop_if(&p,0x55,0,(int)pid);
 self_read(&p,2,16,7,1440,8);self_emit(&p,0x79,7,6,16,0);self_stop_if(&p,0x15,7,0);
 self_read(&p,3,24,7,56,8);self_emit(&p,0x79,8,6,24,0);self_stop_if(&p,0x15,8,0);
 self_read(&p,4,32,8,8*index0,8);self_read(&p,5,40,8,8*index1,8);self_emit(&p,0x7a,6,0,0,6);
 size_t exit=p.n;self_emit(&p,0xb7,0,0,0,0);self_emit(&p,0x95,0,0,0,0);
 for(size_t j=0;j<p.nj;++j){size_t at=p.jumps[j];assert(exit>at&&exit-at-1<=32767);p.insn[at].off=(int16_t)(exit-at-1);}
 return p;
}
#endif
