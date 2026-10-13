/* SPDX-License-Identifier: Apache-2.0
 * Pure actual registration/capture gates shared by qualified observer and graph.
 * Contract docs/design/2026-10-13-translation-persistent-read.md; first error cannot advance.
 */
#ifndef TRANSLATION_PERSISTENT_GATE_H
#define TRANSLATION_PERSISTENT_GATE_H
#include <stdint.h>
#include <stdbool.h>
/* Called before every actual request update: failure state cannot be erased by the next node. */
unsigned persistent_registration_gate(const uint64_t previous[17],bool first){if(first){for(unsigned j=0;j<17;++j)if(previous[j])return 1;return 0;}return previous[0]!=13||previous[1]!=1||previous[2]!=1||previous[13]||previous[14]||previous[15]||!previous[16];}
/* Actual capture-loop gate, including same canonical PFN and two independent parent relations. */
unsigned persistent_capture_gate(unsigned pid,uint64_t va,uint64_t expected,uint64_t word,const uint64_t cb[2],const uint64_t ca[2],const uint64_t before[2],const uint64_t after[2],const uint64_t initial[17],const uint64_t negative[17],const uint64_t p[17]){uint64_t pf=(UINT64_C(1)<<55)-1,pa=(UINT64_C(1)<<48)-4096;for(unsigned j=0;j<16;++j)if(initial[j]||negative[j])return 1;if(initial[16]!=va||negative[16]!=va||p[16]!=va||word!=expected||(cb[0]&pf)==(cb[1]&pf))return 1;for(unsigned j=0;j<2;++j){if(before[j]>>63||before[j]&(UINT64_C(1)<<62)||before[j]&pf)return 1;if(!(cb[j]>>63)||!(ca[j]>>63)||!(after[j]>>63)||(cb[j]|ca[j]|after[j])&(UINT64_C(1)<<62)||!(cb[j]&pf)||(cb[j]&pf)!=(ca[j]&pf)||(cb[j]&pf)!=(after[j]&pf))return 1;}unsigned nonzero=0;for(unsigned j=0;j<16;++j)nonzero|=p[j]!=0;if(!nonzero)return 2;if(p[0]!=13||p[1]!=1||p[2]!=1||p[3]!=pid||p[4]!=va||p[13]||p[14]||p[15])return 1;const unsigned ptrs[]={5,6,7,9,10};for(unsigned j=0;j<5;++j)if(!p[ptrs[j]]||p[ptrs[j]]%8)return 1;if(p[6]%4096!=8*((va>>21)&511)||p[7]%4096!=8*((va>>12)&511)||(p[8]&3)!=3||(p[11]&3)!=3||(p[12]&3)!=3||!(p[8]&pa)||!(p[11]&pa)||(p[12]&pa)/4096!=(cb[0]&pf))return 1;uint64_t a=(p[6]&~UINT64_C(4095))-(p[11]&pa),b=(p[7]&~UINT64_C(4095))-(p[8]&pa);return !a||a!=b;}

#endif
