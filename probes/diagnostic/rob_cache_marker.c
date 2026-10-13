/* SPDX-License-Identifier: Apache-2.0
 * Own transient cache footprint plus architectural marker; N0 qualification only.
 * Contract: docs/design/2026-10-13-rob-cache-marker.md. No PMU or global state writes.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#if defined(__linux__) && defined(__aarch64__)
#include <asm/hwcap.h>
#include <fcntl.h>
#include <sched.h>
#include <setjmp.h>
#include <signal.h>
#include <sys/auxv.h>
#include <sys/mman.h>
#endif
#define ONE UINT64_C(0x3ff0000000000000)
#define MARKER UINT64_C(0x12345678)
static int fail(const char*r){fprintf(stderr,"error[%s]\n",r);printf("{\"type\":\"failure\",\"metrics\":{},\"failure\":{\"reason\":\"%s\"}}\n",r);return 1;}
static const char*controls[]={"cal-hot","cal-cold","architect","architect","bypass","bypass","speculate","speculate"};
static const char*markers[]={"none","none","nop","load","nop","load","nop","load"};
static unsigned member(unsigned t,unsigned p){unsigned i=(t+p)%8;return(t/8)%2?7-i:i;}
static uint64_t train(unsigned i){return(i==4||i==5)?ONE:0;}
static uint64_t test(unsigned i){return i>=4?ONE:0;}
static unsigned build(uint32_t*w,unsigned k,unsigned load){unsigned n=0;w[n++]=0xaa1f03e9u;w[n++]=0x9e670000u;for(unsigned i=0;i<k;++i)w[n++]=0x1e61c000u;const uint32_t tail[]={0x9e66000cu,0xb400004cu,0x14000002u,load?0xf9400029u:0xd503201fu,0xd50330ffu,0x9e660000u,0xd53b442cu,0xf900004cu,0xf9000449u,0xd65f03c0u};for(unsigned i=0;i<10;++i)w[n++]=tail[i];assert(n<128);return n;}
static void schedule(unsigned t,unsigned p){unsigned i=member(t,p);printf("{\"type\":\"schedule\",\"trial\":%u,\"position\":%u,\"control\":\"%s\",\"marker\":\"%s\",\"train_bits\":%"PRIu64",\"test_bits\":%"PRIu64"}",t,p,controls[i],markers[i],train(i),test(i));}
static void config(unsigned k){printf("{\"type\":\"config\",\"version\":1,\"probe\":\"rob-cache-marker\",\"chain\":%u,\"groups\":0,\"trials\":32,\"windows\":256,\"training_calls\":64,\"clock\":\"cntvct_el0\",\"marker_word\":%"PRIu64",\"schedule_reverse_block_trials\":8}\n",k,MARKER);}
#if defined(__linux__) && defined(__aarch64__)
typedef uint64_t(*routine_t)(uint64_t,uintptr_t,uintptr_t);
static int page(int fd,uintptr_t v,uint64_t*out){return pread(fd,out,8,(off_t)(v/4096*8))==8?0:-1;}
static void clear_line(uint64_t*p){__asm__ volatile("dc civac,%0\ndsb sy\nisb"::"r"(p):"memory");}
struct timing{uint64_t ticks,word;};
/* The same single own load is timed in all eight cells; no ioctl inside this window. */
__attribute__((noinline)) static struct timing timed(uint64_t*p){uint64_t a,b,v;__asm__ volatile("isb\nmrs %0,cntvct_el0\nldr %2,[%3]\ndsb sy\nisb\nmrs %1,cntvct_el0":"=&r"(a),"=&r"(b),"=&r"(v):"r"(p):"memory");return(struct timing){b-a,v};}
static sigjmp_buf available;static void feature_signal(int signal){(void)signal;siglongjmp(available,1);}
/* Capability trap handling is confined to the explicit own-line preflight. */
static bool capability(uint64_t*p,uint64_t*freq,uint64_t*ctr){struct sigaction oldill,oldseg,sa={0};sa.sa_handler=feature_signal;sigemptyset(&sa.sa_mask);if(sigaction(SIGILL,&sa,&oldill))return false;if(sigaction(SIGSEGV,&sa,&oldseg)){sigaction(SIGILL,&oldill,NULL);return false;}volatile int ok=0;if(!sigsetjmp(available,1)){__asm__ volatile("mrs %0,cntfrq_el0\nmrs %1,ctr_el0":"=r"(*freq),"=r"(*ctr));clear_line(p);struct timing q=timed(p);ok=q.word==MARKER&&*freq>0;}sigaction(SIGILL,&oldill,NULL);sigaction(SIGSEGV,&oldseg,NULL);return ok;}
#endif
int main(int argc,char**argv){if(argc!=4||(strcmp(argv[1],"--plan")&&strcmp(argv[1],"--run"))||strcmp(argv[2],"--chain")||(strcmp(argv[3],"16")&&strcmp(argv[3],"32")))return fail("usage-cache-marker-plan-run-chain16-32");unsigned k=(unsigned)atoi(argv[3]);uint32_t words[2][128];unsigned len[2]={build(words[0],k,0),build(words[1],k,1)};config(k);for(unsigned load=0;load<2;++load){printf("{\"type\":\"program\",\"marker\":\"%s\",\"code_bytes\":%u,\"words\":[",load?"load":"nop",len[load]*4);for(unsigned j=0;j<len[load];++j)printf("%s%"PRIu32,j?",":"",words[load][j]);puts("]}");}if(!strcmp(argv[1],"--plan")){for(unsigned t=0;t<32;++t)for(unsigned p=0;p<8;++p){schedule(t,p);puts("");}return 0;}
#if !defined(__linux__) || !defined(__aarch64__)
return fail("requires-linux-aarch64");
#else
if(sysconf(_SC_PAGESIZE)!=4096)return fail("page-size");if(!(getauxval(AT_HWCAP)&HWCAP_SB))return fail("SB-unavailable");cpu_set_t cp;CPU_ZERO(&cp);CPU_SET(7,&cp);if(sched_setaffinity(0,sizeof(cp),&cp)||sched_getcpu()!=7)return fail("affinity");uint64_t fpcr;__asm__ volatile("mrs %0,fpcr":"=r"(fpcr));if(fpcr)return fail("FPCR-nonzero");void*code=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);uint64_t*data=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0),*output=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(code==MAP_FAILED||data==MAP_FAILED||output==MAP_FAILED)return fail("owned-mappings");data[0]=MARKER;output[0]=output[1]=0;memcpy(code,words[0],len[0]*4);uint64_t freq=0,ctr=0;if(!capability(data,&freq,&ctr))return fail("DC-timer-unavailable");int pm=open("/proc/self/pagemap",O_RDONLY|O_CLOEXEC);uint64_t before[3],after[3];uintptr_t addresses[3]={(uintptr_t)code,(uintptr_t)data,(uintptr_t)output};if(pm<0)return fail("pagemap");for(unsigned j=0;j<3;++j)if(page(pm,addresses[j],before+j))return fail("initial-pagemap");printf("{\"type\":\"runtime\",\"cpu\":7,\"fpcr\":0,\"hwcap_sb\":true,\"dc_timer_available\":true,\"cntfrq\":%"PRIu64",\"ctr_el0\":%"PRIu64",\"addresses\":[%"PRIuPTR",%"PRIuPTR",%"PRIuPTR"],\"pagemap_before\":[%"PRIu64",%"PRIu64",%"PRIu64"]}\n",freq,ctr,addresses[0],addresses[1],addresses[2],before[0],before[1],before[2]);routine_t routine=(routine_t)code;
for(unsigned t=0;t<32;++t)for(unsigned p=0;p<8;++p){unsigned i=member(t,p),load=i%2;uint64_t result=test(i),architectural=0,status=0;bool matches=true;if(i>=2){if(mprotect(code,4096,PROT_READ|PROT_WRITE))return fail("code-RW");memcpy(code,words[load],4*len[load]);__builtin___clear_cache(code,(char*)code+4*len[load]);if(mprotect(code,4096,PROT_READ|PROT_EXEC))return fail("code-RX");__asm__ volatile("msr fpsr,xzr");for(unsigned j=0;j<64;++j){if(routine(train(i),(uintptr_t)data,(uintptr_t)output)!=train(i)||output[0]||output[1]!=(load&&train(i)==0?MARKER:0))return fail("training-original-result");}matches=!memcmp(code,words[load],4*len[load]);if(!matches)return fail("code-drift");clear_line(data);result=routine(test(i),(uintptr_t)data,(uintptr_t)output);status=output[0];architectural=output[1];}else if(i==0){volatile uint64_t hot=data[0];(void)hot;__asm__ volatile("dsb sy\nisb":::"memory");}else clear_line(data);
struct timing q=timed(data);if(sched_getcpu()!=7||result!=test(i)||status||architectural!=(i==3?MARKER:0)||q.word!=MARKER)return fail("original-marker-timer-CPU");printf("{\"type\":\"round\",\"trial\":%u,\"position\":%u,\"control\":\"%s\",\"marker\":\"%s\",\"train_bits\":%"PRIu64",\"test_bits\":%"PRIu64",\"result_bits\":%"PRIu64",\"status_raw\":%"PRIu64",\"architectural_marker\":%"PRIu64",\"probe_word\":%"PRIu64",\"ticks\":%"PRIu64",\"code_matches_plan\":true,\"code_base\":%"PRIuPTR"}\n",t,p,controls[i],markers[i],train(i),test(i),result,status,architectural,q.word,q.ticks,(uintptr_t)code);if(fflush(stdout))return fail("output-write");}
for(unsigned j=0;j<3;++j)if(page(pm,addresses[j],after+j))return fail("final-pagemap");close(pm);printf("{\"type\":\"final\",\"pagemap_after\":[%"PRIu64",%"PRIu64",%"PRIu64"],\"fds_closed\":true}\n",after[0],after[1],after[2]);munmap(code,4096);munmap(data,4096);munmap(output,4096);return 0;
#endif
}
