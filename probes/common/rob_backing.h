/* SPDX-License-Identifier: Apache-2.0
 * ROB探针的精确映射验收与2MiB对齐分配；契约锚点：OI-ROB-PROBE-20261009。
 * THP hint不代表实际覆盖；AnonHugePages记录PMD映射，Kernel/MMUPageSize可仍为4k。
 * 来源：https://docs.kernel.org/filesystems/proc.html
 *       https://www.kernel.org/doc/html/v6.1/admin-guide/mm/transhuge.html
 */
#ifndef ROB_BACKING_H
#define ROB_BACKING_H
#include <ctype.h>
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

/* 本模式只接受实际2MiB PMD，运行时还须读取hpage_pmd_size确认。 */
#define ROB_PMD_BYTES ((size_t)2097152)
struct rob_backing_info {
    size_t kernel_kb,mmu_kb,huge_kb,rss_kb,swap_kb;
    bool nohuge;
};

/* 解析一个smaps的kB值；拒绝负数、溢出和错误单位，不改写失败输出。 */
static inline bool rob_backing_kb(const char *value,size_t *out) {
    while(isspace((unsigned char)*value)) ++value;
    if(!isdigit((unsigned char)*value)) return false;
    char *end; errno=0; uintmax_t n=strtoumax(value,&end,10);
    if(errno || n>SIZE_MAX) return false;
    while(isspace((unsigned char)*end)) ++end;
    if(strncmp(end,"kB",2)) return false;
    end+=2; while(isspace((unsigned char)*end)) ++end;
    if(*end) return false;
    *out=(size_t)n; return true;
}

/* 从调用者提供的smaps流读取恰好[start,start+bytes)的一个VMA。
 * 缺字段/重复字段/非精确边界/读取错误均返回false，不能跨VMA拼凑覆盖。
 */
static inline bool rob_backing_parse(FILE *f,uintptr_t start,size_t bytes,struct rob_backing_info *out) {
    if(!f || !out || !bytes || bytes>UINTPTR_MAX-start) return false;
    struct rob_backing_info info={0}; unsigned seen=0; bool within=false;
    const char *names[]={"KernelPageSize:","MMUPageSize:","AnonHugePages:","Rss:","Swap:"};
    size_t *values[]={&info.kernel_kb,&info.mmu_kb,&info.huge_kb,&info.rss_kb,&info.swap_kb};
    char line[512];
    while(fgets(line,sizeof(line),f)) {
        uintptr_t a,b; char permission;
        if(sscanf(line,"%"SCNxPTR"-%"SCNxPTR" %c",&a,&b,&permission)==3) {
            if(within) break;
            within=a==start && b==start+bytes;
            continue;
        }
        if(!within) continue;
        for(unsigned i=0;i<5;++i) {
            size_t len=strlen(names[i]);
            if(!strncmp(line,names[i],len)) {
                if((seen&(1u<<i)) || !rob_backing_kb(line+len,values[i])) return false;
                seen|=1u<<i; break;
            }
        }
        if(!strncmp(line,"VmFlags:",8)) {
            if(seen&32u) return false;
            seen|=32u;
            for(char *token=strtok(line+8," \t\r\n");token;token=strtok(NULL," \t\r\n"))
                if(!strcmp(token,"nh")) info.nohuge=true;
        }
    }
    if(ferror(f) || !within || seen!=63u) return false;
    *out=info; return true;
}

/* 验收已解析的整个映射；4k维持NOHUGEPAGE，THP必须全量PMD覆盖，禁止fallback。
 * Linux的Kernel/MMUPageSize报告fallback粒度，不能要求THP时必为2048kB。
 */
static inline bool rob_backing_matches(const struct rob_backing_info *info,size_t bytes,bool thp2m,size_t pmd_bytes) {
    if(!info || !bytes || bytes%1024 || info->rss_kb!=bytes/1024 || info->swap_kb) return false;
    if(!thp2m) return info->kernel_kb==4 && info->mmu_kb==4 && !info->huge_kb && info->nohuge;
    return pmd_bytes==ROB_PMD_BYTES && bytes%ROB_PMD_BYTES==0 && info->huge_kb==bytes/1024 && !info->nohuge
        && (info->kernel_kb==4 || info->kernel_kb==2048) && (info->mmu_kb==4 || info->mmu_kb==2048);
}

/* sysfs PMD大小必须明确为2MiB；hint、mTHP或其它PMD大小不能充当本模式。 */
static inline bool rob_backing_read_pmd(FILE *f,size_t *out) {
    uintmax_t n; char extra;
    if(!f || !out || fscanf(f,"%ju %c",&n,&extra)!=1 || ferror(f) || n!=ROB_PMD_BYTES) return false;
    *out=(size_t)n; return true;
}

/* 输出脱敏实际backing观察；无memory anchor时用null，不以零值冒充已核验。 */
static inline void rob_backing_json(FILE *f,const struct rob_backing_info *info) {
    if(!info) { fputs("null",f); return; }
    fprintf(f,"{\"kernel_page_kb\":%zu,\"mmu_page_kb\":%zu,\"anon_huge_kb\":%zu,"
              "\"rss_kb\":%zu,\"swap_kb\":%zu,\"no_huge\":%s}",
            info->kernel_kb,info->mmu_kb,info->huge_kb,info->rss_kb,info->swap_kb,info->nohuge?"true":"false");
}

/* 返回仅含bytes、2MiB对齐的可读写匿名映射；失败返回MAP_FAILED并设置errno。
 * 本函数不触页、不发THP请求，调用方必须在初始化节点之前madvise并验收实际backing。
 */
static inline void *rob_backing_map_2m(size_t bytes) {
    if(!bytes || bytes%ROB_PMD_BYTES || bytes>SIZE_MAX-ROB_PMD_BYTES) { errno=EINVAL; return MAP_FAILED; }
    size_t reserved=bytes+ROB_PMD_BYTES;
    char *base=mmap(NULL,reserved,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(base==MAP_FAILED) return MAP_FAILED;
    uintptr_t aligned=((uintptr_t)base+ROB_PMD_BYTES-1)&~(uintptr_t)(ROB_PMD_BYTES-1);
    size_t prefix=aligned-(uintptr_t)base,suffix=reserved-prefix-bytes;
    if(prefix && munmap(base,prefix)) { int err=errno; munmap(base,reserved); errno=err; return MAP_FAILED; }
    if(suffix && munmap((void *)(aligned+bytes),suffix)) {
        int err=errno; munmap((void *)aligned,bytes+suffix); errno=err; return MAP_FAILED;
    }
    return (void *)aligned;
}
#endif
