/* SPDX-License-Identifier: Apache-2.0
 * Pure validation/arithmetic for owned long64 perf counters. No MRS here.
 * Contract docs/design/2026-10-13-pmu-own-direct-counter.md.
 */
#ifndef CPU_UARCH_PERF_USER_COUNTER_H
#define CPU_UARCH_PERF_USER_COUNTER_H
#include <stdint.h>
struct pu_metadata {uint32_t first,last,index,width;unsigned cap;uint64_t offset;};
static inline const char*pu_guard(int policy,const struct pu_metadata*m){
 if(policy!=1)return "user-access-disabled";
 if(!m||!m->cap)return "user-counter-capability";
 if(m->index<1||m->index>32)return "user-counter-index";
 if(m->width!=64)return "user-counter-width";
 if((m->first&1)||m->first!=m->last)return "user-counter-sequence";
 return 0;
}
static inline uint64_t pu_total(uint64_t offset,uint64_t hardware){return offset+hardware;}
static inline uint64_t pu_delta(uint64_t before,uint64_t after){return after-before;}
#endif
